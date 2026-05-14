from decimal import Decimal

from app.adapters.mock_llm import MockLLMAdapter
from app.adapters.price_monitor import GENERIC_PRICE_EXTRACTOR_JS
from app.models.content_task import ContentTask, ContentTaskStatus
from app.models.monitored_source import MonitoredSource
from app.seed.load_prompts import load_seed_prompts
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.content_tasks import update_content_task_status
from app.services.skill_registry import sync_agent_skills
from app.worker_jobs import _process_content_task

from tests.test_realistic_solar_category_smoke import SOLAR_CATEGORY_PRODUCTS


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


def _bootstrap_article_skills(db_session, tmp_path) -> None:
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


def test_realistic_solar_category_article_flow(client, db_session, tmp_path):
    _bootstrap_article_skills(db_session, tmp_path)

    created_products = []
    for payload in SOLAR_CATEGORY_PRODUCTS:
        response = client.post("/api/products", json=payload)
        assert response.status_code == 201
        created_products.append(response.json())

    group_response = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Мобільні сонячні зарядки Elektronom",
            "category": "Мобільні сонячні зарядки",
            "keywords": (
                "сонячна батарея USB портативна зарядка ALTEK Kraft "
                "28W 63W 100W автономне живлення"
            ),
            "top_position_limit": 3,
            "min_sources_for_signal": 5,
        },
    )
    assert group_response.status_code == 201
    group = group_response.json()

    for position, product in enumerate(created_products, start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                product_id=product["id"],
                url=product["source_url"],
                label=product["title"],
                source_type="own_category_product",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=position,
                source_priority=position,
                last_price=Decimal(product["price"]),
                last_currency=product["currency"],
                last_availability=product["availability"],
            )
        )
    db_session.commit()

    market_index_response = client.post(
        f"/api/price-monitor/groups/{group['id']}/market-indexes"
    )
    assert market_index_response.status_code == 200
    assert market_index_response.json()["median_price"] == "2400.00"

    opportunities_response = client.post(
        "/api/content-opportunities/discover",
        json={
            "price_group_id": group["id"],
            "language": "uk",
            "market": "UA",
            "limit": 3,
        },
    )
    assert opportunities_response.status_code == 200
    opportunities = opportunities_response.json()["opportunities"]
    assert len(opportunities) == 3
    assert opportunities[0]["scope_type"] == "price_group"
    assert opportunities[0]["intent"] == "commercial"
    assert opportunities[0]["sources_json"]

    task_response = client.post(
        f"/api/content-opportunities/{opportunities[0]['id']}/create-task"
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["task_id"]
    task = db_session.get(ContentTask, task_id)
    assert task is not None
    assert task.task_type == "seo_article"
    assert task.topic == opportunities[0]["title"]

    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )
    _process_content_task(db_session, task_id, llm_adapter=MockLLMAdapter())

    research = client.get(f"/api/tasks/{task_id}/research")
    assert research.status_code == 200
    research_payload = research.json()[0]
    assert research_payload["provider"] == "mock-research"
    assert "customer pain problem solved" in research_payload["normalized_json"]["query"]
    assert "Мобільні сонячні зарядки" in research_payload["normalized_json"]["query"]

    drafts = client.get(f"/api/tasks/{task_id}/drafts")
    assert drafts.status_code == 200
    draft_payload = drafts.json()
    assert [draft["kind"] for draft in draft_payload] == ["initial", "critique", "final"]
    assert "Research report:" in draft_payload[0]["body"]
    assert "customer pain problem solved" in draft_payload[0]["body"]

    approve_task = client.post(
        f"/api/tasks/{task_id}/approve",
        json={"reviewer": "mock-editor", "comment": "Solar category article smoke approved."},
    )
    assert approve_task.status_code == 200

    package_response = client.post(f"/api/tasks/{task_id}/export-package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["status"] == "ready"
    assert package["package_json"]["task"]["task_type"] == "seo_article"
    assert package["package_json"]["task"]["product_id"] is None
    assert package["package_json"]["research"]["provider"] == "mock-research"

    preview_response = client.post(f"/api/tasks/packages/{package['id']}/publication-preview")
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["provider"] == "mock-cms"
    assert preview["status"] == "dry_run_ready"
    assert preview["payload_json"]["schema_json"]["@type"] == "Article"

    media_brief_response = client.post(f"/api/tasks/packages/{package['id']}/media-brief")
    assert media_brief_response.status_code == 200
    media_brief = media_brief_response.json()
    assert media_brief["brief_json"]["source_task"]["task_type"] == "seo_article"
    assert media_brief["brief_json"]["safety"]["real_video_generation_enabled"] is False

