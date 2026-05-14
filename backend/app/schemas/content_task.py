from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.content_task import ContentTaskStatus, ContentTaskType


class ContentTaskCreate(BaseModel):
    product_id: str | None = None
    task_type: ContentTaskType
    language: str = Field(default="ru", max_length=16)
    priority: int = Field(default=5, ge=1, le=10)
    created_by: str | None = None
    topic: str | None = None

    @model_validator(mode="after")
    def require_product_or_topic(self) -> "ContentTaskCreate":
        if not self.product_id and not self.topic:
            raise ValueError("Either product_id or topic is required.")
        return self


class ContentTaskRead(BaseModel):
    id: str
    product_id: str | None
    task_type: str
    language: str
    status: str
    current_step: str | None
    priority: int
    created_by: str | None
    topic: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentTaskStatusUpdate(BaseModel):
    status: ContentTaskStatus
    current_step: str | None = None
    error_message: str | None = None
