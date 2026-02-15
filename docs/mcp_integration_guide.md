# MCP Integration Guide

This guide explains how to connect Model Context Protocol (MCP) servers and
use the tools inside this repository.

Relevant modules:
- core/mcp/config.py
- core/mcp/client.py
- core/mcp/tools.py
- core/di/container.py (DI integration)

## Requirements

- Python dependency: `langchain-mcp-adapters`
- Node.js (for stdio servers launched with `npx`)

Install:
```bash
pip install langchain-mcp-adapters
```

## Configuration

MCP configuration is defined via MCPConfig and MCPServerConfig.
Environment placeholders like `${VAR}` are supported in args and env values.

Example configuration:
```python
from core.mcp import MCPConfig, MCPServerConfig, MCPTransport

config = MCPConfig(
    servers=[
        MCPServerConfig(
            name="filesystem",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
            enabled=True,
        ),
        MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"},
            enabled=True,
        ),
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
            enabled=True,
        ),
    ],
    auto_connect=True,
)
```

## Usage (Direct)

```python
from core.mcp import MCPClientManager

manager = MCPClientManager()
tools = await manager.connect()

tool = manager.get_tool_by_name("filesystem_read_file")
if tool:
    result = await tool.ainvoke({"path": "README.md"})
    print(result)
```

## Usage (Context Manager)

```python
from core.mcp import mcp_client_context

async with mcp_client_context() as manager:
    tools = manager.tools
    print([t.name for t in tools])
```

## Usage (DI Container)

The DI container registers:
- `mcp_manager` (singleton)
- `mcp_tools` (async factory)

```python
from core.di import get_container

container = get_container()
mcp_manager = container.get("mcp_manager")
tools = await container.aget("mcp_tools")
```

## Tool Helpers

Use `core/mcp/tools.py` helpers to filter or convert tools:
```python
from core.mcp.tools import filter_tools_by_names, tools_to_openai_functions

filtered = filter_tools_by_names(tools, ["filesystem_read_file"])
functions = tools_to_openai_functions(filtered)
```

## Notes

- If `langchain-mcp-adapters` cannot be imported, MCP is disabled and tools list is empty.
- STDIO servers require Node.js and `npx`.
- For HTTP/SSE servers, set `url` and optional `headers`/`timeout`.

