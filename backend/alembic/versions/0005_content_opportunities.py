"""add content opportunities

Revision ID: 0005_content_opportunities
Revises: 0004_scheduler
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_content_opportunities"
down_revision: str | None = "0004_scheduler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content_opportunities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("price_group_id", sa.String(length=36), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("h1", sa.String(length=500), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=False),
        sa.Column("priority_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("outline_json", sa.JSON(), nullable=False),
        sa.Column("recommended_product_ids_json", sa.JSON(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("research_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_task_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_task_id"], ["content_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["price_group_id"], ["price_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_opportunities_scope_type"),
        "content_opportunities",
        ["scope_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_product_id"),
        "content_opportunities",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_price_group_id"),
        "content_opportunities",
        ["price_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_brand"),
        "content_opportunities",
        ["brand"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_category"),
        "content_opportunities",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_intent"),
        "content_opportunities",
        ["intent"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_status"),
        "content_opportunities",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_opportunities_created_task_id"),
        "content_opportunities",
        ["created_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_content_opportunities_created_task_id"),
        table_name="content_opportunities",
    )
    op.drop_index(op.f("ix_content_opportunities_status"), table_name="content_opportunities")
    op.drop_index(op.f("ix_content_opportunities_intent"), table_name="content_opportunities")
    op.drop_index(op.f("ix_content_opportunities_category"), table_name="content_opportunities")
    op.drop_index(op.f("ix_content_opportunities_brand"), table_name="content_opportunities")
    op.drop_index(
        op.f("ix_content_opportunities_price_group_id"),
        table_name="content_opportunities",
    )
    op.drop_index(op.f("ix_content_opportunities_product_id"), table_name="content_opportunities")
    op.drop_index(op.f("ix_content_opportunities_scope_type"), table_name="content_opportunities")
    op.drop_table("content_opportunities")
