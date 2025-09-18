from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QuerySpec(BaseModel):
    """Specification for RAG retrieval."""

    text: str = Field(..., min_length=1, description="Query text to retrieve relevant context")
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_top_k: int = Field(default=10, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[str] = Field(default=None)
