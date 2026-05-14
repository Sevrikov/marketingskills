from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_task import ContentTask, ContentTaskStatus
from app.models.task_event import TaskEvent
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ContentTaskStatus.DRAFT.value: {
        ContentTaskStatus.QUEUED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.QUEUED.value: {
        ContentTaskStatus.RESEARCH_RUNNING.value,
        ContentTaskStatus.CONTENT_GENERATING.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.RESEARCH_RUNNING.value: {
        ContentTaskStatus.RESEARCH_COMPLETED.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.RESEARCH_COMPLETED.value: {
        ContentTaskStatus.CONTENT_GENERATING.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.CONTENT_GENERATING.value: {
        ContentTaskStatus.CRITICIZING.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.CRITICIZING.value: {
        ContentTaskStatus.REWRITING.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.REWRITING.value: {
        ContentTaskStatus.WAITING_APPROVAL.value,
        ContentTaskStatus.FAILED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.WAITING_APPROVAL.value: {
        ContentTaskStatus.APPROVED.value,
        ContentTaskStatus.REWRITING.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.APPROVED.value: {
        ContentTaskStatus.PUBLISHING.value,
        ContentTaskStatus.DONE.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.PUBLISHING.value: {
        ContentTaskStatus.DONE.value,
        ContentTaskStatus.FAILED.value,
    },
    ContentTaskStatus.FAILED.value: {
        ContentTaskStatus.QUEUED.value,
        ContentTaskStatus.CANCELLED.value,
    },
    ContentTaskStatus.DONE.value: set(),
    ContentTaskStatus.CANCELLED.value: set(),
}


class InvalidTaskTransition(ValueError):
    pass


def log_task_event(
    db: Session,
    task: ContentTask,
    event_type: str,
    from_status: str | None = None,
    to_status: str | None = None,
    step: str | None = None,
    message: str | None = None,
    metadata_json: dict | None = None,
    created_by: str | None = None,
) -> TaskEvent:
    event = TaskEvent(
        task_id=task.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        step=step,
        message=message,
        metadata_json=metadata_json,
        created_by=created_by,
    )
    db.add(event)
    return event


def create_content_task(db: Session, data: ContentTaskCreate) -> ContentTask:
    task = ContentTask(
        product_id=data.product_id,
        task_type=data.task_type.value,
        language=data.language,
        priority=data.priority,
        created_by=data.created_by,
        topic=data.topic,
    )
    db.add(task)
    db.flush()
    log_task_event(
        db,
        task,
        event_type="task_created",
        to_status=task.status,
        step="created",
        message="Content task created.",
        created_by=data.created_by,
        metadata_json={
            "task_type": data.task_type.value,
            "language": data.language,
            "product_id": data.product_id,
            "topic": data.topic,
        },
    )
    db.commit()
    db.refresh(task)
    return task


def list_content_tasks(db: Session, limit: int = 50, offset: int = 0) -> list[ContentTask]:
    stmt = select(ContentTask).order_by(ContentTask.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_content_task(db: Session, task_id: str) -> ContentTask | None:
    return db.get(ContentTask, task_id)


def list_task_events(db: Session, task_id: str) -> list[TaskEvent]:
    stmt = (
        select(TaskEvent)
        .where(TaskEvent.task_id == task_id)
        .order_by(TaskEvent.created_at.asc(), TaskEvent.id.asc())
    )
    return list(db.scalars(stmt))


def update_content_task_status(
    db: Session,
    task: ContentTask,
    data: ContentTaskStatusUpdate,
) -> ContentTask:
    target_status = data.status.value
    allowed = ALLOWED_STATUS_TRANSITIONS.get(task.status, set())
    if target_status not in allowed and target_status != task.status:
        raise InvalidTaskTransition(
            f"Cannot transition task from {task.status} to {target_status}."
        )

    from_status = task.status
    task.status = target_status
    task.current_step = data.current_step
    task.error_message = data.error_message
    db.add(task)
    log_task_event(
        db,
        task,
        event_type="status_changed",
        from_status=from_status,
        to_status=target_status,
        step=data.current_step,
        message=data.error_message,
    )
    db.commit()
    db.refresh(task)
    return task
