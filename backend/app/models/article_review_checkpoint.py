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


class ArticleCheckpointType(StrEnum):
    ARTICLE_BRIEF = "article_brief"
    EDITOR_NOTES = "editor_notes"
    IMAGE_BRIEF = "image_brief"
    QA = "qa"


class ArticleCheckpointStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class ArticleReviewCheckpoint(TimestampMixin, Base):
    __tablename__ = "article_review_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "checkpoint_type",
            name="uq_article_review_checkpoints_task_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=ArticleCheckpointStatus.DRAFT.value,
        index=True,
    )
    reviewer: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    task: Mapped["ContentTask"] = relationship(back_populates="article_checkpoints")
