from app.adapters.mock_llm import MockLLMAdapter
from app.models.article_review_checkpoint import ArticleCheckpointType
from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.approval import ApprovalPayload
from app.schemas.article_review_checkpoint import ArticleCheckpointUpsert
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.seed.load_prompts import load_seed_prompts
from app.services.approvals import approve_task
from app.services.article_review_checkpoints import upsert_article_checkpoint
from app.services.content_drafts import create_content_draft, list_content_drafts
from app.services.content_tasks import create_content_task, update_content_task_status
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


def _create_waiting_approval_task(db_session, tmp_path):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Publish package export test",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())
    return task


def test_export_package_requires_approved_task(client, db_session, tmp_path):
    task = _create_waiting_approval_task(db_session, tmp_path)

    response = client.post(f"/api/tasks/{task.id}/export-package")

    assert response.status_code == 409


def test_export_package_for_approved_task(client, db_session, tmp_path):
    task = _create_waiting_approval_task(db_session, tmp_path)
    upsert_article_checkpoint(
        db_session,
        task,
        ArticleCheckpointType.ARTICLE_BRIEF,
        ArticleCheckpointUpsert(
            body_markdown="ARTICLE BRIEF\n- PACKAGE_BRIEF_MARKER",
            reviewer="operator",
        ),
    )
    upsert_article_checkpoint(
        db_session,
        task,
        ArticleCheckpointType.IMAGE_BRIEF,
        ArticleCheckpointUpsert(
            body_markdown="IMAGE BRIEF\n- PACKAGE_IMAGE_MARKER",
            reviewer="designer",
        ),
    )
    approve_task(
        db_session,
        task,
        ApprovalPayload(reviewer="marketer", comment="Approved for export."),
    )

    response = client.post(f"/api/tasks/{task.id}/export-package")

    assert response.status_code == 200
    package = response.json()
    assert package["status"] == "ready"
    assert package["slug"] == "publish-package-export-test"
    assert "## Final Content" in package["markdown"]
    assert package["package_json"]["content"]["prompt_template_key"] == "ecommerce.rewriter.v1"
    assert package["package_json"]["workflow"]["drafts"][0]["prompt_template_key"] == (
        "ecommerce.aeo_product_description.v1"
    )
    assert package["package_json"]["research"]["sources"][0]["source_type"] == "mock"
    assert package["package_json"]["article_studio"]["checkpoints"]["article_brief"][
        "body_markdown"
    ].endswith("PACKAGE_BRIEF_MARKER")
    assert package["package_json"]["article_studio"]["checkpoints"]["image_brief"][
        "reviewer"
    ] == "designer"
    assert "PACKAGE_IMAGE_MARKER" in package["markdown"]


def test_list_task_packages(client, db_session, tmp_path):
    task = _create_waiting_approval_task(db_session, tmp_path)
    approve_task(db_session, task, ApprovalPayload(reviewer="marketer"))
    export_response = client.post(f"/api/tasks/{task.id}/export-package")

    response = client.get(f"/api/tasks/{task.id}/packages")

    assert response.status_code == 200
    packages = response.json()
    assert len(packages) == 1
    assert packages[0]["id"] == export_response.json()["id"]


def test_export_package_skips_rejected_latest_final(client, db_session, tmp_path):
    task = _create_waiting_approval_task(db_session, tmp_path)
    first_final = [draft for draft in list_content_drafts(db_session, task.id) if draft.kind == "final"][-1]
    rejected_final = create_content_draft(
        db_session,
        task,
        kind="final",
        title="Rejected rewrite",
        body="REJECTED_REWRITE_BODY",
        provider="mock",
        model="mock",
        metadata_json={"article_checkpoint_context_included": True},
    )
    db_session.commit()
    decision_response = client.post(
        f"/api/tasks/{task.id}/drafts/{rejected_final.id}/version-decision",
        json={
            "decision": "rejected",
            "reviewer": "operator",
            "comment": "Reject latest rewrite.",
        },
    )
    assert decision_response.status_code == 200
    approve_task(db_session, task, ApprovalPayload(reviewer="marketer"))

    response = client.post(f"/api/tasks/{task.id}/export-package")

    assert response.status_code == 200
    package = response.json()
    assert package["package_json"]["content"]["draft_id"] == first_final.id
    assert "REJECTED_REWRITE_BODY" not in package["markdown"]
