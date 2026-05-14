from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PublicationPublishRequest(BaseModel):
    confirmation_phrase: str | None = None


class PublicationPreviewRead(BaseModel):
    id: str
    package_id: str
    provider: str
    destination_type: str
    status: str
    payload_json: dict
    result_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
