from __future__ import annotations

import asyncio

import pytest

from core.tools.tool_registry import (ToolMetadata, get_tool_registry,
                                      reset_tool_registry)


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_tool_registry()
    yield
    reset_tool_registry()


async def _demo_tool(**kwargs):
    return {"echo": kwargs}


@pytest.mark.asyncio
async def test_register_and_invoke_with_role():
    registry = get_tool_registry()
    registry.register(
        "demo",
        _demo_tool,
        metadata=ToolMetadata(
            name="Demo",
            description="Echo tool",
            allowed_roles={"admin", "lawyer"},
        ),
    )

    result = await registry.invoke("demo", caller_role="admin", arguments={"value": 1})
    assert result == {"echo": {"value": 1}}


@pytest.mark.asyncio
async def test_invoke_denied_for_role():
    registry = get_tool_registry()
    registry.register(
        "restricted",
        _demo_tool,
        metadata=ToolMetadata(
            name="Restricted",
            description="",
            allowed_roles={"admin"},
        ),
    )

    with pytest.raises(PermissionError):
        await registry.invoke("restricted", caller_role="client")


def test_history_tracking():
    registry = get_tool_registry()

    async def tool(**kwargs):
        return kwargs

    registry.register(
        "hist",
        tool,
        metadata=ToolMetadata(name="History", description=""),
    )

    asyncio.run(registry.invoke("hist", caller_role="lawyer", arguments={"a": 1}))
    history = registry.get_history("hist")
    assert history and history[0]["args"] == {"a": 1}
