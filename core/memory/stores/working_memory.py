from __future__ import annotations


class WorkingMemory:
    """Simple RMT buffer keyed by thread_id.

    Replace with Redis in production. Stores small rolling summaries and slots.
    """

    def __init__(self) -> None:
        self._buffers: dict[str, dict[str, str]] = {}

    async def aset_buffer(self, thread_id: str, slots: dict[str, str]) -> None:
        self._buffers[thread_id] = dict(slots)

    async def aget_buffer(self, thread_id: str) -> dict[str, str] | None:
        return self._buffers.get(thread_id)
