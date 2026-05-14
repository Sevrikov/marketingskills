from app.adapters.mock_llm import MockLLMAdapter
from app.config import Settings, get_settings
from app.main import app
from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.approval import ApprovalPayload
from app.schemas.article_asset import ArticleAssetStatusUpdate
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.schemas.product import ProductCreate
from app.seed.load_prompts import load_seed_prompts
from app.services.approvals import approve_task
from app.services.article_assets import generate_article_assets, update_article_asset_status
from app.services.content_drafts import create_content_draft
from app.services.content_tasks import create_content_task, list_task_events, update_content_task_status
from app.services.product_content_profiles import (
    approve_product_content_profile,
    generate_product_content_profile,
)
from app.services.products import create_product
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


def _create_publish_package(
    db_session,
    tmp_path,
    product_id=None,
    task_type=ContentTaskType.SEO_ARTICLE,
):
    _write_skill(tmp_path)
    load_seed_prompts(db_session)
    sync_agent_skills(db_session, tmp_path)
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=task_type,
            language="ru",
            product_id=product_id,
            topic="Publication preview export test",
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


def test_create_publication_preview_for_package(client, db_session, tmp_path):
    task, package = _create_publish_package(db_session, tmp_path)

    response = client.post(f"/api/tasks/packages/{package.id}/publication-preview")

    assert response.status_code == 200
    preview = response.json()
    assert preview["package_id"] == package.id
    assert preview["provider"] == "mock-cms"
    assert preview["status"] == "dry_run_ready"
    assert preview["payload_json"]["operation"] == "create_draft"
    assert preview["payload_json"]["post"]["title"] == package.title
    assert preview["payload_json"]["schema_json"]["@type"] == "Article"
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "publication_preview_created"


def test_publication_preview_includes_approved_product_profile(client, db_session, tmp_path):
    product = create_product(
        db_session,
        ProductCreate(
            title="Starlink Mini",
            brand="Starlink",
            model="Mini",
            category="satellite internet",
            sku="SL-MINI-TEST",
            price="499.00",
            currency="USD",
            availability="in_stock",
        ),
    )
    task, package = _create_publish_package(
        db_session,
        tmp_path,
        product_id=product.id,
        task_type=ContentTaskType.PRODUCT_CARD,
    )
    profile = generate_product_content_profile(db_session, product, source_task_id=task.id)
    approve_product_content_profile(db_session, profile)

    response = client.post(f"/api/tasks/packages/{package.id}/publication-preview")

    assert response.status_code == 200
    payload = response.json()["payload_json"]
    assert payload["product_card_json"]["product_id"] == product.id
    assert payload["product_card_json"]["status"] == "approved"
    assert payload["schema_json"]["@graph"][1]["@type"] == "Product"


def test_publication_preview_inserts_article_asset_placeholders(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Publication image slots",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        title="Publication image slots",
        body="# Publication image slots\n{{image:hero}}\n{{infographic:comparison}}",
        provider="mock",
        model="mock",
    )
    db_session.commit()
    assets = generate_article_assets(db_session, task)
    hero_asset = next(asset for asset in assets if asset.slot == "image:hero")
    update_article_asset_status(
        db_session,
        task,
        hero_asset,
        ArticleAssetStatusUpdate(status="approved", reviewer="designer"),
    )
    task.status = ContentTaskStatus.APPROVED.value
    db_session.add(task)
    db_session.commit()
    package = export_publish_package(db_session, task)

    response = client.post(f"/api/tasks/packages/{package.id}/publication-preview")

    assert response.status_code == 200
    payload = response.json()["payload_json"]
    html = payload["post"]["content_html"]
    assert 'data-asset-slot="image:hero"' in html
    assert "article-asset-placeholder_waiting_upload" in html
    insertions = {asset["slot"]: asset["cms_insertion"] for asset in payload["media_assets_json"]}
    assert insertions["image:hero"] == "placeholder_waiting_upload"
    assert insertions["infographic:comparison"] == "placeholder_pending_review"


def test_publication_preview_inserts_renderable_article_asset_image(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Renderable image slot",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        title="Renderable image slot",
        body="# Renderable image slot\n{{image:hero}}",
        provider="mock",
        model="mock",
    )
    db_session.commit()
    asset = generate_article_assets(db_session, task)[0]
    client.post(
        f"/api/tasks/{task.id}/article-assets/{asset.id}/upload",
        json={"storage_uri": "https://example.com/hero.jpg", "reviewer": "operator"},
    )
    client.post(
        f"/api/tasks/{task.id}/article-assets/{asset.id}/status",
        json={"status": "approved", "reviewer": "designer"},
    )
    task.status = ContentTaskStatus.APPROVED.value
    db_session.add(task)
    db_session.commit()
    package = export_publish_package(db_session, task)

    response = client.post(f"/api/tasks/packages/{package.id}/publication-preview")

    assert response.status_code == 200
    payload = response.json()["payload_json"]
    assert '<img src="https://example.com/hero.jpg"' in payload["post"]["content_html"]
    assert payload["media_assets_json"][0]["cms_insertion"] == "ready"


def test_list_publication_previews_for_package(client, db_session, tmp_path):
    _, package = _create_publish_package(db_session, tmp_path)
    created = client.post(f"/api/tasks/packages/{package.id}/publication-preview").json()

    response = client.get(f"/api/tasks/packages/{package.id}/publication-previews")

    assert response.status_code == 200
    previews = response.json()
    assert len(previews) == 1
    assert previews[0]["id"] == created["id"]


def test_publication_preview_rejects_missing_package(client):
    response = client.post("/api/tasks/packages/missing/publication-preview")

    assert response.status_code == 404


def test_publish_publication_preview_blocked_by_default(client, db_session, tmp_path):
    _, package = _create_publish_package(db_session, tmp_path)
    preview = client.post(f"/api/tasks/packages/{package.id}/publication-preview").json()

    response = client.post(
        f"/api/tasks/publication-previews/{preview['id']}/publish",
        json={"confirmation_phrase": f"publish:{preview['id']}"},
    )

    assert response.status_code == 409
    assert "Real publishing is disabled" in response.json()["detail"]


def test_publish_publication_preview_requires_exact_confirmation(client, db_session, tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(enable_real_publishing=True)
    _, package = _create_publish_package(db_session, tmp_path)
    preview = client.post(f"/api/tasks/packages/{package.id}/publication-preview").json()

    response = client.post(
        f"/api/tasks/publication-previews/{preview['id']}/publish",
        json={"confirmation_phrase": "publish:wrong"},
    )

    assert response.status_code == 409
    assert "Confirmation phrase is required" in response.json()["detail"]


def test_publish_publication_preview_with_safety_gate(client, db_session, tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(enable_real_publishing=True)
    task, package = _create_publish_package(db_session, tmp_path)
    preview = client.post(f"/api/tasks/packages/{package.id}/publication-preview").json()

    response = client.post(
        f"/api/tasks/publication-previews/{preview['id']}/publish",
        json={"confirmation_phrase": f"publish:{preview['id']}"},
    )

    assert response.status_code == 200
    published = response.json()
    assert published["status"] == "published"
    assert published["result_json"]["provider"] == "mock-cms"
    assert published["result_json"]["safety"]["dry_run"] is False
    events = list_task_events(db_session, task.id)
    assert events[-1].event_type == "publication_published"
