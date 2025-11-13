"""Tools package.

Provides tool registry, execution, and OpenAI function calling support.
"""

from __future__ import annotations

from core.tools.executor import (ToolExecutionError, execute_single_tool,
                                 execute_tool_loop)
from core.tools.tool_registry import (Tool, ToolMetadata, ToolRegistry,
                                      ToolType, get_tool_registry,
                                      reset_tool_registry)

__all__ = [
    # Registry
    "Tool",
    "ToolMetadata",
    "ToolRegistry",
    "ToolType",
    "get_tool_registry",
    "reset_tool_registry",
    # Executor
    "execute_tool_loop",
    "execute_single_tool",
    "ToolExecutionError",
]
