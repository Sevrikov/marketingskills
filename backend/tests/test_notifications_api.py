from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.services.content_tasks import (
    create_content_task,
    list_task_events,
    update_content_task_status,
)


def _create_waiting_task(db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Viber approval notification test",
        ),
    )
    for task_status, step in [
        (ContentTaskStatus.QUEUED, "queued"),
        (ContentTaskStatus.RESEARCH_RUNNING, "context_preparation"),
        (ContentTaskStatus.RESEARCH_COMPLETED, "context_prepared"),
        (ContentTaskStatus.CONTENT_GENERATING, "initial_draft"),
        (ContentTaskStatus.CRITICIZING, "draft_critique"),
        (ContentTaskStatus.REWRITING, "final_rewrite"),
        (ContentTaskStatus.WAITING_APPROVAL, "waiting_approval"),
    ]:
        task = update_content_task_status(
            db_session,
            task,
            ContentTaskStatusUpdate(status=task_status, current_step=step),
        )
    return task


def test_notify_approval_uses_mock_notification_channel(client, db_session):
    task = _create_waiting_task(db_session)

    response = client.post(f"/api/tasks/{task.id}/notify-approval")

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock-notifications"
    assert data["channel"] == "mock"
    assert data["deliveries"][0]["status"] == "recorded"
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "approval_notification_sent"
    assert events[-1].metadata_json["provider"] == "mock-notifications"


def test_notify_approval_rejects_non_waiting_task(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Not ready for notification",
        ),
    )

    response = client.post(f"/api/tasks/{task.id}/notify-approval")

    assert response.status_code == 409


def test_viber_webhook_approves_waiting_task(client, db_session):
    task = _create_waiting_task(db_session)

    response = client.post(
        "/api/webhooks/viber",
        json={
            "event": "message",
            "message_token": 123,
            "sender": {"id": "viber-user-1", "name": "Marketer"},
            "message": {"type": "text", "text": f"approve:{task.id}"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["decision"] == "approved"
    assert data["task_status"] == "approved"
    events = list_task_events(db_session, task.id)
    webhook_events = [event for event in events if event.event_type == "approval_webhook_received"]
    assert webhook_events
    assert webhook_events[-1].metadata_json["provider"] == "viber"


def test_viber_webhook_requests_rewrite(client, db_session):
    task = _create_waiting_task(db_session)

    response = client.post(
        "/api/webhooks/viber",
        json={
            "event": "message",
            "message_token": 124,
            "sender": {"id": "viber-user-1"},
            "message": {"type": "text", "text": f"rewrite:{task.id}"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "rewrite_requested"
    assert data["task_status"] == "rewriting"


def test_viber_webhook_ignores_non_command_message(client):
    response = client.post(
        "/api/webhooks/viber",
        json={
            "event": "message",
            "sender": {"id": "viber-user-1"},
            "message": {"type": "text", "text": "hello"},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
