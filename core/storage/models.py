"""SQLAlchemy models for PostgreSQL storage.

Schema includes:
- semantic_memory: Text + Supabase Vector embeddings
- episodic_memory: Audit trail and event log
- rmt_buffers: RMT (working memory) buffers
- cases: Legal case records
- documents: Document metadata with R2 references
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class SemanticMemoryDB(Base):
    """
    Semantic memory table with pgvector embeddings stored directly in Supabase/PostgreSQL.

    This replaces the previous external metadata table by persisting both content and vectors
    inside the warehouse for deterministic checkpointing and locality.
    """

    __tablename__ = "semantic_memory"
    __table_args__ = (
        CheckConstraint("length(text) > 0", name="semantic_text_not_empty"),
        Index("idx_semantic_user_id", "user_id"),
        Index("idx_semantic_namespace", "namespace"),
        Index("idx_semantic_type", "type"),
        Index("idx_semantic_tags", "tags", postgresql_using="gin"),
        Index("idx_semantic_created", "created_at", postgresql_using="btree"),
        {"schema": "mega_agent"},
    )

    record_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Namespace / tenancy
    namespace: Mapped[str] = mapped_column(String(255), default="default")

    # Ownership
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="fact")
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Embedding (pgvector) + metadata
    # NOTE: Using 2000 dimensions (max for pgvector HNSW index)
    # text-embedding-3-large supports variable dimensions via API parameter
    embedding: Mapped[list[float]] = mapped_column(Vector(2000))
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-3-large")
    embedding_dimension: Mapped[int] = mapped_column(default=2000)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class EpisodicMemoryDB(Base):
    """
    Episodic memory for audit trails and event logging.

    Stores all events and actions for audit purposes.
    """

    __tablename__ = "episodic_memory"
    __table_args__ = (
        CheckConstraint("length(source) > 0", name="episodic_source_not_empty"),
        CheckConstraint("length(action) > 0", name="episodic_action_not_empty"),
        Index("idx_episodic_user_id", "user_id"),
        Index("idx_episodic_thread_id", "thread_id"),
        Index("idx_episodic_source", "source"),
        Index("idx_episodic_action", "action"),
        Index("idx_episodic_timestamp", "timestamp", postgresql_using="btree"),
        Index("idx_episodic_thread_time", "thread_id", "timestamp"),
        Index("idx_episodic_payload", "payload", postgresql_using="gin"),
        {"schema": "mega_agent"},
    )

    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Context
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Event details
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Event chain (optional)
    parent_event_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class RMTBufferDB(Base):
    """
    RMT (Retrieval Memory Transformer) buffers for working memory.

    Stores temporary context slots for active conversations.
    """

    __tablename__ = "rmt_buffers"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(slots) = 'object'", name="rmt_slots_not_empty"),
        Index("idx_rmt_updated", "updated_at", postgresql_using="btree"),
        Index(
            "idx_rmt_expires",
            "expires_at",
            postgresql_where="expires_at IS NOT NULL",
        ),
        {"schema": "mega_agent"},
    )

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # RMT slots (persona, long_term_facts, open_loops, recent_summary)
    slots: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Optional TTL
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class CaseDB(Base):
    """Legal case records."""

    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint("length(title) > 0", name="case_title_not_empty"),
        CheckConstraint(
            "status IN ('draft', 'open', 'in_progress', 'closed', 'archived')",
            name="case_status_valid",
        ),
        Index("idx_cases_user_id", "user_id"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_created", "created_at", postgresql_using="btree"),
        Index("idx_cases_data", "data", postgresql_using="gin"),
        Index(
            "idx_cases_active",
            "user_id",
            "status",
            postgresql_where="deleted_at IS NULL",
        ),
        {"schema": "mega_agent"},
    )

    case_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Ownership
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Case details
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    case_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Flexible data storage
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Versioning
    version: Mapped[int] = mapped_column(default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class DocumentDB(Base):
    """Document metadata with R2 storage references."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("length(filename) > 0", name="doc_filename_not_empty"),
        CheckConstraint("length(r2_key) > 0", name="doc_r2_key_not_empty"),
        Index("idx_documents_case_id", "case_id"),
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_type", "document_type"),
        Index("idx_documents_status", "processing_status"),
        Index("idx_documents_uploaded", "uploaded_at", postgresql_using="btree"),
        {"schema": "mega_agent"},
    )

    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Ownership
    case_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # File details
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # R2 storage reference
    r2_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    r2_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    r2_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Processing status
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    ocr_completed: Mapped[bool] = mapped_column(default=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
