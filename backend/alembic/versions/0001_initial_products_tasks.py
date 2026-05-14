"""initial products and content tasks

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("sku", sa.String(length=255), nullable=True),
        sa.Column("gtin", sa.String(length=64), nullable=True),
        sa.Column("mpn", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("availability", sa.String(length=64), nullable=True),
        sa.Column("cms_product_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_gtin", "products", ["gtin"])

    op.create_table(
        "content_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("current_step", sa.String(length=128), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("topic", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_tasks_product_id", "content_tasks", ["product_id"])
    op.create_index("ix_content_tasks_status", "content_tasks", ["status"])

    op.create_table(
        "task_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("content_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=64), nullable=True),
        sa.Column("to_status", sa.String(length=64), nullable=True),
        sa.Column("step", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_events_task_id", "task_events", ["task_id"])
    op.create_index("ix_task_events_event_type", "task_events", ["event_type"])

    op.create_table(
        "content_research_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("content_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("normalized_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_content_research_reports_task_id",
        "content_research_reports",
        ["task_id"],
    )

    op.create_table(
        "content_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("content_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_template_key", sa.String(length=255), nullable=True),
        sa.Column("prompt_template_version", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_drafts_task_id", "content_drafts", ["task_id"])
    op.create_index("ix_content_drafts_kind", "content_drafts", ["kind"])

    op.create_table(
        "publish_packages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("content_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("package_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("package_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publish_packages_task_id", "publish_packages", ["task_id"])
    op.create_index("ix_publish_packages_slug", "publish_packages", ["slug"])
    op.create_index("ix_publish_packages_status", "publish_packages", ["status"])

    op.create_table(
        "publication_previews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "package_id",
            sa.String(length=36),
            sa.ForeignKey("publish_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("destination_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publication_previews_package_id", "publication_previews", ["package_id"])
    op.create_index("ix_publication_previews_provider", "publication_previews", ["provider"])

    op.create_table(
        "media_briefs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "package_id",
            sa.String(length=36),
            sa.ForeignKey("publish_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brief_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_media_briefs_package_id", "media_briefs", ["package_id"])
    op.create_index("ix_media_briefs_status", "media_briefs", ["status"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("validation_schema", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", "version", name="uq_prompt_templates_key_version"),
    )
    op.create_index("ix_prompt_templates_key", "prompt_templates", ["key"])
    op.create_index("ix_prompt_templates_status", "prompt_templates", ["status"])

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_agent_skills_name"),
    )
    op.create_index("ix_agent_skills_name", "agent_skills", ["name"])
    op.create_index("ix_agent_skills_slug", "agent_skills", ["slug"])
    op.create_index("ix_agent_skills_status", "agent_skills", ["status"])


def downgrade() -> None:
    op.drop_index("ix_media_briefs_status", table_name="media_briefs")
    op.drop_index("ix_media_briefs_package_id", table_name="media_briefs")
    op.drop_table("media_briefs")
    op.drop_index("ix_publication_previews_provider", table_name="publication_previews")
    op.drop_index("ix_publication_previews_package_id", table_name="publication_previews")
    op.drop_table("publication_previews")
    op.drop_index("ix_agent_skills_status", table_name="agent_skills")
    op.drop_index("ix_agent_skills_slug", table_name="agent_skills")
    op.drop_index("ix_agent_skills_name", table_name="agent_skills")
    op.drop_table("agent_skills")
    op.drop_index("ix_prompt_templates_status", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_key", table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index("ix_content_drafts_kind", table_name="content_drafts")
    op.drop_index("ix_content_drafts_task_id", table_name="content_drafts")
    op.drop_table("content_drafts")
    op.drop_index("ix_publish_packages_status", table_name="publish_packages")
    op.drop_index("ix_publish_packages_slug", table_name="publish_packages")
    op.drop_index("ix_publish_packages_task_id", table_name="publish_packages")
    op.drop_table("publish_packages")
    op.drop_index(
        "ix_content_research_reports_task_id",
        table_name="content_research_reports",
    )
    op.drop_table("content_research_reports")
    op.drop_index("ix_task_events_event_type", table_name="task_events")
    op.drop_index("ix_task_events_task_id", table_name="task_events")
    op.drop_table("task_events")
    op.drop_index("ix_content_tasks_status", table_name="content_tasks")
    op.drop_index("ix_content_tasks_product_id", table_name="content_tasks")
    op.drop_table("content_tasks")
    op.drop_index("ix_products_gtin", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
