from __future__ import annotations

from typing import List, Optional

from ..models import AuditEvent, MemoryRecord


def compress_event(event: AuditEvent) -> str:
    """Tiny heuristic compression of an event to a one-liner."""
    user = f"u={event.user_id}" if event.user_id else "u=?"
    act = event.action
    src = event.source
    detail = event.payload.get("summary") or event.payload.get("text") or ""
    if detail:
        detail = str(detail)[:200]
    return f"[{src}] {act} {user} {detail}".strip()


def select_salient_facts(event: AuditEvent) -> List[MemoryRecord]:
    """Heuristic salience picker: convert notable events into semantic facts.

    In production, this should call an LLM to extract stable facts/preferences.
    """
    text = compress_event(event)
    tags = []
    if event.action in {"handle_command", "node_complete"}:
        tags.append("milestone")
    if "preference" in (event.tags or []):
        tags.append("preference")
    rec = MemoryRecord(
        user_id=event.user_id,
        type="semantic",
        text=text,
        salience=0.7,
        confidence=0.6,
        source=event.source,
        tags=tags,
    )
    return [rec]

