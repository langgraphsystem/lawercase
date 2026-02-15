"""Subagent Context Manager.

Orchestrates isolated contexts for parallel subagent execution:
- Spawn subagents with isolated contexts
- Track execution state
- Synthesize results
- Manage resource limits
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from core.context.context_synthesizer import (
    ContextSynthesizer,
    SynthesisResult,
    SynthesisStrategy,
)
from core.context.isolated_context import (
    ContextState,
    IsolatedContext,
    IsolatedContextPool,
)

logger = structlog.get_logger(__name__)


class SubagentState(str, Enum):
    """State of a subagent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubagentTask:
    """Definition of a subagent task."""

    name: str
    task: str
    task_type: str = "general"
    max_tokens: int = 50000
    timeout: float = 300.0  # seconds
    priority: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentResult:
    """Result from a subagent execution."""

    name: str
    state: SubagentState
    result: str = ""
    error: str | None = None
    execution_time: float = 0.0
    tokens_used: int = 0


@dataclass
class ExecutionStats:
    """Statistics for subagent execution."""

    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_tokens: int = 0
    total_time: float = 0.0


class SubagentContextManager:
    """Manage isolated contexts for parallel subagent execution.

    Features:
    - Spawn multiple subagents with isolated contexts
    - Parallel execution with concurrency limits
    - Automatic result synthesis
    - Resource management

    Usage:
        manager = SubagentContextManager(max_concurrent=5)

        # Define tasks
        tasks = [
            SubagentTask(name="research_1", task="Research topic A"),
            SubagentTask(name="research_2", task="Research topic B"),
            SubagentTask(name="research_3", task="Research topic C"),
        ]

        # Execute with custom agent function
        async def run_agent(ctx: IsolatedContext) -> str:
            # Your agent logic here
            return "result"

        results = await manager.execute_all(tasks, run_agent)

        # Get synthesized result
        synthesis = await manager.synthesize_results("Main query")
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        max_total_tokens: int = 500000,
        default_timeout: float = 300.0,
    ) -> None:
        """Initialize subagent context manager.

        Args:
            max_concurrent: Maximum concurrent subagents
            max_total_tokens: Total token budget for all contexts
            default_timeout: Default timeout per task
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout

        self.pool = IsolatedContextPool(
            max_total_tokens=max_total_tokens,
            max_contexts=max_concurrent * 2,  # Allow some buffer
        )

        self.synthesizer = ContextSynthesizer()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._results: dict[str, SubagentResult] = {}
        self._stats = ExecutionStats()

    async def spawn(
        self,
        task: SubagentTask,
        agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
    ) -> SubagentResult:
        """Spawn a single subagent with isolated context.

        Args:
            task: Task definition
            agent_fn: Async function that takes context and returns result

        Returns:
            SubagentResult
        """
        import time

        start_time = time.perf_counter()

        # Create isolated context
        ctx = self.pool.create(
            name=task.name,
            task=task.task,
            task_type=task.task_type,
            max_tokens=task.max_tokens,
            **task.metadata,
        )

        if ctx is None:
            return SubagentResult(
                name=task.name,
                state=SubagentState.FAILED,
                error="Failed to create isolated context (resource limit)",
            )

        ctx.activate()

        try:
            # Execute with timeout
            async with self._semaphore:
                result = await asyncio.wait_for(
                    agent_fn(ctx),
                    timeout=task.timeout or self.default_timeout,
                )

            ctx.set_result(result)
            elapsed = time.perf_counter() - start_time

            self._stats.completed += 1
            self._stats.total_tokens += ctx.total_tokens
            self._stats.total_time += elapsed

            return SubagentResult(
                name=task.name,
                state=SubagentState.COMPLETED,
                result=result,
                execution_time=elapsed,
                tokens_used=ctx.total_tokens,
            )

        except TimeoutError:
            ctx.set_result("", error="Timeout")
            self._stats.failed += 1

            return SubagentResult(
                name=task.name,
                state=SubagentState.FAILED,
                error=f"Timeout after {task.timeout}s",
                execution_time=time.perf_counter() - start_time,
            )

        except asyncio.CancelledError:
            ctx.state = ContextState.FAILED
            self._stats.cancelled += 1

            return SubagentResult(
                name=task.name,
                state=SubagentState.CANCELLED,
                error="Cancelled",
            )

        except Exception as e:
            ctx.set_result("", error=str(e))
            self._stats.failed += 1

            logger.error(
                "subagent.execution_failed",
                task=task.name,
                error=str(e),
            )

            return SubagentResult(
                name=task.name,
                state=SubagentState.FAILED,
                error=str(e),
                execution_time=time.perf_counter() - start_time,
            )

    async def execute_all(
        self,
        tasks: list[SubagentTask],
        agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
        fail_fast: bool = False,
    ) -> list[SubagentResult]:
        """Execute multiple tasks in parallel with isolated contexts.

        Args:
            tasks: List of task definitions
            agent_fn: Async function for each agent
            fail_fast: Stop all on first failure

        Returns:
            List of results (same order as tasks)
        """
        self._stats.total_tasks = len(tasks)

        # Sort by priority
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

        if fail_fast:
            # Execute with early termination
            results = []
            for task in sorted_tasks:
                result = await self.spawn(task, agent_fn)
                results.append(result)
                self._results[task.name] = result

                if result.state == SubagentState.FAILED:
                    break
        else:
            # Execute all in parallel
            coros = [self.spawn(task, agent_fn) for task in sorted_tasks]
            results = await asyncio.gather(*coros, return_exceptions=False)

            for task, result in zip(sorted_tasks, results, strict=False):
                self._results[task.name] = result

        # Return in original order
        return [self._results.get(t.name) for t in tasks]

    async def synthesize_results(
        self,
        query: str = "",
        strategy: SynthesisStrategy = SynthesisStrategy.DEDUPLICATE,
        max_tokens: int = 10000,
    ) -> SynthesisResult:
        """Synthesize all results into unified output.

        Args:
            query: Original query for relevance
            strategy: Synthesis strategy
            max_tokens: Max output tokens

        Returns:
            SynthesisResult
        """
        return await self.synthesizer.synthesize_pool(
            self.pool,
            query=query,
            strategy=strategy,
        )

    def get_result(self, name: str) -> SubagentResult | None:
        """Get result for a specific task."""
        return self._results.get(name)

    def get_all_results(self) -> dict[str, SubagentResult]:
        """Get all results."""
        return self._results.copy()

    def get_successful_results(self) -> list[SubagentResult]:
        """Get only successful results."""
        return [r for r in self._results.values() if r.state == SubagentState.COMPLETED]

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "total_tasks": self._stats.total_tasks,
            "completed": self._stats.completed,
            "failed": self._stats.failed,
            "cancelled": self._stats.cancelled,
            "success_rate": self._stats.completed / max(1, self._stats.total_tasks),
            "total_tokens": self._stats.total_tokens,
            "total_time_seconds": self._stats.total_time,
            "avg_time_per_task": self._stats.total_time / max(1, self._stats.completed),
            "pool_stats": self.pool.get_stats(),
        }

    def reset(self) -> None:
        """Reset manager state."""
        self.pool.clear_all()
        self._results.clear()
        self._stats = ExecutionStats()

    def cleanup(self) -> int:
        """Cleanup completed contexts."""
        return self.pool.clear_completed()


# Convenience function
def create_subagent_manager(
    max_concurrent: int = 5,
    max_total_tokens: int = 500000,
) -> SubagentContextManager:
    """Create configured subagent context manager."""
    return SubagentContextManager(
        max_concurrent=max_concurrent,
        max_total_tokens=max_total_tokens,
    )
