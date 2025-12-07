from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

from .models import AuditEvent, ConsolidateStats, MemoryRecord, RetrievalQuery
from .policies import select_salient_facts


class Embedder(Protocol):
    async def aembed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - interface
        ...


class _NoOpEmbedder:
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]


def _create_default_stores() -> tuple:
    """Create default Supabase stores for production."""
    from .stores import (SupabaseEpisodicStore, SupabaseSemanticStore,
                         SupabaseWorkingMemory)

    return (
        SupabaseSemanticStore(),
        SupabaseEpisodicStore(),
        SupabaseWorkingMemory(),
    )


class MemoryManager:
    """Facade over episodic/semantic stores and RMT buffer with optional embeddings.

    SUPABASE-ONLY: All stores use Supabase/PostgreSQL by default.
    No in-memory stores in production - data persists across restarts.

    - alog_audit: persist raw event (episodic)
    - awrite: reflect salient facts and store as semantic memory (embeddings optional)
    - aretrieve: hybrid placeholder retrieval from semantic store
    - aconsolidate: dedupe/prune
    - asnapshot_thread: dump episodic events for a thread
    """

    def __init__(
        self,
        *,
        semantic: Any | None = None,
        episodic: Any | None = None,
        working: Any | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        if semantic is None or episodic is None or working is None:
            default_semantic, default_episodic, default_working = _create_default_stores()
            self.semantic = semantic or default_semantic
            self.episodic = episodic or default_episodic
            self.working = working or default_working
        else:
            self.semantic = semantic
            self.episodic = episodic
            self.working = working
        self.embedder = embedder or _NoOpEmbedder()

    # ---- Auditing ----
    async def alog_audit(self, event: AuditEvent) -> None:
        await self.episodic.aappend(event)

    # ---- Write/Reflect ----
    async def awrite(
        self,
        payload: Iterable[MemoryRecord] | AuditEvent,
        *,
        policy: str | None = None,
    ) -> list[MemoryRecord]:
        """Write MemoryRecord(s) or reflect from an AuditEvent.

        - If payload is AuditEvent: run reflection policy to produce MemoryRecord(s).
        - Embeddings are computed if embedder provided.
        """
        if isinstance(payload, AuditEvent):
            records = select_salient_facts(payload)
        else:
            records = list(payload)

        texts = [r.text for r in records]
        if texts:
            embeddings = await self.embedder.aembed(texts)
            for r, emb in zip(records, embeddings, strict=False):
                r.embedding = emb

        await self.semantic.ainsert(records)
        return records

    # ---- Retrieve ----
    async def aretrieve(
        self,
        query: str | RetrievalQuery,
        *,
        user_id: str | None = None,
        topk: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        if isinstance(query, RetrievalQuery):
            user_id = query.user_id
            topk = query.topk
            filters = query.filters
            query = query.query
        return await self.semantic.aretrieve(
            query=query, user_id=user_id, topk=topk or 8, filters=filters
        )

    async def aretrieve_knowledge_base(
        self,
        query: str,
        topk: int = 8,
    ) -> list[MemoryRecord]:
        """Retrieve from knowledge base only (approved petitions, reference cases).

        Use this method when agents need reference materials but NOT
        case-specific client documents.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of MemoryRecord from knowledge base only
        """
        if hasattr(self.semantic, "aretrieve_knowledge_base"):
            return await self.semantic.aretrieve_knowledge_base(query=query, topk=topk)
        # Fallback for stores without this method
        return await self.semantic.aretrieve(
            query=query,
            topk=topk,
            filters={"tags": ["knowledge_base"]},
        )

    async def aretrieve_case_documents(
        self,
        query: str,
        case_id: str,
        user_id: str | None = None,
        topk: int = 8,
    ) -> list[MemoryRecord]:
        """Retrieve case-specific documents with semantic ranking.

        Use this method when agents need client-specific evidence
        but NOT general knowledge base materials.

        Args:
            query: Search query text
            case_id: Case ID to filter by
            user_id: Optional user ID filter
            topk: Maximum number of results

        Returns:
            List of MemoryRecord for the specific case
        """
        if hasattr(self.semantic, "aretrieve_case_documents"):
            return await self.semantic.aretrieve_case_documents(
                query=query, case_id=case_id, user_id=user_id, topk=topk
            )
        # Fallback for stores without this method
        return await self.semantic.aretrieve(
            query=query,
            user_id=user_id,
            topk=topk,
            filters={"case_id": case_id},
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

        Use this method when agents need BOTH reference materials
        AND case-specific evidence (e.g., for EB-1A analysis).

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
        if hasattr(self.semantic, "aretrieve_hybrid"):
            return await self.semantic.aretrieve_hybrid(
                query=query,
                case_id=case_id,
                user_id=user_id,
                topk=topk,
                knowledge_weight=knowledge_weight,
            )
        # Fallback: just use regular retrieve
        return await self.semantic.aretrieve(query=query, user_id=user_id, topk=topk)

    async def aretrieve_all_sources(
        self,
        query: str,
        topk: int = 10,
    ) -> list[MemoryRecord]:
        """Retrieve from ALL memory sources without user filtering.

        Searches both semantic_memory and rfe_knowledge tables.
        Use this for global knowledge lookup when user context is not needed.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of MemoryRecord from all sources, sorted by relevance
        """
        if hasattr(self.semantic, "aretrieve_all_sources"):
            return await self.semantic.aretrieve_all_sources(query=query, topk=topk)
        # Fallback for stores without this method
        return await self.semantic.aretrieve(query=query, user_id=None, topk=topk)

    # ---- Consolidate ----
    async def aconsolidate(self, *, user_id: str | None = None) -> ConsolidateStats:
        """No-op consolidation for Supabase stores.

        SupabaseSemanticStore handles persistence and indexing; in-memory
        deduplication via `_items` is not available. We return zeroed stats
        to keep the API compatible.
        """
        return ConsolidateStats(deduplicated=0, total_after=0)

    # ---- Snapshot ----
    async def asnapshot_thread(self, thread_id: str) -> str:
        events = await self.episodic.aget_thread_events(thread_id)
        lines = [f"{e.timestamp.isoformat()} {e.source}:{e.action} {e.payload}" for e in events]
        return "\n".join(lines)

    # ---- RMT Buffer ----
    async def aset_rmt(self, thread_id: str, slots: dict[str, str]) -> None:
        await self.working.aset_buffer(thread_id, slots)

    async def aget_rmt(self, thread_id: str) -> dict[str, str] | None:
        return await self.working.aget_buffer(thread_id)
