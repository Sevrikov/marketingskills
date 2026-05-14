"""add scheduler tables

Revision ID: 0004_scheduler
Revises: 0003_product_content_profiles
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_scheduler"
down_revision: str | None = "0003_product_content_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_key", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_jobs_job_key"), "scheduled_jobs", ["job_key"], unique=True)
    op.create_index(
        op.f("ix_scheduled_jobs_job_type"),
        "scheduled_jobs",
        ["job_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_jobs_status"),
        "scheduled_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_jobs_is_active"),
        "scheduled_jobs",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_jobs_next_run_at"),
        "scheduled_jobs",
        ["next_run_at"],
        unique=False,
    )
    op.create_table(
        "scheduled_job_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("job_key", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["scheduled_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduled_job_runs_job_id"),
        "scheduled_job_runs",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_job_runs_job_key"),
        "scheduled_job_runs",
        ["job_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_job_runs_job_type"),
        "scheduled_job_runs",
        ["job_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_job_runs_status"),
        "scheduled_job_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_job_runs_status"), table_name="scheduled_job_runs")
    op.drop_index(op.f("ix_scheduled_job_runs_job_type"), table_name="scheduled_job_runs")
    op.drop_index(op.f("ix_scheduled_job_runs_job_key"), table_name="scheduled_job_runs")
    op.drop_index(op.f("ix_scheduled_job_runs_job_id"), table_name="scheduled_job_runs")
    op.drop_table("scheduled_job_runs")
    op.drop_index(op.f("ix_scheduled_jobs_next_run_at"), table_name="scheduled_jobs")
    op.drop_index(op.f("ix_scheduled_jobs_is_active"), table_name="scheduled_jobs")
    op.drop_index(op.f("ix_scheduled_jobs_status"), table_name="scheduled_jobs")
    op.drop_index(op.f("ix_scheduled_jobs_job_type"), table_name="scheduled_jobs")
    op.drop_index(op.f("ix_scheduled_jobs_job_key"), table_name="scheduled_jobs")
    op.drop_table("scheduled_jobs")
