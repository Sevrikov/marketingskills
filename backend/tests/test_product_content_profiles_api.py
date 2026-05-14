def _create_product(client):
    response = client.post(
        "/api/products",
        json={
            "title": "Starlink Mini",
            "brand": "Starlink",
            "model": "Mini",
            "category": "satellite internet",
            "sku": "SL-MINI-TEST",
            "price": "499.00",
            "currency": "USD",
            "availability": "in_stock",
            "raw_description": "Compact satellite internet kit for travel and backup connectivity.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_generate_get_patch_and_approve_product_content_profile(client):
    product = _create_product(client)

    generate_response = client.post(
        f"/api/products/{product['id']}/content-profile/generate",
        json={"language": "ru"},
    )

    assert generate_response.status_code == 200
    profile = generate_response.json()
    assert profile["product_id"] == product["id"]
    assert profile["status"] == "draft"
    assert profile["schema_json"]["@type"] == "Product"
    assert profile["schema_json"]["offers"]["availability"] == "https://schema.org/InStock"
    assert profile["specifications_json"]["known"]["sku"] == "SL-MINI-TEST"
    assert profile["faq_json"]
    assert "ecommerce-aeo-product-description" in profile["metadata_json"]["skills"]

    get_response = client.get(f"/api/products/{product['id']}/content-profile")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == profile["id"]

    patch_response = client.patch(
        f"/api/products/{product['id']}/content-profile",
        json={"seo_title": "Custom SEO title"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["seo_title"] == "Custom SEO title"

    approve_response = client.post(f"/api/products/{product['id']}/content-profile/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_product_content_profile_missing_before_generation(client):
    product = _create_product(client)

    response = client.get(f"/api/products/{product['id']}/content-profile")

    assert response.status_code == 404


def test_product_content_profile_product_not_found(client):
    response = client.post(
        "/api/products/missing/content-profile/generate",
        json={"language": "ru"},
    )

    assert response.status_code == 404
