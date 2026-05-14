from app.models.content_task import ContentTask, ContentTaskStatus
from app.services.content_tasks import list_task_events
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.content_tasks import InvalidTaskTransition, update_content_task_status


def test_state_machine_allows_draft_to_queued(db_session):
    task = ContentTask(task_type="seo_article", language="ru", topic="Test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED),
    )

    assert updated.status == "queued"
    events = list_task_events(db_session, task.id)
    assert len(events) == 1
    assert events[0].event_type == "status_changed"
    assert events[0].from_status == "draft"
    assert events[0].to_status == "queued"


def test_state_machine_blocks_draft_to_done(db_session):
    task = ContentTask(task_type="seo_article", language="ru", topic="Test")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    try:
        update_content_task_status(
            db_session,
            task,
            ContentTaskStatusUpdate(status=ContentTaskStatus.DONE),
        )
    except InvalidTaskTransition:
        return

    raise AssertionError("Expected InvalidTaskTransition")
