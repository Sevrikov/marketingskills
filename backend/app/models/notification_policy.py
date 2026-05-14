from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid


class NotificationPolicy(TimestampMixin, Base):
    __tablename__ = "notification_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_scope: Mapped[str] = mapped_column(String(64), default="price_trend", nullable=False)
    channel: Mapped[str] = mapped_column(String(64), default="viber", nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(64), default="digest", nullable=False)
    min_severity: Mapped[str] = mapped_column(String(32), default="high", nullable=False)
    min_affected_sources: Mapped[int] = mapped_column(default=3, nullable=False)
    min_percent_change: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=10, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5))
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
