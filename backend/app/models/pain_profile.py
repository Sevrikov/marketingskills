from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.product import Product


class PainProfileStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class PainProfileScope(StrEnum):
    PRODUCT = "product"
    GROUP = "group"
    BRAND = "brand"
    TOPIC = "topic"


class PainProfile(TimestampMixin, Base):
    __tablename__ = "pain_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scope_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=PainProfileScope.PRODUCT.value,
        index=True,
    )
    scope_id: Mapped[str | None] = mapped_column(String(255), index=True)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=PainProfileStatus.DRAFT.value,
        index=True,
    )
    primary_pain_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="SET NULL"),
        index=True,
    )
    source_research_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_research_reports.id", ondelete="SET NULL"),
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    product: Mapped["Product | None"] = relationship(back_populates="pain_profiles")
