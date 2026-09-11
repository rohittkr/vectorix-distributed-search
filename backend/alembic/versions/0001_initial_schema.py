"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("source", sa.String(256), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("popularity", sa.Float, nullable=False, server_default="0"),
        sa.Column("doc_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_author", "documents", ["author"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_indexed_at", "documents", ["indexed_at"])

    op.create_table(
        "indexing_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True),
        sa.Column("total_documents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_documents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_documents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_indexing_jobs_status", "indexing_jobs", ["status"])

    op.create_table(
        "indexing_failures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("indexing_jobs.id"), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_indexing_failures_job_id", "indexing_failures", ["job_id"])

    op.create_table(
        "search_queries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("filters_json", sa.Text, nullable=True),
        sa.Column("total_results", sa.Integer, nullable=False, server_default="0"),
        sa.Column("took_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column("cache_hit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_queries_created_at", "search_queries", ["created_at"])

    op.create_table(
        "system_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_events_created_at", "system_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("system_events")
    op.drop_table("search_queries")
    op.drop_table("indexing_failures")
    op.drop_table("indexing_jobs")
    op.drop_table("documents")
