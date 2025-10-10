from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    topk: int = Field(8, ge=1, le=100)
    filters: dict[str, Any] | None = None


class ToolRequest(BaseModel):
    tool_id: str = Field(...)
    arguments: dict[str, Any] | None = None
    timeout: float = Field(2.0, ge=0.1, le=60.0)
    network: bool = False
    filesystem: bool = False
    memory_mb: int = 256
    policy: str | None = None


class AgentCommandRequest(BaseModel):
    user_id: str
    command_type: Literal[
        "ask", "train", "validate", "generate", "case", "search", "workflow", "admin", "tool"
    ]
    action: str
    payload: dict[str, Any] | None = None


class MemoryWriteRequest(BaseModel):
    # Either direct records or audit event-like payload
    text: str | None = None
    user_id: str | None = None
    type: str | None = None
    payload: dict[str, Any] | None = None


class MemoryRetrieveRequest(BaseModel):
    query: str
    user_id: str | None = None
    topk: int = 8
    filters: dict[str, Any] | None = None
