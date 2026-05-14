from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TaskEventRead(BaseModel):
    id: str
    task_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    step: str | None
    message: str | None
    metadata_json: dict[str, Any] | None
    created_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
