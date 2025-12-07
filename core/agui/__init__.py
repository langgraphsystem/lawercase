"""
AG-UI (Agent-User Interaction Protocol) integration for MAS system.

This module provides:
1. AGUIEvent - Standard AG-UI event types
2. AGUIAdapter - Converts workflow execution to AG-UI events
3. AGUIEndpoint - FastAPI SSE endpoint for streaming
4. Human-in-the-loop support for validation approval
"""

from __future__ import annotations

from .adapter import AGUIAdapter
from .events import AGUIEvent, EventType
from .middleware import AGUIMiddleware

__all__ = ["AGUIEvent", "EventType", "AGUIAdapter", "AGUIMiddleware"]
