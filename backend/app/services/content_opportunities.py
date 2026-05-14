from dataclasses import asdict
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.research import ResearchAdapter, ResearchRequest
from app.adapters.source_provider import SourceProvider, SourceSearchRequest
from app.models.content_opportunity import ContentOpportunity
from app.models.content_task import ContentTaskType
from app.models.price_group import PriceGroup
from app.models.product import Product
from app.schemas.content_opportunity import ContentOpportunityDiscover
from app.schemas.content_task import ContentTaskCreate
from app.services.content_tasks import create_content_task


class OpportunityScopeNotFound(ValueError):
    pass


def discover_content_opportunities(
    db: Session,
    payload: ContentOpportunityDiscover,
    source_provider: SourceProvider,
    research_adapter: ResearchAdapter,
) -> tuple[str, str, str, list[ContentOpportunity]]:
    product = db.get(Product, payload.product_id) if payload.product_id else None
    group = db.get(PriceGroup, payload.price_group_id) if payload.price_group_id else None
    if payload.product_id and product is None:
        raise OpportunityScopeNotFound("Product not found.")
    if payload.price_group_id and group is None:
        raise OpportunityScopeNotFound("Price group not found.")

    query = _build_query(payload, product, group)
    source_result = source_provider.search(
        SourceSearchRequest(
            query=query,
            max_results=5,
            include_raw_content="markdown",
            search_depth="basic",
            topic="general",
            country=payload.market,
            metadata={"purpose": "content_opportunity_discovery"},
        )
    )
    research = research_adapter.run_research(
        ResearchRequest(
            query=query,
            mode="content_opportunity_discovery",
            product_id=product.id if product else None,
            metadata={
                "price_group_id": group.id if group else None,
                "brand": payload.brand or (product.brand if product else None) or (group.brand if group else None),
                "category": payload.category
                or (product.category if product else None)
                or (group.category if group else None),
                "source_provider": source_result.provider,
                "source_documents": [asdict(document) for document in source_result.documents],
            },
        )
    )

    ideas = _build_topic_ideas(
        payload=payload,
        product=product,
        group=group,
        query=query,
        sources=[asdict(document) for document in source_result.documents],
        research_summary=_summary(research.markdown),
    )
    created = []
    for idea in ideas[: payload.limit]:
        opportunity = ContentOpportunity(**idea)
        db.add(opportunity)
        created.append(opportunity)
    db.commit()
    for opportunity in created:
        db.refresh(opportunity)
    return query, source_result.provider, research.provider, created


