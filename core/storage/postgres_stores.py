"""PostgreSQL-backed stores for episodic memory and working memory.

These stores replace the in-memory implementations with persistent PostgreSQL storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import desc, select

from .connection import get_db_manager
from .models import EpisodicMemoryDB, RMTBufferDB

if TYPE_CHECKING:
    from ..memory.models import AuditEvent


class PostgresEpisodicStore:
    """
    PostgreSQL-backed episodic memory store for audit trails.

    Stores all audit events persistently in PostgreSQL.
    """

    def __init__(self):
        self.db = get_db_manager()

    async def aappend(self, event: AuditEvent) -> None:
        """
        Append audit event to episodic memory.

        Args:
            event: AuditEvent to store

        Example:
            >>> store = PostgresEpisodicStore()
            >>> event = AuditEvent(
            ...     event_id=str(uuid4()),
            ...     user_id="u1",
            ...     thread_id="t1",
            ...     source="test",
            ...     action="test_action",
            ...     payload={}
            ... )
            >>> await store.aappend(event)
        """
        async with self.db.session() as session:
            db_event = EpisodicMemoryDB(
                event_id=event.event_id if hasattr(event, "event_id") else uuid4(),
                user_id=event.user_id,
                thread_id=event.thread_id or "global",
                source=event.source,
                action=event.action,
                payload=event.payload,
                tags=event.tags if hasattr(event, "tags") and event.tags else [],
                timestamp=event.timestamp if hasattr(event, "timestamp") else None,
            )
            session.add(db_event)

    async def aget_thread_events(self, thread_id: str) -> list[AuditEvent]:
        """
        Get all events for a specific thread.

        Args:
            thread_id: Thread/conversation ID

        Returns:
            List of AuditEvents in chronological order

        Example:
            >>> store = PostgresEpisodicStore()
            >>> events = await store.aget_thread_events("thread_123")
            >>> len(events)
            5
        """
        from ..memory.models import AuditEvent

        async with self.db.session() as session:
            stmt = (
                select(EpisodicMemoryDB)
                .where(EpisodicMemoryDB.thread_id == thread_id)
                .order_by(EpisodicMemoryDB.timestamp)
            )
            result = await session.execute(stmt)
            db_events = result.scalars().all()

            # Convert to AuditEvent objects
            events = []
            for db_event in db_events:
                events.append(
                    AuditEvent(
                        event_id=str(db_event.event_id),
                        user_id=db_event.user_id,
                        thread_id=db_event.thread_id,
                        source=db_event.source,
                        action=db_event.action,
                        payload=db_event.payload,
                        tags=db_event.tags,
                        timestamp=db_event.timestamp,
                    )
                )

            return events

    async def aget_all(self) -> dict[str, list[AuditEvent]]:
        """
        Get all events grouped by thread_id.

        Returns:
            Dict mapping thread_id to list of events

        Example:
            >>> store = PostgresEpisodicStore()
            >>> all_events = await store.aget_all()
            >>> list(all_events.keys())
            ['thread_1', 'thread_2', 'thread_3']
        """
        from collections import defaultdict

        from ..memory.models import AuditEvent

        async with self.db.session() as session:
            stmt = select(EpisodicMemoryDB).order_by(EpisodicMemoryDB.timestamp)
            result = await session.execute(stmt)
            db_events = result.scalars().all()

            # Group by thread_id
            by_thread: dict[str, list[AuditEvent]] = defaultdict(list)
            for db_event in db_events:
                event = AuditEvent(
                    event_id=str(db_event.event_id),
                    user_id=db_event.user_id,
                    thread_id=db_event.thread_id,
                    source=db_event.source,
                    action=db_event.action,
                    payload=db_event.payload,
                    tags=db_event.tags,
                    timestamp=db_event.timestamp,
                )
                by_thread[db_event.thread_id].append(event)

            return dict(by_thread)

    async def aget_recent(self, limit: int = 100) -> list[AuditEvent]:
        """
        Get most recent events across all threads.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent AuditEvents

        Example:
            >>> store = PostgresEpisodicStore()
            >>> recent = await store.aget_recent(limit=50)
            >>> len(recent)
            50
        """
        from ..memory.models import AuditEvent

        async with self.db.session() as session:
            stmt = select(EpisodicMemoryDB).order_by(desc(EpisodicMemoryDB.timestamp)).limit(limit)
            result = await session.execute(stmt)
            db_events = result.scalars().all()

            events = []
            for db_event in db_events:
                events.append(
                    AuditEvent(
                        event_id=str(db_event.event_id),
                        user_id=db_event.user_id,
                        thread_id=db_event.thread_id,
                        source=db_event.source,
                        action=db_event.action,
                        payload=db_event.payload,
                        tags=db_event.tags,
                        timestamp=db_event.timestamp,
                    )
                )

            return events


class PostgresWorkingMemory:
    """
    PostgreSQL-backed working memory (RMT buffers).

    Stores RMT slots persistently for active conversations.
    """

    def __init__(self):
        self.db = get_db_manager()

    async def aset_buffer(self, thread_id: str, slots: dict[str, str]) -> None:
        """
        Set RMT buffer for a thread.

        Args:
            thread_id: Thread/conversation ID
            slots: RMT slots (persona, long_term_facts, open_loops, recent_summary)

        Example:
            >>> memory = PostgresWorkingMemory()
            >>> await memory.aset_buffer(
            ...     "thread_123",
            ...     {
            ...         "persona": "legal assistant",
            ...         "long_term_facts": "user prefers formal tone",
            ...         "open_loops": "",
            ...         "recent_summary": "discussed case X"
            ...     }
            ... )
        """
        async with self.db.session() as session:
            # Try to get existing buffer
            stmt = select(RMTBufferDB).where(RMTBufferDB.thread_id == thread_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.slots = slots
            else:
                # Create new
                new_buffer = RMTBufferDB(thread_id=thread_id, slots=slots)
                session.add(new_buffer)

    async def aget_buffer(self, thread_id: str) -> dict[str, str] | None:
        """
        Get RMT buffer for a thread.

        Args:
            thread_id: Thread/conversation ID

        Returns:
            RMT slots dict or None if not found

        Example:
            >>> memory = PostgresWorkingMemory()
            >>> slots = await memory.aget_buffer("thread_123")
            >>> print(slots["persona"])
            legal assistant
        """
        async with self.db.session() as session:
            stmt = select(RMTBufferDB).where(RMTBufferDB.thread_id == thread_id)
            result = await session.execute(stmt)
            buffer = result.scalar_one_or_none()

            return buffer.slots if buffer else None

    async def adelete_buffer(self, thread_id: str) -> None:
        """
        Delete RMT buffer for a thread.

        Args:
            thread_id: Thread/conversation ID

        Example:
            >>> memory = PostgresWorkingMemory()
            >>> await memory.adelete_buffer("thread_123")
        """
        async with self.db.session() as session:
            stmt = select(RMTBufferDB).where(RMTBufferDB.thread_id == thread_id)
            result = await session.execute(stmt)
            buffer = result.scalar_one_or_none()

            if buffer:
                await session.delete(buffer)

    async def aget_all_buffers(self) -> dict[str, dict[str, str]]:
        """
        Get all RMT buffers.

        Returns:
            Dict mapping thread_id to slots

        Example:
            >>> memory = PostgresWorkingMemory()
            >>> all_buffers = await memory.aget_all_buffers()
            >>> len(all_buffers)
            10
        """
        async with self.db.session() as session:
            stmt = select(RMTBufferDB)
            result = await session.execute(stmt)
            buffers = result.scalars().all()

            return {buffer.thread_id: buffer.slots for buffer in buffers}
