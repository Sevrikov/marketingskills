"""Add article assets."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_article_assets"
down_revision: str | None = "0006_article_review_checkpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("slot", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("qa_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["content_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "slot", name="uq_article_assets_task_slot"),
    )
    op.create_index(op.f("ix_article_assets_asset_type"), "article_assets", ["asset_type"], unique=False)
    op.create_index(op.f("ix_article_assets_slot"), "article_assets", ["slot"], unique=False)
    op.create_index(op.f("ix_article_assets_status"), "article_assets", ["status"], unique=False)
    op.create_index(op.f("ix_article_assets_task_id"), "article_assets", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_article_assets_task_id"), table_name="article_assets")
    op.drop_index(op.f("ix_article_assets_status"), table_name="article_assets")
    op.drop_index(op.f("ix_article_assets_slot"), table_name="article_assets")
    op.drop_index(op.f("ix_article_assets_asset_type"), table_name="article_assets")
    op.drop_table("article_assets")
