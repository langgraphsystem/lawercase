"""Supabase-backed vector store using pgvector in PostgreSQL."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select

from ..memory.models import MemoryRecord
from ..memory.stores.supabase_semantic_store import _ensure_uuid
from .config import get_storage_config
from .connection import get_db_manager
from .models import SemanticMemoryDB


class SupabaseVectorStore:
    """Low-level vector store that reads/writes directly to pgvector."""

    def __init__(self, namespace: str | None = None) -> None:
        config = get_storage_config()
        self.namespace = namespace or config.vector_namespace
        self.embedding_model = config.supabase_embedding_model
        self.embedding_dimension = config.embedding_dimension
        self.db = get_db_manager()

    async def upsert(
        self,
        records: list[MemoryRecord],
        embeddings: list[list[float]],
    ) -> int:
        """Insert or update records with precomputed embeddings."""
        if not records or not embeddings:
            return 0
        if len(records) != len(embeddings):
            raise ValueError("Records and embeddings length mismatch")

        async with self.db.session() as session:
            for record, embedding in zip(records, embeddings, strict=False):
                record_id = _ensure_uuid(record.id)
                session.merge(
                    SemanticMemoryDB(
                        record_id=record_id,
                        namespace=self.namespace,
                        user_id=record.user_id or "anonymous",
                        thread_id=record.thread_id,
                        text=record.text,
                        type=record.type,
                        source=record.source,
                        tags=record.tags,
                        metadata={"salience": record.salience, "confidence": record.confidence},
                        embedding=embedding,
                        embedding_model=self.embedding_model,
                        embedding_dimension=self.embedding_dimension,
                    )
                )
        return len(records)

    async def search(
        self,
        query_embedding: list[float],
        *,
        user_id: str | None = None,
        topk: int = 8,
        filters: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors using cosine similarity."""
        distance = SemanticMemoryDB.embedding.cosine_distance(query_embedding)
        stmt = (
            select(SemanticMemoryDB, distance.label("distance"))
            .where(SemanticMemoryDB.namespace == self.namespace)
            .order_by("distance")
            .limit(topk)
        )

        if user_id:
            stmt = stmt.where(SemanticMemoryDB.user_id == user_id)

        filters = filters or {}
        if record_type := filters.get("type"):
            stmt = stmt.where(SemanticMemoryDB.type == record_type)
        if tags := filters.get("tags"):
            stmt = stmt.where(SemanticMemoryDB.tags.contains(tags))
        if source := filters.get("source"):
            stmt = stmt.where(SemanticMemoryDB.source == source)

        async with self.db.session() as session:
            rows = (await session.execute(stmt)).all()

        results = []
        for db_record, distance_value in rows:
            similarity = max(0.0, 1.0 - float(distance_value or 0.0))
            if similarity < min_score:
                continue
            results.append(
                {
                    "record_id": str(db_record.record_id),
                    "score": similarity,
                    "metadata": {
                        "user_id": db_record.user_id,
                        "text": db_record.text,
                        "type": db_record.type,
                        "source": db_record.source,
                        "tags": db_record.tags,
                    },
                }
            )
        return results

    async def delete(self, record_ids: list[str]) -> None:
        """Delete vectors by record id."""
        if not record_ids:
            return
        uuids = [UUID(rid) for rid in record_ids]
        stmt = delete(SemanticMemoryDB).where(
            SemanticMemoryDB.record_id.in_(uuids),
            SemanticMemoryDB.namespace == self.namespace,
        )
        async with self.db.session() as session:
            await session.execute(stmt)

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        """Delete vectors matching metadata filters."""
        stmt = delete(SemanticMemoryDB).where(SemanticMemoryDB.namespace == self.namespace)
        if user_id := filters.get("user_id"):
            stmt = stmt.where(SemanticMemoryDB.user_id == user_id)
        if record_type := filters.get("type"):
            stmt = stmt.where(SemanticMemoryDB.type == record_type)
        async with self.db.session() as session:
            await session.execute(stmt)

    async def delete_all(self) -> None:
        """Delete everything in the namespace."""
        stmt = delete(SemanticMemoryDB).where(SemanticMemoryDB.namespace == self.namespace)
        async with self.db.session() as session:
            await session.execute(stmt)

    async def get_stats(self) -> dict[str, Any]:
        """Get vector counts for the namespace."""
        stmt = select(func.count()).where(SemanticMemoryDB.namespace == self.namespace)
        async with self.db.session() as session:
            count = (await session.execute(stmt)).scalar() or 0
        return {
            "total_vectors": int(count),
            "dimension": self.embedding_dimension,
            "namespace": self.namespace,
        }

    async def health_check(self) -> bool:
        """Check Postgres connectivity."""
        try:
            await self.get_stats()
            return True
        except Exception:
            return False


def create_supabase_vector_store(namespace: str | None = None) -> SupabaseVectorStore:
    """Factory helper mirroring the previous vector-store API."""

    return SupabaseVectorStore(namespace=namespace)


__all__ = ["SupabaseVectorStore", "create_supabase_vector_store"]
