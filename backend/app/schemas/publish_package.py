from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PublishPackageRead(BaseModel):
    id: str
    task_id: str
    title: str
    slug: str
    package_type: str
    status: str
    markdown: str
    package_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
