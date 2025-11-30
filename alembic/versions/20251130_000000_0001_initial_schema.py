"""Initial schema: Create all core tables.

Revision ID: 0001
Revises: None
Create Date: 2025-11-30 00:00:00

Creates:
- mega_agent schema
- semantic_memory table (pgvector 2000-dim embeddings)
- episodic_memory table (audit trail)
- rmt_buffers table (working memory)
- cases table (legal cases)
- documents table (R2 storage references)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS mega_agent")

    # Ensure pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ============================================================
    # semantic_memory - Text + pgvector embeddings
    # ============================================================
    op.create_table(
        "semantic_memory",
        sa.Column("record_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False, server_default="default"),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="fact"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(2000), nullable=False),
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=False,
            server_default="text-embedding-3-large",
        ),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("length(text) > 0", name="semantic_text_not_empty"),
        schema="mega_agent",
    )

    # Semantic memory indexes
    op.create_index("idx_semantic_user_id", "semantic_memory", ["user_id"], schema="mega_agent")
    op.create_index("idx_semantic_namespace", "semantic_memory", ["namespace"], schema="mega_agent")
    op.create_index("idx_semantic_type", "semantic_memory", ["type"], schema="mega_agent")
    op.create_index(
        "idx_semantic_tags",
        "semantic_memory",
        ["tags"],
        schema="mega_agent",
        postgresql_using="gin",
    )
    op.create_index(
        "idx_semantic_created",
        "semantic_memory",
        ["created_at"],
        schema="mega_agent",
    )

    # HNSW vector index for semantic search
    op.execute(
        """
        CREATE INDEX idx_semantic_embedding_hnsw
        ON mega_agent.semantic_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # ============================================================
    # episodic_memory - Audit trail and event log
    # ============================================================
    op.create_table(
        "episodic_memory",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("parent_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("length(source) > 0", name="episodic_source_not_empty"),
        sa.CheckConstraint("length(action) > 0", name="episodic_action_not_empty"),
        schema="mega_agent",
    )

    # Episodic memory indexes
    op.create_index("idx_episodic_user_id", "episodic_memory", ["user_id"], schema="mega_agent")
    op.create_index("idx_episodic_thread_id", "episodic_memory", ["thread_id"], schema="mega_agent")
    op.create_index("idx_episodic_source", "episodic_memory", ["source"], schema="mega_agent")
    op.create_index("idx_episodic_action", "episodic_memory", ["action"], schema="mega_agent")
    op.create_index("idx_episodic_timestamp", "episodic_memory", ["timestamp"], schema="mega_agent")
    op.create_index(
        "idx_episodic_thread_time",
        "episodic_memory",
        ["thread_id", "timestamp"],
        schema="mega_agent",
    )
    op.create_index(
        "idx_episodic_payload",
        "episodic_memory",
        ["payload"],
        schema="mega_agent",
        postgresql_using="gin",
    )

    # ============================================================
    # rmt_buffers - RMT working memory
    # ============================================================
    op.create_table(
        "rmt_buffers",
        sa.Column("thread_id", sa.String(255), primary_key=True),
        sa.Column("slots", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("jsonb_typeof(slots) = 'object'", name="rmt_slots_not_empty"),
        schema="mega_agent",
    )

    # RMT indexes
    op.create_index("idx_rmt_updated", "rmt_buffers", ["updated_at"], schema="mega_agent")
    op.execute(
        """
        CREATE INDEX idx_rmt_expires
        ON mega_agent.rmt_buffers (expires_at)
        WHERE expires_at IS NOT NULL
        """
    )

    # ============================================================
    # cases - Legal case records
    # ============================================================
    op.create_table(
        "cases",
        sa.Column("case_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("case_type", sa.String(100), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("length(title) > 0", name="case_title_not_empty"),
        sa.CheckConstraint(
            "status IN ('draft', 'open', 'in_progress', 'closed', 'archived')",
            name="case_status_valid",
        ),
        schema="mega_agent",
    )

    # Cases indexes
    op.create_index("idx_cases_user_id", "cases", ["user_id"], schema="mega_agent")
    op.create_index("idx_cases_status", "cases", ["status"], schema="mega_agent")
    op.create_index("idx_cases_created", "cases", ["created_at"], schema="mega_agent")
    op.create_index(
        "idx_cases_data", "cases", ["data"], schema="mega_agent", postgresql_using="gin"
    )
    op.execute(
        """
        CREATE INDEX idx_cases_active
        ON mega_agent.cases (user_id, status)
        WHERE deleted_at IS NULL
        """
    )

    # ============================================================
    # documents - Document metadata with R2 references
    # ============================================================
    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("r2_bucket", sa.String(255), nullable=False),
        sa.Column("r2_key", sa.String(1000), nullable=False),
        sa.Column("r2_url", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("ocr_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("length(filename) > 0", name="doc_filename_not_empty"),
        sa.CheckConstraint("length(r2_key) > 0", name="doc_r2_key_not_empty"),
        schema="mega_agent",
    )

    # Documents indexes
    op.create_index("idx_documents_case_id", "documents", ["case_id"], schema="mega_agent")
    op.create_index("idx_documents_user_id", "documents", ["user_id"], schema="mega_agent")
    op.create_index("idx_documents_type", "documents", ["document_type"], schema="mega_agent")
    op.create_index("idx_documents_status", "documents", ["processing_status"], schema="mega_agent")
    op.create_index("idx_documents_uploaded", "documents", ["uploaded_at"], schema="mega_agent")


def downgrade() -> None:
    """Drop all tables and schema."""
    # Drop tables in reverse order
    op.drop_table("documents", schema="mega_agent")
    op.drop_table("cases", schema="mega_agent")
    op.drop_table("rmt_buffers", schema="mega_agent")
    op.drop_table("episodic_memory", schema="mega_agent")
    op.drop_table("semantic_memory", schema="mega_agent")

    # Drop schema (optional - commented out for safety)
    # op.execute("DROP SCHEMA IF EXISTS mega_agent CASCADE")
