from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MediaBriefRead(BaseModel):
    id: str
    package_id: str
    brief_type: str
    status: str
    markdown: str
    brief_json: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
