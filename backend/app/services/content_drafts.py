from typing import Any
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.content_task import ContentTask
from app.models.prompt_template import PromptTemplate
from app.schemas.content_draft import DraftVersionDecisionPayload
from app.services.content_tasks import log_task_event


def create_content_draft(
    db: Session,
    task: ContentTask,
    kind: str,
    body: str,
    provider: str,
    model: str,
    prompt_template: PromptTemplate | None = None,
    title: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> ContentDraft:
    draft = ContentDraft(
        task_id=task.id,
        kind=kind,
        title=title,
        body=body,
        provider=provider,
        model=model,
        prompt_template_key=prompt_template.key if prompt_template else None,
        prompt_template_version=prompt_template.version if prompt_template else None,
        metadata_json=metadata_json,
    )
    db.add(draft)
    db.flush()
    return draft


def list_content_drafts(db: Session, task_id: str) -> list[ContentDraft]:
    stmt = (
        select(ContentDraft)
        .where(ContentDraft.task_id == task_id)
        .order_by(ContentDraft.created_at.asc(), ContentDraft.id.asc())
    )
    return list(db.scalars(stmt))


def get_content_draft(db: Session, draft_id: str) -> ContentDraft | None:
    return db.get(ContentDraft, draft_id)


def set_draft_version_decision(
    db: Session,
    task: ContentTask,
    draft: ContentDraft,
    payload: DraftVersionDecisionPayload,
) -> ContentDraft:
    metadata_json = dict(draft.metadata_json or {})
    metadata_json["version_decision"] = {
        "decision": payload.decision.value,
        "reviewer": payload.reviewer,
        "comment": payload.comment,
        "decided_at": datetime.now(UTC).isoformat(),
    }
    draft.metadata_json = metadata_json
    db.add(draft)
    log_task_event(
        db,
        task,
        event_type="draft_version_decision",
        from_status=task.status,
        to_status=task.status,
        step=payload.decision.value,
        message=payload.comment,
        created_by=payload.reviewer,
        metadata_json={
            "draft_id": draft.id,
            "decision": payload.decision.value,
        },
    )
    db.commit()
    db.refresh(draft)
    return draft
