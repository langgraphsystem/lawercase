"""Updated MemoryManager with production-ready Pinecone + PostgreSQL + R2 support.

This version maintains backward compatibility with the original MemoryManager
while adding support for production storage backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

from .models import AuditEvent, ConsolidateStats, MemoryRecord, RetrievalQuery
from .policies import select_salient_facts


class Embedder(Protocol):
    """Protocol for embedding providers."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...


class _NoOpEmbedder:
    """Fallback embedder that returns empty vectors."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]


class MemoryManager:
    """
    Unified memory manager with support for both in-memory and production backends.

    Backends:
    - Development: In-memory stores (default)
    - Production: PostgreSQL + Pinecone + R2

    Usage:
        # Development (in-memory)
        memory = MemoryManager()

        # Production
        memory = create_production_memory_manager()
    """

    def __init__(
        self,
        *,
        semantic: Any | None = None,
        episodic: Any | None = None,
        working: Any | None = None,
        embedder: Embedder | None = None,
        use_production: bool = False,
    ) -> None:
        """
        Initialize MemoryManager.

        Args:
            semantic: SemanticStore instance (in-memory or Pinecone)
            episodic: EpisodicStore instance (in-memory or PostgreSQL)
            working: WorkingMemory instance (in-memory or PostgreSQL)
            embedder: Embedder instance (NoOp, Gemini, or Voyage)
            use_production: Auto-setup production stores if True
        """
        if use_production:
            # Auto-initialize production stores
            from ..llm.voyage_embedder import create_voyage_embedder
            from ..storage.postgres_stores import PostgresEpisodicStore, PostgresWorkingMemory
            from .stores.pinecone_semantic_store import PineconeSemanticStoreAdapter

            self.semantic = semantic or PineconeSemanticStoreAdapter()
            self.episodic = episodic or PostgresEpisodicStore()
            self.working = working or PostgresWorkingMemory()
            self.embedder = embedder or create_voyage_embedder()
        else:
            # Use in-memory stores (original behavior)
            from .stores import EpisodicStore, SemanticStore, WorkingMemory

            self.semantic = semantic or SemanticStore()
            self.episodic = episodic or EpisodicStore()
            self.working = working or WorkingMemory()
            self.embedder = embedder or _NoOpEmbedder()

        self._is_production = use_production

    # ---- Auditing ----
    async def alog_audit(self, event: AuditEvent) -> None:
        """
        Log audit event to episodic memory.

        Args:
            event: AuditEvent to log

        Example:
            >>> memory = MemoryManager()
            >>> event = AuditEvent(
            ...     event_id="evt_123",
            ...     user_id="u1",
            ...     thread_id="t1",
            ...     source="test",
            ...     action="test_action",
            ...     payload={}
            ... )
            >>> await memory.alog_audit(event)
        """
        await self.episodic.aappend(event)

    # ---- Write/Reflect ----
    async def awrite(
        self,
        payload: Iterable[MemoryRecord] | AuditEvent,
        *,
        policy: str | None = None,
    ) -> list[MemoryRecord]:
        """
        Write MemoryRecord(s) or reflect from an AuditEvent.

        - If payload is AuditEvent: run reflection policy to produce MemoryRecord(s).
        - Embeddings are computed if embedder provided.
        - Records are stored in semantic memory (Pinecone in production).

        Args:
            payload: Either MemoryRecord list or AuditEvent
            policy: Reflection policy name (currently unused)

        Returns:
            List of MemoryRecord objects that were stored

        Example:
            >>> memory = create_production_memory_manager()
            >>> records = [MemoryRecord(user_id="u1", text="Important fact")]
            >>> stored = await memory.awrite(records)
        """
        if isinstance(payload, AuditEvent):
            records = select_salient_facts(payload)
        else:
            records = list(payload)

        # Generate embeddings
        texts = [r.text for r in records]
        if texts:
            embeddings = await self.embedder.aembed(texts)
            for r, emb in zip(records, embeddings, strict=False):
                r.embedding = emb

        # Insert into semantic store
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
        """
        Retrieve relevant memories using semantic search.

        In production mode, uses Pinecone vector search.
        In dev mode, uses keyword-based search.

        Args:
            query: Search query string or RetrievalQuery object
            user_id: Filter by user_id
            topk: Number of results to return
            filters: Additional metadata filters

        Returns:
            List of relevant MemoryRecord objects

        Example:
            >>> memory = create_production_memory_manager()
            >>> results = await memory.aretrieve(
            ...     "find legal precedents",
            ...     user_id="u1",
            ...     topk=5
            ... )
        """
        if isinstance(query, RetrievalQuery):
            user_id = query.user_id
            topk = query.topk
            filters = query.filters
            query = query.query

        return await self.semantic.aretrieve(
            query=query, user_id=user_id, topk=topk or 8, filters=filters
        )

    # ---- Consolidate ----
    async def aconsolidate(self, *, user_id: str | None = None) -> ConsolidateStats:
        """
        Consolidate memory: deduplicate and prune.

        Note: In production mode (Pinecone), this is a no-op as Pinecone
        handles deduplication via upsert with same ID.

        Args:
            user_id: Optional user_id to consolidate

        Returns:
            ConsolidateStats with consolidation results
        """
        if self._is_production:
            # Pinecone handles deduplication automatically
            count = await self.semantic.acount()
            return ConsolidateStats(deduplicated=0, total_after=count)

        # In-memory consolidation (original logic)
        all_items = await self.semantic.aall(user_id=user_id)
        seen = set()
        deduped: list[MemoryRecord] = []
        deduplicated = 0

        for r in all_items:
            key = (r.user_id, r.type, r.text)
            if key in seen:
                deduplicated += 1
                continue
            seen.add(key)
            deduped.append(r)

        # Replace items (only works for in-memory store)
        if hasattr(self.semantic, "_items"):
            if user_id is None:
                self.semantic._items = deduped  # type: ignore[attr-defined]
            else:
                self.semantic._items = [  # type: ignore[attr-defined]
                    r for r in self.semantic._items if r.user_id != user_id
                ] + deduped

        return ConsolidateStats(
            deduplicated=deduplicated,
            total_after=len(deduped) if hasattr(self.semantic, "_items") else 0,
        )

    # ---- Snapshot ----
    async def asnapshot_thread(self, thread_id: str) -> str:
        """
        Get formatted snapshot of all events in a thread.

        Args:
            thread_id: Thread/conversation ID

        Returns:
            Formatted string with all events

        Example:
            >>> memory = MemoryManager()
            >>> snapshot = await memory.asnapshot_thread("thread_123")
            >>> print(snapshot)
        """
        events = await self.episodic.aget_thread_events(thread_id)
        lines = [f"{e.timestamp.isoformat()} {e.source}:{e.action} {e.payload}" for e in events]
        return "\n".join(lines)

    # ---- RMT Buffer ----
    async def aset_rmt(self, thread_id: str, slots: dict[str, str]) -> None:
        """
        Set RMT buffer slots for a thread.

        Args:
            thread_id: Thread/conversation ID
            slots: RMT slots dict (persona, long_term_facts, open_loops, recent_summary)

        Example:
            >>> memory = MemoryManager()
            >>> await memory.aset_rmt("thread_123", {
            ...     "persona": "legal assistant",
            ...     "long_term_facts": "user prefers formal tone",
            ...     "open_loops": "",
            ...     "recent_summary": "discussed case X"
            ... })
        """
        await self.working.aset_buffer(thread_id, slots)

    async def aget_rmt(self, thread_id: str) -> dict[str, str] | None:
        """
        Get RMT buffer slots for a thread.

        Args:
            thread_id: Thread/conversation ID

        Returns:
            RMT slots dict or None if not found

        Example:
            >>> memory = MemoryManager()
            >>> slots = await memory.aget_rmt("thread_123")
        """
        return await self.working.aget_buffer(thread_id)

    # ---- Health Check ----
    async def health_check(self) -> dict[str, bool]:
        """
        Check health of all storage backends.

        Returns:
            Dict with health status of each component

        Example:
            >>> memory = create_production_memory_manager()
            >>> health = await memory.health_check()
            >>> print(health)
            {'semantic': True, 'episodic': True, 'working': True}
        """
        health = {}

        # Check semantic store (Pinecone or in-memory)
        if hasattr(self.semantic, "health_check"):
            health["semantic"] = await self.semantic.health_check()
        else:
            health["semantic"] = True  # In-memory is always healthy

        # Check episodic store (PostgreSQL or in-memory)
        if hasattr(self.episodic, "health_check"):
            health["episodic"] = await self.episodic.health_check()
        else:
            health["episodic"] = True

        # Check working memory (PostgreSQL or in-memory)
        if hasattr(self.working, "health_check"):
            health["working"] = await self.working.health_check()
        else:
            health["working"] = True

        return health


# ---- Factory Functions ----


def create_production_memory_manager(
    namespace: str | None = None,
) -> MemoryManager:
    """
    Create MemoryManager with production backends (Pinecone + PostgreSQL).

    Args:
        namespace: Pinecone namespace for multi-tenancy

    Returns:
        MemoryManager configured for production

    Example:
        >>> memory = create_production_memory_manager(namespace="production")
        >>> # Now uses Pinecone, PostgreSQL, and Voyage AI
    """
    from ..llm.voyage_embedder import create_voyage_embedder
    from ..storage.postgres_stores import PostgresEpisodicStore, PostgresWorkingMemory
    from .stores.pinecone_semantic_store import PineconeSemanticStoreAdapter

    return MemoryManager(
        semantic=PineconeSemanticStoreAdapter(namespace=namespace),
        episodic=PostgresEpisodicStore(),
        working=PostgresWorkingMemory(),
        embedder=create_voyage_embedder(),
        use_production=True,
    )


def create_dev_memory_manager() -> MemoryManager:
    """
    Create MemoryManager with in-memory backends (for development/testing).

    Returns:
        MemoryManager configured for development

    Example:
        >>> memory = create_dev_memory_manager()
        >>> # Uses in-memory stores, no external dependencies
    """
    return MemoryManager(use_production=False)
