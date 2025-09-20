from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import AuditEvent


class EpisodicStore:
    """In-memory episodic event store, grouped by thread_id."""

    def __init__(self) -> None:
        self._by_thread: dict[str, list[AuditEvent]] = defaultdict(list)

    async def aappend(self, event: AuditEvent) -> None:
        tid = event.thread_id or "global"
        self._by_thread[tid].append(event)

    async def aget_thread_events(self, thread_id: str) -> list[AuditEvent]:
        return list(self._by_thread.get(thread_id, []))

    async def aget_all(self) -> dict[str, list[AuditEvent]]:
        return self._by_thread
