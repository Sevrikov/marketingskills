from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.monitored_source import MonitoredSource
    from app.models.price_snapshot import PriceSnapshot


class PriceChangeEvent(TimestampMixin, Base):
    __tablename__ = "price_change_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    monitored_source_id: Mapped[str] = mapped_column(
        ForeignKey("monitored_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_snapshots.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    old_currency: Mapped[str | None] = mapped_column(String(8))
    new_currency: Mapped[str | None] = mapped_column(String(8))
    old_availability: Mapped[str | None] = mapped_column(String(64))
    new_availability: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="recorded")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    monitored_source: Mapped["MonitoredSource"] = relationship()
    price_snapshot: Mapped["PriceSnapshot | None"] = relationship()
