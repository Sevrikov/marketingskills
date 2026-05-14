from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.content_task import ContentTaskCreate
from app.services.content_drafts import create_content_draft
from app.services.content_tasks import create_content_task


def test_article_assets_generate_list_and_review(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Portable solar charger article",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        title="Portable solar charger",
        body="\n".join(
            [
                "# Portable solar charger",
                "Intro.",
                "{{image:hero}}",
                "{{infographic:comparison}}",
            ]
        ),
        provider="mock",
        model="mock",
    )
    db_session.commit()

    empty_response = client.get(f"/api/tasks/{task.id}/article-assets")

    assert empty_response.status_code == 200
    assert empty_response.json() == []

    generate_response = client.post(f"/api/tasks/{task.id}/article-assets/generate")

    assert generate_response.status_code == 200
    assets = generate_response.json()
    assets_by_slot = {asset["slot"]: asset for asset in assets}
    assert set(assets_by_slot) == {"image:hero", "infographic:comparison"}
    hero_asset = assets_by_slot["image:hero"]
    assert hero_asset["status"] == "generated"
    assert hero_asset["storage_uri"].startswith("mock://article-assets/")
    assert hero_asset["brief_json"]["generation_provider"] == "mock"

    approve_response = client.post(
        f"/api/tasks/{task.id}/article-assets/{hero_asset['id']}/status",
        json={
            "status": "approved",
            "reviewer": "designer",
            "comment": "Hero visual is usable.",
        },
    )

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "approved"
    assert approved["qa_json"]["human_review"]["reviewer"] == "designer"

    list_response = client.get(f"/api/tasks/{task.id}/article-assets")

    assert list_response.status_code == 200
    listed_by_slot = {asset["slot"]: asset for asset in list_response.json()}
    assert listed_by_slot["image:hero"]["status"] == "approved"


def test_article_assets_require_final_draft_slots(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Article without image placeholders",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        body="# Article\nNo image placeholders here.",
        provider="mock",
        model="mock",
    )
    db_session.commit()

    response = client.post(f"/api/tasks/{task.id}/article-assets/generate")

    assert response.status_code == 409


def test_article_asset_mock_image_generation_resets_review(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Generated image article",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        body="# Article\n{{image:hero}}",
        provider="mock",
        model="mock",
    )
    db_session.commit()
    asset = client.post(f"/api/tasks/{task.id}/article-assets/generate").json()[0]
    client.post(
        f"/api/tasks/{task.id}/article-assets/{asset['id']}/status",
        json={"status": "approved", "reviewer": "designer"},
    )

    response = client.post(
        f"/api/tasks/{task.id}/article-assets/{asset['id']}/generate-image",
        json={"reviewer": "operator", "comment": "Generate placeholder."},
    )

    assert response.status_code == 200
    generated = response.json()
    assert generated["status"] == "generated"
    assert generated["storage_uri"].startswith("data:image/svg+xml")
    assert generated["qa_json"]["image_generation"]["provider"] == "mock-image"
    assert generated["qa_json"]["image_generation"]["approval_reset"] is True


def test_article_asset_manual_upload_updates_uri_and_resets_review(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Uploaded image article",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        body="# Article\n{{image:hero}}",
        provider="mock",
        model="mock",
    )
    db_session.commit()
    asset = client.post(f"/api/tasks/{task.id}/article-assets/generate").json()[0]

    response = client.post(
        f"/api/tasks/{task.id}/article-assets/{asset['id']}/upload",
        json={
            "storage_uri": "https://example.com/image.jpg",
            "alt_text": "Uploaded solar charger image",
            "caption": "Uploaded article visual.",
            "reviewer": "operator",
        },
    )

    assert response.status_code == 200
    uploaded = response.json()
    assert uploaded["status"] == "generated"
    assert uploaded["storage_uri"] == "https://example.com/image.jpg"
    assert uploaded["alt_text"] == "Uploaded solar charger image"
    assert uploaded["qa_json"]["manual_upload"]["approval_reset"] is True


def test_export_package_includes_approved_article_assets(client, db_session):
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            task_type=ContentTaskType.SEO_ARTICLE,
            language="ru",
            topic="Article asset export",
        ),
    )
    create_content_draft(
        db_session,
        task,
        kind="final",
        title="Article asset export",
        body="# Article asset export\n{{image:hero}}\n{{infographic:comparison}}",
        provider="mock",
        model="mock",
    )
    db_session.commit()

    assets = client.post(f"/api/tasks/{task.id}/article-assets/generate").json()
    hero_asset = next(asset for asset in assets if asset["slot"] == "image:hero")
    client.post(
        f"/api/tasks/{task.id}/article-assets/{hero_asset['id']}/status",
        json={"status": "approved", "reviewer": "designer"},
    )
    task.status = ContentTaskStatus.APPROVED.value
    db_session.add(task)
    db_session.commit()

    response = client.post(f"/api/tasks/{task.id}/export-package")

    assert response.status_code == 200
    package = response.json()
    article_studio = package["package_json"]["article_studio"]
    assert {asset["slot"] for asset in article_studio["assets"]} == {
        "image:hero",
        "infographic:comparison",
    }
    assert article_studio["approved_assets"]["image:hero"]["status"] == "approved"
    assert "## Article Assets" in package["markdown"]
