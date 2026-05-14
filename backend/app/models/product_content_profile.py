from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.product import Product


class ProductContentProfile(TimestampMixin, Base):
    __tablename__ = "product_content_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft", index=True)
    generated_title: Mapped[str] = mapped_column(String(500), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    long_description: Mapped[str] = mapped_column(Text, nullable=False)
    seo_title: Mapped[str] = mapped_column(String(255), nullable=False)
    meta_description: Mapped[str] = mapped_column(String(320), nullable=False)
    specifications_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    faq_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    alt_texts_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="SET NULL"),
        index=True,
    )
    source_draft_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="SET NULL"),
        index=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    product: Mapped["Product"] = relationship(back_populates="content_profile")
