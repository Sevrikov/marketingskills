from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.scheduler import (
    ScheduledJobCreate,
    ScheduledJobRead,
    ScheduledJobRunRead,
    ScheduledJobUpdate,
    SchedulerRunDueResult,
)
from app.services.scheduler import (
    ScheduledJobAlreadyExists,
    UnsupportedScheduledJobType,
    create_scheduled_job,
    get_scheduled_job_by_key,
    list_scheduled_job_runs,
    list_scheduled_jobs,
    run_due_scheduled_jobs,
    run_scheduled_job,
    update_scheduled_job,
)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.post("/jobs", response_model=ScheduledJobRead, status_code=status.HTTP_201_CREATED)
def create_scheduled_job_endpoint(
    payload: ScheduledJobCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_scheduled_job(db, payload)
    except ScheduledJobAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UnsupportedScheduledJobType as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[ScheduledJobRead])
def list_scheduled_jobs_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_defaults: bool = True,
    db: Session = Depends(get_db),
):
    return list_scheduled_jobs(
        db,
        limit=limit,
        offset=offset,
        include_defaults=include_defaults,
    )


@router.patch("/jobs/{job_key}", response_model=ScheduledJobRead)
def update_scheduled_job_endpoint(
    job_key: str,
    payload: ScheduledJobUpdate,
    db: Session = Depends(get_db),
):
    job = get_scheduled_job_by_key(db, job_key)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")
    return update_scheduled_job(db, job, payload)


@router.post("/jobs/{job_key}/run-now", response_model=ScheduledJobRunRead)
def run_scheduled_job_now_endpoint(
    job_key: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    job = get_scheduled_job_by_key(db, job_key)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled job not found")
    return run_scheduled_job(db, job, settings, trigger="manual")


@router.post("/run-due", response_model=SchedulerRunDueResult)
def run_due_scheduled_jobs_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    summary = run_due_scheduled_jobs(db, settings, limit=limit)
    return SchedulerRunDueResult(
        checked=summary.checked,
        started=summary.started,
        succeeded=summary.succeeded,
        failed=summary.failed,
        skipped=summary.skipped,
        runs=summary.runs,
    )


@router.get("/runs", response_model=list[ScheduledJobRunRead])
def list_scheduled_job_runs_endpoint(
    job_key: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_scheduled_job_runs(db, job_key=job_key, limit=limit, offset=offset)
