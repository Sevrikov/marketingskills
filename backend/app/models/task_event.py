from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.content_task import ContentTask


class TaskEvent(TimestampMixin, Base):
    __tablename__ = "task_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(64))
    to_status: Mapped[str | None] = mapped_column(String(64))
    step: Mapped[str | None] = mapped_column(String(128))
    message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by: Mapped[str | None] = mapped_column(String(255))

    task: Mapped["ContentTask"] = relationship(back_populates="events")
