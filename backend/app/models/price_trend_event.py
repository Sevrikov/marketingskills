from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.price_group import PriceGroup
    from app.models.price_market_index import PriceMarketIndex


class PriceTrendEvent(TimestampMixin, Base):
    __tablename__ = "price_trend_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    price_group_id: Mapped[str] = mapped_column(
        ForeignKey("price_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_index_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_market_indexes.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="low", nullable=False)
    affected_sources_count: Mapped[int] = mapped_column(default=0, nullable=False)
    percent_change: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    notify_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    price_group: Mapped["PriceGroup"] = relationship()
    market_index: Mapped["PriceMarketIndex | None"] = relationship()
