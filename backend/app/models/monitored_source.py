from decimal import Decimal
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.price_snapshot import PriceSnapshot
    from app.models.price_group import PriceGroup
    from app.models.product import Product


class MonitoredSource(TimestampMixin, Base):
    __tablename__ = "monitored_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
    price_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_groups.id", ondelete="SET NULL"),
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    competitor_name: Mapped[str | None] = mapped_column(String(255))
    market_position: Mapped[int | None] = mapped_column(Integer)
    source_priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="competitor_product")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extractor_type: Mapped[str] = mapped_column(String(64), default="generic_js")
    extractor_script: Mapped[str] = mapped_column(Text, nullable=False)
    expected_currency: Mapped[str | None] = mapped_column(String(8))
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_currency: Mapped[str | None] = mapped_column(String(8))
    last_availability: Mapped[str | None] = mapped_column(String(64))
    last_status: Mapped[str | None] = mapped_column(String(64))
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    product: Mapped["Product | None"] = relationship(back_populates="monitored_sources")
    price_group: Mapped["PriceGroup | None"] = relationship(back_populates="monitored_sources")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="monitored_source",
        cascade="all, delete-orphan",
    )
