from __future__ import annotations

"""High level memory hierarchy manager.

Phase 2 requires a coordinated memory stack that understands episodic,
semantic, and working-memory layers. This module exposes a single facade
that uses the existing MemoryManager implementation while providing richer
context assembly utilities demanded by orchestrators and agents.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .episodic_memory import EpisodicMemory, EventQuery
from .models import AuditEvent, MemoryRecord

# We favour the production-ready MemoryManager v2 when available, but fall back
# to the original implementation to keep backwards compatibility for tests.
try:
    from .memory_manager_v2 import MemoryManager as _BaseMemoryManager, create_dev_memory_manager
except ImportError:  # pragma: no cover - defensive in environments without v2
    from .memory_manager import MemoryManager as _BaseMemoryManager  # type: ignore

    def create_dev_memory_manager() -> _BaseMemoryManager:
        return _BaseMemoryManager()


@dataclass(slots=True)
class MemoryContext:
    """Aggregated view returned by `MemoryHierarchy.load_context`."""

    reflected: Sequence[MemoryRecord]
    retrieved: Sequence[MemoryRecord]
    episodic_events: Sequence[AuditEvent]
    rmt_slots: dict[str, str]


class MemoryHierarchy:
    """Compose episodic, semantic and working memory into a single facade."""

    def __init__(
        self,
        *,
        memory_manager: _BaseMemoryManager | None = None,
        episodic: EpisodicMemory | None = None,
    ) -> None:
        self.manager = memory_manager or create_dev_memory_manager()
        self.episodic = episodic or EpisodicMemory(self.manager.episodic)

    # --------------------------------------------------------------------- #
    # Write paths
    # --------------------------------------------------------------------- #
    async def record_event(self, event: AuditEvent, *, reflect: bool = True) -> list[MemoryRecord]:
        """Log an event into episodic memory and optionally reflect into semantic memory."""

        await self.manager.alog_audit(event)
        if reflect:
            return await self.manager.awrite(event)
        return []

    async def record_events(
        self, events: Iterable[AuditEvent], *, reflect: bool = True
    ) -> list[MemoryRecord]:
        """Bulk variant of :meth:`record_event`."""

        reflected: list[MemoryRecord] = []
        for event in events:
            await self.manager.alog_audit(event)
            if reflect:
                reflected.extend(await self.manager.awrite(event))
        return reflected

    async def update_working_memory(self, thread_id: str, slots: dict[str, str]) -> None:
        """Persist RMT buffer for the conversation thread."""

        await self.manager.aset_rmt(thread_id, slots)

    # --------------------------------------------------------------------- #
    # Read paths
    # --------------------------------------------------------------------- #
    async def retrieve_semantic(
        self,
        query: str,
        *,
        user_id: str | None = None,
        topk: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Hybrid semantic retrieval wrapper."""

        return await self.manager.aretrieve(
            query,
            user_id=user_id,
            topk=topk,
            filters=filters,
        )

    async def load_context(
        self,
        *,
        thread_id: str,
        query: str | None = None,
        user_id: str | None = None,
        topk: int = 8,
        since: timedelta | None = timedelta(hours=6),
    ) -> MemoryContext:
        """Assemble a full memory context for agent orchestration."""

        # Semantic retrieval first (optional query)
        retrieved: list[MemoryRecord] = []
        if query:
            retrieved = await self.retrieve_semantic(query, user_id=user_id, topk=topk)

        # Episodic events in horizon window
        horizon = datetime.utcnow() - since if since is not None else None

        episodic_events = await self.episodic.query(
            EventQuery(thread_id=thread_id, user_id=user_id, since=horizon)
        )

        # Reflect newly relevant episodic events into semantic slots
        reflected: list[MemoryRecord] = []
        if episodic_events:
            # Only reflect the most recent event to keep budget in check
            reflected = await self.manager.awrite(episodic_events[-1])

        # Working memory snapshot
        rmt_slots = await self.manager.aget_rmt(thread_id) or {}

        return MemoryContext(
            reflected=reflected,
            retrieved=retrieved,
            episodic_events=episodic_events,
            rmt_slots=rmt_slots,
        )

    async def get_thread_snapshot(self, thread_id: str) -> str:
        """Return formatted episodic snapshot (delegates to manager helper)."""

        return await self.manager.asnapshot_thread(thread_id)

    async def recent_timeline(self, thread_id: str, *, hours: int = 1) -> list[str]:
        """Convenience wrapper to expose the episodic timeline helper."""

        return await self.episodic.recent_summary(thread_id, horizon=timedelta(hours=hours))

    # --------------------------------------------------------------------- #
    # Maintenance
    # --------------------------------------------------------------------- #
    async def consolidate(self, *, user_id: str | None = None) -> dict[str, Any]:
        """Invoke semantic consolidation and return stats."""

        stats = await self.manager.aconsolidate(user_id=user_id)
        return stats.model_dump() if hasattr(stats, "model_dump") else dict(stats.__dict__)

    async def purge_episodic_before(self, cutoff: datetime) -> int:
        """Keep episodic memory bounded."""

        return await self.episodic.purge_before(cutoff=cutoff)

    async def health_check(self) -> dict[str, bool]:
        """Expose backend health information."""

        if hasattr(self.manager, "health_check"):
            return await self.manager.health_check()
        # Legacy managers do not implement health checks but operate in-memory
        return {"semantic": True, "episodic": True, "working": True}


__all__ = ["EventQuery", "MemoryContext", "MemoryHierarchy"]
