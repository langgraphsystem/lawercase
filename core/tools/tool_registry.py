"""Tool registry and metadata for MegaAgent tool invocation.

This module provides:
    - ``Tool`` protocol describing async callable tools
    - ``ToolMetadata`` describing RBAC constraints and tags
    - ``ToolRegistry`` for registering, invoking, and auditing tool usage
    - OpenAI function calling format support (March 2025)
    - Built-in tools (file_search, web_search, code_interpreter)
    - Module-level helpers to obtain a shared registry instance

Updated for GPT-5 function calling (March 2025).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for async tools callable by MegaAgent."""

    async def __call__(self, **kwargs: Any) -> Any:  # pragma: no cover - protocol
        ...


class ToolType(str, Enum):
    """Types of tools available in the system (GPT-5.1 November 2025).

    New in GPT-5.1:
    - APPLY_PATCH: Reliable code editing tool
    - SHELL: Execute shell commands
    """

    FUNCTION = "function"  # Standard function calling
    CUSTOM = "custom"  # GPT-5 freeform (raw text payload)
    FILE_SEARCH = "file_search"  # Built-in file search
    WEB_SEARCH = "web_search"  # Built-in web search (Responses API, $10/K)
    CODE_INTERPRETER = "code_interpreter"  # Built-in code execution
    IMAGE_GEN = "gpt-image-1"  # Built-in image generation
    # GPT-5.1 New Tools (November 2025)
    APPLY_PATCH = "apply_patch"  # Reliable code editing
    SHELL = "shell"  # Execute shell commands


@dataclass(slots=True)
class ToolMetadata:
    """Describe a tool for discovery and RBAC enforcement.

    Enhanced for OpenAI function calling format (March 2025).
    """

    name: str
    description: str
    allowed_roles: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    tool_type: ToolType = ToolType.FUNCTION
    parameters: dict[str, Any] | None = None  # JSON Schema for function parameters
    strict: bool = False  # Structured outputs mode (GPT-5)
    enabled: bool = True


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

    def get_tools_for_openai(
        self,
        model: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tools formatted for OpenAI API (March 2025 format).

        Args:
            model: Model identifier (for GPT-5.1 specific features)
            role: User role for RBAC filtering

        Returns:
            List of tool definitions in OpenAI format
        """
        tools = []

        for _, metadata in self._metadata.items():
            # Skip disabled tools
            if not metadata.enabled:
                continue

            # RBAC filtering
            if role and metadata.allowed_roles and role not in metadata.allowed_roles:
                continue

            # Format based on tool type
            if metadata.tool_type == ToolType.FUNCTION:
                # Standard function calling
                tool_def: dict[str, Any] = {
                    "type": "function",
                    "function": {
                        "name": metadata.name,
                        "description": metadata.description,
                    },
                }

                # Add parameters if specified
                if metadata.parameters:
                    tool_def["function"]["parameters"] = metadata.parameters

                # Add strict mode for structured outputs (GPT-5.1)
                if metadata.strict:
                    tool_def["function"]["strict"] = True

                tools.append(tool_def)

            elif metadata.tool_type in {
                ToolType.FILE_SEARCH,
                ToolType.WEB_SEARCH,
                ToolType.CODE_INTERPRETER,
                ToolType.APPLY_PATCH,
                ToolType.SHELL,
            }:
                # Built-in tools (no executor needed)
                # GPT-5.1 adds apply_patch and shell tools
                tools.append({"type": metadata.tool_type.value})

            elif metadata.tool_type == ToolType.CUSTOM:
                # GPT-5 custom tools (freeform payload)
                tools.append(
                    {
                        "type": "custom",
                        "name": metadata.name,
                        "description": metadata.description,
                    }
                )

        return tools

    def get_history(self, tool_id: str) -> list[dict[str, Any]]:
        """Return recorded invocation history (copy) for ``tool_id``."""

        return list(self._history.get(tool_id, []))


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Return the global ``ToolRegistry`` instance."""

    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_tool_registry() -> None:
    """Reset the shared registry (mainly for testing)."""

    global _registry
    _registry = None
