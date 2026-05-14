"""add price monitoring tables

Revision ID: 0002_price_monitoring
Revises: 0001_initial_products_tasks
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_price_monitoring"
down_revision: str | None = "0001_initial_products_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_scope", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("delivery_mode", sa.String(length=64), nullable=False),
        sa.Column("min_severity", sa.String(length=32), nullable=False),
        sa.Column("min_affected_sources", sa.Integer(), nullable=False),
        sa.Column("min_percent_change", sa.Numeric(8, 4), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "market_digest_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("delivery_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "price_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("top_position_limit", sa.Integer(), nullable=False),
        sa.Column("min_sources_for_signal", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "monitored_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("price_group_id", sa.String(length=36), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("competitor_name", sa.String(length=255), nullable=True),
        sa.Column("market_position", sa.Integer(), nullable=True),
        sa.Column("source_priority", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("check_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extractor_type", sa.String(length=64), nullable=False),
        sa.Column("extractor_script", sa.Text(), nullable=False),
        sa.Column("expected_currency", sa.String(length=8), nullable=True),
        sa.Column("last_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("last_currency", sa.String(length=8), nullable=True),
        sa.Column("last_availability", sa.String(length=64), nullable=True),
        sa.Column("last_status", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["price_group_id"], ["price_groups.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_monitored_sources_product_id"),
        "monitored_sources",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monitored_sources_next_check_at"),
        "monitored_sources",
        ["next_check_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monitored_sources_price_group_id"),
        "monitored_sources",
        ["price_group_id"],
        unique=False,
    )
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("monitored_source_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("availability", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("sku", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("extractor_type", sa.String(length=64), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitored_source_id"],
            ["monitored_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_price_snapshots_monitored_source_id"),
        "price_snapshots",
        ["monitored_source_id"],
        unique=False,
    )
    op.create_table(
        "price_change_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("monitored_source_id", sa.String(length=36), nullable=False),
        sa.Column("price_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("old_currency", sa.String(length=8), nullable=True),
        sa.Column("new_currency", sa.String(length=8), nullable=True),
        sa.Column("old_availability", sa.String(length=64), nullable=True),
        sa.Column("new_availability", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitored_source_id"],
            ["monitored_sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["price_snapshot_id"],
            ["price_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_price_change_events_monitored_source_id"),
        "price_change_events",
        ["monitored_source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_price_change_events_price_snapshot_id"),
        "price_change_events",
        ["price_snapshot_id"],
        unique=False,
    )
    op.create_table(
        "price_market_indexes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("price_group_id", sa.String(length=36), nullable=False),
        sa.Column("window", sa.String(length=32), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("in_stock_count", sa.Integer(), nullable=False),
        sa.Column("min_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("avg_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("median_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("top_sources_avg_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("availability_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["price_group_id"], ["price_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_price_market_indexes_price_group_id"),
        "price_market_indexes",
        ["price_group_id"],
        unique=False,
    )
    op.create_table(
        "price_trend_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("price_group_id", sa.String(length=36), nullable=False),
        sa.Column("market_index_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("affected_sources_count", sa.Integer(), nullable=False),
        sa.Column("percent_change", sa.Numeric(8, 4), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("notify_status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["price_group_id"], ["price_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["market_index_id"],
            ["price_market_indexes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_price_trend_events_price_group_id"),
        "price_trend_events",
        ["price_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_price_trend_events_market_index_id"),
        "price_trend_events",
        ["market_index_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_price_trend_events_market_index_id"), table_name="price_trend_events")
    op.drop_index(op.f("ix_price_trend_events_price_group_id"), table_name="price_trend_events")
    op.drop_table("price_trend_events")
    op.drop_index(op.f("ix_price_market_indexes_price_group_id"), table_name="price_market_indexes")
    op.drop_table("price_market_indexes")
    op.drop_index(
        op.f("ix_price_change_events_price_snapshot_id"),
        table_name="price_change_events",
    )
    op.drop_index(
        op.f("ix_price_change_events_monitored_source_id"),
        table_name="price_change_events",
    )
    op.drop_table("price_change_events")
    op.drop_index(op.f("ix_price_snapshots_monitored_source_id"), table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_index(op.f("ix_monitored_sources_price_group_id"), table_name="monitored_sources")
    op.drop_index(op.f("ix_monitored_sources_next_check_at"), table_name="monitored_sources")
    op.drop_index(op.f("ix_monitored_sources_product_id"), table_name="monitored_sources")
    op.drop_table("monitored_sources")
    op.drop_table("price_groups")
    op.drop_table("market_digest_batches")
    op.drop_table("notification_policies")
