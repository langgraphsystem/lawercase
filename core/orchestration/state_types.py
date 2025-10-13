from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CaseWorkflowState(BaseModel):
    thread_id: str = Field(...)
    user_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
