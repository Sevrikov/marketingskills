from typing import Any
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.publish_package import PublishPackage


class PublicationPreview(TimestampMixin, Base):
    __tablename__ = "publication_previews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    package_id: Mapped[str] = mapped_column(
        ForeignKey("publish_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False, default="cms")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="dry_run_ready")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    package: Mapped["PublishPackage"] = relationship(back_populates="publication_previews")
