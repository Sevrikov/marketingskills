from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.adapters.factory import build_notification_adapter, build_price_monitor_adapter
from app.config import Settings
from app.models.scheduled_job import ScheduledJob
from app.models.scheduled_job_run import ScheduledJobRun
from app.schemas.scheduler import ScheduledJobCreate, ScheduledJobUpdate
from app.services.price_monitor import (
    evaluate_price_trend_notification_policies,
    run_due_price_monitor_checks,
    run_market_digest_batch,
    send_ready_market_trend_alerts,
)

SUPPORTED_JOB_TYPES = {
    "price_monitor_due_checks",
    "price_trend_policy_evaluation",
    "market_trend_immediate_alerts",
    "market_digest_batch",
}

DEFAULT_SCHEDULED_JOBS = [
    {
        "job_key": "price-monitor-due-checks",
        "job_type": "price_monitor_due_checks",
        "name": "Price monitor due checks",
        "description": "Capture due price snapshots for known product and competitor URLs.",
        "interval_minutes": 15,
        "params_json": {"limit": 20},
    },
    {
        "job_key": "price-trend-policy-evaluation",
        "job_type": "price_trend_policy_evaluation",
        "name": "Price trend policy evaluation",
        "description": "Classify pending market trend events for immediate alerts or digests.",
        "interval_minutes": 15,
        "params_json": {"limit": 100},
    },
    {
        "job_key": "market-trend-immediate-alerts",
        "job_type": "market_trend_immediate_alerts",
        "name": "Market trend immediate alerts",
        "description": "Send ready immediate market trend alerts through notification adapters.",
        "interval_minutes": 10,
        "params_json": {"limit": 10},
    },
    {
        "job_key": "market-digest-batch",
        "job_type": "market_digest_batch",
        "name": "Market digest batch",
        "description": "Send queued market trend digest batches.",
        "interval_minutes": 720,
        "params_json": {"limit": 20},
    },
]


class ScheduledJobAlreadyExists(ValueError):
    pass


class UnsupportedScheduledJobType(ValueError):
    pass


def create_scheduled_job(db: Session, data: ScheduledJobCreate) -> ScheduledJob:
    if data.job_type not in SUPPORTED_JOB_TYPES:
        raise UnsupportedScheduledJobType(f"Unsupported scheduled job type: {data.job_type}.")
    if get_scheduled_job_by_key(db, data.job_key) is not None:
        raise ScheduledJobAlreadyExists(f"Scheduled job already exists: {data.job_key}.")
    payload = data.model_dump()
    if payload.get("next_run_at") is None:
        payload["next_run_at"] = _utc_now()
    job = ScheduledJob(**payload)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def ensure_default_scheduled_jobs(db: Session, now: datetime | None = None) -> list[ScheduledJob]:
    now = now or _utc_now()
    jobs: list[ScheduledJob] = []
    changed = False
    for item in DEFAULT_SCHEDULED_JOBS:
        job = get_scheduled_job_by_key(db, item["job_key"])
        if job is None:
            job = ScheduledJob(
                status="active",
                is_active=True,
                next_run_at=now,
                metadata_json={"source": "default_registry"},
                **item,
            )
            db.add(job)
            changed = True
        jobs.append(job)
    if changed:
        db.commit()
        for job in jobs:
            db.refresh(job)
    return jobs


