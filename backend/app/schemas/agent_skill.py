from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentSkillRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    version: str | None
    source_path: str
    body: str
    metadata_json: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillSyncResponse(BaseModel):
    scanned: int = Field(ge=0)
    upserted: int = Field(ge=0)
    archived: int = Field(ge=0)
