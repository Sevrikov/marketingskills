def _product_payload() -> dict:
    return {
        "title": "ALTEK ALT-63 portable solar panel",
        "brand": "Altek",
        "model": "ALT-63",
        "category": "мобильные солнечные зарядки",
        "sku": "ALT-63-INFOGRAPHIC",
        "price": "3799.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://example.com/altek-alt-63",
        "raw_description": (
            "Портативная солнечная батарея для зарядки смартфонов, павербанков "
            "и туристического оборудования вдали от розетки."
        ),
    }


def test_infographic_project_data_pack_and_design_prompt(client):
    product = client.post("/api/products", json=_product_payload()).json()
    pain_profile = client.post(
        "/api/pain-profiles/generate",
        json={"product_id": product["id"], "language": "ru"},
    ).json()
    client.post(f"/api/pain-profiles/{pain_profile['id']}/approve", json={"reviewer": "editor"})

    create_response = client.post(
        "/api/infographics/projects",
        json={
            "product_id": product["id"],
            "title": "ALT-63 product card infographic",
            "infographic_type": "product_position",
            "target_channel": "product_card",
            "brand_style_json": {
                "name": "Elektronom clean product system",
                "palette": {"background": "#F8FAFC", "accent": "#0F766E", "ink": "#172033"},
                "typography": {"heading": "Inter", "body": "Inter"},
            },
        },
    )

    assert create_response.status_code == 201
    project = create_response.json()
    assert project["status"] == "draft"
    assert project["brand_style_json"]["name"] == "Elektronom clean product system"

    data_pack_response = client.post(
        f"/api/infographics/projects/{project['id']}/generate-data-pack"
    )

    assert data_pack_response.status_code == 200
    data_pack = data_pack_response.json()
    data = data_pack["data_pack_json"]
    assert data_pack["source_count"] >= 1
    assert data["scope"]["target_channel"] == "product_card"
    assert data["pain_profile"]["status"] == "approved"
    assert data["main_subject"]["price"]["currency"] == "UAH"
    assert {item["query_type"] for item in data["research_query_plan"]} == {
        "product_card_data_extraction",
        "image_infographic_context",
        "article_placement",
        "video_presentation",
    }
    assert {item["material"] for item in data["content_placement_plan"]} >= {
        "product_card",
        "seo_article",
        "video_presentation",
    }
    assert {item["key"] for item in data["pictogram_system"]} >= {
        "pain",
        "proof",
        "price",
        "autonomy",
        "pain_to_proof",
    }
    assert data["brand_style_block"]["name"] == "Elektronom clean product system"

    brief_response = client.post(f"/api/infographics/projects/{project['id']}/generate-brief")

    assert brief_response.status_code == 200
    brief = brief_response.json()
    assert brief["status"] == "design_prompt_ready"
    assert "Infographic Design Brief" in brief["brief_markdown"]
    assert brief["brief_json"]["dimensions"] == {"width": 1200, "height": 900}
    browser_prompt = brief["prompt_pack_json"]["browser_design_prompt"]
    assert "Do not add new facts" in browser_prompt
    assert "brand_style_block" in browser_prompt
    assert "pictograms" in browser_prompt.lower()

    list_response = client.get(f"/api/infographics/projects?product_id={product['id']}")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == project["id"]


def test_infographic_brief_requires_data_pack(client):
    product = client.post("/api/products", json=_product_payload()).json()
    project = client.post(
        "/api/infographics/projects",
        json={
            "product_id": product["id"],
            "title": "ALT-63 article infographic",
            "infographic_type": "article_aeo",
            "target_channel": "cms_article",
        },
    ).json()

    response = client.post(f"/api/infographics/projects/{project['id']}/generate-brief")

    assert response.status_code == 409
