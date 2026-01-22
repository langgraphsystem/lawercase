from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MemoryType = Literal["episodic", "semantic", "persona", "open_loop"]


class AuditEvent(BaseModel):
    """Structured audit event captured on each command/graph transition.

    This is the raw event; reflection policies may convert it into MemoryRecord(s).
    """

    event_id: str = Field(..., description="Unique event id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str | None = None
    thread_id: str | None = None
    source: str = Field(..., description="origin like mega_agent|workflow_node|telegram")
    action: str = Field(..., description="e.g., handle_command|node_complete")
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class MemoryRecord(BaseModel):
    """Normalized memory item stored in semantic/episodic memory.

    Use Pydantic v2 model_dump for serialization.
    """

    id: str | None = None
    user_id: str | None = None
    case_id: str | None = None  # Added for intake questionnaire
    thread_id: str | None = None  # Added for thread context
    type: MemoryType = Field("semantic")
    text: str
    embedding: list[float] | None = None
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    decay_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None  # Added for flexible metadata storage


class RetrievalQuery(BaseModel):
    query: str
    user_id: str | None = None
    topk: int = 8
    filters: dict[str, Any] = Field(default_factory=dict)


class ConsolidateStats(BaseModel):
    deduplicated: int = 0
    pruned: int = 0
    merged: int = 0
    total_after: int = 0
