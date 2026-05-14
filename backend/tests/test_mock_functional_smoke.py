from app.adapters.mock_llm import MockLLMAdapter
from app.adapters.price_monitor import GENERIC_PRICE_EXTRACTOR_JS
from app.models.content_task import ContentTask, ContentTaskStatus
from app.models.monitored_source import MonitoredSource
from app.seed.load_prompts import load_seed_prompts
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.content_tasks import update_content_task_status
from app.services.skill_registry import sync_agent_skills
from app.worker_jobs import _process_content_task


def _write_skill(tmp_path, name: str, description: str) -> None:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "---",
                "",
                f"# {name}",
            ]
        ),
        encoding="utf-8",
    )


def _bootstrap_mock_registries(db_session, tmp_path) -> None:
    load_seed_prompts(db_session)
    for name, description in [
        ("ecommerce-product-normalization", "Normalize ecommerce product data."),
        ("ecommerce-aeo-product-description", "Generate AEO product descriptions."),
        ("ecommerce-customer-pain-research", "Research customer pain and proof map."),
        ("ecommerce-infographic-brief", "Prepare ecommerce infographic briefs."),
        ("ecommerce-video-brief", "Prepare ecommerce video and Shorts briefs."),
    ]:
        _write_skill(tmp_path, name, description)
    sync_agent_skills(db_session, tmp_path)


def test_mock_mode_core_business_functions_are_stable(client, db_session, tmp_path):
    _bootstrap_mock_registries(db_session, tmp_path)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    prompts = client.get("/api/prompts")
    assert prompts.status_code == 200
    assert {prompt["key"] for prompt in prompts.json()} >= {
        "ecommerce.customer_pain_research.v1",
        "ecommerce.aeo_product_description.v1",
        "ecommerce.content_critic.v1",
        "ecommerce.rewriter.v1",
        "ecommerce.video_brief.v1",
    }

    skills = client.get("/api/skills")
    assert skills.status_code == 200
    assert {skill["name"] for skill in skills.json()} >= {
        "ecommerce-customer-pain-research",
        "ecommerce-infographic-brief",
        "ecommerce-video-brief",
    }

    product_response = client.post(
        "/api/products",
        json={
            "title": "Starlink Mini",
            "brand": "Starlink",
            "model": "Mini",
            "category": "satellite internet",
            "sku": "SL-MINI-SMOKE",
            "price": "499.00",
            "currency": "USD",
            "availability": "in_stock",
            "raw_description": "Portable internet terminal for travel and backup connectivity.",
        },
    )
    assert product_response.status_code == 201
    product = product_response.json()

    profile_response = client.post(
        f"/api/products/{product['id']}/content-profile/generate",
        json={"language": "ru"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["status"] == "draft"

    approve_profile = client.post(f"/api/products/{product['id']}/content-profile/approve")
    assert approve_profile.status_code == 200
    assert approve_profile.json()["status"] == "approved"

    opportunities_response = client.post(
        "/api/content-opportunities/discover",
        json={
            "product_id": product["id"],
            "language": "ru",
            "market": "UA",
            "limit": 2,
        },
    )
    assert opportunities_response.status_code == 200
    opportunities = opportunities_response.json()["opportunities"]
    assert len(opportunities) == 2

    task_from_opportunity = client.post(
        f"/api/content-opportunities/{opportunities[0]['id']}/create-task"
    )
    assert task_from_opportunity.status_code == 200
    task_id = task_from_opportunity.json()["task_id"]

    task = db_session.get(ContentTask, task_id)
    assert task is not None
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task_id, llm_adapter=MockLLMAdapter())

    task_after_worker = client.get(f"/api/tasks/{task_id}")
    assert task_after_worker.status_code == 200
    assert task_after_worker.json()["status"] == "waiting_approval"

    drafts = client.get(f"/api/tasks/{task_id}/drafts")
    assert drafts.status_code == 200
    assert [draft["kind"] for draft in drafts.json()] == ["initial", "critique", "final"]

    research = client.get(f"/api/tasks/{task_id}/research")
    assert research.status_code == 200
    assert research.json()[0]["provider"] == "mock-research"

    notify = client.post(f"/api/tasks/{task_id}/notify-approval")
    assert notify.status_code == 200
    assert notify.json()["provider"] == "mock-notifications"

    approve_task = client.post(
        f"/api/tasks/{task_id}/approve",
        json={"reviewer": "mock-smoke", "comment": "Approved in mock smoke."},
    )
    assert approve_task.status_code == 200
    assert approve_task.json()["status"] == "approved"

    package_response = client.post(f"/api/tasks/{task_id}/export-package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["status"] == "ready"

    preview_response = client.post(f"/api/tasks/packages/{package['id']}/publication-preview")
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["provider"] == "mock-cms"
    assert preview["status"] == "dry_run_ready"

    blocked_publish = client.post(
        f"/api/tasks/publication-previews/{preview['id']}/publish",
        json={"confirmation_phrase": f"publish:{preview['id']}"},
    )
    assert blocked_publish.status_code == 409

    media_brief_response = client.post(f"/api/tasks/packages/{package['id']}/media-brief")
    assert media_brief_response.status_code == 200
    media_brief = media_brief_response.json()
    assert media_brief["brief_type"] == "video_brief_pack"
    assert media_brief["brief_json"]["safety"]["real_video_generation_enabled"] is False
    assert "pain_profile" in media_brief["brief_json"]

    group_response = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Portable internet devices",
            "category": "satellite internet",
            "min_sources_for_signal": 3,
        },
    )
    assert group_response.status_code == 201
    group = group_response.json()

    for index, price in enumerate([1000, 1100, 1200], start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                url=f"https://example.com/mock-market-{index}",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=index,
                last_price=price,
                last_currency="UAH",
                last_availability="in_stock",
            )
        )
    db_session.commit()

    first_index = client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    assert first_index.status_code == 200
    assert first_index.json()["source_count"] == 3

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [800, 880, 960], strict=False):
        source.last_price = price
    db_session.commit()

    second_index = client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    assert second_index.status_code == 200
    assert second_index.json()["avg_price"] == "880.00"

    policy_response = client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "Mock high trend digest",
            "delivery_mode": "digest",
            "min_severity": "high",
            "min_affected_sources": 3,
            "min_percent_change": "10.0",
        },
    )
    assert policy_response.status_code == 201

    evaluate_response = client.post("/api/price-monitor/notification-policies/evaluate")
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["queued_digest"] == 1

    digest_response = client.post("/api/price-monitor/trend-digests/run-batch")
    assert digest_response.status_code == 200
    assert digest_response.json()["status"] == "sent"

    scheduler_jobs = client.get("/api/scheduler/jobs")
    assert scheduler_jobs.status_code == 200
    assert scheduler_jobs.json()

    scheduler_run = client.post("/api/scheduler/run-due")
    assert scheduler_run.status_code == 200
    assert "runs" in scheduler_run.json()
