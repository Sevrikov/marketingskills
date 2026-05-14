from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PainProfileGenerate(BaseModel):
    product_id: str | None = None
    source_task_id: str | None = None
    source_research_report_id: str | None = None
    scope_type: str = Field(default="product", max_length=64)
    scope_id: str | None = Field(default=None, max_length=255)
    language: str = Field(default="ru", max_length=16)


class PainProfileApprove(BaseModel):
    reviewer: str | None = Field(default=None, max_length=255)
    comment: str | None = None


class PainProfileRead(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    product_id: str | None
    status: str
    primary_pain_summary: str
    confidence: str
    profile_json: dict[str, Any]
    source_task_id: str | None
    source_research_report_id: str | None
    approved_by: str | None
    approved_at: datetime | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
