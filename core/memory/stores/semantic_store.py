from __future__ import annotations

from collections import OrderedDict
import time
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..models import MemoryRecord


class SemanticStore:
    """Lightweight in-memory semantic store with LRU eviction and TTL.

    Features:
    - LRU (Least Recently Used) eviction when max_items exceeded
    - TTL (Time To Live) for automatic expiration of old items
    - Prevents unbounded memory growth

    Replace with pgvector/FAISS in production. API kept async-compatible.
    """

    def __init__(
        self,
        max_items: int = 10000,
        ttl_seconds: int = 86400,  # 24 hours default
    ) -> None:
        """Initialize store with capacity limits.

        Args:
            max_items: Maximum number of items before LRU eviction (default: 10000)
            ttl_seconds: Time-to-live for items in seconds (default: 86400 = 24h)
        """
        # OrderedDict maintains insertion order for LRU
        # Key: record_id, Value: (MemoryRecord, timestamp)
        self._items: OrderedDict[str, tuple[MemoryRecord, float]] = OrderedDict()
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds

    async def ainsert(self, records: Iterable[MemoryRecord]) -> int:
        """Insert records with LRU eviction and TTL tracking.

        If a record doesn't have an ID, one will be generated.
        Oldest items are evicted when max_items is exceeded.
        """
        current_time = time.time()
        count = 0

        for r in records:
            # Ensure record has an ID
            if not r.id:
                r.id = str(uuid.uuid4())

            # Add/update with current timestamp
            self._items[r.id] = (r, current_time)
            count += 1

            # LRU eviction: remove oldest item if exceeded capacity
            if len(self._items) > self.max_items:
                self._items.popitem(last=False)  # Remove oldest (FIFO)

        # Cleanup expired items after insert
        await self._cleanup_expired()

        return count

    async def _cleanup_expired(self) -> int:
        """Remove expired items based on TTL.

        Returns:
            Number of items removed
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._items.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._items[key]

        return len(expired_keys)

    async def aretrieve(
        self,
        query: str,
        user_id: str | None = None,
        topk: int = 8,
        filters: dict | None = None,
    ) -> list[MemoryRecord]:
        """Naive keyword-based retrieval with TTL cleanup.

        Scores by token overlap; filter by user_id and optional tags/type.
        """
        # Cleanup expired items before retrieval
        await self._cleanup_expired()

        filters = filters or {}
        q_tokens = set(query.lower().split())
        scored: list[tuple[float, MemoryRecord]] = []

        # Iterate over (record, timestamp) tuples
        for record, _ in self._items.values():
            if user_id and record.user_id != user_id:
                continue
            if t := filters.get("type"):
                if record.type != t:
                    continue
            if tags := filters.get("tags"):
                if not set(tags).issubset(set(record.tags)):
                    continue
            text_tokens = set(record.text.lower().split())
            overlap = len(q_tokens & text_tokens)
            if overlap:
                scored.append((float(overlap), record))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:topk]]

    async def aall(self, user_id: str | None = None) -> list[MemoryRecord]:
        """Get all records, optionally filtered by user_id."""
        # Cleanup expired items first
        await self._cleanup_expired()

        return [
            record
            for record, _ in self._items.values()
            if (not user_id or record.user_id == user_id)
        ]

    async def acount(self) -> int:
        """Get count of active (non-expired) items."""
        # Cleanup expired items first
        await self._cleanup_expired()
        return len(self._items)
