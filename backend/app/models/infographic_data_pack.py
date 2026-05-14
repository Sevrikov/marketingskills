from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.utils.ids import new_uuid

if TYPE_CHECKING:
    from app.models.infographic_project import InfographicProject


class InfographicDataPack(TimestampMixin, Base):
    __tablename__ = "infographic_data_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("infographic_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_pack_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_fields_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=0.5)

    project: Mapped["InfographicProject"] = relationship(back_populates="data_packs")
