from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:  # scaffold
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}
