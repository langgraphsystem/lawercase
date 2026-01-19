"""
MCP Client Wrapper.

Provides async context manager for connecting to MCP servers.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog

from core.mcp.config import MCPConfig, MCPServerConfig

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = structlog.get_logger(__name__)

# Try to import langchain_mcp_adapters (may fail due to version incompatibility)
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    MCP_ADAPTERS_AVAILABLE = True
except ImportError as e:
    logger.warning(
        "mcp.langchain_adapters_unavailable",
        error=str(e),
        hint="langchain-mcp-adapters may have version incompatibility with langchain-core",
    )
    MultiServerMCPClient = None  # type: ignore
    MCP_ADAPTERS_AVAILABLE = False


class MCPClientManager:
    """Manager for MCP client connections with retry logic."""

    def __init__(self, config: MCPConfig | None = None):
        """Initialize MCP client manager.

        Args:
            config: MCP configuration. If None, uses default config.
        """
        from core.mcp.config import DEFAULT_MCP_CONFIG

        self.config = config or DEFAULT_MCP_CONFIG
        self._client: MultiServerMCPClient | None = None
        self._tools: list[BaseTool] = []
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    @property
    def tools(self) -> list[BaseTool]:
        """Get loaded tools from MCP servers."""
        return self._tools

    async def connect(self) -> list[BaseTool]:
        """Connect to all enabled MCP servers and load tools.

        Returns:
            List of LangChain tools from all connected servers.
        """
        if not MCP_ADAPTERS_AVAILABLE:
            logger.warning(
                "mcp.client.adapters_unavailable",
                hint="MCP tools disabled due to langchain-mcp-adapters import error",
            )
            return []

        if self._connected:
            return self._tools

        server_config = self.config.to_multi_server_config()
        if not server_config:
            logger.warning("mcp.client.no_servers_enabled")
            return []

        retries = 0
        last_error: Exception | None = None

        while retries <= self.config.max_retries:
            try:
                self._client = MultiServerMCPClient(server_config)
                await self._client.__aenter__()
                self._tools = self._client.get_tools()
                self._connected = True

                logger.info(
                    "mcp.client.connected",
                    servers=list(server_config.keys()),
                    tools_count=len(self._tools),
                    tool_names=[t.name for t in self._tools],
                )
                return self._tools

            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self.config.max_retries and self.config.retry_on_failure:
                    logger.warning(
                        "mcp.client.connect_retry",
                        attempt=retries,
                        max_retries=self.config.max_retries,
                        error=str(e),
                    )
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    break

        logger.error(
            "mcp.client.connect_failed",
            error=str(last_error),
            attempts=retries,
        )
        raise ConnectionError(f"Failed to connect to MCP servers: {last_error}")

    async def disconnect(self) -> None:
        """Disconnect from all MCP servers."""
        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
                logger.info("mcp.client.disconnected")
            except Exception as e:
                logger.warning("mcp.client.disconnect_error", error=str(e))
            finally:
                self._client = None
                self._tools = []
                self._connected = False

    async def reconnect(self) -> list[BaseTool]:
        """Reconnect to MCP servers."""
        await self.disconnect()
        return await self.connect()

    def get_tool_by_name(self, name: str) -> BaseTool | None:
        """Get a specific tool by name.

        Args:
            name: Tool name to find.

        Returns:
            Tool if found, None otherwise.
        """
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools with metadata.

        Returns:
            List of tool info dicts with name, description.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools
        ]


@asynccontextmanager
async def mcp_client_context(
    config: MCPConfig | None = None,
) -> AsyncGenerator[MCPClientManager, None]:
    """Async context manager for MCP client.

    Usage:
        async with mcp_client_context(config) as manager:
            tools = manager.tools
            # Use tools...

    Args:
        config: MCP configuration.

    Yields:
        Connected MCPClientManager instance.
    """
    manager = MCPClientManager(config)
    try:
        await manager.connect()
        yield manager
    finally:
        await manager.disconnect()


async def create_mcp_client(
    servers: list[MCPServerConfig] | None = None,
    auto_connect: bool = True,
) -> MCPClientManager:
    """Create and optionally connect an MCP client.

    Args:
        servers: List of server configs. If None, uses defaults.
        auto_connect: Whether to connect immediately.

    Returns:
        MCPClientManager instance.
    """
    config = MCPConfig(servers=servers) if servers else None
    manager = MCPClientManager(config)

    if auto_connect:
        await manager.connect()

    return manager


# Singleton instance for global access
_global_manager: MCPClientManager | None = None


async def get_mcp_manager() -> MCPClientManager:
    """Get or create global MCP client manager.

    Returns:
        Global MCPClientManager instance.
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = MCPClientManager()
    return _global_manager


async def get_mcp_tools() -> list[BaseTool]:
    """Get tools from global MCP manager.

    Connects if not already connected.

    Returns:
        List of LangChain tools.
    """
    manager = await get_mcp_manager()
    if not manager.is_connected:
        await manager.connect()
    return manager.tools
