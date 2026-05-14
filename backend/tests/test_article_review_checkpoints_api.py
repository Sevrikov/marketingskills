from app.models.content_task import ContentTaskType
from app.schemas.content_task import ContentTaskCreate
from app.services.content_tasks import create_content_task


def test_article_checkpoint_upsert_list_update_delete(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Portable solar charger article",
        ),
    )

    empty_response = client.get(f"/api/tasks/{task.id}/article-checkpoints")

    assert empty_response.status_code == 200
    assert empty_response.json() == []

    create_response = client.put(
        f"/api/tasks/{task.id}/article-checkpoints/article_brief",
        json={
            "body_markdown": "ARTICLE BRIEF\n- cover the main buyer pain",
            "status": "draft",
            "reviewer": "operator",
            "metadata_json": {"source": "article_studio"},
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["task_id"] == task.id
    assert created["checkpoint_type"] == "article_brief"
    assert created["body_markdown"].startswith("ARTICLE BRIEF")
    assert created["metadata_json"] == {"source": "article_studio"}

    update_response = client.put(
        f"/api/tasks/{task.id}/article-checkpoints/article_brief",
        json={
            "body_markdown": "ARTICLE BRIEF\n- updated by editor",
            "status": "reviewed",
            "reviewer": "editor",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["status"] == "reviewed"
    assert updated["reviewer"] == "editor"

    list_response = client.get(f"/api/tasks/{task.id}/article-checkpoints")

    assert list_response.status_code == 200
    checkpoints = list_response.json()
    assert len(checkpoints) == 1
    assert checkpoints[0]["body_markdown"].endswith("updated by editor")

    delete_response = client.delete(f"/api/tasks/{task.id}/article-checkpoints/article_brief")

    assert delete_response.status_code == 204
    assert client.get(f"/api/tasks/{task.id}/article-checkpoints").json() == []


def test_article_checkpoint_rejects_unknown_task(client):
    response = client.put(
        "/api/tasks/missing/article-checkpoints/article_brief",
        json={"body_markdown": "ARTICLE BRIEF"},
    )

    assert response.status_code == 404


def test_article_checkpoint_rejects_unknown_type(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Portable solar charger article",
        ),
    )

    response = client.put(
        f"/api/tasks/{task.id}/article-checkpoints/unknown",
        json={"body_markdown": "ARTICLE BRIEF"},
    )

    assert response.status_code == 422
