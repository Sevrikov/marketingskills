import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article_asset import ArticleAsset
from app.models.content_draft import ContentDraft
from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask, ContentTaskStatus
from app.models.publish_package import PublishPackage
from app.services.article_assets import list_article_assets
from app.services.article_review_checkpoints import article_checkpoints_by_type
from app.services.content_drafts import list_content_drafts
from app.services.content_research import list_content_research_reports
from app.services.content_tasks import log_task_event


class TaskNotApprovedForExport(ValueError):
    pass


class MissingFinalDraft(ValueError):
    pass


def export_publish_package(db: Session, task: ContentTask) -> PublishPackage:
    if task.status != ContentTaskStatus.APPROVED.value:
        raise TaskNotApprovedForExport(
            f"Task must be approved before export, current status is {task.status}."
        )

    drafts = list_content_drafts(db, task.id)
    final_draft = _publishable_final_draft(drafts)
    if final_draft is None:
        raise MissingFinalDraft("Task has no final draft to export.")

    research_reports = list_content_research_reports(db, task.id)
    latest_research = research_reports[-1] if research_reports else None
    article_checkpoints = article_checkpoints_by_type(db, task.id)
    article_assets = list_article_assets(db, task.id)
    title = final_draft.title or task.topic or f"{task.task_type} package"
    slug = _slugify(title)
    package_json = _build_package_json(
        task,
        final_draft,
        latest_research,
        drafts,
        article_checkpoints,
        article_assets,
    )
    markdown = _build_package_markdown(task, final_draft, latest_research, package_json)

    package = PublishPackage(
        task_id=task.id,
        title=title,
        slug=slug,
        package_type="manual_export",
        status="ready",
        markdown=markdown,
        package_json=package_json,
    )
    db.add(package)
    db.flush()
    log_task_event(
        db,
        task,
        event_type="publish_package_exported",
        from_status=task.status,
        to_status=task.status,
        step="export_package",
        message=f"Publish package exported: {slug}",
        metadata_json={"package_id": package.id, "slug": slug},
    )
    db.commit()
    db.refresh(package)
    return package


def list_publish_packages(db: Session, task_id: str) -> list[PublishPackage]:
    stmt = (
        select(PublishPackage)
        .where(PublishPackage.task_id == task_id)
        .order_by(PublishPackage.created_at.asc(), PublishPackage.id.asc())
    )
    return list(db.scalars(stmt))


def get_publish_package(db: Session, package_id: str) -> PublishPackage | None:
    return db.get(PublishPackage, package_id)


def _latest_draft_by_kind(drafts: list[ContentDraft], kind: str) -> ContentDraft | None:
    matching = [draft for draft in drafts if draft.kind == kind]
    return matching[-1] if matching else None


def _publishable_final_draft(drafts: list[ContentDraft]) -> ContentDraft | None:
    final_drafts = [draft for draft in drafts if draft.kind == "final"]
    approved = [draft for draft in final_drafts if _draft_decision(draft) == "approved"]
    if approved:
        return approved[-1]
    not_rejected = [draft for draft in final_drafts if _draft_decision(draft) != "rejected"]
    return not_rejected[-1] if not_rejected else None


def _draft_decision(draft: ContentDraft) -> str | None:
    decision = (draft.metadata_json or {}).get("version_decision") or {}
    return decision.get("decision")


