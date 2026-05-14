from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentOpportunityDiscover(BaseModel):
    product_id: str | None = None
    price_group_id: str | None = None
    brand: str | None = None
    category: str | None = None
    query: str | None = None
    language: str = Field(default="ru", max_length=16)
    market: str | None = Field(default=None, max_length=64)
    limit: int = Field(default=8, ge=1, le=20)

    @model_validator(mode="after")
    def require_scope(self) -> "ContentOpportunityDiscover":
        if not any([self.product_id, self.price_group_id, self.brand, self.category, self.query]):
            raise ValueError("Pass product_id, price_group_id, brand, category or query.")
        return self


class ContentOpportunityRead(BaseModel):
    id: str
    scope_type: str
    product_id: str | None
    price_group_id: str | None
    brand: str | None
    category: str | None
    language: str
    market: str | None
    title: str
    h1: str
    intent: str
    priority_score: float
    status: str
    reason: str
    outline_json: list[str]
    recommended_product_ids_json: list[str]
    sources_json: list[dict[str, Any]]
    research_summary: str | None
    metadata_json: dict[str, Any] | None
    created_task_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentOpportunityDiscoverResult(BaseModel):
    query: str
    provider: str
    research_provider: str
    created: int
    opportunities: list[ContentOpportunityRead]


class ContentOpportunityCreateTaskResult(BaseModel):
    opportunity_id: str
    task_id: str
    task_status: str
