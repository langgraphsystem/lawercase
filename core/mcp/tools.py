"""
MCP Tool Loading Utilities.

Provides utilities for loading and converting MCP tools to LangChain format.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = structlog.get_logger(__name__)


def filter_tools_by_server(
    tools: list[BaseTool],
    server_name: str,
) -> list[BaseTool]:
    """Filter tools by their originating server.

    Note: This relies on tool naming convention where server name
    is typically part of the tool name or metadata.

    Args:
        tools: List of tools to filter.
        server_name: Server name to match.

    Returns:
        Filtered list of tools.
    """
    # MCP tools often have server prefix in name
    filtered = []
    for tool in tools:
        # Check if tool name starts with server name
        if tool.name.startswith(f"{server_name}_"):
            filtered.append(tool)
        # Also check metadata if available
        elif hasattr(tool, "metadata") and tool.metadata:
            if tool.metadata.get("server") == server_name:
                filtered.append(tool)
    return filtered


def filter_tools_by_names(
    tools: list[BaseTool],
    names: list[str],
) -> list[BaseTool]:
    """Filter tools by exact names.

    Args:
        tools: List of tools to filter.
        names: Tool names to include.

    Returns:
        Filtered list of tools.
    """
    name_set = set(names)
    return [t for t in tools if t.name in name_set]


def exclude_tools_by_names(
    tools: list[BaseTool],
    names: list[str],
) -> list[BaseTool]:
    """Exclude tools by exact names.

    Args:
        tools: List of tools to filter.
        names: Tool names to exclude.

    Returns:
        Filtered list of tools.
    """
    name_set = set(names)
    return [t for t in tools if t.name not in name_set]


def filter_tools_by_predicate(
    tools: list[BaseTool],
    predicate: Callable[[BaseTool], bool],
) -> list[BaseTool]:
    """Filter tools using a custom predicate function.

    Args:
        tools: List of tools to filter.
        predicate: Function that returns True for tools to include.

    Returns:
        Filtered list of tools.
    """
    return [t for t in tools if predicate(t)]


def get_tool_schemas(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Get JSON schemas for all tools.

    Args:
        tools: List of tools.

    Returns:
        List of tool schemas in OpenAI function format.
    """
    schemas = []
    for tool in tools:
        schema = {
            "name": tool.name,
            "description": tool.description or "",
        }
        # Get input schema if available
        if hasattr(tool, "args_schema") and tool.args_schema:
            schema["parameters"] = tool.args_schema.schema()
        elif hasattr(tool, "get_input_schema"):
            try:
                schema["parameters"] = tool.get_input_schema().schema()
            except Exception:
                schema["parameters"] = {"type": "object", "properties": {}}
        else:
            schema["parameters"] = {"type": "object", "properties": {}}

        schemas.append(schema)

    return schemas


def tool_to_openai_function(tool: BaseTool) -> dict[str, Any]:
    """Convert a LangChain tool to OpenAI function format.

    Args:
        tool: LangChain tool.

    Returns:
        OpenAI function definition dict.
    """
    schema = {
        "name": tool.name,
        "description": tool.description or "",
    }

    if hasattr(tool, "args_schema") and tool.args_schema:
        schema["parameters"] = tool.args_schema.schema()
    else:
        schema["parameters"] = {"type": "object", "properties": {}}

    return {"type": "function", "function": schema}


def tools_to_openai_functions(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Convert multiple tools to OpenAI function format.

    Args:
        tools: List of LangChain tools.

    Returns:
        List of OpenAI function definitions.
    """
    return [tool_to_openai_function(t) for t in tools]


class ToolRegistry:
    """Registry for managing MCP tools with categories."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._categories: dict[str, list[str]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(
        self,
        tool: BaseTool,
        category: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool.

        Args:
            tool: Tool to register.
            category: Optional category name.
            metadata: Optional additional metadata.
        """
        self._tools[tool.name] = tool

        if category:
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool.name)

        if metadata:
            self._metadata[tool.name] = metadata

        logger.debug(
            "mcp.tools.registered",
            name=tool.name,
            category=category,
        )

    def register_many(
        self,
        tools: list[BaseTool],
        category: str | None = None,
    ) -> None:
        """Register multiple tools.

        Args:
            tools: Tools to register.
            category: Optional category for all tools.
        """
        for tool in tools:
            self.register(tool, category=category)

    def get(self, name: str) -> BaseTool | None:
        """Get tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool if found, None otherwise.
        """
        return self._tools.get(name)

    def get_by_category(self, category: str) -> list[BaseTool]:
        """Get all tools in a category.

        Args:
            category: Category name.

        Returns:
            List of tools in category.
        """
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def all_tools(self) -> list[BaseTool]:
        """Get all registered tools.

        Returns:
            List of all tools.
        """
        return list(self._tools.values())

    def categories(self) -> list[str]:
        """Get all category names.

        Returns:
            List of category names.
        """
        return list(self._categories.keys())

    def unregister(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name to remove.

        Returns:
            True if tool was removed.
        """
        if name in self._tools:
            del self._tools[name]
            # Remove from categories
            for cat_tools in self._categories.values():
                if name in cat_tools:
                    cat_tools.remove(name)
            # Remove metadata
            self._metadata.pop(name, None)
            return True
        return False

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._categories.clear()
        self._metadata.clear()


# Global tool registry
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry.

    Returns:
        Global ToolRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
