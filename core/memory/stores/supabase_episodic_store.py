"""Supabase-backed episodic memory store for audit events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import delete, select

from ...logging_utils import get_logger
from ...storage.connection import get_db_manager
from ...storage.models import EpisodicMemoryDB
from ..models import AuditEvent

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger(__name__)


class SupabaseEpisodicStore:
    """Episodic event store backed by Supabase/PostgreSQL.

    Stores audit events for conversations and agent actions.
    Replaces in-memory EpisodicStore for production use.
    """

    def __init__(self) -> None:
        self.db = get_db_manager()

    async def aappend(self, event: AuditEvent) -> str:
        """Append an audit event to the store. Returns event_id."""
        event_id = uuid4()
        thread_id = event.thread_id or "global"
        user_id = event.user_id or "system"

        logger.info(
            "supabase_episodic_store.append",
            event_id=str(event_id),
            thread_id=thread_id,
            source=event.source,
            action=event.action,
        )

        async with self.db.session() as session:
            db_event = EpisodicMemoryDB(
                event_id=event_id,
                user_id=user_id,
                thread_id=thread_id,
                source=event.source,
                action=event.action,
                payload=(
                    event.payload if isinstance(event.payload, dict) else {"value": event.payload}
                ),
                tags=list(event.tags) if event.tags else [],
                timestamp=event.timestamp or datetime.now(UTC),
                parent_event_id=None,
            )
            session.add(db_event)
            await session.commit()

        return str(event_id)

    async def aget_thread_events(
        self,
        thread_id: str,
        *,
        limit: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditEvent]:
        """Get all events for a thread, ordered by timestamp."""
        async with self.db.session() as session:
            stmt = (
                select(EpisodicMemoryDB)
                .where(EpisodicMemoryDB.thread_id == thread_id)
                .order_by(EpisodicMemoryDB.timestamp.asc())
            )

            if since is not None:
                stmt = stmt.where(EpisodicMemoryDB.timestamp >= since)
            if until is not None:
                stmt = stmt.where(EpisodicMemoryDB.timestamp <= until)
            if limit is not None and limit > 0:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            events = [self._row_to_event(row) for row in rows]
            logger.debug(
                "supabase_episodic_store.get_thread_events",
                thread_id=thread_id,
                count=len(events),
            )
            return events

    async def aget_user_events(
        self,
        user_id: str,
        *,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> list[AuditEvent]:
        """Get all events for a user across all threads."""
        async with self.db.session() as session:
            stmt = (
                select(EpisodicMemoryDB)
                .where(EpisodicMemoryDB.user_id == user_id)
                .order_by(EpisodicMemoryDB.timestamp.desc())
            )

            if since is not None:
                stmt = stmt.where(EpisodicMemoryDB.timestamp >= since)
            if limit is not None and limit > 0:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [self._row_to_event(row) for row in rows]

    async def aquery(
        self,
        *,
        thread_id: str | None = None,
        user_id: str | None = None,
        source: str | None = None,
        action: str | None = None,
        tags: Sequence[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        """Flexible query for episodic events."""
        async with self.db.session() as session:
            stmt = select(EpisodicMemoryDB).order_by(EpisodicMemoryDB.timestamp.asc())

            if thread_id is not None:
                stmt = stmt.where(EpisodicMemoryDB.thread_id == thread_id)
            if user_id is not None:
                stmt = stmt.where(EpisodicMemoryDB.user_id == user_id)
            if source is not None:
                stmt = stmt.where(EpisodicMemoryDB.source == source)
            if action is not None:
                stmt = stmt.where(EpisodicMemoryDB.action == action)
            if tags is not None and len(tags) > 0:
                stmt = stmt.where(EpisodicMemoryDB.tags.overlap(list(tags)))
            if since is not None:
                stmt = stmt.where(EpisodicMemoryDB.timestamp >= since)
            if until is not None:
                stmt = stmt.where(EpisodicMemoryDB.timestamp <= until)
            if limit is not None and limit > 0:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [self._row_to_event(row) for row in rows]

    async def aget_all(self) -> dict[str, list[AuditEvent]]:
        """Get all events grouped by thread_id."""
        async with self.db.session() as session:
            stmt = select(EpisodicMemoryDB).order_by(EpisodicMemoryDB.timestamp.asc())
            result = await session.execute(stmt)
            rows = result.scalars().all()

            by_thread: dict[str, list[AuditEvent]] = {}
            for row in rows:
                event = self._row_to_event(row)
                tid = event.thread_id or "global"
                if tid not in by_thread:
                    by_thread[tid] = []
                by_thread[tid].append(event)

            return by_thread

    async def apurge_before(self, cutoff: datetime) -> int:
        """Delete events older than cutoff. Returns count of deleted events."""
        async with self.db.session() as session:
            stmt = delete(EpisodicMemoryDB).where(EpisodicMemoryDB.timestamp < cutoff)
            result = await session.execute(stmt)
            await session.commit()

            logger.info(
                "supabase_episodic_store.purge_before",
                cutoff=cutoff.isoformat(),
                deleted_count=result.rowcount,
            )
            return result.rowcount

    async def adelete_thread(self, thread_id: str) -> int:
        """Delete all events for a thread."""
        async with self.db.session() as session:
            stmt = delete(EpisodicMemoryDB).where(EpisodicMemoryDB.thread_id == thread_id)
            result = await session.execute(stmt)
            await session.commit()

            logger.info(
                "supabase_episodic_store.delete_thread",
                thread_id=thread_id,
                deleted_count=result.rowcount,
            )
            return result.rowcount

    def _row_to_event(self, row: EpisodicMemoryDB) -> AuditEvent:
        """Convert a database row to an AuditEvent."""
        return AuditEvent(
            user_id=row.user_id,
            thread_id=row.thread_id,
            source=row.source,
            action=row.action,
            payload=row.payload,
            tags=list(row.tags) if row.tags else [],
            timestamp=row.timestamp,
        )
