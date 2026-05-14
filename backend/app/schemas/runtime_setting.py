from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeSettingField(BaseModel):
    key: str
    label: str
    section: str
    kind: str
    configured: bool
    value: str | bool | None = None
    masked_value: str | None = None
    env_value: str | bool | None = None
    options: list[str] = Field(default_factory=list)
    description: str | None = None
    updated_at: datetime | None = None


class RuntimeSettingsRead(BaseModel):
    fields: list[RuntimeSettingField]
    sections: list[str]


class RuntimeSettingsUpdate(BaseModel):
    values: dict[str, Any]
