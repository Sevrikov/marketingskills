from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.content_research_report import ContentResearchReport
from app.models.product import Product
from app.models.product_content_profile import ProductContentProfile
from app.schemas.product_content_profile import ProductContentProfileUpdate


def get_product_content_profile(
    db: Session,
    product_id: str,
) -> ProductContentProfile | None:
    stmt = select(ProductContentProfile).where(ProductContentProfile.product_id == product_id)
    return db.scalars(stmt).first()


def generate_product_content_profile(
    db: Session,
    product: Product,
    source_task_id: str | None = None,
    source_draft_id: str | None = None,
    language: str = "ru",
) -> ProductContentProfile:
    latest_research = _latest_research_for_task(db, source_task_id)
    source_draft = db.get(ContentDraft, source_draft_id) if source_draft_id else None
    profile_data = build_product_content_profile_payload(
        product,
        language=language,
        research_markdown=latest_research.markdown if latest_research else None,
        draft_body=source_draft.body if source_draft else None,
    )
    profile = get_product_content_profile(db, product.id)
    if profile is None:
        profile = ProductContentProfile(product_id=product.id, **profile_data)
    else:
        for key, value in profile_data.items():
            setattr(profile, key, value)
    profile.status = "draft"
    profile.source_task_id = source_task_id
    profile.source_draft_id = source_draft_id
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_product_content_profile(
    db: Session,
    profile: ProductContentProfile,
    data: ProductContentProfileUpdate,
) -> ProductContentProfile:
    update_data = data.model_dump(exclude_unset=True, by_alias=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def approve_product_content_profile(
    db: Session,
    profile: ProductContentProfile,
) -> ProductContentProfile:
    profile.status = "approved"
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def build_product_content_profile_payload(
    product: Product,
    language: str = "ru",
    research_markdown: str | None = None,
    draft_body: str | None = None,
) -> dict[str, Any]:
    title = _display_title(product)
    specs = _specifications(product)
    short_description = _short_description(product, title, language)
    long_description = _long_description(
        product,
        title=title,
        specs=specs,
        language=language,
        research_markdown=research_markdown,
        draft_body=draft_body,
    )
    faq = _faq(product, title, specs, language)
    schema = _schema(product, title, short_description)
    return {
        "generated_title": title,
        "short_description": short_description,
        "long_description": long_description,
        "seo_title": _truncate(f"{title}: характеристики, цена и выбор", 255),
        "meta_description": _truncate(short_description, 320),
        "specifications_json": specs,
        "faq_json": faq,
        "schema_json": schema,
        "alt_texts_json": [
            _truncate(f"{title} на карточке товара", 160),
            _truncate(f"{title}: внешний вид и комплектация", 160),
            _truncate(f"{title}: ключевые характеристики для сравнения", 160),
        ],
        "metadata_json": {
            "generator": "structured-product-profile-v1",
            "language": language,
            "skills": [
                "ecommerce-product-normalization",
                "ecommerce-aeo-product-description",
            ],
            "uses_research": bool(research_markdown),
            "uses_source_draft": bool(draft_body),
            "missing_fields": specs["missing_fields"],
            "facts_policy": "Do not invent exact identifiers, specs, prices or availability.",
        },
    }


def _latest_research_for_task(
    db: Session,
    task_id: str | None,
) -> ContentResearchReport | None:
    if not task_id:
        return None
    stmt = (
        select(ContentResearchReport)
        .where(ContentResearchReport.task_id == task_id)
        .order_by(ContentResearchReport.created_at.desc(), ContentResearchReport.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _display_title(product: Product) -> str:
    parts = [product.brand, product.title, product.model]
    seen: set[str] = set()
    clean_parts = []
    for part in parts:
        clean = _clean(part)
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        clean_parts.append(clean)
    return " ".join(clean_parts) or product.title


def _specifications(product: Product) -> dict[str, Any]:
    known = {
        "title": _clean(product.title),
        "brand": _clean(product.brand),
        "model": _clean(product.model),
        "category": _clean(product.category),
        "sku": _clean(product.sku),
        "gtin": _clean(product.gtin),
        "mpn": _clean(product.mpn),
        "price": _decimal_to_string(product.price),
        "currency": _clean(product.currency),
        "availability": _clean(product.availability),
        "source_url": _clean(product.source_url),
    }
    missing_fields = [key for key, value in known.items() if value in (None, "")]
    facts = [
        {"name": key, "value": value}
        for key, value in known.items()
        if value not in (None, "")
    ]
    research_required = [
        field
        for field in ["brand", "model", "category", "gtin", "mpn", "availability"]
        if field in missing_fields
    ]
    return {
        "known": known,
        "facts": facts,
        "missing_fields": missing_fields,
        "research_required": research_required,
        "hypotheses": [],
    }


def _short_description(product: Product, title: str, language: str) -> str:
    category = product.category or "товар"
    base = f"{title} — {category} для покупателей, которым важно быстро сравнить цену, наличие и ключевые характеристики."
    if product.raw_description:
        return _truncate(f"{base} Исходное описание: {_clean(product.raw_description)}", 320)
    return _truncate(
        f"{base} Точные характеристики, идентификаторы и условия покупки нужно подтверждать по источникам.",
        320,
    )


def _long_description(
    product: Product,
    title: str,
    specs: dict[str, Any],
    language: str,
    research_markdown: str | None,
    draft_body: str | None,
) -> str:
    known_lines = [
        f"- {item['name']}: {item['value']}" for item in specs["facts"] if item["value"]
    ]
    missing = ", ".join(specs["missing_fields"]) or "нет"
    research_note = "Исследование подключено и может уточнять позиционирование карточки."
    if not research_markdown:
        research_note = "Исследование пока не подключено, поэтому спорные факты оставлены на проверку."
    draft_note = "Черновик контента использован как дополнительный источник формулировок."
    if not draft_body:
        draft_note = "Черновик контента не использовался."
    use_case = (
        f"{title} стоит показывать в карточке через сценарии сравнения: цена, наличие, "
        "совместимость с задачей покупателя и проверяемые характеристики."
    )
    return "\n\n".join(
        [
            f"# {title}",
            f"{title} — карточка товара с фокусом на проверяемые факты и быстрый выбор.",
            "## Краткий ответ",
            _short_description(product, title, language),
            "## Обзор",
            use_case,
            "## Польза для покупателя",
            "Покупатель сразу видит, что уже известно о товаре, а какие поля требуют проверки перед публикацией или рекламным запуском.",
            "## Ограничения",
            f"Нельзя придумывать отсутствующие характеристики. Поля на проверку: {missing}.",
            "## Характеристики",
            "\n".join(known_lines) if known_lines else "- нет подтвержденных структурированных полей",
            "## Заметки для сравнения",
            "Сравнивайте товар с конкурентами по цене, наличию, топ-позициям выдачи и подтвержденным спецификациям.",
            "## Источники и черновики",
            f"{research_note} {draft_note}",
        ]
    )


def _faq(
    product: Product,
    title: str,
    specs: dict[str, Any],
    language: str,
) -> list[dict[str, str]]:
    missing = ", ".join(specs["missing_fields"]) or "нет"
    return [
        {
            "question": f"Для кого подходит {title}?",
            "answer": (
                f"{title} подходит покупателям, которые сравнивают товары в категории "
                f"{product.category or 'e-commerce'} по цене, наличию и подтвержденным характеристикам."
            ),
        },
        {
            "question": f"Какие характеристики {title} уже известны?",
            "answer": "Известные поля сохранены в блоке specifications_json и не дополнены выдуманными данными.",
        },
        {
            "question": "Что нужно проверить перед публикацией карточки?",
            "answer": f"Перед публикацией нужно проверить поля: {missing}.",
        },
    ]


def _schema(product: Product, title: str, description: str) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "description": description,
    }
    if product.brand:
        schema["brand"] = {"@type": "Brand", "name": product.brand}
    if product.sku:
        schema["sku"] = product.sku
    if product.gtin:
        schema["gtin"] = product.gtin
    if product.mpn:
        schema["mpn"] = product.mpn
    if product.price is not None or product.availability:
        offer: dict[str, Any] = {"@type": "Offer"}
        if product.price is not None:
            offer["price"] = _decimal_to_string(product.price)
        if product.currency:
            offer["priceCurrency"] = product.currency
        if product.availability:
            offer["availability"] = _schema_availability(product.availability)
        schema["offers"] = offer
    return schema


def _schema_availability(value: str) -> str:
    normalized = value.strip().casefold()
    if normalized in {"in_stock", "instock", "available", "yes"}:
        return "https://schema.org/InStock"
    if normalized in {"out_of_stock", "outofstock", "unavailable", "no"}:
        return "https://schema.org/OutOfStock"
    if normalized in {"preorder", "pre_order"}:
        return "https://schema.org/PreOrder"
    return value


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _truncate(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
