from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.article_asset import ArticleAsset
    from app.models.article_review_checkpoint import ArticleReviewCheckpoint
    from app.models.content_draft import ContentDraft
    from app.models.content_research_report import ContentResearchReport
    from app.models.product import Product
    from app.models.publish_package import PublishPackage
    from app.models.task_event import TaskEvent


class ContentTaskStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    RESEARCH_RUNNING = "research_running"
    RESEARCH_COMPLETED = "research_completed"
    CONTENT_GENERATING = "content_generating"
    CRITICIZING = "criticizing"
    REWRITING = "rewriting"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentTaskType(StrEnum):
    PRODUCT_CARD = "product_card"
    SEO_ARTICLE = "seo_article"
    RESEARCH = "research"
    VIDEO_BRIEF = "video_brief"


class ContentTask(TimestampMixin, Base):
    __tablename__ = "content_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru")
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=ContentTaskStatus.DRAFT.value,
        index=True,
    )
    current_step: Mapped[str | None] = mapped_column(String(128))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_by: Mapped[str | None] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product | None"] = relationship(back_populates="tasks")
    events: Mapped[list["TaskEvent"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskEvent.created_at",
    )
    drafts: Mapped[list["ContentDraft"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ContentDraft.created_at",
    )
    research_reports: Mapped[list["ContentResearchReport"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ContentResearchReport.created_at",
    )
    publish_packages: Mapped[list["PublishPackage"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="PublishPackage.created_at",
    )
    article_checkpoints: Mapped[list["ArticleReviewCheckpoint"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ArticleReviewCheckpoint.created_at",
    )
    article_assets: Mapped[list["ArticleAsset"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ArticleAsset.created_at",
    )
