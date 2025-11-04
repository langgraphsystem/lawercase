from __future__ import annotations

from datetime import datetime


def utcnow_iso() -> str:  # scaffold
    return datetime.utcnow().isoformat()
