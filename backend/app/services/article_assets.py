import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.image_generation import ImageGenerationAdapter, ImageGenerationRequest
from app.models.article_asset import ArticleAsset, ArticleAssetStatus, ArticleAssetType
from app.models.content_draft import ContentDraft
from app.models.content_task import ContentTask
from app.schemas.article_asset import (
    ArticleAssetGeneratePayload,
    ArticleAssetStatusUpdate,
    ArticleAssetUploadPayload,
)
from app.services.article_review_checkpoints import article_checkpoints_by_type
from app.services.content_drafts import list_content_drafts
from app.services.content_tasks import log_task_event

SLOT_RE = re.compile(r"\{\{(image|infographic):([a-zA-Z0-9_-]+)\}\}")


class MissingArticleDraftForAssets(ValueError):
    pass


class MissingArticleAssetSlots(ValueError):
    pass


def list_article_assets(db: Session, task_id: str) -> list[ArticleAsset]:
    stmt = (
        select(ArticleAsset)
        .where(ArticleAsset.task_id == task_id)
        .order_by(ArticleAsset.created_at.asc(), ArticleAsset.id.asc())
    )
    return list(db.scalars(stmt))


def get_article_asset(db: Session, asset_id: str) -> ArticleAsset | None:
    return db.get(ArticleAsset, asset_id)


def generate_article_assets(db: Session, task: ContentTask) -> list[ArticleAsset]:
    drafts = list_content_drafts(db, task.id)
    final_draft = _publishable_final_draft(drafts)
    if final_draft is None:
        raise MissingArticleDraftForAssets("Task has no final draft with image slots.")

    slots = _extract_asset_slots(final_draft.body)
    if not slots:
        raise MissingArticleAssetSlots(
            "Final draft has no asset placeholders like {{image:hero}} or {{infographic:comparison}}."
        )

    checkpoints = article_checkpoints_by_type(db, task.id)
    image_checkpoint = checkpoints.get("image_brief")
    existing_assets = {asset.slot: asset for asset in list_article_assets(db, task.id)}
    for slot in slots:
        asset = existing_assets.get(slot["slot"])
        if asset is None:
            asset = ArticleAsset(task_id=task.id, slot=slot["slot"])
        asset.asset_type = slot["asset_type"]
        if asset.status != ArticleAssetStatus.APPROVED.value:
            asset.status = ArticleAssetStatus.GENERATED.value
        asset.brief_json = _build_mock_asset_brief(task, final_draft, slot, image_checkpoint)
        asset.storage_uri = f"mock://article-assets/{task.id}/{slot['asset_type']}/{slot['name']}"
        asset.alt_text = _build_alt_text(task, slot)
        asset.caption = _build_caption(task, slot)
        asset.qa_json = _build_asset_qa(asset, slot)
        db.add(asset)

    log_task_event(
        db,
        task,
        event_type="article_assets_generated",
        from_status=task.status,
        to_status=task.status,
        step="article_assets",
        message=f"Article assets prepared: {len(slots)} slot(s)",
        metadata_json={
            "provider": "mock",
            "slots": [slot["token"] for slot in slots],
            "source_draft_id": final_draft.id,
        },
    )
    db.commit()
    return list_article_assets(db, task.id)


