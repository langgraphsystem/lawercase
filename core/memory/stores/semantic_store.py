from __future__ import annotations

from collections.abc import Iterable

from ..models import MemoryRecord


class SemanticStore:
    """Lightweight in-memory semantic store interface.

    Replace with pgvector/FAISS in production. API kept async-compatible.
    """

    def __init__(self) -> None:
        self._items: list[MemoryRecord] = []

    async def ainsert(self, records: Iterable[MemoryRecord]) -> int:
        count = 0
        for r in records:
            self._items.append(r)
            count += 1
        return count

    async def aretrieve(
        self,
        query: str,
        user_id: str | None = None,
        topk: int = 8,
        filters: dict | None = None,
    ) -> list[MemoryRecord]:
        """Naive keyword-based retrieval as a placeholder.

        Scores by token overlap; filter by user_id and optional tags/type.
        """

        filters = filters or {}
        q_tokens = set(query.lower().split())
        scored: list[tuple[float, MemoryRecord]] = []
        for r in self._items:
            if user_id and r.user_id != user_id:
                continue
            if t := filters.get("type"):
                if r.type != t:
                    continue
            if tags := filters.get("tags"):
                if not set(tags).issubset(set(r.tags)):
                    continue
            text_tokens = set(r.text.lower().split())
            overlap = len(q_tokens & text_tokens)
            if overlap:
                scored.append((float(overlap), r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:topk]]

    async def aall(self, user_id: str | None = None) -> list[MemoryRecord]:
        return [r for r in self._items if (not user_id or r.user_id == user_id)]

    async def acount(self) -> int:
        return len(self._items)
