from app.adapters.mock_llm import MockLLMAdapter
from app.models.content_task import ContentTask, ContentTaskStatus, ContentTaskType
from app.seed.load_prompts import load_seed_prompts
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.content_tasks import update_content_task_status
from app.services.skill_registry import sync_agent_skills
from app.worker_jobs import _process_content_task


ELEKTRONOM_ALTEK_ALT_63 = {
    "title": "Портативна сонячна батарея 63W чорний",
    "brand": "ALTEK",
    "model": "ALT-63",
    "category": "Мобільні сонячні зарядки",
    "sku": "PROM-1859660505",
    "mpn": "ALT-63",
    "price": "4200.00",
    "currency": "UAH",
    "availability": "in_stock",
    "source_url": (
        "https://elektronom.com.ua/ua/"
        "p1859660505-portativnaya-solnechnaya-batareya.html"
    ),
    "raw_description": "\n".join(
        [
            "Монокристалічна сонячна панель ALTEK ALT-63 потужністю 63 Вт з MPPT контролером.",
            "Сценарії: походи, подорожі, польові умови, заряд мобільних пристроїв, павербанків, ноутбуків, камер, рацій, телефонів, АКБ невеликої потужності та невеликих дронів.",
            "Виходи: USB 1 5В/2.4A, USB 2 5В/2.4A, USB-C 5В/3A, DC 19В/3A.",
            "Габарити: 865x700x5 мм у розкладеному стані, 290x175x65 мм у складеному стані.",
            "Вага: 1.65 кг. Комплектація: USB кабель, Type-C кабель, DC5521 кабель, кабель із затискачами, комплект роз'ємів 10 в 1.",
            "Гарантія: 12 місяців. Важливо: потрібне пряме сонячне проміння; не рекомендується залишати під дощем; заборонено заряджати літієві акумулятори від затискачів.",
        ]
    ),
}


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


def _bootstrap_product_card_skills(db_session, tmp_path) -> None:
    load_seed_prompts(db_session)
    for name, description in [
        ("ecommerce-product-normalization", "Normalize ecommerce product data."),
        ("ecommerce-aeo-product-description", "Generate AEO product descriptions."),
        ("ecommerce-customer-pain-research", "Research customer pain and proof map."),
        ("ecommerce-video-brief", "Prepare ecommerce video and Shorts briefs."),
    ]:
        _write_skill(tmp_path, name, description)
    sync_agent_skills(db_session, tmp_path)


def test_realistic_altek_solar_panel_product_card_flow(client, db_session, tmp_path):
    _bootstrap_product_card_skills(db_session, tmp_path)

    product_response = client.post("/api/products", json=ELEKTRONOM_ALTEK_ALT_63)
    assert product_response.status_code == 201
    product = product_response.json()
    assert product["source_url"] == ELEKTRONOM_ALTEK_ALT_63["source_url"]

    profile_response = client.post(
        f"/api/products/{product['id']}/content-profile/generate",
        json={"language": "uk"},
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["status"] == "draft"
    assert profile["generated_title"] == (
        "ALTEK Портативна сонячна батарея 63W чорний ALT-63"
    )
    assert profile["specifications_json"]["known"]["price"] == "4200.00"
    assert profile["specifications_json"]["known"]["currency"] == "UAH"
    assert profile["specifications_json"]["known"]["mpn"] == "ALT-63"
    assert profile["schema_json"]["offers"]["price"] == "4200.00"

    approved_profile = client.post(f"/api/products/{product['id']}/content-profile/approve")
    assert approved_profile.status_code == 200
    assert approved_profile.json()["status"] == "approved"

    task_response = client.post(
        "/api/tasks",
        json={
            "task_type": ContentTaskType.PRODUCT_CARD.value,
            "language": "uk",
            "product_id": product["id"],
            "topic": "Картка товару ALTEK ALT-63",
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    task = db_session.get(ContentTask, task_id)
    assert task is not None
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
    assert "ALT-63" in research_payload["markdown"]

    drafts = client.get(f"/api/tasks/{task_id}/drafts")
    assert drafts.status_code == 200
    assert [draft["kind"] for draft in drafts.json()] == ["initial", "critique", "final"]
    assert "Портативна сонячна батарея 63W" in drafts.json()[0]["body"]

    approve_task = client.post(
        f"/api/tasks/{task_id}/approve",
        json={"reviewer": "mock-marketer", "comment": "Realistic product card smoke approved."},
    )
    assert approve_task.status_code == 200

    package_response = client.post(f"/api/tasks/{task_id}/export-package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["status"] == "ready"
    assert package["package_json"]["task"]["product_id"] == product["id"]

    preview_response = client.post(f"/api/tasks/packages/{package['id']}/publication-preview")
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["payload_json"]["product_card_json"]["product_id"] == product["id"]
    assert preview["payload_json"]["schema_json"]["@graph"][1]["offers"]["price"] == "4200.00"

    media_brief_response = client.post(f"/api/tasks/packages/{package['id']}/media-brief")
    assert media_brief_response.status_code == 200
    media_brief = media_brief_response.json()
    assert media_brief["brief_json"]["pain_profile"]["confidence"] == "low"
    assert media_brief["brief_json"]["safety"]["real_video_generation_enabled"] is False

