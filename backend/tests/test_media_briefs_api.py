from app.adapters.mock_llm import MockLLMAdapter
from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.approval import ApprovalPayload
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.seed.load_prompts import load_seed_prompts
from app.services.approvals import approve_task
from app.services.content_tasks import create_content_task, list_task_events, update_content_task_status
from app.services.publish_packages import export_publish_package
from app.services.skill_registry import sync_agent_skills
from app.worker_jobs import _process_content_task


def _write_skill(tmp_path):
    skill_dir = tmp_path / "ecommerce-aeo-product-description"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                "name: ecommerce-aeo-product-description",
                "description: Generate AEO product descriptions.",
                "metadata:",
                "  version: 0.1.0",
                "---",
                "",
                "# AEO Product Description",
            ]
        ),
        encoding="utf-8",
    )


def _create_publish_package(db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Media brief export test",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())
    approve_task(db_session, task, ApprovalPayload(reviewer="marketer"))
    package = export_publish_package(db_session, task)
    return task, package


def test_create_media_brief_for_package(client, db_session, tmp_path):
    task, package = _create_publish_package(db_session, tmp_path)

    response = client.post(f"/api/tasks/packages/{package.id}/media-brief")

    assert response.status_code == 200
    brief = response.json()
    assert brief["package_id"] == package.id
    assert brief["brief_type"] == "video_brief_pack"
    assert brief["status"] == "brief_ready"
    formats = [item["format"] for item in brief["brief_json"]["deliverables"]]
    assert formats == ["long_video", "vertical_short", "veo_prompt_pack"]
    assert brief["brief_json"]["safety"]["real_video_generation_enabled"] is False
    assert "## Google Veo / veo_prompt_pack" in brief["markdown"]
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "media_brief_created"


def test_list_media_briefs_for_package(client, db_session, tmp_path):
    _, package = _create_publish_package(db_session, tmp_path)
    created = client.post(f"/api/tasks/packages/{package.id}/media-brief").json()

    response = client.get(f"/api/tasks/packages/{package.id}/media-briefs")

    assert response.status_code == 200
    briefs = response.json()
    assert len(briefs) == 1
    assert briefs[0]["id"] == created["id"]


def test_media_brief_rejects_missing_package(client):
    response = client.post("/api/tasks/packages/missing/media-brief")

    assert response.status_code == 404
