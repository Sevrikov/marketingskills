from app.adapters.price_monitor import GENERIC_PRICE_EXTRACTOR_JS
from app.models.monitored_source import MonitoredSource
from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot


def test_create_capture_and_list_price_snapshots(client, db_session):
    product = Product(title="Competitor anchor product", currency="UAH")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_response = client.post(
        "/api/price-monitor/sources",
        json={
            "product_id": product.id,
            "url": "https://example.com/product-1",
            "label": "Competitor product 1",
            "expected_currency": "UAH",
        },
    )

    assert create_response.status_code == 201
    source = create_response.json()
    assert source["extractor_type"] == "generic_js"
    assert source["extractor_script"] == GENERIC_PRICE_EXTRACTOR_JS
    assert source["last_status"] is None

    capture_response = client.post(f"/api/price-monitor/sources/{source['id']}/capture")

    assert capture_response.status_code == 200
    snapshot = capture_response.json()
    assert snapshot["status"] == "captured"
    assert snapshot["price"] == "999.00"
    assert snapshot["currency"] == "UAH"
    assert snapshot["availability"] == "in_stock"

    updated_source_response = client.get(f"/api/price-monitor/sources/{source['id']}")
    assert updated_source_response.status_code == 200
    updated_source = updated_source_response.json()
    assert updated_source["last_price"] == "999.00"
    assert updated_source["last_status"] == "captured"

    list_response = client.get(f"/api/price-monitor/sources/{source['id']}/snapshots")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_price_monitor_source_not_found(client):
    response = client.post("/api/price-monitor/sources/missing/capture")

    assert response.status_code == 404


def test_run_price_monitor_once_records_price_change(client, db_session):
    source = MonitoredSource(
        url="https://example.com/product-2",
        label="Competitor product 2",
        extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
        expected_currency="UAH",
        last_price=1200,
        last_currency="UAH",
        last_availability="in_stock",
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    response = client.post("/api/price-monitor/run-once")

    assert response.status_code == 200
    assert response.json() == {"checked": 1, "snapshots": 1, "changes": 1, "errors": 0}

    changes_response = client.get("/api/price-monitor/changes")

    assert changes_response.status_code == 200
    changes = changes_response.json()
    assert len(changes) == 1
    assert changes[0]["event_type"] == "price_changed"
    assert changes[0]["old_price"] == "1200.00"
    assert changes[0]["new_price"] == "999.00"

    updated_source = client.get(f"/api/price-monitor/sources/{source.id}").json()
    assert updated_source["last_checked_at"] is not None
    assert updated_source["next_check_at"] is not None


def test_run_price_monitor_once_ignores_not_due_sources(client, db_session):
    source = MonitoredSource(
        url="https://example.com/product-3",
        extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
        is_active=False,
    )
    db_session.add(source)
    db_session.commit()

    response = client.post("/api/price-monitor/run-once")

    assert response.status_code == 200
    assert response.json()["checked"] == 0


def test_capture_without_previous_price_does_not_create_change_event(client, db_session):
    source = MonitoredSource(
        url="https://example.com/product-4",
        extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    response = client.post(f"/api/price-monitor/sources/{source.id}/capture")

    assert response.status_code == 200
    assert db_session.query(PriceSnapshot).count() == 1
    assert client.get("/api/price-monitor/changes").json() == []


def test_price_group_market_index_and_trend_event(client, db_session):
    group_response = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Portable power stations",
            "category": "power",
            "top_position_limit": 2,
            "min_sources_for_signal": 3,
        },
    )
    assert group_response.status_code == 201
    group = group_response.json()

    for index, price in enumerate([1000, 1100, 1200], start=1):
        source = MonitoredSource(
            price_group_id=group["id"],
            url=f"https://example.com/group-product-{index}",
            extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
            market_position=index,
            source_priority=index,
            last_price=price,
            last_currency="UAH",
            last_availability="in_stock",
        )
        db_session.add(source)
    db_session.commit()

    first_index_response = client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    assert first_index_response.status_code == 200
    first_index = first_index_response.json()
    assert first_index["source_count"] == 3
    assert first_index["avg_price"] == "1100.00"
    assert first_index["median_price"] == "1100.00"
    assert first_index["top_sources_avg_price"] == "1050.00"
    assert first_index["availability_rate"] == "1.0000"

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [900, 990, 1080], strict=False):
        source.last_price = price
    db_session.commit()

    second_index_response = client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    assert second_index_response.status_code == 200
    assert second_index_response.json()["avg_price"] == "990.00"

    trend_response = client.get(f"/api/price-monitor/trend-events?group_id={group['id']}")

    assert trend_response.status_code == 200
    trends = trend_response.json()
    assert len(trends) == 1
    assert trends[0]["event_type"] == "mass_price_drop"
    assert trends[0]["severity"] == "high"
    assert trends[0]["affected_sources_count"] == 3


def test_market_index_rejects_missing_group(client):
    response = client.post("/api/price-monitor/groups/missing/market-indexes")

    assert response.status_code == 404


def test_notification_policy_evaluates_high_severity_trends(client, db_session):
    group = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Smart speakers",
            "min_sources_for_signal": 3,
        },
    ).json()
    for index, price in enumerate([1000, 1100, 1200], start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                url=f"https://example.com/speaker-{index}",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=index,
                last_price=price,
                last_currency="UAH",
                last_availability="in_stock",
            )
        )
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [800, 880, 960], strict=False):
        source.last_price = price
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    policy_response = client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "High trend digest",
            "delivery_mode": "digest",
            "min_severity": "high",
            "min_affected_sources": 3,
            "min_percent_change": "10.0",
        },
    )
    assert policy_response.status_code == 201

    evaluate_response = client.post("/api/price-monitor/notification-policies/evaluate")

    assert evaluate_response.status_code == 200
    assert evaluate_response.json() == {
        "evaluated": 1,
        "ready_immediate": 0,
        "queued_digest": 1,
        "suppressed": 0,
    }
    trends = client.get(f"/api/price-monitor/trend-events?group_id={group['id']}").json()
    assert trends[0]["notify_status"] == "queued_digest"


