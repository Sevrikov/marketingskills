from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.price_group import PriceGroup


class PriceMarketIndex(TimestampMixin, Base):
    __tablename__ = "price_market_indexes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    price_group_id: Mapped[str] = mapped_column(
        ForeignKey("price_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window: Mapped[str] = mapped_column(String(32), nullable=False, default="latest")
    source_count: Mapped[int] = mapped_column(default=0, nullable=False)
    in_stock_count: Mapped[int] = mapped_column(default=0, nullable=False)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    median_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    top_sources_avg_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    availability_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    price_group: Mapped["PriceGroup"] = relationship()
