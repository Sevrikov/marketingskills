from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid


class AgentSkillStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AgentSkill(TimestampMixin, Base):
    __tablename__ = "agent_skills"
    __table_args__ = (UniqueConstraint("name", name="uq_agent_skills_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str | None] = mapped_column(String(64))
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=AgentSkillStatus.ACTIVE.value,
        index=True,
    )
