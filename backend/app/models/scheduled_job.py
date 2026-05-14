from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.scheduled_job_run import ScheduledJobRun


class ScheduledJob(TimestampMixin, Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(64))
    last_error: Mapped[str | None] = mapped_column(Text)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    runs: Mapped[list["ScheduledJobRun"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ScheduledJobRun.created_at",
    )
