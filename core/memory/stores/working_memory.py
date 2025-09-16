from __future__ import annotations

from typing import Dict, Optional


class WorkingMemory:
    """Simple RMT buffer keyed by thread_id.

    Replace with Redis in production. Stores small rolling summaries and slots.
    """

    def __init__(self) -> None:
        self._buffers: Dict[str, Dict[str, str]] = {}

    async def aset_buffer(self, thread_id: str, slots: Dict[str, str]) -> None:
        self._buffers[thread_id] = dict(slots)

    async def aget_buffer(self, thread_id: str) -> Optional[Dict[str, str]]:
        return self._buffers.get(thread_id)

