from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.monitored_source import MonitoredSource


class PriceGroup(TimestampMixin, Base):
    __tablename__ = "price_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(255))
    keywords: Mapped[str | None] = mapped_column(Text)
    top_position_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    min_sources_for_signal: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    monitored_sources: Mapped[list["MonitoredSource"]] = relationship(back_populates="price_group")
