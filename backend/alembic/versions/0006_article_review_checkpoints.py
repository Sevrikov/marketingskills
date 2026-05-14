"""add article review checkpoints

Revision ID: 0006_article_review_checkpoints
Revises: 0005_content_opportunities
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_article_review_checkpoints"
down_revision: str | None = "0005_content_opportunities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_review_checkpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=64), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["content_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "checkpoint_type",
            name="uq_article_review_checkpoints_task_type",
        ),
    )
    op.create_index(
        op.f("ix_article_review_checkpoints_task_id"),
        "article_review_checkpoints",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_review_checkpoints_checkpoint_type"),
        "article_review_checkpoints",
        ["checkpoint_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_review_checkpoints_status"),
        "article_review_checkpoints",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_article_review_checkpoints_status"), table_name="article_review_checkpoints")
    op.drop_index(
        op.f("ix_article_review_checkpoints_checkpoint_type"),
        table_name="article_review_checkpoints",
    )
    op.drop_index(
        op.f("ix_article_review_checkpoints_task_id"),
        table_name="article_review_checkpoints",
    )
    op.drop_table("article_review_checkpoints")
