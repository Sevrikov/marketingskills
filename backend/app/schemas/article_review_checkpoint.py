from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.article_review_checkpoint import ArticleCheckpointStatus
from app.models.article_review_checkpoint import ArticleCheckpointType


class ArticleCheckpointUpsert(BaseModel):
    body_markdown: str = Field(min_length=1)
    status: ArticleCheckpointStatus = ArticleCheckpointStatus.DRAFT
    reviewer: str | None = "operator"
    metadata_json: dict[str, Any] | None = None


class ArticleCheckpointRead(BaseModel):
    id: str
    task_id: str
    checkpoint_type: ArticleCheckpointType
    body_markdown: str
    status: ArticleCheckpointStatus
    reviewer: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
