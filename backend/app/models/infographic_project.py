from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.infographic_data_pack import InfographicDataPack
    from app.models.infographic_design_brief import InfographicDesignBrief
    from app.models.product import Product


class InfographicProjectStatus(StrEnum):
    DRAFT = "draft"
    DATA_READY = "data_ready"
    BRIEF_READY = "brief_ready"
    DESIGN_PROMPT_READY = "design_prompt_ready"
    APPROVED = "approved"


class InfographicProject(TimestampMixin, Base):
    __tablename__ = "infographic_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False, default="product", index=True)
    scope_id: Mapped[str | None] = mapped_column(String(255), index=True)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
    source_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_tasks.id", ondelete="SET NULL"),
        index=True,
    )
    source_research_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_research_reports.id", ondelete="SET NULL"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    infographic_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_channel: Mapped[str] = mapped_column(String(64), nullable=False, default="product_card")
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=InfographicProjectStatus.DRAFT.value,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(String(255))
    brand_style_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    product: Mapped["Product | None"] = relationship(back_populates="infographic_projects")
    data_packs: Mapped[list["InfographicDataPack"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="InfographicDataPack.created_at",
    )
    design_briefs: Mapped[list["InfographicDesignBrief"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="InfographicDesignBrief.created_at",
    )
