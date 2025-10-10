"""Secure sandbox utilities for executing tools and code with policies.

Phase 3 scaffolding: provides policy loading, resource limits, and a simple
async runner interface. Concrete enforcement (e.g. OS-level sandboxing) will be
implemented incrementally.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SandboxPolicy:
    """Describe limits and permissions for sandbox execution."""

    name: str
    description: str
    allowed_tools: set[str] = field(default_factory=set)
    network_access: bool = False
    filesystem_access: bool = False
    max_cpu_seconds: float = 2.0
    max_memory_mb: int = 256


class SandboxViolation(Exception):
    """Raised when sandbox constraints are breached."""


class SandboxRunner:
    """Run callables under a sandbox policy (placeholder implementation)."""

    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    async def run_async(
        self,
        func: Callable[..., Awaitable[Any]],
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute ``func`` with timeout enforcement.

        Resource isolation is minimal for now; future work will integrate
        subprocess sandboxing / cgroups. Timeout guarantees are provided.
        """

        timeout = timeout or self.policy.max_cpu_seconds

        try:
            return await asyncio.wait_for(func(**kwargs), timeout=timeout)
        except TimeoutError as exc:  # pragma: no cover - simple guard
            raise SandboxViolation("Execution exceeded time limit") from exc


def ensure_tool_allowed(policy: SandboxPolicy, tool_id: str) -> None:
    """Helper to assert that ``tool_id`` is permitted under ``policy``."""

    if policy.allowed_tools and tool_id not in policy.allowed_tools:
        raise SandboxViolation(f"Tool '{tool_id}' not permitted for policy '{policy.name}'")
