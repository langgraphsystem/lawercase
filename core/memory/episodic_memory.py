from __future__ import annotations

"""High level episodic memory utilities built on top of the episodic store.

The Phase 2 roadmap calls for an explicit episodic memory layer that can:
    * capture chronological audit events
    * filter/search events by user, tags, and time windows
    * provide lightweight summarisation helpers for recent conversations

The core `EpisodicStore` already persists raw `AuditEvent` instances.
This module wraps that store with ergonomics and additional querying helpers
without forcing downstream callers to work with the low-level dictionary API.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import AuditEvent
from .stores.episodic_store import EpisodicStore


@dataclass(slots=True)
class EventQuery:
    """Filter options for episodic event retrieval."""

    thread_id: str | None = None
    user_id: str | None = None
    tags: Sequence[str] | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int | None = None


class EpisodicMemory:
    """Wrapper that offers rich access patterns over `EpisodicStore`.

    The wrapper stays fully async to match the underlying store API but adds
    ergonomics such as bulk logging, filtered queries, and summarisation
    helpers required by the Phase 2 memory hierarchy deliverable.
    """

    def __init__(self, store: EpisodicStore | None = None) -> None:
        self.store = store or EpisodicStore()

    async def record(self, event: AuditEvent) -> None:
        """Append a single event to the episodic store."""

        await self.store.aappend(event)

    async def record_many(self, events: Iterable[AuditEvent]) -> None:
        """Append several events in-order."""

        for event in events:
            await self.store.aappend(event)

    async def get_thread_events(
        self, thread_id: str, *, limit: int | None = None
    ) -> list[AuditEvent]:
        """Return the chronological list of events for a thread."""

        events = await self.store.aget_thread_events(thread_id)
        if limit is None or limit <= 0:
            return events
        return events[-limit:]

    async def query(self, query: EventQuery) -> list[AuditEvent]:
        """Flexible event filtering."""

        tags = {tag.lower() for tag in query.tags} if query.tags else None

        all_events = await self.store.aget_all()
        result: list[AuditEvent] = []

        thread_ids: Iterable[str]
        thread_ids = [query.thread_id] if query.thread_id is not None else all_events.keys()

        for thread_id in thread_ids:
            for event in all_events.get(thread_id, []):
                if query.user_id and event.user_id != query.user_id:
                    continue
                if query.since and event.timestamp < query.since:
                    continue
                if query.until and event.timestamp > query.until:
                    continue
                if tags and not tags.intersection(t.lower() for t in event.tags or []):
                    continue
                result.append(event)

        # Honour chronological order and limit from the tail
        result.sort(key=lambda e: e.timestamp)
        if query.limit and query.limit > 0:
            result = result[-query.limit :]
        return result

    async def recent_summary(
        self,
        thread_id: str,
        *,
        horizon: timedelta = timedelta(hours=12),
    ) -> list[str]:
        """Return human-friendly bullet points for the recent conversation."""

        now = datetime.utcnow()
        events = await self.query(EventQuery(thread_id=thread_id, since=now - horizon, until=now))
        lines: list[str] = []
        for event in events:
            payload = event.payload if isinstance(event.payload, str | int | float) else ""
            if isinstance(payload, dict):
                payload = payload.get("summary") or payload.get("text") or ""
            lines.append(
                f"{event.timestamp.isoformat(timespec='seconds')} • {event.source}:{event.action} {payload}"
            )
        return lines

    async def purge_before(self, *, cutoff: datetime) -> int:
        """Remove episodic events older than `cutoff`.

        Returns the number of deleted entries. This is primarily used during
        consolidation jobs to keep memory usage bounded.
        """

        all_events = await self.store.aget_all()
        deleted = 0
        for thread_id, events in list(all_events.items()):
            kept = [event for event in events if event.timestamp >= cutoff]
            deleted += len(events) - len(kept)
            all_events[thread_id] = kept
        return deleted

    async def timeline(self, thread_id: str) -> list[str]:
        """Render a full timeline for auditing or operator review."""

        events = await self.get_thread_events(thread_id)
        return [
            f"{event.timestamp.isoformat(timespec='seconds')} | {event.user_id or 'unknown'} | "
            f"{event.source}:{event.action} | {event.payload}"
            for event in events
        ]


__all__ = ["EpisodicMemory", "EventQuery"]
