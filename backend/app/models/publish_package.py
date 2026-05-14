from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.content_task import ContentTask

from app.models.media_brief import MediaBrief
from app.models.publication_preview import PublicationPreview


class PublishPackage(TimestampMixin, Base):
    __tablename__ = "publish_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    package_type: Mapped[str] = mapped_column(String(64), nullable=False, default="manual_export")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="ready", index=True)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    package_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    task: Mapped["ContentTask"] = relationship(back_populates="publish_packages")
    publication_previews: Mapped[list["PublicationPreview"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="PublicationPreview.created_at",
    )
    media_briefs: Mapped[list["MediaBrief"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="MediaBrief.created_at",
    )
