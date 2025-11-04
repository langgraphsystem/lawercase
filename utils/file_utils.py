from __future__ import annotations

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:  # scaffold
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
