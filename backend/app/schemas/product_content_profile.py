from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductContentProfileGenerate(BaseModel):
    source_task_id: str | None = None
    source_draft_id: str | None = None
    language: str = Field(default="ru", max_length=16)


class ProductContentProfileUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str | None = Field(default=None, max_length=64)
    generated_title: str | None = Field(default=None, min_length=1, max_length=500)
    short_description: str | None = None
    long_description: str | None = None
    seo_title: str | None = Field(default=None, min_length=1, max_length=255)
    meta_description: str | None = Field(default=None, min_length=1, max_length=320)
    specifications_json: dict[str, Any] | None = None
    faq_json: list[dict[str, Any]] | None = None
    schema_data: dict[str, Any] | None = Field(default=None, alias="schema_json")
    alt_texts_json: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class ProductContentProfileRead(BaseModel):
    id: str
    product_id: str
    status: str
    generated_title: str
    short_description: str
    long_description: str
    seo_title: str
    meta_description: str
    specifications_json: dict[str, Any]
    faq_json: list[dict[str, Any]]
    schema_data: dict[str, Any] = Field(alias="schema_json")
    alt_texts_json: list[str]
    source_task_id: str | None
    source_draft_id: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
