from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.content_task import ContentTask
    from app.models.monitored_source import MonitoredSource
    from app.models.product_content_profile import ProductContentProfile


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    sku: Mapped[str | None] = mapped_column(String(255), index=True)
    gtin: Mapped[str | None] = mapped_column(String(64), index=True)
    mpn: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    availability: Mapped[str | None] = mapped_column(String(64))
    cms_product_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_description: Mapped[str | None] = mapped_column(Text)

    tasks: Mapped[list["ContentTask"]] = relationship(back_populates="product")
    monitored_sources: Mapped[list["MonitoredSource"]] = relationship(back_populates="product")
    content_profile: Mapped["ProductContentProfile | None"] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )
