from datetime import UTC, datetime, timedelta

from app.adapters.price_monitor import GENERIC_PRICE_EXTRACTOR_JS
from app.models.monitored_source import MonitoredSource


def test_scheduler_lists_default_jobs(client):
    response = client.get("/api/scheduler/jobs")

    assert response.status_code == 200
    jobs = response.json()
    job_keys = {job["job_key"] for job in jobs}
    assert "price-monitor-due-checks" in job_keys
    assert "market-digest-batch" in job_keys
    assert all(job["is_active"] for job in jobs)


def test_scheduler_create_update_and_run_price_monitor_job(client, db_session):
    source = MonitoredSource(
        url="https://example.com/scheduled-product",
        extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
        expected_currency="UAH",
    )
    db_session.add(source)
    db_session.commit()

    create_response = client.post(
        "/api/scheduler/jobs",
        json={
            "job_key": "custom-price-monitor",
            "job_type": "price_monitor_due_checks",
            "name": "Custom price monitor",
            "interval_minutes": 30,
            "params_json": {"limit": 5},
        },
    )
    assert create_response.status_code == 201
    job = create_response.json()
    assert job["job_key"] == "custom-price-monitor"

    patch_response = client.patch(
        "/api/scheduler/jobs/custom-price-monitor",
        json={"interval_minutes": 45, "params_json": {"limit": 2}},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["interval_minutes"] == 45

    run_response = client.post("/api/scheduler/jobs/custom-price-monitor/run-now")

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "succeeded"
    assert run["trigger"] == "manual"
    assert run["summary_json"]["checked"] == 1
    assert run["summary_json"]["snapshots"] == 1

    runs_response = client.get("/api/scheduler/runs?job_key=custom-price-monitor")
    assert runs_response.status_code == 200
    assert len(runs_response.json()) == 1


def test_scheduler_run_due_runs_default_jobs(client, db_session):
    source = MonitoredSource(
        url="https://example.com/due-product",
        extractor_script=GENERIC_PRICE_EXTRACTOR_JS,
        expected_currency="UAH",
    )
    db_session.add(source)
    db_session.commit()

    response = client.post("/api/scheduler/run-due?limit=4")

    assert response.status_code == 200
    result = response.json()
    assert result["checked"] == 4
    assert result["started"] == 4
    assert result["failed"] == 0
    job_keys = {run["job_key"] for run in result["runs"]}
    assert "price-monitor-due-checks" in job_keys
    assert "price-trend-policy-evaluation" in job_keys


def test_scheduler_inactive_job_run_is_skipped(client):
    client.post(
        "/api/scheduler/jobs",
        json={
            "job_key": "paused-digest",
            "job_type": "market_digest_batch",
            "name": "Paused digest",
            "interval_minutes": 60,
            "is_active": False,
            "params_json": {"limit": 10},
        },
    )

    response = client.post("/api/scheduler/jobs/paused-digest/run-now")

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "skipped"
    assert run["summary_json"]["reason"] == "job_inactive"


def test_scheduler_rejects_unsupported_job_type(client):
    response = client.post(
        "/api/scheduler/jobs",
        json={
            "job_key": "future-stock-sync",
            "job_type": "stock_sync",
            "name": "Future stock sync",
            "interval_minutes": 30,
        },
    )

    assert response.status_code == 400


def test_scheduler_does_not_run_future_jobs(client):
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.post(
        "/api/scheduler/jobs",
        json={
            "job_key": "future-digest",
            "job_type": "market_digest_batch",
            "name": "Future digest",
            "interval_minutes": 60,
            "next_run_at": future,
        },
    )

    response = client.post("/api/scheduler/run-due?limit=10")

    assert response.status_code == 200
    job_keys = {run["job_key"] for run in response.json()["runs"]}
    assert "future-digest" not in job_keys
