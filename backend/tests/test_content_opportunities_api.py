from app.models.price_group import PriceGroup
from app.models.product import Product


def test_discover_content_opportunities_for_product(client, db_session):
    product = Product(
        title="Starlink Mini",
        brand="Starlink",
        model="Mini",
        category="satellite internet",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post(
        "/api/content-opportunities/discover",
        json={"product_id": product.id, "language": "ru", "market": "UA", "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 3
    assert payload["provider"] == "mock-source-provider"
    assert payload["research_provider"] == "mock-research"
    opportunities = payload["opportunities"]
    assert opportunities[0]["scope_type"] == "product"
    assert opportunities[0]["product_id"] == product.id
    assert opportunities[0]["intent"] == "commercial"
    assert opportunities[0]["sources_json"]


def test_discover_content_opportunities_for_price_group(client, db_session):
    group = PriceGroup(
        name="Portable power stations",
        category="power",
        brand="EcoFlow",
        keywords="backup power camping power station",
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        "/api/content-opportunities/discover",
        json={"price_group_id": group.id, "language": "ru", "limit": 2},
    )

    assert response.status_code == 200
    opportunities = response.json()["opportunities"]
    assert len(opportunities) == 2
    assert opportunities[0]["scope_type"] == "price_group"
    assert opportunities[0]["price_group_id"] == group.id
    assert opportunities[0]["brand"] == "EcoFlow"


def test_list_opportunities_and_create_article_task(client, db_session):
    discover = client.post(
        "/api/content-opportunities/discover",
        json={"brand": "Xiaomi", "category": "smartphones", "limit": 1},
    ).json()
    opportunity = discover["opportunities"][0]

    list_response = client.get("/api/content-opportunities")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == opportunity["id"]

    task_response = client.post(
        f"/api/content-opportunities/{opportunity['id']}/create-task",
    )

    assert task_response.status_code == 200
    result = task_response.json()
    assert result["opportunity_id"] == opportunity["id"]
    assert result["task_status"] == "draft"

    updated = client.get("/api/content-opportunities").json()[0]
    assert updated["status"] == "task_created"
    assert updated["created_task_id"] == result["task_id"]


def test_discover_opportunities_rejects_missing_scope(client):
    response = client.post(
        "/api/content-opportunities/discover",
        json={"product_id": "missing", "limit": 1},
    )

    assert response.status_code == 404


def test_create_task_from_missing_opportunity(client):
    response = client.post("/api/content-opportunities/missing/create-task")

    assert response.status_code == 404
