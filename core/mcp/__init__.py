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
from core.mcp.external_integrations import (
    AcademicSearchTool,
    DatabaseQueryTool,
    GitHubSearchTool,
    IntegrationConfig,
    LLMQueryTool,
    WebSearchTool,
    get_default_integrations,
    register_all_integrations,
)
from core.mcp.mcp_server import (
    MCPErrorCode,
    MCPRequest,
    MCPResponse,
    MCPServer,
    MCPSession,
    create_mcp_server,
    get_mcp_server,
)
from core.mcp.tool_discovery import (
    DiscoveredTool,
    DiscoveryConfig,
    ToolDiscovery,
    discoverable_tool,
)
from core.mcp.tool_provider import (
    BaseTool,
    FunctionTool,
    ToolCategory as ToolProviderCategory,
    ToolParameter,
    ToolProvider,
    ToolResult,
    ToolSchema,
)
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
    "DEFAULT_MCP_CONFIG",
    "AcademicSearchTool",
    "BaseTool",
    "DatabaseQueryTool",
    "DiscoveredTool",
    "DiscoveryConfig",
    "FunctionTool",
    "GitHubSearchTool",
    "IntegrationConfig",
    "LLMQueryTool",
    # Client
    "MCPClientManager",
    # Config
    "MCPConfig",
    "MCPErrorCode",
    "MCPRequest",
    "MCPResponse",
    # MCP Server
    "MCPServer",
    "MCPServerConfig",
    "MCPSession",
    # Tool Search (Dynamic Loading)
    "MCPToolSearch",
    "MCPTransport",
    "ToolCategory",
    # Tool Discovery
    "ToolDiscovery",
    "ToolMetadata",
    "ToolParameter",
    "ToolPriority",
    # Tool Provider (v2.0)
    "ToolProvider",
    "ToolProviderCategory",
    "ToolRecommendation",
    # Tools
    "ToolRegistry",
    "ToolResult",
    "ToolSchema",
    "ToolSearchResult",
    # External Integrations
    "WebSearchTool",
    "create_mcp_client",
    "create_mcp_server",
    "discoverable_tool",
    "exclude_tools_by_names",
    "filter_tools_by_names",
    "filter_tools_by_predicate",
    "filter_tools_by_server",
    "get_default_integrations",
    "get_mcp_manager",
    "get_mcp_server",
    "get_mcp_tools",
    "get_tool_registry",
    "get_tool_schemas",
    "get_tool_search",
    "mcp_client_context",
    "register_all_integrations",
    "tool_to_openai_function",
    "tools_to_openai_functions",
]
