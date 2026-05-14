from typing import Any

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid


class ContentOpportunity(TimestampMixin, Base):
    __tablename__ = "content_opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
    price_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_groups.id", ondelete="SET NULL"),
        index=True,
    )
    brand: Mapped[str | None] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(255), index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru")
    market: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    h1: Mapped[str] = mapped_column(String(500), nullable=False)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="new", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    outline_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recommended_product_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    sources_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    research_summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="SET NULL"),
        index=True,
    )
