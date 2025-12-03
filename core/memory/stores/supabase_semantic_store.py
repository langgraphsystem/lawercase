"""Supabase-backed semantic memory store using pgvector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Text, delete, func, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY

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

                # Clean text for PostgreSQL (remove null bytes)
                clean_text = _sanitize_text(record.text)

                db_record = SemanticMemoryDB(
                    record_id=record_id,
                    namespace=self.namespace,
                    user_id=record.user_id or "anonymous",
                    thread_id=record.thread_id,
                    text=clean_text,
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
        """Retrieve similar memories using pgvector cosine distance.

        Args:
            query: Search query text
            user_id: Optional user ID filter
            topk: Maximum number of results
            filters: Optional filters dict with keys:
                - type: Memory type filter
                - tags: List of tags (all must match)
                - source: Source filter
                - case_id: Case ID filter (from metadata_json)
                - exclude_tags: List of tags to exclude

        Returns:
            List of MemoryRecord sorted by similarity
        """
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
            # Explicit cast to TEXT[] to match PostgreSQL column type
            stmt = stmt.where(SemanticMemoryDB.tags.contains(type_coerce(tags, ARRAY(Text))))
        if source := filters.get("source"):
            stmt = stmt.where(SemanticMemoryDB.source == source)
        # NEW: case_id filter from metadata_json
        if case_id := filters.get("case_id"):
            stmt = stmt.where(SemanticMemoryDB.metadata_json["case_id"].astext == case_id)
        # NEW: exclude_tags filter - exclude records containing any of these tags
        if exclude_tags := filters.get("exclude_tags"):
            for tag in exclude_tags:
                # Explicit cast to TEXT[] to match PostgreSQL column type
                stmt = stmt.where(~SemanticMemoryDB.tags.contains(type_coerce([tag], ARRAY(Text))))

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
                    case_id=(
                        db_record.metadata_json.get("case_id") if db_record.metadata_json else None
                    ),
                    type=db_record.type,
                    text=db_record.text,
                    source=db_record.source,
                    tags=db_record.tags,
                    metadata=db_record.metadata_json,
                    confidence=similarity,
                    created_at=db_record.created_at,
                )
            )
        return memories

    async def aretrieve_knowledge_base(
        self,
        query: str,
        topk: int = 8,
    ) -> list[MemoryRecord]:
        """Retrieve from knowledge base only (approved petitions, reference cases).

        Automatically filters to records tagged with 'knowledge_base'.
        Excludes case-specific documents.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of MemoryRecord from knowledge base only
        """
        logger.info(
            "supabase_semantic_store.aretrieve_knowledge_base",
            query=query[:100],
            topk=topk,
        )
        return await self.aretrieve(
            query=query,
            user_id=None,  # Knowledge base is shared across all users
            topk=topk,
            filters={
                "tags": ["knowledge_base"],
                "exclude_tags": ["case_document"],
            },
        )

    async def aretrieve_case_documents(
        self,
        query: str,
        case_id: str,
        user_id: str | None = None,
        topk: int = 8,
    ) -> list[MemoryRecord]:
        """Retrieve case-specific documents with semantic ranking.

        Automatically filters to records for the specific case.
        Excludes general knowledge base documents.

        Args:
            query: Search query text
            case_id: Case ID to filter by
            user_id: Optional user ID filter
            topk: Maximum number of results

        Returns:
            List of MemoryRecord for the specific case
        """
        logger.info(
            "supabase_semantic_store.aretrieve_case_documents",
            query=query[:100],
            case_id=case_id,
            topk=topk,
        )
        return await self.aretrieve(
            query=query,
            user_id=user_id,
            topk=topk,
            filters={
                "case_id": case_id,
                "exclude_tags": ["knowledge_base"],
            },
        )

    async def aretrieve_hybrid(
        self,
        query: str,
        case_id: str | None = None,
        user_id: str | None = None,
        topk: int = 8,
        knowledge_weight: float = 0.3,
    ) -> list[MemoryRecord]:
        """Retrieve from both knowledge base and case documents.

        Combines results from both sources with configurable weighting.
        Useful when agents need both reference materials and case-specific data.

        Args:
            query: Search query text
            case_id: Optional case ID for case-specific documents
            user_id: Optional user ID filter
            topk: Maximum number of results
            knowledge_weight: Weight for knowledge base results (0-1)
                0.0 = only case documents
                1.0 = only knowledge base
                0.3 = 30% knowledge, 70% case (default)

        Returns:
            List of MemoryRecord from both sources, merged by relevance
        """
        knowledge_k = max(1, int(topk * knowledge_weight))
        case_k = max(1, topk - knowledge_k)

        # Get knowledge base results
        knowledge_results = await self.aretrieve_knowledge_base(query=query, topk=knowledge_k)

        # Get case-specific results if case_id provided
        case_results: list[MemoryRecord] = []
        if case_id:
            case_results = await self.aretrieve_case_documents(
                query=query,
                case_id=case_id,
                user_id=user_id,
                topk=case_k,
            )

        # Merge and sort by confidence
        all_results = knowledge_results + case_results
        all_results.sort(key=lambda r: r.confidence or 0.0, reverse=True)

        logger.info(
            "supabase_semantic_store.aretrieve_hybrid",
            query=query[:100],
            case_id=case_id,
            knowledge_count=len(knowledge_results),
            case_count=len(case_results),
            total=len(all_results),
        )

        return all_results[:topk]

    async def aretrieve_rfe_knowledge(
        self,
        query: str,
        topk: int = 8,
    ) -> list[MemoryRecord]:
        """Search RFE knowledge base using pgvector similarity.

        Searches the mega_agent.rfe_knowledge table which contains
        RFE response patterns, USCIS quotes, and success strategies.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of MemoryRecord from RFE knowledge base
        """
        from sqlalchemy import text

        query_embedding = await self.embedder.aembed_query(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text(
            """
            SELECT
                id::text,
                criterion,
                issue_type,
                uscis_quote,
                problem_description,
                success_response,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM mega_agent.rfe_knowledge
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :topk
        """
        )

        async with self.db.session() as session:
            result = await session.execute(sql, {"embedding": embedding_str, "topk": topk})
            rows = result.fetchall()

        memories: list[MemoryRecord] = []
        for row in rows:
            # Build text from RFE fields
            text_parts = []
            if row.criterion:
                text_parts.append(f"Criterion: {row.criterion}")
            if row.issue_type:
                text_parts.append(f"Issue: {row.issue_type}")
            if row.problem_description:
                text_parts.append(f"Problem: {row.problem_description}")
            if row.uscis_quote:
                text_parts.append(f"USCIS: {row.uscis_quote}")
            if row.success_response:
                text_parts.append(f"Response: {row.success_response}")

            text_content = "\n".join(text_parts)

            memories.append(
                MemoryRecord(
                    id=row.id,
                    user_id=None,
                    type="rfe_knowledge",
                    text=text_content,
                    source="rfe_knowledge",
                    tags=["rfe", row.criterion] if row.criterion else ["rfe"],
                    confidence=float(row.similarity) if row.similarity else 0.0,
                )
            )

        logger.info(
            "supabase_semantic_store.aretrieve_rfe_knowledge",
            query=query[:100],
            topk=topk,
            results=len(memories),
        )

        return memories

    async def aretrieve_all_sources(
        self,
        query: str,
        topk: int = 10,
    ) -> list[MemoryRecord]:
        """Search ALL memory sources without user filtering.

        Combines results from:
        - semantic_memory table (knowledge base, case docs, etc.)
        - rfe_knowledge table (RFE patterns and responses)

        Args:
            query: Search query text
            topk: Maximum total results

        Returns:
            List of MemoryRecord from all sources, sorted by relevance
        """
        # Get from semantic memory (no user filter)
        semantic_results = await self.aretrieve(
            query=query,
            user_id=None,  # No user filter - search all
            topk=topk,
            filters=None,
        )

        # Get from RFE knowledge
        rfe_results = await self.aretrieve_rfe_knowledge(
            query=query,
            topk=topk,
        )

        # Combine and sort by confidence/similarity
        all_results = semantic_results + rfe_results
        all_results.sort(key=lambda r: r.confidence or 0.0, reverse=True)

        logger.info(
            "supabase_semantic_store.aretrieve_all_sources",
            query=query[:100],
            semantic_count=len(semantic_results),
            rfe_count=len(rfe_results),
            total=len(all_results),
        )

        return all_results[:topk]

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

    async def afetch_by_case_id(self, case_id: str, limit: int = 100) -> list[MemoryRecord]:
        """Fetch all records for a specific case_id from metadata_json.

        Args:
            case_id: The case ID to fetch records for
            limit: Maximum number of records to return

        Returns:
            List of MemoryRecord objects for this case
        """
        stmt = (
            select(SemanticMemoryDB)
            .where(SemanticMemoryDB.namespace == self.namespace)
            .where(SemanticMemoryDB.metadata_json["case_id"].astext == case_id)
            .order_by(SemanticMemoryDB.created_at.desc())
            .limit(limit)
        )

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        logger.info(
            "supabase_semantic_store.afetch_by_case_id",
            case_id=case_id,
            records_found=len(rows),
        )

        return [
            MemoryRecord(
                id=str(row.record_id),
                user_id=row.user_id,
                case_id=row.metadata_json.get("case_id") if row.metadata_json else None,
                type=row.type,
                text=row.text,
                source=row.source,
                tags=row.tags,
                metadata=row.metadata_json,
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

    async def acount_by_tags(self, tags: list[str]) -> int:
        """Count records that contain all specified tags.

        Args:
            tags: List of tags that must all be present

        Returns:
            Count of matching records
        """
        stmt = select(func.count()).select_from(
            select(SemanticMemoryDB.record_id)
            .where(SemanticMemoryDB.namespace == self.namespace)
            .where(SemanticMemoryDB.tags.contains(type_coerce(tags, ARRAY(Text))))
            .subquery()
        )
        async with self.db.session() as session:
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def aget_unique_sources(self, tags: list[str] | None = None) -> list[dict]:
        """Get unique sources with record counts.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of dicts with source and count
        """
        stmt = (
            select(
                SemanticMemoryDB.source,
                func.count(SemanticMemoryDB.record_id).label("count"),
            )
            .where(SemanticMemoryDB.namespace == self.namespace)
            .group_by(SemanticMemoryDB.source)
            .order_by(func.count(SemanticMemoryDB.record_id).desc())
        )

        if tags:
            stmt = stmt.where(SemanticMemoryDB.tags.contains(type_coerce(tags, ARRAY(Text))))

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.all()

        return [{"source": row.source, "count": row.count} for row in rows]

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


def _sanitize_text(text: str) -> str:
    """Remove null bytes and other invalid characters for PostgreSQL UTF-8.

    Args:
        text: Input text potentially containing invalid characters

    Returns:
        Cleaned text safe for PostgreSQL
    """
    if not text:
        return ""
    # Remove null bytes (0x00) which are invalid in PostgreSQL
    text = text.replace("\x00", "")
    # Remove Unicode replacement character
    text = text.replace("\ufffd", "")
    return text


def _ensure_uuid(record_id: str | None) -> UUID:
    """Ensure we always have a UUID for primary keys."""
    if record_id:
        try:
            return UUID(record_id)
        except ValueError:
            pass
    return uuid4()


__all__ = ["SupabaseSemanticStore"]
