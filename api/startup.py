from __future__ import annotations

from core.tools.tool_registry import ToolMetadata, get_tool_registry


def register_builtin_tools() -> None:
    """Register built-in tools that should always be available."""
    registry = get_tool_registry()

    if any(meta.name == "http.get" for meta in registry.list_tools()):
        return

    async def _http_get(url: str) -> dict[str, str]:
        # Placeholder implementation; production code should perform real HTTP requests.
        return {"url": url, "status": "stubbed"}

    registry.register(
        "http.get",
        _http_get,
        metadata=ToolMetadata(
            name="http.get",
            description="Simplified HTTP GET tool used for smoke tests and development.",
            allowed_roles={"admin", "lawyer"},
            tags={"network", "builtin"},
        ),
    )
