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
            topic="Approval flow test",
        ),
    )
    for status, step in [
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
            ContentTaskStatusUpdate(status=status, current_step=step),
        )
    return task


def test_approve_waiting_task(client, db_session):
    task = _create_waiting_task(db_session)

    response = client.post(
        f"/api/tasks/{task.id}/approve",
        json={"reviewer": "marketer", "comment": "Looks good."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "approval_decision"
    assert events[-1].metadata_json["decision"] == "approved"


def test_request_rewrite_waiting_task(client, db_session):
    task = _create_waiting_task(db_session)

    response = client.post(
        f"/api/tasks/{task.id}/request-rewrite",
        json={"reviewer": "marketer", "comment": "Add stronger FAQ."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rewriting"
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "approval_decision"
    assert events[-1].metadata_json["decision"] == "rewrite_requested"


def test_approval_rejects_non_waiting_task(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Not ready",
        ),
    )

    response = client.post(f"/api/tasks/{task.id}/approve", json={"reviewer": "marketer"})

    assert response.status_code == 409
