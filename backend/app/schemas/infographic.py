from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InfographicProjectCreate(BaseModel):
    scope_type: str = Field(default="product", max_length=64)
    scope_id: str | None = Field(default=None, max_length=255)
    product_id: str | None = None
    source_task_id: str | None = None
    source_research_report_id: str | None = None
    title: str = Field(min_length=1, max_length=500)
    infographic_type: str = Field(default="product_position", max_length=64)
    target_channel: str = Field(default="product_card", max_length=64)
    created_by: str | None = Field(default=None, max_length=255)
    brand_style_json: dict[str, Any] | None = None


class InfographicProjectRead(BaseModel):
    id: str
    scope_type: str
    scope_id: str | None
    product_id: str | None
    source_task_id: str | None
    source_research_report_id: str | None
    title: str
    infographic_type: str
    target_channel: str
    status: str
    created_by: str | None
    brand_style_json: dict[str, Any] | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InfographicDataPackRead(BaseModel):
    id: str
    project_id: str
    data_pack_json: dict[str, Any]
    source_count: int
    missing_fields_json: list[dict[str, Any]]
    confidence_score: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InfographicDesignBriefRead(BaseModel):
    id: str
    project_id: str
    data_pack_id: str | None
    status: str
    brief_markdown: str
    brief_json: dict[str, Any]
    prompt_pack_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
