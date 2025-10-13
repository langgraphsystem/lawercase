from __future__ import annotations


class KnowledgeStore:
    def __init__(self) -> None:
        self._data: list[dict] = []

    def upsert(self, item: dict) -> None:  # pragma: no cover - scaffold
        self._data.append(item)
