from app.adapters.mock_llm import MockLLMAdapter
from app.models.article_review_checkpoint import ArticleCheckpointType
from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.article_review_checkpoint import ArticleCheckpointUpsert
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.seed.load_prompts import load_seed_prompts
from app.services.article_review_checkpoints import upsert_article_checkpoint
from app.services.content_drafts import list_content_drafts
from app.services.content_research import list_content_research_reports
from app.services.content_tasks import (
    create_content_task,
    get_content_task,
    update_content_task_status,
)
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


def test_worker_generates_drafts_and_waits_for_approval(db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Starlink Mini travel guide",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )

    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())

    processed_task = get_content_task(db_session, task.id)
    drafts = list_content_drafts(db_session, task.id)
    research_reports = list_content_research_reports(db_session, task.id)

    assert processed_task is not None
    assert processed_task.status == ContentTaskStatus.WAITING_APPROVAL.value
    assert len(research_reports) == 1
    assert research_reports[0].provider == "mock-research"
    assert research_reports[0].normalized_json["source_corpus"]["document_count"] == 2
    assert [draft.kind for draft in drafts] == ["initial", "critique", "final"]
    assert drafts[0].prompt_template_key == "ecommerce.aeo_product_description.v1"
    assert drafts[0].metadata_json == {"skills_used": ["ecommerce-aeo-product-description"]}
    assert "Mock research report" in drafts[0].body
    assert "Collected source corpus" in drafts[0].body


def test_worker_includes_article_studio_checkpoints_in_generation(db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Solar charger article with operator brief",
        ),
    )
    upsert_article_checkpoint(
        db_session,
        task,
        ArticleCheckpointType.ARTICLE_BRIEF,
        ArticleCheckpointUpsert(
            body_markdown="ARTICLE BRIEF\n- OPERATOR_BRIEF_MARKER",
            reviewer="operator",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )

    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())

    drafts = list_content_drafts(db_session, task.id)
    assert "OPERATOR_BRIEF_MARKER" in drafts[0].body
    assert "OPERATOR_BRIEF_MARKER" in drafts[-1].body
    assert drafts[-1].metadata_json == {"article_checkpoint_context_included": True}


def test_rewrite_from_article_studio_checkpoints_api(client, db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Solar charger rewrite from notes",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())
    upsert_article_checkpoint(
        db_session,
        task,
        ArticleCheckpointType.EDITOR_NOTES,
        ArticleCheckpointUpsert(
            body_markdown="EDITOR CHECKPOINT\n- REWRITE_NOTE_MARKER",
            reviewer="operator",
        ),
    )

    response = client.post(f"/api/tasks/{task.id}/rewrite-from-checkpoints")

    assert response.status_code == 200
    rewritten = response.json()
    assert rewritten["kind"] == "final"
    assert "REWRITE_NOTE_MARKER" in rewritten["body"]
    assert rewritten["metadata_json"] == {"article_checkpoint_context_included": True}
    task_after_rewrite = get_content_task(db_session, task.id)
    assert task_after_rewrite is not None
    assert task_after_rewrite.status == ContentTaskStatus.WAITING_APPROVAL.value
    assert task_after_rewrite.current_step == "article_studio_rewrite_ready"
    final_drafts = [draft for draft in list_content_drafts(db_session, task.id) if draft.kind == "final"]
    assert len(final_drafts) == 2


def test_set_draft_version_decision_api(client, db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Draft decision test",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())
    final_draft = [draft for draft in list_content_drafts(db_session, task.id) if draft.kind == "final"][-1]

    response = client.post(
        f"/api/tasks/{task.id}/drafts/{final_draft.id}/version-decision",
        json={
            "decision": "approved",
            "reviewer": "operator",
            "comment": "Looks good.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata_json"]["version_decision"]["decision"] == "approved"
    assert payload["metadata_json"]["version_decision"]["reviewer"] == "operator"


def test_get_task_drafts_via_api(client, db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.VIDEO_BRIEF,
            language="ru",
            topic="Samsung smartphone Shorts",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())

    response = client.get(f"/api/tasks/{task.id}/drafts")

    assert response.status_code == 200
    assert [draft["kind"] for draft in response.json()] == ["initial", "critique", "final"]


def test_get_task_research_via_api(client, db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Portable internet research",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())

    response = client.get(f"/api/tasks/{task.id}/research")

    assert response.status_code == 200
    research_reports = response.json()
    assert len(research_reports) == 1
    assert research_reports[0]["provider"] == "mock-research"
    assert research_reports[0]["sources_json"][0]["source_type"] == "mock"