def list_content_opportunities(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> list[ContentOpportunity]:
    stmt = select(ContentOpportunity).order_by(
        ContentOpportunity.priority_score.desc(),
        ContentOpportunity.created_at.desc(),
    )
    if status:
        stmt = stmt.where(ContentOpportunity.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_content_opportunity(db: Session, opportunity_id: str) -> ContentOpportunity | None:
    return db.get(ContentOpportunity, opportunity_id)


def create_task_from_opportunity(db: Session, opportunity: ContentOpportunity) -> tuple[str, str]:
    task = create_content_task(
        db,
        ContentTaskCreate(
            product_id=opportunity.product_id,
            task_type=ContentTaskType.SEO_ARTICLE,
            language=opportunity.language,
            topic=opportunity.title,
            created_by="content_opportunity_discovery",
        ),
    )
    opportunity.status = "task_created"
    opportunity.created_task_id = task.id
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return task.id, task.status


def _build_query(
    payload: ContentOpportunityDiscover,
    product: Product | None,
    group: PriceGroup | None,
) -> str:
    parts = [
        payload.query,
        product.title if product else None,
        product.brand if product else None,
        product.model if product else None,
        product.category if product else None,
        group.name if group else None,
        group.brand if group else None,
        group.category if group else None,
        group.keywords if group else None,
        payload.brand,
        payload.category,
        payload.market,
        "article topic ideas buyer questions comparisons problems SEO",
    ]
    return " ".join(part for part in parts if part)


def _build_topic_ideas(
    payload: ContentOpportunityDiscover,
    product: Product | None,
    group: PriceGroup | None,
    query: str,
    sources: list[dict[str, Any]],
    research_summary: str,
) -> list[dict[str, Any]]:
    subject = _subject(payload, product, group)
    scope_type = _scope_type(payload)
    product_ids = [product.id] if product else []
    brand = payload.brand or (product.brand if product else None) or (group.brand if group else None)
    category = payload.category or (product.category if product else None) or (group.category if group else None)
    templates = [
        (
            "commercial",
            92,
            f"Как выбрать {subject}: критерии, ошибки и проверка перед покупкой",
            [
                "Краткий ответ для покупателя",
                "Ключевые критерии выбора",
                "Ошибки и риски",
                "Что проверить в цене, наличии и характеристиках",
                "FAQ",
            ],
        ),
        (
            "comparison",
            88,
            f"{subject}: сравнение популярных вариантов и когда какой подходит",
            [
                "Кому нужен такой товар",
                "Сравнение сценариев использования",
                "Плюсы и ограничения",
                "Как читать характеристики",
                "Вывод для разных покупателей",
            ],
        ),
        (
            "problem",
            84,
            f"Проблемы покупателей {subject}: что учесть до заказа",
            [
                "Главная проблема покупателя",
                "Какие симптомы видны до покупки",
                "Как проверить совместимость",
                "Когда стоит искать альтернативу",
                "FAQ по рискам",
            ],
        ),
        (
            "faq",
            79,
            f"Частые вопросы о {subject}: цена, наличие, характеристики и доставка",
            [
                "Вопросы по цене",
                "Вопросы по наличию",
                "Вопросы по характеристикам",
                "Вопросы по гарантиям и совместимости",
                "Короткие ответы для сниппетов",
            ],
        ),
        (
            "informational",
            75,
            f"{subject}: что это, как работает и кому подходит",
            [
                "Что это за категория",
                "Как работает продукт",
                "Кому подходит",
                "Ограничения",
                "Как перейти к выбору модели",
            ],
        ),
        (
            "trend",
            72,
            f"Почему меняется цена на {subject} и когда выгоднее покупать",
            [
                "Что влияет на цену",
                "Как читать рыночные изменения",
                "Сезонность и наличие",
                "Когда цена выглядит подозрительно",
                "Как настроить ожидания покупателя",
            ],
        ),
    ]
    return [
        {
            "scope_type": scope_type,
            "product_id": product.id if product else None,
            "price_group_id": group.id if group else None,
            "brand": brand,
            "category": category,
            "language": payload.language,
            "market": payload.market,
            "title": title,
            "h1": title,
            "intent": intent,
            "priority_score": Decimal(score),
            "status": "new",
            "reason": (
                f"Тема закрывает intent '{intent}' по запросу: {query}. "
                "Подходит для deep research, AEO-блоков и внутренних ссылок на товары."
            ),
            "outline_json": outline,
            "recommended_product_ids_json": product_ids,
            "sources_json": _source_cards(sources),
            "research_summary": research_summary,
            "metadata_json": {
                "generator": "content-opportunity-discovery-v1",
                "query": query,
                "source_count": len(sources),
            },
        }
        for intent, score, title, outline in templates
    ]


def _scope_type(payload: ContentOpportunityDiscover) -> str:
    if payload.product_id:
        return "product"
    if payload.price_group_id:
        return "price_group"
    if payload.brand:
        return "brand"
    if payload.category:
        return "category"
    return "query"


def _subject(
    payload: ContentOpportunityDiscover,
    product: Product | None,
    group: PriceGroup | None,
) -> str:
    if product:
        return " ".join(part for part in [product.brand, product.title, product.model] if part)
    if group:
        return group.name
    return payload.brand or payload.category or payload.query or "товар"


def _source_cards(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": source.get("title"),
            "url": source.get("url"),
            "snippet": source.get("snippet"),
            "score": source.get("score"),
            "source_type": source.get("source_type"),
        }
        for source in sources[:5]
    ]


def _summary(markdown: str) -> str:
    plain = " ".join(markdown.replace("#", " ").split())
    return plain[:800]
