"""MCP Tool Provider - unified interface for tool registration and execution.

Provides MCP-compatible tool management:
- Tool registration with schemas
- Async tool execution
- Tool validation
- Permission management
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import inspect
import json
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ToolCategory(str, Enum):
    """Standard tool categories."""

    SEARCH = "search"
    DATABASE = "database"
    FILE = "file"
    API = "api"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass(slots=True)
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


@dataclass(slots=True)
class ToolSchema:
    """MCP-compatible tool schema."""

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "string"
    category: ToolCategory = ToolCategory.CUSTOM
    requires_auth: bool = False
    rate_limit: int | None = None  # requests per minute

    def to_mcp_format(self) -> dict[str, Any]:
        """Convert to MCP tool format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function format."""
        mcp_format = self.to_mcp_format()
        return {
            "type": "function",
            "function": {
                "name": mcp_format["name"],
                "description": mcp_format["description"],
                "parameters": mcp_format["inputSchema"],
            },
        }


@dataclass(slots=True)
class ToolResult:
    """Result of tool execution."""

    success: bool
    data: Any
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class BaseTool(ABC):
    """Abstract base for MCP tools."""

    schema: ToolSchema

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""

    def validate_params(self, **kwargs: Any) -> tuple[bool, str | None]:
        """Validate parameters against schema."""
        for param in self.schema.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
        return True, None


class FunctionTool(BaseTool):
    """Tool wrapper for Python functions."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
        category: ToolCategory = ToolCategory.CUSTOM,
    ) -> None:
        self.func = func
        self._is_async = asyncio.iscoroutinefunction(func)

        # Build schema from function
        self.schema = self._build_schema(
            func,
            name or func.__name__,
            description or func.__doc__ or "",
            category,
        )

    def _build_schema(
        self,
        func: Callable,
        name: str,
        description: str,
        category: ToolCategory,
    ) -> ToolSchema:
        """Build schema from function signature."""
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Infer type
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation in (int, float):
                    param_type = "number"
                elif param.annotation is bool:
                    param_type = "boolean"
                elif param.annotation is list:
                    param_type = "array"
                elif param.annotation is dict:
                    param_type = "object"

            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=f"Parameter: {param_name}",
                    required=param.default == inspect.Parameter.empty,
                    default=None if param.default == inspect.Parameter.empty else param.default,
                )
            )

        return ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            category=category,
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the wrapped function."""
        import time

        start = time.perf_counter()

        try:
            # Validate
            valid, error = self.validate_params(**kwargs)
            if not valid:
                return ToolResult(success=False, data=None, error=error)

            # Execute
            if self._is_async:
                result = await self.func(**kwargs)
            else:
                result = await asyncio.to_thread(self.func, **kwargs)

            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=True,
                data=result,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("tool.execution.failed", tool=self.schema.name, error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=elapsed,
            )


class ToolProvider:
    """MCP-compatible tool provider.

    Manages tool registration, discovery, and execution.

    Usage:
        provider = ToolProvider()

        # Register function as tool
        @provider.tool(category=ToolCategory.SEARCH)
        async def search_web(query: str, top_k: int = 10) -> list[dict]:
            '''Search the web for information.'''
            ...

        # Or register manually
        provider.register(my_tool)

        # Execute tool
        result = await provider.execute("search_web", query="EB-1A visa")

        # Get all tools for LLM
        schemas = provider.get_openai_tools()
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._tools: dict[str, BaseTool] = {}
        self._categories: dict[ToolCategory, list[str]] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.schema.name] = tool

        category = tool.schema.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.schema.name)

        logger.info("mcp.tool.registered", name=tool.schema.name, category=category.value)

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        category: ToolCategory = ToolCategory.CUSTOM,
    ) -> Callable:
        """Decorator to register a function as a tool."""

        def decorator(func: Callable) -> Callable:
            tool = FunctionTool(func, name, description, category)
            self.register(tool)
            return func

        return decorator

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            tool = self._tools.pop(name)
            category = tool.schema.category
            if category in self._categories:
                self._categories[category].remove(name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """Get tool by name."""
        return self._tools.get(name)

    def get_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Get all tools in a category."""
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def all_tools(self) -> list[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def list_tools(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool not found: {name}",
            )
        return await tool.execute(**kwargs)

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get all tools in MCP format."""
        return [t.schema.to_mcp_format() for t in self._tools.values()]

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function format."""
        return [t.schema.to_openai_format() for t in self._tools.values()]

    def get_tool_schemas(self) -> list[ToolSchema]:
        """Get all tool schemas."""
        return [t.schema for t in self._tools.values()]

    def to_json(self) -> str:
        """Export tools as JSON."""
        return json.dumps(self.get_mcp_tools(), indent=2)


# Global provider
_global_provider: ToolProvider | None = None


def get_tool_provider() -> ToolProvider:
    """Get global tool provider."""
    global _global_provider
    if _global_provider is None:
        _global_provider = ToolProvider("global")
    return _global_provider


def tool(
    name: str | None = None,
    description: str | None = None,
    category: ToolCategory = ToolCategory.CUSTOM,
) -> Callable:
    """Decorator to register a function as a global tool."""
    return get_tool_provider().tool(name, description, category)
