"""Add runtime settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_runtime_settings"
down_revision: str | None = "0007_article_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_runtime_settings_key"),
    )
    op.create_index(op.f("ix_runtime_settings_key"), "runtime_settings", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runtime_settings_key"), table_name="runtime_settings")
    op.drop_table("runtime_settings")
