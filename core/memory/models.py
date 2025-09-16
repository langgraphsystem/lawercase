from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


MemoryType = Literal["episodic", "semantic", "persona", "open_loop"]


class AuditEvent(BaseModel):
    """Structured audit event captured on each command/graph transition.

    This is the raw event; reflection policies may convert it into MemoryRecord(s).
    """

    event_id: str = Field(..., description="Unique event id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    source: str = Field(..., description="origin like mega_agent|workflow_node|telegram")
    action: str = Field(..., description="e.g., handle_command|node_complete")
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class MemoryRecord(BaseModel):
    """Normalized memory item stored in semantic/episodic memory.

    Use Pydantic v2 model_dump for serialization.
    """

    id: Optional[str] = None
    user_id: Optional[str] = None
    type: MemoryType = Field("semantic")
    text: str
    embedding: Optional[List[float]] = None
    salience: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    decay_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class RetrievalQuery(BaseModel):
    query: str
    user_id: Optional[str] = None
    topk: int = 8
    filters: Dict[str, Any] = Field(default_factory=dict)


class ConsolidateStats(BaseModel):
    deduplicated: int = 0
    pruned: int = 0
    merged: int = 0
    total_after: int = 0

