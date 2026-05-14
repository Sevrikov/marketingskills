from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.infographic_project import InfographicProject


class InfographicDesignBrief(TimestampMixin, Base):
    __tablename__ = "infographic_design_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("infographic_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_pack_id: Mapped[str | None] = mapped_column(
        ForeignKey("infographic_data_packs.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="brief_ready", index=True)
    brief_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    brief_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prompt_pack_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    project: Mapped["InfographicProject"] = relationship(back_populates="design_briefs")
