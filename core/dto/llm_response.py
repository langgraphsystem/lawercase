from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Normalized LLM completion payload."""

    request_id: str
    text: str
    provider: str
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: Optional[float] = Field(default=None, ge=0.0)
    latency_ms: Optional[float] = Field(default=None, ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
