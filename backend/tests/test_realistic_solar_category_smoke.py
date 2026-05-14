from decimal import Decimal

from app.adapters.price_monitor import GENERIC_PRICE_EXTRACTOR_JS
from app.models.monitored_source import MonitoredSource
from app.seed.load_prompts import load_seed_prompts
from app.services.skill_registry import sync_agent_skills


ELEKTRONOM_SOLAR_CATEGORY_URL = (
    "https://elektronom.com.ua/ua/g117987855-mobilnye-solnechnye-zaryadki"
)

SOLAR_CATEGORY_PRODUCTS = [
    {
        "title": "Портативна сонячна батарея для смартфонів USB 28W 5V хакі",
        "brand": "ALTEK",
        "model": "ALT-28",
        "category": "Мобільні сонячні зарядки",
        "sku": "ALT-28-KHAKI",
        "mpn": "ALT-28",
        "price": "2200.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p1874719214-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Складна портативна сонячна батарея 28W 5V для зарядки смартфонів через USB у подорожах і польових умовах.",
    },
    {
        "title": "Сонячний модуль 70 Вт 12В-18В 4А гнучкий з люверсами",
        "brand": None,
        "model": "ALF-70W",
        "category": "Мобільні сонячні зарядки",
        "sku": "2115787",
        "mpn": "ALF-70W",
        "price": "2600.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p2930987570-solnezhnyj-modul-12v.html",
        "raw_description": "Гнучкий сонячний модуль 70 Вт 12В-18В 4А з люверсами для мобільного або тимчасового живлення.",
    },
    {
        "title": "Портативна сонячна батарея для смартфонів USB 28W 5V чорна",
        "brand": "ALTEK",
        "model": "ALT-28",
        "category": "Мобільні сонячні зарядки",
        "sku": "ALT-28-BLACK",
        "mpn": "ALT-28",
        "price": "2100.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p1856897285-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Портативна чорна сонячна батарея 28W 5V ALTEK ALT-28 для USB зарядки смартфонів.",
    },
    {
        "title": "Портативна сонячна розкладна батарея 7.5 Вт 5В 1.5А",
        "brand": "Kraft",
        "model": "TPB-SLP5F",
        "category": "Мобільні сонячні зарядки",
        "sku": "43-00045",
        "mpn": "TPB-SLP5F",
        "price": "970.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p2393114226-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Компактна розкладна сонячна батарея 7.5 Вт для базової зарядки невеликих пристроїв.",
    },
    {
        "title": "Портативна сонячна батарея 14W чорна",
        "brand": "ALTEK",
        "model": "ALT-14",
        "category": "Мобільні сонячні зарядки",
        "sku": "ALT-14",
        "mpn": "ALT-14",
        "price": "1200.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p1856897286-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Портативна сонячна батарея 14W ALTEK ALT-14 для легкого мобільного заряджання.",
    },
    {
        "title": "Портативна сонячна батарея розкладна 36W USB та штекер ноутбуку",
        "brand": "ALTEK",
        "model": "ALT-36",
        "category": "Мобільні сонячні зарядки",
        "sku": "ALT-36",
        "mpn": "ALT-36",
        "price": "3600.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p1856897287-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Розкладна сонячна батарея 36W ALTEK ALT-36 з USB та універсальним штекером ноутбуку.",
    },
    {
        "title": "Портативна сонячна батарея розкладна 100 Вт 20В KFP-100SP",
        "brand": "Kraft",
        "model": "KFP-100SP",
        "category": "Мобільні сонячні зарядки",
        "sku": "42-00065",
        "mpn": "KFP-100SP",
        "price": "4950.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p2393114255-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Розкладна портативна сонячна батарея 100 Вт 20В для потужнішого автономного живлення.",
    },
    {
        "title": "Портативна сонячна батарея 63W чорний",
        "brand": "ALTEK",
        "model": "ALT-63",
        "category": "Мобільні сонячні зарядки",
        "sku": "ALT-63-BLACK",
        "mpn": "ALT-63",
        "price": "4200.00",
        "currency": "UAH",
        "availability": "in_stock",
        "source_url": "https://elektronom.com.ua/ua/p1859660505-portativnaya-solnechnaya-batareya.html",
        "raw_description": "Монокристалічна сонячна панель 63W ALTEK ALT-63 з MPPT контролером, USB-C 5В/3A та DC 19В/3A.",
    },
]


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


def _bootstrap_category_skills(db_session, tmp_path) -> None:
    load_seed_prompts(db_session)
    for name, description in [
        ("ecommerce-product-normalization", "Normalize ecommerce product data."),
        ("ecommerce-aeo-product-description", "Generate AEO product descriptions."),
        ("ecommerce-customer-pain-research", "Research customer pain and proof map."),
    ]:
        _write_skill(tmp_path, name, description)
    sync_agent_skills(db_session, tmp_path)


def test_realistic_solar_category_product_cards_and_market_index(client, db_session, tmp_path):
    _bootstrap_category_skills(db_session, tmp_path)

    created_products = []
    for payload in SOLAR_CATEGORY_PRODUCTS:
        response = client.post("/api/products", json=payload)
        assert response.status_code == 201
        created = response.json()
        created_products.append(created)

        profile_response = client.post(
            f"/api/products/{created['id']}/content-profile/generate",
            json={"language": "uk"},
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["status"] == "draft"
        assert profile["specifications_json"]["known"]["price"] == payload["price"]
        assert profile["schema_json"]["offers"]["price"] == payload["price"]

    assert len(created_products) == len(SOLAR_CATEGORY_PRODUCTS)

    group_response = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Мобільні сонячні зарядки Elektronom",
            "category": "Мобільні сонячні зарядки",
            "keywords": "сонячна батарея USB портативна зарядка ALTEK Kraft",
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
    market_index = market_index_response.json()
    assert market_index["source_count"] == 8
    assert market_index["min_price"] == "970.00"
    assert market_index["max_price"] == "4950.00"
    assert market_index["avg_price"] == "2727.50"
    assert market_index["median_price"] == "2400.00"
    assert market_index["top_sources_avg_price"] == "2300.00"
    assert market_index["availability_rate"] == "1.0000"

    opportunity_response = client.post(
        "/api/content-opportunities/discover",
        json={"price_group_id": group["id"], "language": "uk", "market": "UA", "limit": 2},
    )
    assert opportunity_response.status_code == 200
    opportunities = opportunity_response.json()["opportunities"]
    assert len(opportunities) == 2
    assert opportunities[0]["scope_type"] == "price_group"
    assert opportunities[0]["price_group_id"] == group["id"]

    list_sources_response = client.get(f"/api/price-monitor/sources?product_id={created_products[0]['id']}")
    assert list_sources_response.status_code == 200
    assert len(list_sources_response.json()) == 1