def update_article_asset_status(
    db: Session,
    task: ContentTask,
    asset: ArticleAsset,
    payload: ArticleAssetStatusUpdate,
) -> ArticleAsset:
    asset.status = payload.status.value
    qa_json = dict(asset.qa_json or {})
    qa_json["human_review"] = {
        "status": payload.status.value,
        "reviewer": payload.reviewer,
        "comment": payload.comment,
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    asset.qa_json = qa_json
    db.add(asset)
    log_task_event(
        db,
        task,
        event_type="article_asset_status_changed",
        from_status=task.status,
        to_status=task.status,
        step=payload.status.value,
        message=payload.comment,
        created_by=payload.reviewer,
        metadata_json={"asset_id": asset.id, "slot": asset.slot, "status": payload.status.value},
    )
    db.commit()
    db.refresh(asset)
    return asset


def attach_article_asset_upload(
    db: Session,
    task: ContentTask,
    asset: ArticleAsset,
    payload: ArticleAssetUploadPayload,
) -> ArticleAsset:
    asset.storage_uri = payload.storage_uri
    if payload.alt_text is not None:
        asset.alt_text = payload.alt_text
    if payload.caption is not None:
        asset.caption = payload.caption
    asset.status = ArticleAssetStatus.GENERATED.value
    qa_json = dict(asset.qa_json or {})
    qa_json["manual_upload"] = {
        "storage_uri": payload.storage_uri,
        "reviewer": payload.reviewer,
        "comment": payload.comment,
        "uploaded_at": datetime.now(UTC).isoformat(),
        "approval_reset": True,
    }
    qa_json["status"] = "needs_human_review"
    asset.qa_json = qa_json
    db.add(asset)
    log_task_event(
        db,
        task,
        event_type="article_asset_upload_attached",
        from_status=task.status,
        to_status=task.status,
        step="article_asset_upload",
        message=payload.comment,
        created_by=payload.reviewer,
        metadata_json={"asset_id": asset.id, "slot": asset.slot, "storage_uri": payload.storage_uri},
    )
    db.commit()
    db.refresh(asset)
    return asset


def generate_article_asset_image(
    db: Session,
    task: ContentTask,
    asset: ArticleAsset,
    payload: ArticleAssetGeneratePayload,
    adapter: ImageGenerationAdapter,
) -> ArticleAsset:
    prompt = payload.prompt_override or _asset_generation_prompt(task, asset)
    result = adapter.generate(
        ImageGenerationRequest(
            asset_id=asset.id,
            slot=asset.slot,
            asset_type=asset.asset_type,
            prompt=prompt,
            dimensions=(asset.brief_json or {}).get("dimensions"),
            metadata={"task_id": task.id, "brief_json": asset.brief_json},
        )
    )
    asset.storage_uri = result.storage_uri
    asset.status = ArticleAssetStatus.GENERATED.value
    qa_json = dict(asset.qa_json or {})
    qa_json["image_generation"] = {
        "provider": result.provider,
        "model": result.model,
        "prompt": result.prompt,
        "metadata": result.metadata or {},
        "comment": payload.comment,
        "reviewer": payload.reviewer,
        "generated_at": datetime.now(UTC).isoformat(),
        "approval_reset": True,
    }
    qa_json["status"] = "needs_human_review"
    asset.qa_json = qa_json
    db.add(asset)
    log_task_event(
        db,
        task,
        event_type="article_asset_image_generated",
        from_status=task.status,
        to_status=task.status,
        step="article_asset_image",
        message=payload.comment,
        created_by=payload.reviewer,
        metadata_json={
            "asset_id": asset.id,
            "slot": asset.slot,
            "provider": result.provider,
            "storage_uri": result.storage_uri[:240],
        },
    )
    db.commit()
    db.refresh(asset)
    return asset


def _extract_asset_slots(markdown: str) -> list[dict[str, str]]:
    slots = []
    seen = set()
    for match in SLOT_RE.finditer(markdown or ""):
        asset_type = match.group(1)
        name = match.group(2)
        slot_key = f"{asset_type}:{name}"
        if slot_key in seen:
            continue
        seen.add(slot_key)
        slots.append(
            {
                "token": match.group(0),
                "slot": slot_key,
                "asset_type": asset_type,
                "name": name,
            }
        )
    return slots


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


def _build_mock_asset_brief(
    task: ContentTask,
    draft: ContentDraft,
    slot: dict[str, str],
    image_checkpoint: Any | None,
) -> dict[str, Any]:
    dimensions = "16:9" if slot["asset_type"] == ArticleAssetType.IMAGE.value else "wide editorial"
    if slot["name"] in {"social_cover", "shorts_cover"}:
        dimensions = "9:16 safe area"
    return {
        "slot": slot["slot"],
        "token": slot["token"],
        "asset_type": slot["asset_type"],
        "slot_name": slot["name"],
        "source_draft_id": draft.id,
        "generation_provider": "mock",
        "article_topic": task.topic or task.product_id or task.id,
        "dimensions": dimensions,
        "operator_brief": image_checkpoint.body_markdown if image_checkpoint else None,
        "requirements": [
            "Use the article's buyer pain and use-case context.",
            "Keep factual text overlays in the layout layer, not inside generated bitmap art.",
            "Do not invent prices, ratings, certifications, warranty terms, or availability.",
            "Keep alt text and caption human-reviewable before export.",
        ],
    }


def _build_alt_text(task: ContentTask, slot: dict[str, str]) -> str:
    topic = task.topic or task.product_id or "Article"
    label = slot["name"].replace("_", " ")
    if slot["asset_type"] == ArticleAssetType.INFOGRAPHIC.value:
        return f"{topic}: infographic for {label}."
    return f"{topic}: product visual for {label}."


def _build_caption(task: ContentTask, slot: dict[str, str]) -> str:
    topic = task.topic or task.product_id or "article"
    label = slot["name"].replace("_", " ")
    if slot["asset_type"] == ArticleAssetType.INFOGRAPHIC.value:
        return f"Structured comparison block for {topic}: {label}."
    return f"Generated visual placeholder for {topic}: {label}."


def _build_asset_qa(asset: ArticleAsset, slot: dict[str, str]) -> dict[str, Any]:
    return {
        "status": "needs_human_review" if asset.status != ArticleAssetStatus.APPROVED.value else "approved",
        "checks": [
            "alt_text_present",
            "caption_present",
            "brief_present",
            "no_unverified_text_in_bitmap",
            "source_notes_required_for_exact_numbers",
        ],
        "slot_type": slot["asset_type"],
    }


def _asset_generation_prompt(task: ContentTask, asset: ArticleAsset) -> str:
    brief = asset.brief_json or {}
    requirements = "\n".join(f"- {item}" for item in brief.get("requirements", []))
    return "\n".join(
        [
            "Generate an ecommerce article visual asset.",
            f"Article/topic: {task.topic or task.product_id or task.id}",
            f"Slot: {asset.slot}",
            f"Asset type: {asset.asset_type}",
            f"Dimensions: {brief.get('dimensions') or 'article default'}",
            f"Alt text target: {asset.alt_text}",
            f"Caption target: {asset.caption}",
            "",
            "Requirements:",
            requirements or "- Keep the visual factual, clean and suitable for ecommerce content.",
            "- Do not invent logos, prices, ratings, certifications, warranty terms, or availability.",
            "- Exact tables, scores and source notes must be rendered as a controlled overlay outside the bitmap.",
        ]
    )
