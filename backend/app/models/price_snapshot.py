from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.monitored_source import MonitoredSource


class PriceSnapshot(TimestampMixin, Base):
    __tablename__ = "price_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    monitored_source_id: Mapped[str] = mapped_column(
        ForeignKey("monitored_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(64), default="captured")
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    availability: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(500))
    sku: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    extractor_type: Mapped[str] = mapped_column(String(64), default="generic_js")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    monitored_source: Mapped["MonitoredSource"] = relationship(back_populates="price_snapshots")
