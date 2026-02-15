"""Supabase-backed RMT (working memory) store."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ...logging_utils import get_logger
from ...storage.connection import get_db_manager
from ...storage.models import RMTBufferDB

logger = get_logger(__name__)


class SupabaseWorkingMemory:
    """RMT buffer store backed by Supabase/PostgreSQL.

    Stores 4 slots per thread: persona, long_term_facts, open_loops, recent_summary.
    Replaces in-memory WorkingMemory for production use.
    """

    def __init__(self) -> None:
        self.db = get_db_manager()

    async def aset_buffer(self, thread_id: str, slots: dict[str, str]) -> None:
        """Set or update RMT buffer for a thread."""
        logger.info(
            "supabase_working_memory.set_buffer",
            thread_id=thread_id,
            slots_count=len(slots),
        )

        async with self.db.session() as session:
            stmt = (
                insert(RMTBufferDB)
                .values(
                    thread_id=thread_id,
                    slots=slots,
                    updated_at=datetime.now(UTC),
                )
                .on_conflict_do_update(
                    index_elements=["thread_id"],
                    set_={
                        "slots": slots,
                        "updated_at": datetime.now(UTC),
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def aget_buffer(self, thread_id: str) -> dict[str, str] | None:
        """Get RMT buffer for a thread."""
        async with self.db.session() as session:
            stmt = select(RMTBufferDB.slots).where(RMTBufferDB.thread_id == thread_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                logger.debug(
                    "supabase_working_memory.get_buffer.not_found",
                    thread_id=thread_id,
                )
                return None

            logger.debug(
                "supabase_working_memory.get_buffer.found",
                thread_id=thread_id,
                slots_count=len(row) if row else 0,
            )
            return dict(row) if row else {}

    async def adelete_buffer(self, thread_id: str) -> bool:
        """Delete RMT buffer for a thread."""
        from sqlalchemy import delete

        async with self.db.session() as session:
            stmt = delete(RMTBufferDB).where(RMTBufferDB.thread_id == thread_id)
            result = await session.execute(stmt)
            await session.commit()

            deleted = result.rowcount > 0
            logger.info(
                "supabase_working_memory.delete_buffer",
                thread_id=thread_id,
                deleted=deleted,
            )
            return deleted

    async def aupdate_slot(self, thread_id: str, slot_name: str, value: str) -> None:
        """Update a single slot in the RMT buffer."""
        current = await self.aget_buffer(thread_id)
        if current is None:
            current = {}
        current[slot_name] = value
        await self.aset_buffer(thread_id, current)

    async def aget_slot(self, thread_id: str, slot_name: str) -> str | None:
        """Get a single slot value from the RMT buffer."""
        buffer = await self.aget_buffer(thread_id)
        if buffer is None:
            return None
        return buffer.get(slot_name)

    async def acleanup_expired(self) -> int:
        """Remove expired RMT buffers."""
        from sqlalchemy import delete

        async with self.db.session() as session:
            stmt = delete(RMTBufferDB).where(
                RMTBufferDB.expires_at.isnot(None),
                RMTBufferDB.expires_at < datetime.now(UTC),
            )
            result = await session.execute(stmt)
            await session.commit()

            logger.info(
                "supabase_working_memory.cleanup_expired",
                deleted_count=result.rowcount,
            )
            return result.rowcount