def _build_package_json(
    task: ContentTask,
    final_draft: ContentDraft,
    research_report: ContentResearchReport | None,
    drafts: list[ContentDraft],
    article_checkpoints: dict[str, Any],
    article_assets: list[ArticleAsset],
) -> dict[str, Any]:
    sources = research_report.sources_json if research_report else []
    return {
        "task": {
            "id": task.id,
            "task_type": task.task_type,
            "language": task.language,
            "product_id": task.product_id,
            "topic": task.topic,
            "status": task.status,
        },
        "content": {
            "title": final_draft.title,
            "markdown": final_draft.body,
            "draft_id": final_draft.id,
            "provider": final_draft.provider,
            "model": final_draft.model,
            "prompt_template_key": final_draft.prompt_template_key,
            "prompt_template_version": final_draft.prompt_template_version,
        },
        "research": {
            "title": research_report.title if research_report else None,
            "markdown": research_report.markdown if research_report else None,
            "provider": research_report.provider if research_report else None,
            "sources": sources,
        },
        "workflow": {
            "drafts": [
                {
                    "id": draft.id,
                    "kind": draft.kind,
                    "provider": draft.provider,
                    "model": draft.model,
                    "prompt_template_key": draft.prompt_template_key,
                    "prompt_template_version": draft.prompt_template_version,
                    "version_decision": (draft.metadata_json or {}).get("version_decision"),
                }
                for draft in drafts
            ],
            "draft_kinds": [draft.kind for draft in drafts],
            "skills_used": final_draft.metadata_json.get("skills_used", [])
            if final_draft.metadata_json
            else [],
        },
        "article_studio": {
            "checkpoints": {
                checkpoint_type: {
                    "id": checkpoint.id,
                    "status": checkpoint.status,
                    "reviewer": checkpoint.reviewer,
                    "body_markdown": checkpoint.body_markdown,
                    "metadata_json": checkpoint.metadata_json,
                    "updated_at": checkpoint.updated_at.isoformat(),
                }
                for checkpoint_type, checkpoint in article_checkpoints.items()
            },
            "asset_slots": _extract_asset_slots(final_draft.body),
            "assets": [_format_article_asset(asset) for asset in article_assets],
            "approved_assets": {
                asset.slot: _format_article_asset(asset)
                for asset in article_assets
                if asset.status == "approved"
            },
        },
    }


def _build_package_markdown(
    task: ContentTask,
    final_draft: ContentDraft,
    research_report: ContentResearchReport | None,
    package_json: dict[str, Any],
) -> str:
    sources = package_json["research"]["sources"]
    source_lines = "\n".join(
        f"- {source.get('title', 'Source')} ({source.get('url', 'no-url')})" for source in sources
    )
    research_markdown = research_report.markdown if research_report else "No research report."
    return "\n\n".join(
        [
            f"# Publish Package: {final_draft.title or task.topic or task.id}",
            "## Final Content",
            final_draft.body,
            "## Research",
            research_markdown,
            "## Sources",
            source_lines or "No sources.",
            "## Article Studio Checkpoints",
            _format_article_studio_markdown(package_json["article_studio"]["checkpoints"]),
            "## Article Assets",
            _format_article_assets_markdown(package_json["article_studio"]["assets"]),
            "## Metadata",
            (
                f"- Task ID: {task.id}\n"
                f"- Task type: {task.task_type}\n"
                f"- Language: {task.language}\n"
                f"- Prompt: {final_draft.prompt_template_key or 'n/a'}"
            ),
        ]
    )


def _format_article_studio_markdown(checkpoints: dict[str, dict[str, Any]]) -> str:
    if not checkpoints:
        return "No Article Studio checkpoints."
    sections = []
    for checkpoint_type, checkpoint in checkpoints.items():
        sections.append(
            "\n".join(
                [
                    f"### {checkpoint_type}",
                    f"- Status: {checkpoint['status']}",
                    f"- Reviewer: {checkpoint['reviewer'] or 'n/a'}",
                    "",
                    checkpoint["body_markdown"],
                ]
            )
        )
    return "\n\n".join(sections)


def _format_article_asset(asset: ArticleAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "slot": asset.slot,
        "asset_type": asset.asset_type,
        "status": asset.status,
        "storage_uri": asset.storage_uri,
        "alt_text": asset.alt_text,
        "caption": asset.caption,
        "brief_json": asset.brief_json,
        "qa_json": asset.qa_json,
    }


def _format_article_assets_markdown(assets: list[dict[str, Any]]) -> str:
    if not assets:
        return "No Article Studio assets."
    sections = []
    for asset in assets:
        sections.append(
            "\n".join(
                [
                    f"### {asset['slot']}",
                    f"- Type: {asset['asset_type']}",
                    f"- Status: {asset['status']}",
                    f"- Storage URI: {asset['storage_uri']}",
                    f"- Alt text: {asset['alt_text']}",
                    f"- Caption: {asset['caption']}",
                ]
            )
        )
    return "\n\n".join(sections)


def _extract_asset_slots(markdown: str) -> list[str]:
    return sorted(set(re.findall(r"\{\{(?:image|infographic):[a-zA-Z0-9_-]+\}\}", markdown)))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:120] or "publish-package"
