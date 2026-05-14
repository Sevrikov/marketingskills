from sqlalchemy.orm import Session

from app.models.content_task import ContentTask, ContentTaskStatus
from app.schemas.approval import ApprovalPayload
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.article_review_checkpoints import article_checkpoints_by_type
from app.services.content_tasks import (
    log_task_event,
    update_content_task_status,
)


class TaskNotReadyForApproval(ValueError):
    pass


def approve_task(db: Session, task: ContentTask, payload: ApprovalPayload) -> ContentTask:
    _ensure_waiting_approval(task)
    approved_task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.APPROVED,
            current_step="approved",
        ),
    )
    _log_approval_decision(db, approved_task, "approved", payload)
    db.commit()
    db.refresh(approved_task)
    return approved_task


def request_task_rewrite(db: Session, task: ContentTask, payload: ApprovalPayload) -> ContentTask:
    _ensure_waiting_approval(task)
    rewritten_task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.REWRITING,
            current_step="rewrite_requested",
        ),
    )
    _log_approval_decision(db, rewritten_task, "rewrite_requested", payload)
    db.commit()
    db.refresh(rewritten_task)
    return rewritten_task


def _ensure_waiting_approval(task: ContentTask) -> None:
    if task.status != ContentTaskStatus.WAITING_APPROVAL.value:
        raise TaskNotReadyForApproval(
            f"Task must be waiting_approval, current status is {task.status}."
        )


def _log_approval_decision(
    db: Session,
    task: ContentTask,
    decision: str,
    payload: ApprovalPayload,
) -> None:
    article_checkpoints = article_checkpoints_by_type(db, task.id)
    log_task_event(
        db,
        task,
        event_type="approval_decision",
        from_status=task.status,
        to_status=task.status,
        step=decision,
        message=payload.comment,
        created_by=payload.reviewer,
        metadata_json={
            "decision": decision,
            "draft_id": payload.draft_id,
            "article_checkpoints": {
                checkpoint_type: {
                    "id": checkpoint.id,
                    "status": checkpoint.status,
                    "reviewer": checkpoint.reviewer,
                }
                for checkpoint_type, checkpoint in article_checkpoints.items()
            },
        },
    )
