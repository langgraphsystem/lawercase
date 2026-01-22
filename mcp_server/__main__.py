"""Entry point for running MCP server as a module."""

from __future__ import annotations

import asyncio

from .server import run_server

if __name__ == "__main__":
    asyncio.run(run_server())
