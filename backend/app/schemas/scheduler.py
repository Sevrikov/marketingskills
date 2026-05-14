from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScheduledJobCreate(BaseModel):
    job_key: str = Field(min_length=1, max_length=128)
    job_type: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="active", max_length=64)
    is_active: bool = True
    interval_minutes: int = Field(default=60, ge=1)
    next_run_at: datetime | None = None
    params_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] | None = None


class ScheduledJobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1)
    next_run_at: datetime | None = None
    params_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


class ScheduledJobRead(BaseModel):
    id: str
    job_key: str
    job_type: str
    name: str
    description: str | None
    status: str
    is_active: bool
    interval_minutes: int
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_status: str | None
    last_error: str | None
    params_json: dict[str, Any]
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduledJobRunRead(BaseModel):
    id: str
    job_id: str
    job_key: str
    job_type: str
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulerRunDueResult(BaseModel):
    checked: int
    started: int
    succeeded: int
    failed: int
    skipped: int
    runs: list[ScheduledJobRunRead]
