"""Supabase-backed semantic memory store using pgvector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select

from ...logging_utils import get_logger
from ...storage.config import get_storage_config
from ...storage.connection import get_db_manager
from ...storage.models import SemanticMemoryDB
from ..models import MemoryRecord

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ...llm.supabase_embedder import SupabaseEmbedder


class SupabaseSemanticStore:
    """Semantic store that keeps vectors directly inside Supabase/PostgreSQL."""

    def __init__(
        self,
        *,
        namespace: str | None = None,
        embedder: SupabaseEmbedder | None = None,
    ) -> None:
        config = get_storage_config()
        self.namespace = namespace or config.vector_namespace
        self.db = get_db_manager()
        if embedder is None:
            from ...llm.supabase_embedder import create_supabase_embedder

            embedder = create_supabase_embedder()
        self.embedder = embedder
        self.embedding_model = getattr(self.embedder, "model", "text-embedding-3-large")
        self.embedding_dimension = getattr(self.embedder, "dimension", config.embedding_dimension)

    async def ainsert(self, records: Iterable[MemoryRecord]) -> int:
        """Insert memory records with Supabase embeddings."""
        records_list = list(records)
        if not records_list:
            return 0

        logger.info(
            "supabase_semantic_store.ainsert.start",
            count=len(records_list),
            namespace=self.namespace,
        )

        texts = [record.text for record in records_list]

        try:
            logger.info(
                "supabase_semantic_store.creating_embeddings",
                texts_count=len(texts),
                model=self.embedding_model,
                dimension=self.embedding_dimension,
            )

            embeddings = await self.embedder.aembed_documents(texts)

            logger.info(
                "supabase_semantic_store.embeddings_created",
                embeddings_count=len(embeddings),
                dimension=len(embeddings[0]) if embeddings else 0,
            )

            if len(embeddings) != len(records_list):
                raise ValueError(
                    f"Mismatch between records ({len(records_list)}) "
                    f"and embeddings ({len(embeddings)}) count"
                )

        except Exception as e:
            logger.exception(
                "supabase_semantic_store.embedding_failed",
                error=str(e),
                texts_count=len(texts),
                model=self.embedding_model,
            )
            raise

        async with self.db.session() as session:
            for i, (record, embedding) in enumerate(zip(records_list, embeddings, strict=False)):
                record_id = _ensure_uuid(record.id)
                record.id = str(record_id)

                # Collect metadata including case_id
                metadata = {
                    "thread_id": record.thread_id,
                    "case_id": record.case_id,  # Added for intake questionnaire
                    "salience": record.salience,
                    "confidence": record.confidence,
                    "tags": record.tags,
                }

                # Merge with record.metadata if present
                if record.metadata:
                    metadata.update(record.metadata)

                db_record = SemanticMemoryDB(
                    record_id=record_id,
                    namespace=self.namespace,
                    user_id=record.user_id or "anonymous",
                    thread_id=record.thread_id,
                    text=record.text,
                    type=record.type,
                    source=record.source,
                    tags=record.tags,
                    metadata_json={k: v for k, v in metadata.items() if v is not None},
                    embedding=embedding,
                    embedding_model=self.embedding_model,
                    embedding_dimension=self.embedding_dimension,
                )
                session.add(db_record)

                logger.debug(
                    "supabase_semantic_store.record_added",
                    record_id=str(record_id),
                    user_id=record.user_id,
                    case_id=record.case_id,
                    index=i + 1,
                    total=len(records_list),
                )

        logger.info(
            "supabase_semantic_store.ainsert.complete",
            count=len(records_list),
            namespace=self.namespace,
        )

        return len(records_list)

    async def aretrieve(
        self,
        query: str,
        user_id: str | None = None,
        topk: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Retrieve similar memories using pgvector cosine distance."""
        query_embedding = await self.embedder.aembed_query(query)

        stmt = select(
            SemanticMemoryDB,
            SemanticMemoryDB.embedding.cosine_distance(query_embedding).label("distance"),
        ).where(SemanticMemoryDB.namespace == self.namespace)

        if user_id:
            stmt = stmt.where(SemanticMemoryDB.user_id == user_id)

        filters = filters or {}
        if record_type := filters.get("type"):
            stmt = stmt.where(SemanticMemoryDB.type == record_type)
        if tags := filters.get("tags"):
            stmt = stmt.where(SemanticMemoryDB.tags.contains(tags))
        if source := filters.get("source"):
            stmt = stmt.where(SemanticMemoryDB.source == source)

        stmt = stmt.order_by("distance").limit(topk)

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.all()

        memories: list[MemoryRecord] = []
        for db_record, distance in rows:
            similarity = max(0.0, 1.0 - float(distance or 0.0))
            memories.append(
                MemoryRecord(
                    id=str(db_record.record_id),
                    user_id=db_record.user_id,
                    type=db_record.type,
                    text=db_record.text,
                    source=db_record.source,
                    tags=db_record.tags,
                    confidence=similarity,
                    created_at=db_record.created_at,
                )
            )
        return memories

    async def aall(self, user_id: str | None = None) -> list[MemoryRecord]:
        """Fetch all records (optionally filtered by user)."""
        stmt = select(SemanticMemoryDB).where(SemanticMemoryDB.namespace == self.namespace)
        if user_id:
            stmt = stmt.where(SemanticMemoryDB.user_id == user_id)

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            MemoryRecord(
                id=str(row.record_id),
                user_id=row.user_id,
                type=row.type,
                text=row.text,
                source=row.source,
                tags=row.tags,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def acount(self) -> int:
        """Count records in namespace."""
        stmt = select(func.count()).select_from(
            select(SemanticMemoryDB.record_id)
            .where(SemanticMemoryDB.namespace == self.namespace)
            .subquery()
        )
        async with self.db.session() as session:
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def adelete_by_user(self, user_id: str) -> None:
        """Delete all records for a user."""
        stmt = (
            delete(SemanticMemoryDB)
            .where(SemanticMemoryDB.user_id == user_id)
            .where(SemanticMemoryDB.namespace == self.namespace)
        )
        async with self.db.session() as session:
            await session.execute(stmt)

    async def health_check(self) -> bool:
        """Basic health check hitting Supabase/Postgres."""
        try:
            await self.acount()
            return True
        except Exception:
            return False


def _ensure_uuid(record_id: str | None) -> UUID:
    """Ensure we always have a UUID for primary keys."""
    if record_id:
        try:
            return UUID(record_id)
        except ValueError:
            pass
    return uuid4()


__all__ = ["SupabaseSemanticStore"]
