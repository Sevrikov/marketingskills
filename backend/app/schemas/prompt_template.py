from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.prompt_template import PromptTemplateStatus


class PromptTemplateBase(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    task_type: str = Field(min_length=1, max_length=64)
    provider: str = Field(default="gemini", max_length=64)
    model: str | None = Field(default=None, max_length=128)
    system_prompt: str | None = None
    user_template: str = Field(min_length=1)
    expected_output: str | None = None
    validation_schema: dict[str, Any] | None = None
    status: PromptTemplateStatus = PromptTemplateStatus.DRAFT


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateRead(BaseModel):
    id: str
    key: str
    name: str
    version: str
    task_type: str
    provider: str
    model: str | None
    system_prompt: str | None
    user_template: str
    expected_output: str | None
    validation_schema: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
