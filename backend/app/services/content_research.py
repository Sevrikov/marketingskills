from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.research import ResearchAdapter, ResearchReport, ResearchRequest, ResearchSource
from app.adapters.source_provider import (
    SourceDocument,
    SourceProvider,
    SourceSearchRequest,
    SourceSearchResult,
)
from app.config import get_settings
from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask
from app.models.product import Product
from app.services.content_tasks import log_task_event


def run_task_research(
    db: Session,
    task: ContentTask,
    research_adapter: ResearchAdapter,
    source_provider: SourceProvider | None = None,
) -> ContentResearchReport:
    product = db.get(Product, task.product_id) if task.product_id else None
    query = build_research_query(task, product)
    source_result = collect_source_corpus(task, query, source_provider)
    source_corpus_markdown = _format_source_corpus(source_result.documents)
    report = research_adapter.run_research(
        ResearchRequest(
            query=query,
            mode=_research_mode_for_task(task),
            product_id=task.product_id,
            task_id=task.id,
            metadata={
                "task_type": task.task_type,
                "language": task.language,
                "source_provider": source_result.provider,
                "source_corpus_markdown": source_corpus_markdown,
                "source_documents": [_source_document_dict(doc) for doc in source_result.documents],
                "source_usage": source_result.usage or {},
            },
        )
    )
    report = _merge_source_corpus(report, source_result, source_corpus_markdown)
    stored_report = create_research_report(db, task, report)
    log_task_event(
        db,
        task,
        event_type="research_completed",
        from_status=task.status,
        to_status=task.status,
        step="research_completed",
        message=report.title,
        metadata_json={
            "provider": report.provider,
            "external_id": report.external_id,
            "source_count": len(report.sources),
            "source_provider": source_result.provider,
            "source_provider_document_count": len(source_result.documents),
        },
    )
    return stored_report


def collect_source_corpus(
    task: ContentTask,
    query: str,
    source_provider: SourceProvider | None,
) -> SourceSearchResult:
    settings = get_settings()
    if not settings.source_collection_enabled or source_provider is None:
        return _empty_source_result(query)
    try:
        return source_provider.search(
            SourceSearchRequest(
                query=query,
                task_id=task.id,
                max_results=settings.source_collection_max_results,
                include_raw_content=settings.tavily_include_raw_content,
                search_depth=settings.tavily_search_depth,
                country=settings.tavily_country,
                metadata={"task_type": task.task_type, "language": task.language},
            )
        )
    except Exception as exc:
        if settings.source_collection_required:
            raise
        return SourceSearchResult(
            provider="source-collection-error",
            query=query,
            documents=[],
            raw={"error": str(exc)[:500]},
        )


def _empty_source_result(query: str) -> SourceSearchResult:
    return SourceSearchResult(provider="none", query=query, documents=[])


def _merge_source_corpus(
    report: ResearchReport,
    source_result: SourceSearchResult,
    source_corpus_markdown: str,
) -> ResearchReport:
    documents = source_result.documents
    source_map = {source.url: source for source in report.sources if source.url}
    merged_sources = list(report.sources)
    for document in documents:
        if document.url and document.url in source_map:
            continue
        merged_sources.append(
            ResearchSource(
                title=document.title,
                url=document.url,
                source_type=document.source_type,
                confidence=document.score,
            )
        )
    normalized = dict(report.normalized or {})
    normalized["source_corpus"] = {
        "provider": source_result.provider,
        "document_count": len(documents),
        "markdown_chars": len(source_corpus_markdown),
        "documents": [_source_document_dict(document) for document in documents],
        "usage": source_result.usage or {},
        "error": (source_result.raw or {}).get("error"),
    }
    return ResearchReport(
        title=report.title,
        markdown=report.markdown,
        sources=merged_sources,
        normalized=normalized,
        provider=report.provider,
        external_id=report.external_id,
    )


def _format_source_corpus(documents: list[SourceDocument]) -> str:
    if not documents:
        return ""
    settings = get_settings()
    remaining = max(settings.source_corpus_max_chars, 0)
    sections: list[str] = []
    for index, document in enumerate(documents, start=1):
        body = document.content or document.snippet or ""
        section = "\n".join(
            [
                f"## Source {index}: {document.title}",
                f"URL: {document.url or 'n/a'}",
                f"Score: {document.score if document.score is not None else 'n/a'}",
                "",
                body.strip(),
            ]
        ).strip()
        if not section:
            continue
        if len(section) > remaining:
            section = section[:remaining].rstrip()
        sections.append(section)
        remaining -= len(section)
        if remaining <= 0:
            break
    return "\n\n".join(sections)


def _source_document_dict(document: SourceDocument) -> dict:
    return {
        "title": document.title,
        "url": document.url,
        "snippet": document.snippet,
        "content_chars": len(document.content or ""),
        "score": document.score,
        "source_type": document.source_type,
        "raw": document.raw or {},
    }


def create_research_report(
    db: Session,
    task: ContentTask,
    report: ResearchReport,
) -> ContentResearchReport:
    stored_report = ContentResearchReport(
        task_id=task.id,
        title=report.title,
        markdown=report.markdown,
        provider=report.provider,
        external_id=report.external_id,
        sources_json=[asdict(source) for source in report.sources],
        normalized_json=report.normalized,
    )
    db.add(stored_report)
    db.flush()
    return stored_report


def list_content_research_reports(db: Session, task_id: str) -> list[ContentResearchReport]:
    stmt = (
        select(ContentResearchReport)
        .where(ContentResearchReport.task_id == task_id)
        .order_by(ContentResearchReport.created_at.asc(), ContentResearchReport.id.asc())
    )
    return list(db.scalars(stmt))


def get_latest_research_markdown(db: Session, task_id: str) -> str:
    stmt = (
        select(ContentResearchReport)
        .where(ContentResearchReport.task_id == task_id)
        .order_by(ContentResearchReport.created_at.desc(), ContentResearchReport.id.desc())
        .limit(1)
    )
    report = db.scalars(stmt).first()
    return report.markdown if report else "Research report is not available."


def build_research_query(task: ContentTask, product: Product | None) -> str:
    if product is not None:
        parts = [
            product.title,
            product.brand,
            product.model,
            product.category,
            product.raw_description,
        ]
        subject = " ".join(part for part in parts if part)
    else:
        subject = task.topic or task.task_type
    return " ".join(
        [
            subject,
            "customer pain problem solved buyer use cases trigger events objections alternatives proof points",
            "identify confirmed pains and separate facts from hypotheses for ecommerce content",
        ]
    )


def _research_mode_for_task(task: ContentTask) -> str:
    if task.task_type in {"product_card", "seo_article"}:
        return "marketing_deep_research"
    if task.task_type == "video_brief":
        return "video_marketing_research"
    return "standard"
