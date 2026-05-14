from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DraftVersionDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class DraftVersionDecisionPayload(BaseModel):
    decision: DraftVersionDecision
    reviewer: str | None = Field(default="operator", max_length=255)
    comment: str | None = None


class ContentDraftRead(BaseModel):
    id: str
    task_id: str
    kind: str
    title: str | None
    body: str
    provider: str
    model: str
    prompt_template_key: str | None
    prompt_template_version: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