def test_notification_policy_suppresses_low_impact_trends(client, db_session):
    group = client.post(
        "/api/price-monitor/groups",
        json={"name": "Routers", "min_sources_for_signal": 1},
    ).json()
    db_session.add(
        MonitoredSource(
            price_group_id=group["id"],
            url="https://example.com/router",
            extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
            last_price=1000,
            last_currency="UAH",
            last_availability="in_stock",
        )
    )
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    source = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).one()
    source.last_price = 950
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "Only high immediate",
            "delivery_mode": "immediate",
            "min_severity": "high",
            "min_affected_sources": 1,
            "min_percent_change": "10.0",
        },
    )

    evaluate_response = client.post("/api/price-monitor/notification-policies/evaluate")

    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["suppressed"] == 1


def test_send_market_trend_digest_marks_queued_events_sent(client, db_session):
    group = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Robot vacuums",
            "min_sources_for_signal": 3,
        },
    ).json()
    for index, price in enumerate([1000, 1100, 1200], start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                url=f"https://example.com/vacuum-{index}",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=index,
                last_price=price,
                last_currency="UAH",
                last_availability="in_stock",
            )
        )
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [800, 880, 960], strict=False):
        source.last_price = price
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "Digest high market moves",
            "delivery_mode": "digest",
            "min_severity": "high",
            "min_affected_sources": 3,
            "min_percent_change": "10.0",
        },
    )
    client.post("/api/price-monitor/notification-policies/evaluate")

    send_response = client.post("/api/price-monitor/trend-digests/send")

    assert send_response.status_code == 200
    assert send_response.json() == {"events": 1, "deliveries": 1}
    trends = client.get(f"/api/price-monitor/trend-events?group_id={group['id']}").json()
    assert trends[0]["notify_status"] == "sent_digest"
    assert trends[0]["metadata_json"]["digest_delivery"][0]["provider"] == "mock-notifications"


def test_run_market_digest_batch_creates_batch_and_marks_events(client, db_session):
    group = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Action cameras",
            "min_sources_for_signal": 3,
        },
    ).json()
    for index, price in enumerate([1000, 1100, 1200], start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                url=f"https://example.com/camera-{index}",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=index,
                last_price=price,
                last_currency="UAH",
                last_availability="in_stock",
            )
        )
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [800, 880, 960], strict=False):
        source.last_price = price
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "Batch digest",
            "delivery_mode": "digest",
            "min_severity": "high",
            "min_affected_sources": 3,
            "min_percent_change": "10.0",
        },
    )
    client.post("/api/price-monitor/notification-policies/evaluate")

    run_response = client.post("/api/price-monitor/trend-digests/run-batch")

    assert run_response.status_code == 200
    batch_result = run_response.json()
    assert batch_result["events"] == 1
    assert batch_result["deliveries"] == 1
    assert batch_result["status"] == "sent"
    assert batch_result["batch_id"] is not None

    batches_response = client.get("/api/price-monitor/trend-digests/batches")
    assert batches_response.status_code == 200
    batches = batches_response.json()
    assert len(batches) == 1
    assert batches[0]["event_count"] == 1
    assert batches[0]["delivery_json"]["deliveries"][0]["provider"] == "mock-notifications"

    trends = client.get(f"/api/price-monitor/trend-events?group_id={group['id']}").json()
    assert trends[0]["notify_status"] == "sent_digest"
    assert trends[0]["metadata_json"]["digest_batch_id"] == batch_result["batch_id"]


def test_send_immediate_market_trend_alerts_marks_ready_events_sent(client, db_session):
    group = client.post(
        "/api/price-monitor/groups",
        json={
            "name": "Gaming laptops",
            "min_sources_for_signal": 3,
        },
    ).json()
    for index, price in enumerate([1000, 1100, 1200], start=1):
        db_session.add(
            MonitoredSource(
                price_group_id=group["id"],
                url=f"https://example.com/laptop-{index}",
                extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
                market_position=index,
                last_price=price,
                last_currency="UAH",
                last_availability="in_stock",
            )
        )
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")

    sources = db_session.query(MonitoredSource).filter_by(price_group_id=group["id"]).all()
    for source, price in zip(sources, [1250, 1375, 1500], strict=False):
        source.last_price = price
    db_session.commit()
    client.post(f"/api/price-monitor/groups/{group['id']}/market-indexes")
    client.post(
        "/api/price-monitor/notification-policies",
        json={
            "name": "Immediate critical market moves",
            "delivery_mode": "immediate",
            "min_severity": "high",
            "min_affected_sources": 3,
            "min_percent_change": "10.0",
        },
    )
    evaluate_response = client.post("/api/price-monitor/notification-policies/evaluate")
    assert evaluate_response.json()["ready_immediate"] == 1

    send_response = client.post("/api/price-monitor/trend-alerts/send")

    assert send_response.status_code == 200
    assert send_response.json() == {"events": 1, "deliveries": 1}
    trends = client.get(f"/api/price-monitor/trend-events?group_id={group['id']}").json()
    assert trends[0]["notify_status"] == "sent_immediate"
    assert trends[0]["metadata_json"]["immediate_delivery"][0]["provider"] == "mock-notifications"
