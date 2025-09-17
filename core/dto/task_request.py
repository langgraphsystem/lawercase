from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .route_policy import RoutePolicy


class TaskRequest(BaseModel):
    """High-level LLM task description."""

    prompt: str = Field(..., min_length=1, description="User or system prompt")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task metadata")
    policy: Optional[RoutePolicy] = Field(default=None, description="Optional routing overrides")
    conversation_id: Optional[str] = Field(default=None, description="Conversation/session identifier")
    expected_tokens: Optional[int] = Field(default=None, ge=0, description="Optional estimate of tokens in prompt")
