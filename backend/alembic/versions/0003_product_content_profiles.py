"""add product content profiles

Revision ID: 0003_product_content_profiles
Revises: 0002_price_monitoring
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_product_content_profiles"
down_revision: str | None = "0002_price_monitoring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_content_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("generated_title", sa.String(length=500), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("long_description", sa.Text(), nullable=False),
        sa.Column("seo_title", sa.String(length=255), nullable=False),
        sa.Column("meta_description", sa.String(length=320), nullable=False),
        sa.Column("specifications_json", sa.JSON(), nullable=False),
        sa.Column("faq_json", sa.JSON(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("alt_texts_json", sa.JSON(), nullable=False),
        sa.Column("source_task_id", sa.String(length=36), nullable=True),
        sa.Column("source_draft_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_task_id"], ["content_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_draft_id"], ["content_drafts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_content_profiles_product_id"),
        "product_content_profiles",
        ["product_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_product_content_profiles_source_task_id"),
        "product_content_profiles",
        ["source_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_content_profiles_source_draft_id"),
        "product_content_profiles",
        ["source_draft_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_content_profiles_status"),
        "product_content_profiles",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_product_content_profiles_status"), table_name="product_content_profiles")
    op.drop_index(
        op.f("ix_product_content_profiles_source_draft_id"),
        table_name="product_content_profiles",
    )
    op.drop_index(
        op.f("ix_product_content_profiles_source_task_id"),
        table_name="product_content_profiles",
    )
    op.drop_index(
        op.f("ix_product_content_profiles_product_id"),
        table_name="product_content_profiles",
    )
    op.drop_table("product_content_profiles")
