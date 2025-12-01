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
