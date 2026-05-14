import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask
from app.models.pain_profile import PainProfile, PainProfileStatus
from app.models.product import Product
from app.schemas.pain_profile import PainProfileApprove, PainProfileGenerate


def list_pain_profiles(
    db: Session,
    *,
    product_id: str | None = None,
    status: str | None = None,
    scope_type: str | None = None,
    limit: int = 100,
) -> list[PainProfile]:
    stmt = select(PainProfile).order_by(PainProfile.created_at.desc(), PainProfile.id.desc())
    if product_id:
        stmt = stmt.where(PainProfile.product_id == product_id)
    if status:
        stmt = stmt.where(PainProfile.status == status)
    if scope_type:
        stmt = stmt.where(PainProfile.scope_type == scope_type)
    return list(db.scalars(stmt.limit(limit)))


def get_pain_profile(db: Session, profile_id: str) -> PainProfile | None:
    return db.get(PainProfile, profile_id)


def get_approved_pain_profile_for_product(db: Session, product_id: str) -> PainProfile | None:
    stmt = (
        select(PainProfile)
        .where(
            PainProfile.product_id == product_id,
            PainProfile.status == PainProfileStatus.APPROVED.value,
        )
        .order_by(PainProfile.approved_at.desc(), PainProfile.updated_at.desc(), PainProfile.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def generate_pain_profile(
    db: Session,
    payload: PainProfileGenerate,
    *,
    product: Product | None = None,
    source_task: ContentTask | None = None,
    source_research_report: ContentResearchReport | None = None,
) -> PainProfile:
    resolved_product = product or _product_from_task(db, source_task)
    resolved_research = source_research_report or _latest_research_for_task(db, source_task)
    profile_json = _build_profile_json(
        payload,
        product=resolved_product,
        source_task=source_task,
        source_research_report=resolved_research,
    )
    profile = PainProfile(
        scope_type=payload.scope_type,
        scope_id=payload.scope_id or (resolved_product.id if resolved_product else None),
        product_id=resolved_product.id if resolved_product else payload.product_id,
        status=PainProfileStatus.DRAFT.value,
        primary_pain_summary=profile_json["primary_pain"]["summary"],
        confidence=profile_json["primary_pain"]["confidence"],
        profile_json=profile_json,
        source_task_id=source_task.id if source_task else payload.source_task_id,
        source_research_report_id=resolved_research.id if resolved_research else None,
        metadata_json={
            "generator": "deterministic-pain-profile-mvp",
            "language": payload.language,
            "requires_human_review": True,
        },
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def approve_pain_profile(
    db: Session,
    profile: PainProfile,
    payload: PainProfileApprove,
) -> PainProfile:
    profile.status = PainProfileStatus.APPROVED.value
    profile.approved_by = payload.reviewer
    profile.approved_at = datetime.now(UTC)
    metadata_json = dict(profile.metadata_json or {})
    metadata_json["approval"] = {
        "reviewer": payload.reviewer,
        "comment": payload.comment,
        "approved_at": profile.approved_at.isoformat(),
    }
    profile.metadata_json = metadata_json
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def pain_profile_prompt_context(profile: PainProfile | None) -> str:
    if profile is None:
        return (
            "No approved pain_profile is available yet. Treat buyer pain as a hypothesis and "
            "avoid aggressive or unsupported pain claims."
        )
    return json.dumps(profile.profile_json, ensure_ascii=False, indent=2)


def _product_from_task(db: Session, task: ContentTask | None) -> Product | None:
    if task is None or not task.product_id:
        return None
    return db.get(Product, task.product_id)


def _latest_research_for_task(
    db: Session,
    task: ContentTask | None,
) -> ContentResearchReport | None:
    if task is None:
        return None
    stmt = (
        select(ContentResearchReport)
        .where(ContentResearchReport.task_id == task.id)
        .order_by(ContentResearchReport.created_at.desc(), ContentResearchReport.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _build_profile_json(
    payload: PainProfileGenerate,
    *,
    product: Product | None,
    source_task: ContentTask | None,
    source_research_report: ContentResearchReport | None,
) -> dict[str, Any]:
    subject = _subject(product, source_task, payload)
    category = product.category if product and product.category else None
    sources = _sources(product, source_research_report)
    source_ids = [source["id"] for source in sources[:3]]
    confidence = "medium" if source_research_report or (product and product.raw_description) else "low"
    primary_summary = _primary_pain_summary(product, subject)
    buyer_words = _buyer_words(product, subject)
    proof_feature = _proof_feature(product)

    return {
        "schema_version": "1.0",
        "scope": {
            "type": payload.scope_type,
            "id": payload.scope_id or (product.id if product else None),
            "title": subject,
            "category": category,
            "snapshot_date": datetime.now(UTC).date().isoformat(),
        },
        "primary_pain": {
            "summary": primary_summary,
            "buyer_words": buyer_words,
            "severity": "medium",
            "confidence": confidence,
            "source_ids": source_ids,
        },
        "secondary_pains": [
            {
                "summary": "Покупателю нужно быстро понять, подходит ли товар под его сценарий, бюджет и ограничения.",
                "buyer_words": [
                    "подойдет ли мне",
                    "чем отличается от аналогов",
                    "на что смотреть перед покупкой",
                ],
                "confidence": "medium",
                "source_ids": source_ids,
            }
        ],
        "use_contexts": [
            {
                "context": _use_context(product),
                "pain_expression": "Без понятного выбора покупатель рискует купить товар, который не закрывает реальный сценарий.",
                "product_relevance": _product_relevance(product),
                "source_ids": source_ids,
            }
        ],
        "trigger_events": [
            {
                "event": "Покупателю нужен товар под конкретную задачу или замену менее удобного решения.",
                "message_angle": "Начинать материал с практического сценария и затем связывать характеристики с доказательствами.",
                "source_ids": source_ids,
            }
        ],
        "proof_map": [
            {
                "pain": primary_summary,
                "product_feature": proof_feature,
                "proof_type": "spec",
                "evidence": _proof_evidence(product),
                "source_ids": source_ids,
            }
        ],
        "objections": [
            {
                "objection": "Покупатель может сомневаться, хватит ли характеристик для его сценария.",
                "response": "Показывать только подтвержденные характеристики, ограничения и сценарии применения.",
                "source_ids": source_ids,
            },
            {
                "objection": "Покупатель может сравнивать с более дешевыми аналогами.",
                "response": "Сравнивать по задаче, комплектации, совместимости, наличию и цене без неподтвержденных обещаний.",
                "source_ids": source_ids,
            },
        ],
        "content_guidance": {
            "description_angle": "Начать с задачи покупателя, затем показать характеристики как доказательство решения.",
            "article_angle": "Строить статью как buyer guide: сценарий, критерии выбора, ошибки, доказательства, FAQ.",
            "infographic_angle": "Визуализировать цепочку pain -> feature -> evidence и сравнение с альтернативами.",
            "video_hook": "Показать ситуацию выбора или проблему в первые секунды, затем перейти к проверяемым фактам.",
            "shorts_hook": "Один практический вопрос покупателя и один доказанный критерий выбора.",
            "viber_alert_angle": "Коротко сообщать только значимый тренд или пользу, без неподтвержденных обещаний.",
        },
        "do_not_claim": [
            "Не обещать экономию денег, автономность, надежность, безопасность или результат без источника.",
            "Не выдумывать отзывы, рейтинги, сертификаты, гарантию, наличие или сравнения.",
            "Не усиливать боль страхом, если она не подтверждена источниками или надежной внутренней логикой.",
        ],
        "sources": sources,
        "missing_or_risky_data": _missing_or_risky_data(product, source_research_report),
    }


def _subject(
    product: Product | None,
    source_task: ContentTask | None,
    payload: PainProfileGenerate,
) -> str:
    if product is not None:
        return product.title
    if source_task is not None and source_task.topic:
        return source_task.topic
    return payload.scope_id or "Untitled pain profile scope"


def _primary_pain_summary(product: Product | None, subject: str) -> str:
    category = (product.category or "").lower() if product else ""
    raw = (product.raw_description or "").lower() if product else ""
    if any(term in f"{category} {raw}" for term in ["solar", "солнеч", "заряд"]):
        return "Покупателю нужна автономная зарядка для устройств там, где обычная розетка недоступна или неудобна."
    return f"Покупателю нужно понять, какую практическую задачу закрывает {subject}, и не ошибиться при выборе."


def _buyer_words(product: Product | None, subject: str) -> list[str]:
    words = [
        "что выбрать",
        "подойдет ли для моей задачи",
        "чем отличается от аналогов",
        "какие характеристики важны",
    ]
    if product and product.category:
        words.insert(0, f"как выбрать {product.category}")
    else:
        words.insert(0, f"как выбрать {subject}")
    return words


def _use_context(product: Product | None) -> str:
    category = (product.category or "").lower() if product else ""
    if any(term in category for term in ["солнеч", "solar", "заряд"]):
        return "Travel / outdoor / backup charging"
    return "Product comparison before purchase"


def _product_relevance(product: Product | None) -> str:
    if product and product.raw_description:
        return "Связать заявленные характеристики и описание товара с конкретным сценарием использования."
    return "Использовать только подтвержденные данные товара и явно отметить недостающие характеристики."


def _proof_feature(product: Product | None) -> str:
    parts = []
    if product and product.brand:
        parts.append(f"brand: {product.brand}")
    if product and product.model:
        parts.append(f"model: {product.model}")
    if product and product.category:
        parts.append(f"category: {product.category}")
    if product and product.price is not None:
        parts.append(f"price: {_decimal_to_str(product.price)} {product.currency or ''}".strip())
    return "; ".join(parts) or "Confirmed product data"


def _proof_evidence(product: Product | None) -> str:
    if product and product.raw_description:
        return product.raw_description[:500]
    return "Only structured product fields are available; additional research is required before strong claims."


def _sources(
    product: Product | None,
    source_research_report: ContentResearchReport | None,
) -> list[dict[str, Any]]:
    sources = [
        {
            "id": "internal-product-data",
            "title": product.title if product else "Internal product/task data",
            "url": product.source_url if product else None,
            "captured_at": datetime.now(UTC).isoformat(),
            "source_type": "internal",
        }
    ]
    if source_research_report is None:
        return sources
    for index, source in enumerate(source_research_report.sources_json or [], start=1):
        sources.append(
            {
                "id": f"s{index}",
                "title": source.get("title") or f"Research source {index}",
                "url": source.get("url"),
                "captured_at": source_research_report.created_at.isoformat(),
                "source_type": source.get("source_type") or "research",
            }
        )
    return sources


def _missing_or_risky_data(
    product: Product | None,
    source_research_report: ContentResearchReport | None,
) -> list[dict[str, str]]:
    missing = []
    if source_research_report is None:
        missing.append(
            {
                "field": "external pain evidence",
                "reason": "No research report was linked to this pain_profile.",
                "action": "run_deep_research_or_manual_review",
            }
        )
    if product is not None and not product.raw_description:
        missing.append(
            {
                "field": "product specifications",
                "reason": "Product raw_description is empty.",
                "action": "add_specs_before_strong_claims",
            }
        )
    return missing


def _decimal_to_str(value: Decimal) -> str:
    return format(value.normalize(), "f")
