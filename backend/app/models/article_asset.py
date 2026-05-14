from enum import StrEnum
from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.content_task import ContentTask


class ArticleAssetType(StrEnum):
    IMAGE = "image"
    INFOGRAPHIC = "infographic"


class ArticleAssetStatus(StrEnum):
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArticleAsset(TimestampMixin, Base):
    __tablename__ = "article_assets"
    __table_args__ = (
        UniqueConstraint("task_id", "slot", name="uq_article_assets_task_slot"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=ArticleAssetStatus.GENERATED.value,
        index=True,
    )
    brief_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    qa_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    task: Mapped["ContentTask"] = relationship(back_populates="article_assets")
