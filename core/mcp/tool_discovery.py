"""Tool Discovery for MCP.

Automatic discovery and registration of tools:
- Scan modules for tool decorators
- Load from configuration
- Runtime tool registration
- Health checking
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import importlib
import inspect
import os
from pathlib import Path
from typing import Any

import structlog

from .tool_provider import (
    BaseTool,
    FunctionTool,
    ToolCategory,
    ToolProvider,
)

logger = structlog.get_logger(__name__)


@dataclass
class DiscoveredTool:
    """Information about a discovered tool."""

    name: str
    source: str  # module path or file path
    category: ToolCategory
    tool: BaseTool
    healthy: bool = True
    last_check: float = 0.0


@dataclass
class DiscoveryConfig:
    """Configuration for tool discovery."""

    # Modules to scan for tools
    scan_modules: list[str] = field(
        default_factory=lambda: [
            "core.mcp.external_integrations",
            "core.tools",
        ]
    )

    # Directories to scan for tool files
    scan_directories: list[str] = field(default_factory=list)

    # Tool file patterns
    tool_file_patterns: list[str] = field(
        default_factory=lambda: [
            "*_tool.py",
            "*_tools.py",
            "tool_*.py",
        ]
    )

    # Auto-register discovered tools
    auto_register: bool = True

    # Health check interval (seconds)
    health_check_interval: float = 300.0

    # Categories to include (empty = all)
    include_categories: list[ToolCategory] = field(default_factory=list)

    # Categories to exclude
    exclude_categories: list[ToolCategory] = field(default_factory=list)


class ToolDiscovery:
    """Automatic tool discovery and management.

    Features:
    - Scan modules for @tool decorated functions
    - Load tools from configuration files
    - Health checking for tools
    - Dynamic tool registration

    Usage:
        discovery = ToolDiscovery(provider)

        # Scan for tools
        await discovery.scan()

        # Get all discovered tools
        tools = discovery.get_discovered()

        # Health check
        healthy = await discovery.health_check()
    """

    def __init__(
        self,
        provider: ToolProvider,
        config: DiscoveryConfig | None = None,
    ) -> None:
        self.provider = provider
        self.config = config or DiscoveryConfig()
        self._discovered: dict[str, DiscoveredTool] = {}
        self._health_task: asyncio.Task | None = None

    async def scan(self) -> list[DiscoveredTool]:
        """Scan for tools and optionally register them.

        Returns:
            List of discovered tools
        """
        discovered = []

        # Scan modules
        for module_path in self.config.scan_modules:
            try:
                tools = self._scan_module(module_path)
                discovered.extend(tools)
            except Exception as e:
                logger.warning("mcp.discovery.module_scan_failed", module=module_path, error=str(e))

        # Scan directories
        for dir_path in self.config.scan_directories:
            try:
                tools = self._scan_directory(dir_path)
                discovered.extend(tools)
            except Exception as e:
                logger.warning("mcp.discovery.dir_scan_failed", directory=dir_path, error=str(e))

        # Filter by categories
        discovered = self._filter_by_category(discovered)

        # Register if enabled
        if self.config.auto_register:
            for tool_info in discovered:
                if tool_info.name not in self._discovered:
                    self.provider.register(tool_info.tool)
                    self._discovered[tool_info.name] = tool_info

        logger.info("mcp.discovery.scan_complete", tools_found=len(discovered))
        return discovered

    def _scan_module(self, module_path: str) -> list[DiscoveredTool]:
        """Scan a module for tools."""
        discovered = []

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.debug("mcp.discovery.import_failed", module=module_path, error=str(e))
            return []

        for name, obj in inspect.getmembers(module):
            # Check for BaseTool subclasses
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                try:
                    tool_instance = obj()
                    discovered.append(
                        DiscoveredTool(
                            name=tool_instance.schema.name,
                            source=module_path,
                            category=tool_instance.schema.category,
                            tool=tool_instance,
                        )
                    )
                except Exception as e:
                    logger.debug(
                        "mcp.discovery.instantiation_failed", class_name=name, error=str(e)
                    )

            # Check for functions with _mcp_tool attribute
            elif callable(obj) and hasattr(obj, "_mcp_tool"):
                tool_info = obj._mcp_tool
                discovered.append(
                    DiscoveredTool(
                        name=tool_info["name"],
                        source=module_path,
                        category=tool_info.get("category", ToolCategory.CUSTOM),
                        tool=FunctionTool(obj, **tool_info),
                    )
                )

        return discovered

    def _scan_directory(self, dir_path: str) -> list[DiscoveredTool]:
        """Scan a directory for tool files."""
        discovered = []
        path = Path(dir_path)

        if not path.exists():
            return []

        for pattern in self.config.tool_file_patterns:
            for file_path in path.glob(pattern):
                try:
                    # Convert file path to module path
                    module_path = str(file_path.with_suffix("")).replace(os.sep, ".")
                    # Clean up leading dots
                    while module_path.startswith("."):
                        module_path = module_path[1:]

                    tools = self._scan_module(module_path)
                    discovered.extend(tools)
                except Exception as e:
                    logger.debug(
                        "mcp.discovery.file_scan_failed", file=str(file_path), error=str(e)
                    )

        return discovered

    def _filter_by_category(self, tools: list[DiscoveredTool]) -> list[DiscoveredTool]:
        """Filter tools by category configuration."""
        filtered = []

        for tool in tools:
            # Check exclusions
            if self.config.exclude_categories and tool.category in self.config.exclude_categories:
                continue

            # Check inclusions (if specified)
            if (
                self.config.include_categories
                and tool.category not in self.config.include_categories
            ):
                continue

            filtered.append(tool)

        return filtered

    async def health_check(self, timeout: float = 5.0) -> dict[str, bool]:
        """Check health of all discovered tools.

        Args:
            timeout: Timeout for each health check

        Returns:
            Dict of tool name -> health status
        """
        import time

        results = {}
        current_time = time.time()

        for name, tool_info in self._discovered.items():
            try:
                # Simple health check: try to validate empty params
                _valid, _ = tool_info.tool.validate_params()
                results[name] = True
                tool_info.healthy = True
            except Exception:
                results[name] = False
                tool_info.healthy = False

            tool_info.last_check = current_time

        healthy_count = sum(1 for v in results.values() if v)
        logger.info(
            "mcp.discovery.health_check",
            healthy=healthy_count,
            total=len(results),
        )

        return results

    def get_discovered(self) -> list[DiscoveredTool]:
        """Get all discovered tools."""
        return list(self._discovered.values())

    def get_healthy(self) -> list[DiscoveredTool]:
        """Get only healthy tools."""
        return [t for t in self._discovered.values() if t.healthy]

    def get_by_category(self, category: ToolCategory) -> list[DiscoveredTool]:
        """Get discovered tools by category."""
        return [t for t in self._discovered.values() if t.category == category]

    def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._health_task is not None:
            return

        async def monitor():
            while True:
                await asyncio.sleep(self.config.health_check_interval)
                await self.health_check()

        self._health_task = asyncio.create_task(monitor())
        logger.info("mcp.discovery.health_monitor_started")

    def stop_health_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._health_task is not None:
            self._health_task.cancel()
            self._health_task = None
            logger.info("mcp.discovery.health_monitor_stopped")

    def register_function(
        self,
        func: Callable,
        name: str | None = None,
        category: ToolCategory = ToolCategory.CUSTOM,
    ) -> None:
        """Manually register a function as a tool.

        Args:
            func: Function to register
            name: Optional tool name
            category: Tool category
        """
        tool = FunctionTool(func, name=name, category=category)
        self.provider.register(tool)

        self._discovered[tool.schema.name] = DiscoveredTool(
            name=tool.schema.name,
            source="manual",
            category=category,
            tool=tool,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get discovery statistics."""
        by_category = {}
        for tool in self._discovered.values():
            cat = tool.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        healthy = sum(1 for t in self._discovered.values() if t.healthy)

        return {
            "total_discovered": len(self._discovered),
            "healthy": healthy,
            "unhealthy": len(self._discovered) - healthy,
            "by_category": by_category,
            "monitoring_active": self._health_task is not None,
        }


# Decorator for marking functions as discoverable tools
def discoverable_tool(
    name: str | None = None,
    description: str | None = None,
    category: ToolCategory = ToolCategory.CUSTOM,
) -> Callable:
    """Decorator to mark a function as a discoverable tool.

    Usage:
        @discoverable_tool(name="my_tool", category=ToolCategory.SEARCH)
        async def my_tool(query: str) -> str:
            '''Tool description.'''
            return "result"
    """

    def decorator(func: Callable) -> Callable:
        func._mcp_tool = {
            "name": name or func.__name__,
            "description": description or func.__doc__ or "",
            "category": category,
        }
        return func

    return decorator
