def test_create_and_get_product(client):
    create_response = client.post(
        "/api/products",
        json={
            "title": "Starlink Mini",
            "brand": "Starlink",
            "model": "Mini",
            "category": "satellite internet",
            "price": "499.00",
            "currency": "USD",
        },
    )

    assert create_response.status_code == 201
    product = create_response.json()
    assert product["title"] == "Starlink Mini"

    get_response = client.get(f"/api/products/{product['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == product["id"]


def test_product_not_found(client):
    response = client.get("/api/products/missing")

    assert response.status_code == 404
