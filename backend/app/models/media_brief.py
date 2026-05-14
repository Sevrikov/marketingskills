from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.publish_package import PublishPackage


class MediaBrief(TimestampMixin, Base):
    __tablename__ = "media_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    package_id: Mapped[str] = mapped_column(
        ForeignKey("publish_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brief_type: Mapped[str] = mapped_column(String(64), nullable=False, default="video_brief_pack")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="brief_ready", index=True)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    brief_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    package: Mapped["PublishPackage"] = relationship(back_populates="media_briefs")
