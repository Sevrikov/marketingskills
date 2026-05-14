from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ContentResearchReportRead(BaseModel):
    id: str
    task_id: str
    title: str
    markdown: str
    provider: str
    external_id: str | None
    sources_json: list[dict[str, Any]]
    normalized_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
