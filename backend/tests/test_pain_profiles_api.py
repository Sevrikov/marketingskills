from app.adapters.mock_llm import MockLLMAdapter
from app.models.content_task import ContentTaskStatus, ContentTaskType
from app.schemas.content_task import ContentTaskCreate, ContentTaskStatusUpdate
from app.seed.load_prompts import load_seed_prompts
from app.services.content_drafts import list_content_drafts
from app.services.content_tasks import create_content_task, update_content_task_status
from app.worker_jobs import _process_content_task


def _product_payload(sku: str = "ALT-63-PAIN") -> dict:
    return {
        "title": "ALTEK ALT-63 portable solar panel",
        "brand": "Altek",
        "model": "ALT-63",
        "category": "мобильные солнечные зарядки",
        "sku": sku,
        "price": "3799.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://example.com/altek-alt-63",
        "raw_description": (
            "Портативная солнечная батарея для зарядки смартфонов, павербанков "
            "и туристического оборудования вдали от розетки."
        ),
    }


def test_generate_list_get_and_approve_pain_profile(client):
    product = client.post("/api/products", json=_product_payload()).json()

    generate_response = client.post(
        "/api/pain-profiles/generate",
        json={"product_id": product["id"], "language": "ru"},
    )

    assert generate_response.status_code == 201
    profile = generate_response.json()
    assert profile["status"] == "draft"
    assert profile["product_id"] == product["id"]
    assert profile["profile_json"]["schema_version"] == "1.0"
    assert "автономная зарядка" in profile["primary_pain_summary"]
    assert profile["profile_json"]["proof_map"][0]["source_ids"]
    assert profile["profile_json"]["do_not_claim"]
    assert profile["profile_json"]["content_guidance"]["infographic_angle"]

    list_response = client.get(f"/api/pain-profiles?product_id={product['id']}")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [profile["id"]]

    get_response = client.get(f"/api/pain-profiles/{profile['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == profile["id"]

    approve_response = client.post(
        f"/api/pain-profiles/{profile['id']}/approve",
        json={"reviewer": "marketer", "comment": "Pain map is usable."},
    )

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "marketer"
    assert approved["metadata_json"]["approval"]["comment"] == "Pain map is usable."


def test_approved_pain_profile_is_injected_into_draft_pipeline(client, db_session):
    load_seed_prompts(db_session)
    product = client.post("/api/products", json=_product_payload("ALT-63-INJECT")).json()
    profile = client.post(
        "/api/pain-profiles/generate",
        json={"product_id": product["id"], "language": "ru"},
    ).json()
    client.post(f"/api/pain-profiles/{profile['id']}/approve", json={"reviewer": "editor"})
    task = create_content_task(
        db_session,
        ContentTaskCreate(
            product_id=product["id"],
            task_type=ContentTaskType.PRODUCT_CARD,
            language="ru",
            topic="ALT-63 product card",
        ),
    )
    update_content_task_status(
        db_session,
        task,
        ContentTaskStatusUpdate(status=ContentTaskStatus.QUEUED, current_step="queued"),
    )

    _process_content_task(db_session, task.id, llm_adapter=MockLLMAdapter())

    drafts = list_content_drafts(db_session, task.id)
    assert [draft.kind for draft in drafts] == ["initial", "critique", "final"]
    assert "Approved pain_profile:" in drafts[0].body
    assert "автономная зарядка" in drafts[0].body
    assert "{{image:hero}}" in drafts[-1].body
