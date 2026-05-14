from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article_review_checkpoint import ArticleCheckpointType
from app.models.article_review_checkpoint import ArticleReviewCheckpoint
from app.models.content_task import ContentTask
from app.schemas.article_review_checkpoint import ArticleCheckpointUpsert
from app.services.content_tasks import log_task_event


def list_article_checkpoints(db: Session, task_id: str) -> list[ArticleReviewCheckpoint]:
    stmt = (
        select(ArticleReviewCheckpoint)
        .where(ArticleReviewCheckpoint.task_id == task_id)
        .order_by(
            ArticleReviewCheckpoint.created_at.asc(),
            ArticleReviewCheckpoint.id.asc(),
        )
    )
    return list(db.scalars(stmt))


def article_checkpoints_by_type(
    db: Session,
    task_id: str,
) -> dict[str, ArticleReviewCheckpoint]:
    return {checkpoint.checkpoint_type: checkpoint for checkpoint in list_article_checkpoints(db, task_id)}


def format_article_checkpoint_context(db: Session, task_id: str) -> str:
    checkpoints = list_article_checkpoints(db, task_id)
    if not checkpoints:
        return ""
    sections = []
    for checkpoint in checkpoints:
        sections.append(
            "\n".join(
                [
                    f"CHECKPOINT: {checkpoint.checkpoint_type}",
                    f"Status: {checkpoint.status}",
                    f"Reviewer: {checkpoint.reviewer or 'n/a'}",
                    "",
                    checkpoint.body_markdown,
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def get_article_checkpoint(
    db: Session,
    task_id: str,
    checkpoint_type: ArticleCheckpointType,
) -> ArticleReviewCheckpoint | None:
    stmt = select(ArticleReviewCheckpoint).where(
        ArticleReviewCheckpoint.task_id == task_id,
        ArticleReviewCheckpoint.checkpoint_type == checkpoint_type.value,
    )
    return db.scalars(stmt).first()


def upsert_article_checkpoint(
    db: Session,
    task: ContentTask,
    checkpoint_type: ArticleCheckpointType,
    payload: ArticleCheckpointUpsert,
) -> ArticleReviewCheckpoint:
    checkpoint = get_article_checkpoint(db, task.id, checkpoint_type)
    is_created = checkpoint is None
    if checkpoint is None:
        checkpoint = ArticleReviewCheckpoint(
            task_id=task.id,
            checkpoint_type=checkpoint_type.value,
        )
    checkpoint.body_markdown = payload.body_markdown
    checkpoint.status = payload.status.value
    checkpoint.reviewer = payload.reviewer
    checkpoint.metadata_json = payload.metadata_json
    db.add(checkpoint)
    db.flush()
    log_task_event(
        db,
        task,
        event_type="article_checkpoint_saved",
        step=checkpoint_type.value,
        message="Article Studio checkpoint saved.",
        metadata_json={
            "checkpoint_type": checkpoint_type.value,
            "checkpoint_status": payload.status.value,
            "operation": "created" if is_created else "updated",
        },
        created_by=payload.reviewer,
    )
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


def delete_article_checkpoint(
    db: Session,
    task: ContentTask,
    checkpoint_type: ArticleCheckpointType,
) -> bool:
    checkpoint = get_article_checkpoint(db, task.id, checkpoint_type)
    if checkpoint is None:
        return False
    db.delete(checkpoint)
    log_task_event(
        db,
        task,
        event_type="article_checkpoint_deleted",
        step=checkpoint_type.value,
        message="Article Studio checkpoint deleted.",
        metadata_json={"checkpoint_type": checkpoint_type.value},
    )
    db.commit()
    return True
