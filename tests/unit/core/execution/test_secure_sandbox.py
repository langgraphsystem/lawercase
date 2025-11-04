from __future__ import annotations

import asyncio

import pytest

from core.execution.secure_sandbox import (SandboxPolicy, SandboxRunner,
                                           SandboxViolation,
                                           ensure_tool_allowed)


@pytest.mark.asyncio
async def test_runner_timeout():
    policy = SandboxPolicy(name="test", description="")
    runner = SandboxRunner(policy)

    async def slow_task():
        await asyncio.sleep(0.1)

    with pytest.raises(SandboxViolation):
        await runner.run_async(slow_task, timeout=0.01)


def test_ensure_tool_allowed():
    policy = SandboxPolicy(
        name="test",
        description="",
        allowed_tools={"alpha"},
    )

    ensure_tool_allowed(policy, "alpha")

    with pytest.raises(SandboxViolation):
        ensure_tool_allowed(policy, "beta")
