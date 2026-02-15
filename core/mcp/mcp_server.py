"""MCP Server - Model Context Protocol server implementation.

Provides the MCP server endpoint for tool registration and execution:
- JSON-RPC 2.0 protocol handling
- Tool invocation
- Resource management
- Session handling
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
from typing import Any, TypeVar
import uuid

import structlog

from .tool_provider import BaseTool, ToolProvider

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class MCPErrorCode(int, Enum):
    """Standard JSON-RPC 2.0 error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # MCP-specific codes
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    UNAUTHORIZED = -32003
    RATE_LIMITED = -32004


@dataclass
class MCPRequest:
    """MCP JSON-RPC request."""

    jsonrpc: str
    method: str
    id: str | int | None = None
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPRequest:
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            id=data.get("id"),
            params=data.get("params", {}),
        )


@dataclass
class MCPResponse:
    """MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error_data:
            response["error"] = self.error_data
        else:
            response["result"] = self.result
        return response

    @classmethod
    def success(cls, request_id: str | int | None, result: Any) -> MCPResponse:
        return cls(id=request_id, result=result)

    @classmethod
    def error(
        cls,
        request_id: str | int | None,
        code: MCPErrorCode,
        message: str,
        data: Any = None,
    ) -> MCPResponse:
        error_obj: dict[str, Any] = {
            "code": code.value,
            "message": message,
        }
        if data is not None:
            error_obj["data"] = data
        return cls(id=request_id, error_data=error_obj)


@dataclass
class MCPSession:
    """MCP client session."""

    id: str
    created_at: datetime
    client_info: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, client_info: dict[str, Any] | None = None) -> MCPSession:
        return cls(
            id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            client_info=client_info or {},
        )


class MCPServerConfig:
    """MCP Server configuration."""

    def __init__(
        self,
        name: str = "mega_agent_mcp",
        version: str = "1.0.0",
        max_sessions: int = 100,
        request_timeout: float = 30.0,
        enable_auth: bool = False,
        rate_limit_rpm: int = 1000,
    ) -> None:
        self.name = name
        self.version = version
        self.max_sessions = max_sessions
        self.request_timeout = request_timeout
        self.enable_auth = enable_auth
        self.rate_limit_rpm = rate_limit_rpm


class MCPServer:
    """MCP Protocol Server.

    Implements the Model Context Protocol for tool invocation.

    Usage:
        server = MCPServer()

        # Register tools
        server.register_tool(my_tool)

        # Or use tool provider
        server.use_provider(get_tool_provider())

        # Handle incoming request
        response = await server.handle_request(request_data)

        # For stdio transport
        await server.run_stdio()
    """

    def __init__(
        self,
        config: MCPServerConfig | None = None,
        tool_provider: ToolProvider | None = None,
    ) -> None:
        self.config = config or MCPServerConfig()
        self._provider = tool_provider or ToolProvider(self.config.name)

        self._sessions: dict[str, MCPSession] = {}
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

        # Register standard MCP methods
        self._register_standard_handlers()

        # Stats
        self._stats = {
            "requests_handled": 0,
            "tools_invoked": 0,
            "errors": 0,
        }

    def _register_standard_handlers(self) -> None:
        """Register standard MCP method handlers."""
        self._handlers["initialize"] = self._handle_initialize
        self._handlers["tools/list"] = self._handle_list_tools
        self._handlers["tools/call"] = self._handle_call_tool
        self._handlers["resources/list"] = self._handle_list_resources
        self._handlers["ping"] = self._handle_ping
        self._handlers["shutdown"] = self._handle_shutdown

    def use_provider(self, provider: ToolProvider) -> None:
        """Use an existing tool provider."""
        self._provider = provider

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the server."""
        self._provider.register(tool)

    def register_handler(
        self,
        method: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register a custom method handler."""
        self._handlers[method] = handler

    async def handle_request(
        self,
        data: str | bytes | dict[str, Any],
    ) -> MCPResponse:
        """Handle an MCP request.

        Args:
            data: JSON string, bytes, or parsed dict

        Returns:
            MCPResponse object
        """
        self._stats["requests_handled"] += 1

        try:
            parsed = json.loads(data) if isinstance(data, str | bytes) else data

            request = MCPRequest.from_dict(parsed)

        except json.JSONDecodeError as e:
            self._stats["errors"] += 1
            return MCPResponse.error(
                None,
                MCPErrorCode.PARSE_ERROR,
                f"Invalid JSON: {e}",
            )
        except (KeyError, TypeError) as e:
            self._stats["errors"] += 1
            return MCPResponse.error(
                None,
                MCPErrorCode.INVALID_REQUEST,
                f"Invalid request: {e}",
            )

        # Find handler
        handler = self._handlers.get(request.method)
        if not handler:
            self._stats["errors"] += 1
            return MCPResponse.error(
                request.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}",
            )

        # Execute handler with timeout
        try:
            result = await asyncio.wait_for(
                handler(request),
                timeout=self.config.request_timeout,
            )
            return MCPResponse.success(request.id, result)

        except TimeoutError:
            self._stats["errors"] += 1
            return MCPResponse.error(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                "Request timeout",
            )
        except Exception as e:
            self._stats["errors"] += 1
            logger.exception("mcp.handler.error", method=request.method)
            return MCPResponse.error(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                str(e),
            )

    async def handle_batch(
        self,
        requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Handle batch of requests."""
        tasks = [self.handle_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        return [r.to_dict() for r in responses]

    # Standard MCP handlers

    async def _handle_initialize(self, request: MCPRequest) -> dict[str, Any]:
        """Handle initialize request."""
        client_info = request.params.get("clientInfo", {})
        session = MCPSession.create(client_info)
        self._sessions[session.id] = session

        logger.info(
            "mcp.session.created",
            session_id=session.id,
            client=client_info.get("name", "unknown"),
        )

        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self.config.name,
                "version": self.config.version,
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": False},
            },
            "sessionId": session.id,
        }

    async def _handle_list_tools(self, request: MCPRequest) -> dict[str, Any]:
        """Handle tools/list request."""
        tools = self._provider.get_mcp_tools()
        return {"tools": tools}

    async def _handle_call_tool(self, request: MCPRequest) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if not tool_name:
            raise ValueError("Missing tool name")

        tool = self._provider.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        self._stats["tools_invoked"] += 1

        logger.info(
            "mcp.tool.invoke",
            tool=tool_name,
            args_keys=list(arguments.keys()),
        )

        result = await tool.execute(**arguments)

        if result.success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            json.dumps(result.data)
                            if not isinstance(result.data, str)
                            else result.data
                        ),
                    }
                ],
                "isError": False,
            }
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.error or "Tool execution failed",
                }
            ],
            "isError": True,
        }

    async def _handle_list_resources(self, request: MCPRequest) -> dict[str, Any]:
        """Handle resources/list request."""
        # Resources are not currently implemented
        return {"resources": []}

    async def _handle_ping(self, request: MCPRequest) -> dict[str, Any]:
        """Handle ping request."""
        return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    async def _handle_shutdown(self, request: MCPRequest) -> dict[str, Any]:
        """Handle shutdown request."""
        session_id = request.params.get("sessionId")
        if session_id and session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("mcp.session.closed", session_id=session_id)

        return {"status": "shutdown"}

    # Transport implementations

    async def run_stdio(self) -> None:
        """Run server using stdio transport.

        Reads JSON-RPC requests from stdin, writes responses to stdout.
        """
        import sys

        logger.info("mcp.server.starting", transport="stdio")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(
            writer_transport, writer_protocol, reader, asyncio.get_event_loop()
        )

        try:
            while True:
                # Read content-length header
                header = await reader.readline()
                if not header:
                    break

                if header.startswith(b"Content-Length:"):
                    length = int(header.decode().split(":")[1].strip())
                    await reader.readline()  # Empty line
                    content = await reader.read(length)

                    response = await self.handle_request(content)
                    response_json = json.dumps(response.to_dict())
                    response_bytes = response_json.encode()

                    writer.write(f"Content-Length: {len(response_bytes)}\r\n\r\n".encode())
                    writer.write(response_bytes)
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        finally:
            logger.info("mcp.server.stopped")

    async def run_websocket(
        self,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        """Run server using WebSocket transport.

        Requires websockets library.
        """
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets library required for WebSocket transport")

        async def handler(websocket: Any) -> None:
            session = MCPSession.create()
            self._sessions[session.id] = session

            try:
                async for message in websocket:
                    response = await self.handle_request(message)
                    await websocket.send(json.dumps(response.to_dict()))
            finally:
                if session.id in self._sessions:
                    del self._sessions[session.id]

        logger.info("mcp.server.starting", transport="websocket", host=host, port=port)

        async with websockets.serve(handler, host, port):
            await asyncio.Future()  # Run forever

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            **self._stats,
            "active_sessions": len(self._sessions),
            "registered_tools": len(self._provider.list_tools()),
        }


# Global server instance
_global_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """Get global MCP server."""
    global _global_server
    if _global_server is None:
        _global_server = MCPServer()
    return _global_server


def create_mcp_server(
    config: MCPServerConfig | None = None,
    tool_provider: ToolProvider | None = None,
) -> MCPServer:
    """Create configured MCP server."""
    return MCPServer(config=config, tool_provider=tool_provider)


__all__ = [
    "MCPErrorCode",
    "MCPRequest",
    "MCPResponse",
    "MCPServer",
    "MCPServerConfig",
    "MCPSession",
    "create_mcp_server",
    "get_mcp_server",
]
