from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Protocol

from .models import AuditEvent, ConsolidateStats, MemoryRecord, RetrievalQuery
from .policies import select_salient_facts
from .stores import EpisodicStore, SemanticStore, WorkingMemory


class Embedder(Protocol):
    async def aembed(self, texts: List[str]) -> List[List[float]]:  # pragma: no cover - interface
        ...


class _NoOpEmbedder:
    async def aembed(self, texts: List[str]) -> List[List[float]]:
        return [[] for _ in texts]


# Import real embedder when available
try:
    from ..embeddings import RealEmbedder, EmbeddingManager
except ImportError:
    RealEmbedder = None
    EmbeddingManager = None


class MemoryManager:
    """Facade over episodic/semantic stores and RMT buffer with optional embeddings.

    - alog_audit: persist raw event (episodic)
    - awrite: reflect salient facts and store as semantic memory (embeddings optional)
    - aretrieve: hybrid placeholder retrieval from semantic store
    - aconsodlidate: naive dedupe/prune placeholder
    - asnapshot_thread: dump episodic events for a thread
    """

    def __init__(
        self,
        *,
        semantic: Optional[SemanticStore] = None,
        episodic: Optional[EpisodicStore] = None,
        working: Optional[WorkingMemory] = None,
        embedder: Optional[Embedder] = None,
    ) -> None:
        self.semantic = semantic or SemanticStore()
        self.episodic = episodic or EpisodicStore()
        self.working = working or WorkingMemory()
        self.embedder = embedder or _NoOpEmbedder()

    # ---- Auditing ----
    async def alog_audit(self, event: AuditEvent) -> None:
        await self.episodic.aappend(event)

    # ---- Write/Reflect ----
    async def awrite(
        self,
        payload: Iterable[MemoryRecord] | AuditEvent,
        *,
        policy: Optional[str] = None,
    ) -> List[MemoryRecord]:
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
            for r, emb in zip(records, embeddings):
                r.embedding = emb

        await self.semantic.ainsert(records)
        return records

    # ---- Retrieve ----
    async def aretrieve(
        self, query: str | RetrievalQuery, *, user_id: Optional[str] = None, topk: Optional[int] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryRecord]:
        if isinstance(query, RetrievalQuery):
            user_id = query.user_id
            topk = query.topk
            filters = query.filters
            query = query.query
        return await self.semantic.aretrieve(query=query, user_id=user_id, topk=topk or 8, filters=filters)

    # ---- Consolidate ----
    async def aconsolidate(self, *, user_id: Optional[str] = None) -> ConsolidateStats:
        """Placeholder consolidation: deduplicate identical texts per user."""
        all_items = await self.semantic.aall(user_id=user_id)
        seen = set()
        deduped: List[MemoryRecord] = []
        deduplicated = 0
        for r in all_items:
            key = (r.user_id, r.type, r.text)
            if key in seen:
                deduplicated += 1
                continue
            seen.add(key)
            deduped.append(r)
        # Replace store items only in in-memory placeholder
        if user_id is None:
            self.semantic._items = deduped  # type: ignore[attr-defined]
        else:
            # selective rewrite
            self.semantic._items = [  # type: ignore[attr-defined]
                r for r in self.semantic._items if r.user_id != user_id
            ] + deduped
        return ConsolidateStats(deduplicated=deduplicated, total_after=len(self.semantic._items))  # type: ignore[attr-defined]

    # ---- Snapshot ----
    async def asnapshot_thread(self, thread_id: str) -> str:
        events = await self.episodic.aget_thread_events(thread_id)
        lines = [f"{e.timestamp.isoformat()} {e.source}:{e.action} {e.payload}" for e in events]
        return "\n".join(lines)

    # ---- RMT Buffer ----
    async def aset_rmt(self, thread_id: str, slots: Dict[str, str]) -> None:
        await self.working.aset_buffer(thread_id, slots)

    async def aget_rmt(self, thread_id: str) -> Optional[Dict[str, str]]:
        return await self.working.aget_buffer(thread_id)

    @classmethod
    def create_with_real_embeddings(
        cls,
        embedding_configs: Optional[List[Any]] = None,
        semantic: Optional[SemanticStore] = None,
        episodic: Optional[EpisodicStore] = None,
        working: Optional[WorkingMemory] = None,
    ) -> "MemoryManager":
        """Create MemoryManager with real embedding integration.

        Args:
            embedding_configs: List of EmbeddingConfig objects
            semantic: Optional semantic store
            episodic: Optional episodic store
            working: Optional working memory

        Returns:
            MemoryManager configured with real embeddings

        Note:
            Falls back to NoOpEmbedder if real embeddings are not available
        """
        embedder = None

        if RealEmbedder and EmbeddingManager and embedding_configs:
            try:
                embedding_manager = EmbeddingManager(embedding_configs)
                embedder = RealEmbedder(embedding_manager)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to initialize real embeddings, falling back to NoOp: {e}")
                embedder = _NoOpEmbedder()
        else:
            embedder = _NoOpEmbedder()

        return cls(
            semantic=semantic,
            episodic=episodic,
            working=working,
            embedder=embedder,
        )

