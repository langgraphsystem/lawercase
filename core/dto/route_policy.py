from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RoutePolicy(BaseModel):
    """Routing hints that influence provider selection and retry behaviour."""

    provider_priority: List[str] = Field(default_factory=list, description="Ordered list of preferred providers")
    max_retries: Optional[int] = Field(default=None, ge=0, description="Override retry count")
    timeout_seconds: Optional[float] = Field(default=None, ge=1.0, description="Override request timeout")
    max_cost_usd: Optional[float] = Field(default=None, ge=0.0, description="Budget ceiling for this request")
    label: Optional[str] = Field(default=None, description="Friendly name for telemetry/diagnostics")
