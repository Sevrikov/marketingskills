from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.scheduled_job import ScheduledJob


class ScheduledJobRun(TimestampMixin, Base):
    __tablename__ = "scheduled_job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    job: Mapped["ScheduledJob"] = relationship(back_populates="runs")
