"""Tool registry and metadata for MegaAgent tool invocation.

This module provides:
    - ``Tool`` protocol describing async callable tools
    - ``ToolMetadata`` describing RBAC constraints and tags
    - ``ToolRegistry`` for registering, invoking, and auditing tool usage
    - Module-level helpers to obtain a shared registry instance

Phase 3 foundation for agentic tool support.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for async tools callable by MegaAgent."""

    async def __call__(self, **kwargs: Any) -> Any:  # pragma: no cover - protocol
        ...


@dataclass(slots=True)
class ToolMetadata:
    """Describe a tool for discovery and RBAC enforcement."""

    name: str
    description: str
    allowed_roles: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)


class ToolRegistry:
    """Maintain tool registrations, permissions, and invocation history."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def register(self, tool_id: str, tool: Tool, *, metadata: ToolMetadata) -> None:
        """Register a new tool.

        Raises ``ValueError`` if the identifier is already in use.
        """

        if tool_id in self._tools:
            raise ValueError(f"Tool '{tool_id}' already registered")
        self._tools[tool_id] = tool
        self._metadata[tool_id] = metadata

    def unregister(self, tool_id: str) -> None:
        """Remove a tool and its metadata if present."""

        self._tools.pop(tool_id, None)
        self._metadata.pop(tool_id, None)
        self._history.pop(tool_id, None)

    def get_metadata(self, tool_id: str) -> ToolMetadata:
        """Return metadata for ``tool_id`` or raise ``KeyError``."""

        try:
            return self._metadata[tool_id]
        except KeyError as exc:  # pragma: no cover - small guard
            raise KeyError(f"Tool '{tool_id}' not found") from exc

    def list_tools(self) -> list[ToolMetadata]:
        """List metadata for all registered tools."""

        return list(self._metadata.values())

    async def invoke(
        self,
        tool_id: str,
        *,
        caller_role: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke a tool ensuring role-based permissions."""

        if tool_id not in self._tools:
            raise KeyError(f"Tool '{tool_id}' not registered")

        metadata = self._metadata[tool_id]
        if metadata.allowed_roles and caller_role not in metadata.allowed_roles:
            raise PermissionError(f"Role '{caller_role}' not permitted to call '{tool_id}'")

        tool = self._tools[tool_id]
        args = dict(arguments or {})
        result = await tool(**args)
        self._history[tool_id].append(
            {
                "role": caller_role,
                "args": args,
                "result": result,
            }
        )
        return result

    def get_history(self, tool_id: str) -> list[dict[str, Any]]:
        """Return recorded invocation history (copy) for ``tool_id``."""

        return list(self._history.get(tool_id, []))


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Return the global ``ToolRegistry`` instance."""

    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_tool_registry() -> None:
    """Reset the shared registry (mainly for testing)."""

    global _registry  # noqa: PLW0603
    _registry = None
