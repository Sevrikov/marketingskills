from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid


class MarketDigestBatch(TimestampMixin, Base):
    __tablename__ = "market_digest_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    status: Mapped[str] = mapped_column(String(64), default="created", nullable=False)
    event_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    event_count: Mapped[int] = mapped_column(default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
