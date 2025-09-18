from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ContextChunk(BaseModel):
    """A chunk of contextual knowledge used during retrieval."""

    chunk_id: str
    document_id: str
    text: str
    score: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
