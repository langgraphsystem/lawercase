from __future__ import annotations

from typing import Any


def check_for_error(state: Any) -> bool:
    return bool(getattr(state, "error", None))


async def handle_error(state: Any) -> Any:
    # Placeholder: attach error info and continue or stop
    return state
