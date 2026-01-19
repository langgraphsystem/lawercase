"""
MCP (Model Context Protocol) Integration Module.

Provides integration with MCP servers for dynamic tool loading.

Usage:
    from core.mcp import get_mcp_tools, MCPConfig, MCPServerConfig

    # Get tools from default servers
    tools = await get_mcp_tools()

    # Or configure custom servers
    config = MCPConfig(
        servers=[
            MCPServerConfig(
                name="supabase",
                transport=MCPTransport.STDIO,
                command="npx",
                args=["-y", "@supabase/mcp-server-supabase"],
                enabled=True,
            ),
        ]
    )
    async with mcp_client_context(config) as manager:
        tools = manager.tools
        # Use tools...
"""

from __future__ import annotations

from core.mcp.client import (
    MCPClientManager,
    create_mcp_client,
    get_mcp_manager,
    get_mcp_tools,
    mcp_client_context,
)
from core.mcp.config import DEFAULT_MCP_CONFIG, MCPConfig, MCPServerConfig, MCPTransport
from core.mcp.tool_search import (
    MCPToolSearch,
    ToolCategory,
    ToolMetadata,
    ToolPriority,
    ToolRecommendation,
    ToolSearchResult,
    get_tool_search,
)
from core.mcp.tools import (
    ToolRegistry,
    exclude_tools_by_names,
    filter_tools_by_names,
    filter_tools_by_predicate,
    filter_tools_by_server,
    get_tool_registry,
    get_tool_schemas,
    tool_to_openai_function,
    tools_to_openai_functions,
)

__all__ = [
    # Config
    "MCPConfig",
    "MCPServerConfig",
    "MCPTransport",
    "DEFAULT_MCP_CONFIG",
    # Client
    "MCPClientManager",
    "create_mcp_client",
    "get_mcp_manager",
    "get_mcp_tools",
    "mcp_client_context",
    # Tools
    "ToolRegistry",
    "get_tool_registry",
    "filter_tools_by_server",
    "filter_tools_by_names",
    "exclude_tools_by_names",
    "filter_tools_by_predicate",
    "get_tool_schemas",
    "tool_to_openai_function",
    "tools_to_openai_functions",
    # Tool Search (Dynamic Loading)
    "MCPToolSearch",
    "ToolCategory",
    "ToolMetadata",
    "ToolPriority",
    "ToolRecommendation",
    "ToolSearchResult",
    "get_tool_search",
]
