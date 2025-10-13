from __future__ import annotations

from typing import Any


async def aembed(texts: list[str], provider: str = "voyage", **kwargs: Any) -> list[list[float]]:
    # Scaffold: return zero vectors
    return [[0.0] * 8 for _ in texts]
