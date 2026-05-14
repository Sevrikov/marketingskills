from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.article_asset import ArticleAssetStatus


class ArticleAssetStatusUpdate(BaseModel):
    status: ArticleAssetStatus
    reviewer: str | None = Field(default="operator", max_length=255)
    comment: str | None = None


class ArticleAssetUploadPayload(BaseModel):
    storage_uri: str = Field(min_length=1, max_length=4000)
    alt_text: str | None = None
    caption: str | None = None
    reviewer: str | None = Field(default="operator", max_length=255)
    comment: str | None = None


class ArticleAssetGeneratePayload(BaseModel):
    prompt_override: str | None = None
    reviewer: str | None = Field(default="operator", max_length=255)
    comment: str | None = None


class ArticleAssetRead(BaseModel):
    id: str
    task_id: str
    slot: str
    asset_type: str
    status: str
    brief_json: dict
    storage_uri: str
    alt_text: str
    caption: str
    qa_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