def list_scheduled_jobs(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    include_defaults: bool = True,
) -> list[ScheduledJob]:
    if include_defaults:
        ensure_default_scheduled_jobs(db)
    stmt = select(ScheduledJob).order_by(ScheduledJob.created_at.asc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_scheduled_job_by_key(db: Session, job_key: str) -> ScheduledJob | None:
    stmt = select(ScheduledJob).where(ScheduledJob.job_key == job_key)
    return db.scalars(stmt).first()


def update_scheduled_job(
    db: Session,
    job: ScheduledJob,
    data: ScheduledJobUpdate,
) -> ScheduledJob:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_scheduled_job_runs(
    db: Session,
    job_key: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ScheduledJobRun]:
    stmt = select(ScheduledJobRun).order_by(
        ScheduledJobRun.started_at.desc(),
        ScheduledJobRun.id.desc(),
    )
    if job_key:
        stmt = stmt.where(ScheduledJobRun.job_key == job_key)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def list_due_scheduled_jobs(
    db: Session,
    limit: int = 20,
    now: datetime | None = None,
) -> list[ScheduledJob]:
    now = now or _utc_now()
    ensure_default_scheduled_jobs(db, now=now)
    stmt = (
        select(ScheduledJob)
        .where(ScheduledJob.is_active.is_(True))
        .where(ScheduledJob.status == "active")
        .where(or_(ScheduledJob.next_run_at.is_(None), ScheduledJob.next_run_at <= now))
        .order_by(ScheduledJob.next_run_at.asc(), ScheduledJob.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


@dataclass(frozen=True)
class SchedulerRunDueSummary:
    checked: int
    started: int
    succeeded: int
    failed: int
    skipped: int
    runs: list[ScheduledJobRun]


def run_due_scheduled_jobs(
    db: Session,
    settings: Settings,
    limit: int = 20,
    now: datetime | None = None,
) -> SchedulerRunDueSummary:
    now = now or _utc_now()
    jobs = list_due_scheduled_jobs(db, limit=limit, now=now)
    runs: list[ScheduledJobRun] = []
    for job in jobs:
        runs.append(run_scheduled_job(db, job, settings, trigger="schedule", now=now))
    succeeded = sum(1 for run in runs if run.status == "succeeded")
    failed = sum(1 for run in runs if run.status == "failed")
    skipped = sum(1 for run in runs if run.status == "skipped")
    return SchedulerRunDueSummary(
        checked=len(jobs),
        started=len(runs),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        runs=runs,
    )


def run_scheduled_job(
    db: Session,
    job: ScheduledJob,
    settings: Settings,
    trigger: str = "manual",
    now: datetime | None = None,
) -> ScheduledJobRun:
    now = now or _utc_now()
    run = ScheduledJobRun(
        job_id=job.id,
        job_key=job.job_key,
        job_type=job.job_type,
        trigger=trigger,
        status="running",
        started_at=now,
    )
    db.add(run)
    db.flush()
    try:
        if not job.is_active or job.status != "active":
            summary = {"reason": "job_inactive", "job_status": job.status}
            _finish_run(db, job, run, now, "skipped", summary=summary)
            return run
        summary = _execute_job(db, job, settings)
        _finish_run(db, job, run, now, "succeeded", summary=summary)
        return run
    except Exception as exc:
        _finish_run(db, job, run, now, "failed", error=str(exc)[:1000])
        return run


def _execute_job(db: Session, job: ScheduledJob, settings: Settings) -> dict[str, Any]:
    params = job.params_json or {}
    limit = int(params.get("limit", 20))
    if job.job_type == "price_monitor_due_checks":
        summary = run_due_price_monitor_checks(
            db,
            adapter=build_price_monitor_adapter(settings),
            limit=limit,
        )
        return {
            "checked": summary.checked,
            "snapshots": summary.snapshots,
            "changes": summary.changes,
            "errors": summary.errors,
        }
    if job.job_type == "price_trend_policy_evaluation":
        summary = evaluate_price_trend_notification_policies(db, limit=limit)
        return {
            "evaluated": summary.evaluated,
            "ready_immediate": summary.ready_immediate,
            "queued_digest": summary.queued_digest,
            "suppressed": summary.suppressed,
        }
    if job.job_type == "market_trend_immediate_alerts":
        summary = send_ready_market_trend_alerts(
            db,
            adapter=build_notification_adapter(settings),
            console_url=settings.operator_console_url,
            limit=limit,
        )
        return {"events": summary.events, "deliveries": summary.deliveries}
    if job.job_type == "market_digest_batch":
        summary = run_market_digest_batch(
            db,
            adapter=build_notification_adapter(settings),
            console_url=settings.operator_console_url,
            limit=limit,
        )
        return {
            "batch_id": summary.batch_id,
            "events": summary.events,
            "deliveries": summary.deliveries,
            "status": summary.status,
        }
    raise UnsupportedScheduledJobType(f"Unsupported scheduled job type: {job.job_type}.")


def _finish_run(
    db: Session,
    job: ScheduledJob,
    run: ScheduledJobRun,
    now: datetime,
    status: str,
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    finished_at = _utc_now()
    run.status = status
    run.finished_at = finished_at
    run.summary_json = summary
    run.error_message = error
    job.last_run_at = now
    job.last_status = status
    job.last_error = error
    job.next_run_at = now + timedelta(minutes=max(job.interval_minutes, 1))
    db.add(job)
    db.add(run)
    db.commit()
    db.refresh(run)
    db.refresh(job)


def _utc_now() -> datetime:
    return datetime.now(UTC)
