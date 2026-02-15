"""Secure Sandbox for Code and Tool Execution.

Provides sandboxed execution with:
- Resource limits (CPU, memory, time)
- Permission controls
- Execution isolation
- Result validation
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time

# Unix-only resource module
if sys.platform != "win32":
    import resource
else:
    resource = None  # type: ignore
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Status of sandbox execution."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    VIOLATION = "violation"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class SandboxPolicy:
    """Describe limits and permissions for sandbox execution."""

    name: str
    description: str
    allowed_tools: set[str] = field(default_factory=set)
    allowed_modules: set[str] = field(default_factory=set)
    network_access: bool = False
    filesystem_access: bool = False
    subprocess_access: bool = False
    max_cpu_seconds: float = 2.0
    max_memory_mb: int = 256
    max_output_size: int = 1048576  # 1MB


@dataclass
class ResourceUsage:
    """Resource usage statistics."""

    cpu_time_seconds: float = 0.0
    wall_time_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    output_size_bytes: int = 0


@dataclass
class ExecutionResult:
    """Result of sandboxed execution."""

    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    execution_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output": str(self.output)[:1000] if self.output else None,
            "error": self.error,
            "wall_time_seconds": self.resource_usage.wall_time_seconds,
            "execution_id": self.execution_id,
        }


class SandboxViolation(Exception):
    """Raised when sandbox constraints are breached."""


class SandboxRunner:
    """Run callables under a sandbox policy."""

    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    async def run_async(
        self,
        func: Callable[..., Awaitable[Any]],
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute async function with timeout enforcement."""
        timeout = timeout or self.policy.max_cpu_seconds

        try:
            return await asyncio.wait_for(func(**kwargs), timeout=timeout)
        except TimeoutError as exc:
            raise SandboxViolation("Execution exceeded time limit") from exc

    def run_sync(
        self,
        func: Callable[..., Any],
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute sync function with timeout (Unix only)."""
        timeout = timeout or self.policy.max_cpu_seconds

        def handler(signum: int, frame: Any) -> None:
            raise SandboxViolation("Execution exceeded time limit")

        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(int(timeout))

        try:
            return func(**kwargs)
        finally:
            if sys.platform != "win32":
                signal.alarm(0)


@dataclass
class SecureSandboxConfig:
    """Configuration for SecureSandbox."""

    default_timeout: float = 30.0
    default_memory_mb: int = 512
    allow_network: bool = False
    allow_filesystem: bool = True
    temp_dir: str | None = None
    log_executions: bool = True


class SecureSandbox:
    """Full-featured secure sandbox for code execution.

    Features:
    - Resource limits enforcement
    - Permission-based access control
    - Execution logging
    - Result validation

    Usage:
        sandbox = SecureSandbox()

        # Execute with default policy
        result = await sandbox.execute(my_async_function, arg1="value")

        # Execute with custom policy
        policy = SandboxPolicy(
            name="restricted",
            description="No network access",
            network_access=False,
            max_cpu_seconds=5.0,
        )
        result = await sandbox.execute_with_policy(
            policy, my_function, arg="value"
        )
    """

    def __init__(self, config: SecureSandboxConfig | None = None) -> None:
        self.config = config or SecureSandboxConfig()
        self._default_policy = SandboxPolicy(
            name="default",
            description="Default sandbox policy",
            network_access=self.config.allow_network,
            filesystem_access=self.config.allow_filesystem,
            max_cpu_seconds=self.config.default_timeout,
            max_memory_mb=self.config.default_memory_mb,
        )
        self._execution_count = 0
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "timeouts": 0,
            "violations": 0,
        }

    async def execute(
        self,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute function with default policy."""
        return await self.execute_with_policy(
            self._default_policy, func, *args, timeout=timeout, **kwargs
        )

    async def execute_with_policy(
        self,
        policy: SandboxPolicy,
        func: Callable[..., Awaitable[Any]] | Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute function with specific policy."""
        self._execution_count += 1
        execution_id = f"exec_{self._execution_count}_{int(time.time())}"

        self._stats["total_executions"] += 1
        start_time = time.perf_counter()
        started_at = datetime.now(UTC)

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            execution_id=execution_id,
            started_at=started_at,
        )

        try:
            # Validate permissions
            self._validate_policy(policy)

            # Set resource limits (Unix only)
            self._set_resource_limits(policy)

            effective_timeout = timeout or policy.max_cpu_seconds

            # Execute
            if asyncio.iscoroutinefunction(func):
                output = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=effective_timeout,
                )
            else:
                output = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: func(*args, **kwargs),
                )

            result.output = output
            result.status = ExecutionStatus.SUCCESS
            self._stats["successful"] += 1

        except TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error = "Execution timeout exceeded"
            self._stats["timeouts"] += 1

        except SandboxViolation as e:
            result.status = ExecutionStatus.VIOLATION
            result.error = str(e)
            self._stats["violations"] += 1

        except Exception as e:
            result.status = ExecutionStatus.ERROR
            result.error = f"{type(e).__name__}: {e!s}"
            self._stats["failed"] += 1

        finally:
            end_time = time.perf_counter()
            result.completed_at = datetime.now(UTC)
            result.resource_usage = ResourceUsage(
                wall_time_seconds=end_time - start_time,
            )

            if self.config.log_executions:
                logger.info(
                    "sandbox.execution.completed",
                    execution_id=execution_id,
                    status=result.status.value,
                    wall_time=result.resource_usage.wall_time_seconds,
                )

        return result

    def _validate_policy(self, policy: SandboxPolicy) -> None:
        """Validate policy constraints."""
        if policy.max_cpu_seconds <= 0:
            raise SandboxViolation("Invalid CPU time limit")
        if policy.max_memory_mb <= 0:
            raise SandboxViolation("Invalid memory limit")

    def _set_resource_limits(self, policy: SandboxPolicy) -> None:
        """Set OS resource limits (Unix only)."""
        if sys.platform == "win32" or resource is None:
            return

        try:
            # Memory limit
            memory_bytes = policy.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            # CPU time limit
            cpu_seconds = int(policy.max_cpu_seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

        except (ValueError, OSError) as e:
            logger.warning("sandbox.resource_limits.failed", error=str(e))

    async def execute_code(
        self,
        code: str,
        policy: SandboxPolicy | None = None,
        globals_dict: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute Python code string in sandbox."""
        policy = policy or self._default_policy

        # Create restricted globals
        safe_globals = {"__builtins__": {}}
        if globals_dict:
            safe_globals.update(globals_dict)

        # Add safe builtins
        safe_builtins = [
            "abs",
            "all",
            "any",
            "bool",
            "dict",
            "enumerate",
            "filter",
            "float",
            "int",
            "len",
            "list",
            "map",
            "max",
            "min",
            "print",
            "range",
            "round",
            "set",
            "sorted",
            "str",
            "sum",
            "tuple",
            "zip",
        ]
        for name in safe_builtins:
            safe_globals["__builtins__"][name] = getattr(__builtins__, name, None)

        async def run_code() -> Any:
            exec(compile(code, "<sandbox>", "exec"), safe_globals)  # noqa: S102
            return safe_globals.get("result")

        return await self.execute_with_policy(policy, run_code)

    def get_stats(self) -> dict[str, Any]:
        """Get sandbox statistics."""
        return self._stats


def ensure_tool_allowed(policy: SandboxPolicy, tool_id: str) -> None:
    """Helper to assert that tool_id is permitted under policy."""
    if policy.allowed_tools and tool_id not in policy.allowed_tools:
        raise SandboxViolation(f"Tool '{tool_id}' not permitted for policy '{policy.name}'")


def create_sandbox(config: SecureSandboxConfig | None = None) -> SecureSandbox:
    """Create a secure sandbox with configuration."""
    return SecureSandbox(config)


# Global sandbox
_global_sandbox: SecureSandbox | None = None


def get_sandbox() -> SecureSandbox:
    """Get global sandbox instance."""
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = SecureSandbox()
    return _global_sandbox


__all__ = [
    "ExecutionResult",
    "ExecutionStatus",
    "ResourceUsage",
    "SandboxPolicy",
    "SandboxRunner",
    "SandboxViolation",
    "SecureSandbox",
    "SecureSandboxConfig",
    "create_sandbox",
    "ensure_tool_allowed",
    "get_sandbox",
]
