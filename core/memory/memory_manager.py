from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

from .models import AuditEvent, ConsolidateStats, MemoryRecord, RetrievalQuery
from .policies import select_salient_facts
from .stores import EpisodicStore, SemanticStore, WorkingMemory


class Embedder(Protocol):
    async def aembed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - interface
        ...


class _NoOpEmbedder:
    async def aembed(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]


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
        semantic: SemanticStore | None = None,
        episodic: EpisodicStore | None = None,
        working: WorkingMemory | None = None,
        embedder: Embedder | None = None,
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

    # ---- Consolidate ----
    async def aconsolidate(self, *, user_id: str | None = None) -> ConsolidateStats:
        """Placeholder consolidation: deduplicate identical texts per user."""
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
    async def aset_rmt(self, thread_id: str, slots: dict[str, str]) -> None:
        await self.working.aset_buffer(thread_id, slots)

    async def aget_rmt(self, thread_id: str) -> dict[str, str] | None:
        return await self.working.aget_buffer(thread_id)
