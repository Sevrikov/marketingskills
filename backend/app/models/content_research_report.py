from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.content_task import ContentTask


class ContentResearchReport(TimestampMixin, Base):
    __tablename__ = "content_research_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    sources_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    normalized_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    task: Mapped["ContentTask"] = relationship(back_populates="research_reports")
