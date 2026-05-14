from sqlalchemy.orm import Session

from app.adapters.notifications import (
    ApprovalNotificationRequest,
    NotificationAdapter,
    NotificationDelivery,
)
from app.config import Settings
from app.models.content_task import ContentTask, ContentTaskStatus
from app.services.content_tasks import log_task_event


class TaskNotReadyForNotification(ValueError):
    pass


def send_approval_notification(
    db: Session,
    task: ContentTask,
    adapter: NotificationAdapter,
    settings: Settings,
) -> list[NotificationDelivery]:
    if task.status != ContentTaskStatus.WAITING_APPROVAL.value:
        raise TaskNotReadyForNotification(
            f"Task must be waiting_approval before notification, current status is {task.status}."
        )

    deliveries = adapter.send_approval_request(
        ApprovalNotificationRequest(
            task_id=task.id,
            task_type=task.task_type,
            topic=task.topic,
            language=task.language,
            status=task.status,
            console_url=_task_console_url(settings, task.id),
        )
    )
    log_task_event(
        db,
        task,
        event_type="approval_notification_sent",
        from_status=task.status,
        to_status=task.status,
        step="approval_notification",
        message=f"Approval notification sent through {adapter.provider}.",
        metadata_json={
            "provider": adapter.provider,
            "deliveries": [
                {
                    "channel": delivery.channel,
                    "status": delivery.status,
                    "recipient": delivery.recipient,
                    "message_id": delivery.message_id,
                    "metadata": delivery.metadata,
                }
                for delivery in deliveries
            ],
        },
    )
    db.commit()
    db.refresh(task)
    return deliveries


def _task_console_url(settings: Settings, task_id: str) -> str:
    return f"{settings.operator_console_url.rstrip('/')}?task_id={task_id}"
