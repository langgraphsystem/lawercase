"""
MCP Server Configuration.

Defines configuration for connecting to Model Context Protocol servers.
"""

from __future__ import annotations

from enum import Enum
import os
import re
from typing import Any

from pydantic import BaseModel, Field


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR} placeholders with environment variables."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, value)


class MCPTransport(str, Enum):
    """Supported MCP transport types."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str = Field(..., description="Unique name for this server")
    transport: MCPTransport = Field(..., description="Transport type")

    # For stdio transport
    command: str | None = Field(default=None, description="Command to run (stdio)")
    args: list[str] | None = Field(default=None, description="Command arguments (stdio)")
    env: dict[str, str] | None = Field(default=None, description="Environment variables (stdio)")

    # For HTTP transports
    url: str | None = Field(default=None, description="Server URL (http/sse)")
    headers: dict[str, str] | None = Field(default=None, description="HTTP headers")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")
    sse_read_timeout: float = Field(default=300.0, description="SSE keep-alive timeout")

    # General options
    enabled: bool = Field(default=True, description="Whether this server is enabled")
    description: str | None = Field(default=None, description="Server description")

    def to_client_config(self) -> dict[str, Any]:
        """Convert to format expected by MultiServerMCPClient.

        Resolves ${VAR} placeholders in args and env values.
        """
        config: dict[str, Any] = {
            "transport": self.transport.value,
        }

        if self.transport == MCPTransport.STDIO:
            if self.command:
                config["command"] = self.command
            if self.args:
                # Resolve env vars in arguments
                config["args"] = [_resolve_env_vars(arg) for arg in self.args]
            if self.env:
                # Resolve env vars in environment values
                config["env"] = {k: _resolve_env_vars(v) for k, v in self.env.items()}
        else:
            if self.url:
                config["url"] = _resolve_env_vars(self.url)
            if self.headers:
                config["headers"] = {k: _resolve_env_vars(v) for k, v in self.headers.items()}
            if self.timeout:
                config["timeout"] = self.timeout
            if self.transport == MCPTransport.SSE and self.sse_read_timeout:
                config["sse_read_timeout"] = self.sse_read_timeout

        return config


class MCPConfig(BaseModel):
    """Global MCP configuration."""

    servers: list[MCPServerConfig] = Field(default_factory=list, description="MCP servers")
    auto_connect: bool = Field(default=True, description="Auto-connect on startup")
    retry_on_failure: bool = Field(default=True, description="Retry failed connections")
    max_retries: int = Field(default=3, description="Maximum connection retries")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Get only enabled servers."""
        return [s for s in self.servers if s.enabled]

    def to_multi_server_config(self) -> dict[str, dict[str, Any]]:
        """Convert to MultiServerMCPClient format."""
        return {server.name: server.to_client_config() for server in self.get_enabled_servers()}


# Default MCP configuration with common servers
DEFAULT_MCP_CONFIG = MCPConfig(
    servers=[
        # Filesystem server - provides file operations
        MCPServerConfig(
            name="filesystem",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
            description="Filesystem access via MCP",
            enabled=True,
        ),
        # GitHub MCP server - uses GITHUB_PERSONAL_ACCESS_TOKEN from .env
        MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"},
            description="GitHub API via MCP",
            enabled=True,
        ),
        # Supabase MCP server - requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
        MCPServerConfig(
            name="supabase",
            transport=MCPTransport.STDIO,
            command="npx",
            args=[
                "-y",
                "@supabase/mcp-server-supabase",
                "--supabase-url",
                "${SUPABASE_URL}",
                "--supabase-key",
                "${SUPABASE_SERVICE_ROLE_KEY}",
            ],
            description="Supabase database access via MCP",
            enabled=True,
        ),
    ],
)
