"""Parallel Research Execution.

Orchestrates parallel research tasks with:
- Fan-out/fan-in patterns
- Configurable concurrency
- Result aggregation
- Progress tracking
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar

import structlog

from core.context.context_synthesizer import ContextSynthesizer, SynthesisStrategy
from core.context.isolated_context import IsolatedContext, IsolatedContextPool

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ResearchPhase(str, Enum):
    """Phases of research execution."""

    PLANNING = "planning"
    EXECUTING = "executing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """Status of individual research task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResearchTask:
    """Definition of a research task."""

    id: str
    name: str
    query: str
    task_type: str = "research"
    priority: int = 5
    timeout: float = 300.0
    max_tokens: int = 50000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a research task."""

    task_id: str
    status: TaskStatus
    result: str = ""
    error: str | None = None
    execution_time: float = 0.0
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPlan:
    """Plan for parallel research."""

    id: str
    main_query: str
    tasks: list[ResearchTask]
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchResult:
    """Final result of parallel research."""

    plan_id: str
    main_query: str
    synthesized_result: str
    task_results: list[TaskResult]
    phase: ResearchPhase
    total_time: float
    total_tokens: int
    success_rate: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ParallelResearchExecutor:
    """Execute research tasks in parallel with fan-out/fan-in.

    Features:
    - Configurable concurrency limits
    - Isolated contexts for each task
    - Result synthesis
    - Progress callbacks

    Usage:
        executor = ParallelResearchExecutor(max_concurrent=5)

        # Define research tasks
        tasks = [
            ResearchTask(id="1", name="task1", query="Research topic A"),
            ResearchTask(id="2", name="task2", query="Research topic B"),
        ]

        # Execute with agent function
        async def agent_fn(ctx: IsolatedContext) -> str:
            # Your research logic
            return "result"

        result = await executor.execute(
            main_query="Main research question",
            tasks=tasks,
            agent_fn=agent_fn,
        )
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        max_total_tokens: int = 500000,
        default_timeout: float = 300.0,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.max_total_tokens = max_total_tokens
        self.default_timeout = default_timeout

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._pool = IsolatedContextPool(
            max_total_tokens=max_total_tokens,
            max_contexts=max_concurrent * 2,
        )
        self._synthesizer = ContextSynthesizer()

        # Tracking
        self._current_phase = ResearchPhase.PLANNING
        self._task_status: dict[str, TaskStatus] = {}
        self._progress_callback: Callable[[str, float], None] | None = None

    def set_progress_callback(
        self,
        callback: Callable[[str, float], None],
    ) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    async def execute(
        self,
        main_query: str,
        tasks: list[ResearchTask],
        agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
        synthesis_strategy: SynthesisStrategy = SynthesisStrategy.DEDUPLICATE,
    ) -> ResearchResult:
        """Execute parallel research.

        Args:
            main_query: Main research question
            tasks: List of research tasks
            agent_fn: Async function to run for each task
            synthesis_strategy: How to synthesize results

        Returns:
            ResearchResult with synthesized findings
        """
        import time

        start_time = time.perf_counter()

        # Initialize tracking
        for task in tasks:
            self._task_status[task.id] = TaskStatus.PENDING

        self._current_phase = ResearchPhase.EXECUTING
        self._report_progress("Starting parallel execution", 0.0)

        # Fan-out: Execute tasks in parallel
        task_results = await self._fan_out(tasks, agent_fn)

        self._current_phase = ResearchPhase.SYNTHESIZING
        self._report_progress("Synthesizing results", 0.8)

        # Fan-in: Synthesize results
        synthesis = await self._fan_in(main_query, synthesis_strategy)

        self._current_phase = ResearchPhase.COMPLETED
        total_time = time.perf_counter() - start_time

        # Calculate stats
        completed = sum(1 for r in task_results if r.status == TaskStatus.COMPLETED)
        total_tokens = sum(r.tokens_used for r in task_results)
        success_rate = completed / max(1, len(task_results))

        self._report_progress("Research complete", 1.0)

        logger.info(
            "parallel_research.complete",
            tasks=len(tasks),
            completed=completed,
            total_time=total_time,
            total_tokens=total_tokens,
            success_rate=success_rate,
        )

        return ResearchResult(
            plan_id=f"research_{int(start_time)}",
            main_query=main_query,
            synthesized_result=synthesis.content,
            task_results=task_results,
            phase=self._current_phase,
            total_time=total_time,
            total_tokens=total_tokens,
            success_rate=success_rate,
            metadata={
                "strategy": synthesis_strategy.value,
                "max_concurrent": self.max_concurrent,
            },
        )

    async def _fan_out(
        self,
        tasks: list[ResearchTask],
        agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
    ) -> list[TaskResult]:
        """Fan-out: Execute tasks in parallel."""
        # Sort by priority (higher first)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

        # Create coroutines for parallel execution
        coros = [self._execute_task(task, agent_fn) for task in sorted_tasks]

        # Execute with gather
        results = await asyncio.gather(*coros, return_exceptions=True)

        # Process results
        task_results = []
        for task, result in zip(sorted_tasks, results, strict=False):
            if isinstance(result, Exception):
                task_results.append(
                    TaskResult(
                        task_id=task.id,
                        status=TaskStatus.FAILED,
                        error=str(result),
                    )
                )
            else:
                task_results.append(result)

        return task_results

    async def _execute_task(
        self,
        task: ResearchTask,
        agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
    ) -> TaskResult:
        """Execute a single research task."""
        import time

        start_time = time.perf_counter()

        self._task_status[task.id] = TaskStatus.RUNNING

        # Create isolated context
        ctx = self._pool.create(
            name=task.name,
            task=task.query,
            task_type=task.task_type,
            max_tokens=task.max_tokens,
            **task.metadata,
        )

        if ctx is None:
            self._task_status[task.id] = TaskStatus.FAILED
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="Failed to create isolated context",
            )

        ctx.activate()

        try:
            # Execute with semaphore and timeout
            async with self._semaphore:
                result = await asyncio.wait_for(
                    agent_fn(ctx),
                    timeout=task.timeout or self.default_timeout,
                )

            ctx.set_result(result)
            elapsed = time.perf_counter() - start_time

            self._task_status[task.id] = TaskStatus.COMPLETED
            self._update_progress()

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=elapsed,
                tokens_used=ctx.total_tokens,
            )

        except TimeoutError:
            ctx.set_result("", error="Timeout")
            self._task_status[task.id] = TaskStatus.FAILED

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=f"Timeout after {task.timeout}s",
                execution_time=time.perf_counter() - start_time,
            )

        except asyncio.CancelledError:
            self._task_status[task.id] = TaskStatus.CANCELLED

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.CANCELLED,
                error="Cancelled",
            )

        except Exception as e:
            ctx.set_result("", error=str(e))
            self._task_status[task.id] = TaskStatus.FAILED

            logger.error(
                "parallel_research.task_failed",
                task_id=task.id,
                error=str(e),
            )

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=time.perf_counter() - start_time,
            )

    async def _fan_in(
        self,
        main_query: str,
        strategy: SynthesisStrategy,
    ):
        """Fan-in: Synthesize results from all contexts."""
        return await self._synthesizer.synthesize_pool(
            self._pool,
            query=main_query,
            strategy=strategy,
        )

    def _update_progress(self) -> None:
        """Update progress based on task completion."""
        total = len(self._task_status)
        completed = sum(
            1
            for s in self._task_status.values()
            if s in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        )
        progress = completed / max(1, total) * 0.8  # Reserve 20% for synthesis
        self._report_progress(f"Tasks: {completed}/{total}", progress)

    def _report_progress(self, message: str, progress: float) -> None:
        """Report progress via callback."""
        if self._progress_callback:
            try:
                self._progress_callback(message, progress)
            except Exception:
                pass

    def get_status(self) -> dict[str, Any]:
        """Get current execution status."""
        return {
            "phase": self._current_phase.value,
            "tasks": dict(self._task_status),
            "completed": sum(1 for s in self._task_status.values() if s == TaskStatus.COMPLETED),
            "failed": sum(1 for s in self._task_status.values() if s == TaskStatus.FAILED),
            "pending": sum(
                1
                for s in self._task_status.values()
                if s in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ),
        }

    def cleanup(self) -> None:
        """Cleanup resources."""
        self._pool.clear_all()
        self._task_status.clear()


class ResearchPlanner:
    """Plan research tasks from a main query.

    Uses LLM to decompose complex queries into parallel subtasks.
    """

    def __init__(self, max_tasks: int = 10) -> None:
        self.max_tasks = max_tasks

    async def create_plan(
        self,
        main_query: str,
        context: str = "",
    ) -> ResearchPlan:
        """Create research plan from main query.

        Args:
            main_query: Main research question
            context: Additional context

        Returns:
            ResearchPlan with decomposed tasks
        """
        try:
            from core.llm_interface import TaskRequest, TaskRouter, TaskType

            router = TaskRouter()

            prompt = f"""Decompose this research question into {self.max_tasks} parallel sub-questions.
Each sub-question should explore a different aspect that can be researched independently.

Main Question: {main_query}

{f"Context: {context}" if context else ""}

Return a JSON array of objects with:
- id: unique identifier (1, 2, 3...)
- name: short name for the task
- query: the specific sub-question to research
- priority: importance 1-10 (10 = most important)

Example:
[
  {{"id": "1", "name": "background", "query": "What is the historical context?", "priority": 8}},
  {{"id": "2", "name": "current_state", "query": "What is the current situation?", "priority": 9}}
]

Return ONLY the JSON array, no other text."""

            response = await router.route(
                TaskRequest(
                    prompt=prompt,
                    task_type=TaskType.RESEARCH,
                    temperature=0.3,
                )
            )

            # Parse response
            import json

            try:
                tasks_data = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re

                match = re.search(r"\[.*\]", response.content, re.DOTALL)
                if match:
                    tasks_data = json.loads(match.group())
                else:
                    raise ValueError("Could not parse tasks from response")

            tasks = [
                ResearchTask(
                    id=str(t.get("id", i)),
                    name=t.get("name", f"task_{i}"),
                    query=t.get("query", main_query),
                    priority=t.get("priority", 5),
                )
                for i, t in enumerate(tasks_data[: self.max_tasks])
            ]

            return ResearchPlan(
                id=f"plan_{int(datetime.now(UTC).timestamp())}",
                main_query=main_query,
                tasks=tasks,
            )

        except Exception as e:
            logger.warning("research_planner.failed", error=str(e))

            # Fallback: simple decomposition
            return ResearchPlan(
                id=f"plan_{int(datetime.now(UTC).timestamp())}",
                main_query=main_query,
                tasks=[
                    ResearchTask(
                        id="1",
                        name="main_research",
                        query=main_query,
                        priority=10,
                    )
                ],
            )


# Convenience functions
def create_parallel_executor(
    max_concurrent: int = 5,
    max_tokens: int = 500000,
) -> ParallelResearchExecutor:
    """Create configured parallel executor."""
    return ParallelResearchExecutor(
        max_concurrent=max_concurrent,
        max_total_tokens=max_tokens,
    )


async def parallel_research(
    main_query: str,
    agent_fn: Callable[[IsolatedContext], Coroutine[Any, Any, str]],
    max_concurrent: int = 5,
    auto_plan: bool = True,
) -> ResearchResult:
    """Convenience function for parallel research.

    Args:
        main_query: Research question
        agent_fn: Agent function for each task
        max_concurrent: Maximum parallel tasks
        auto_plan: Automatically plan subtasks

    Returns:
        ResearchResult
    """
    executor = create_parallel_executor(max_concurrent=max_concurrent)

    if auto_plan:
        planner = ResearchPlanner()
        plan = await planner.create_plan(main_query)
        tasks = plan.tasks
    else:
        tasks = [ResearchTask(id="1", name="main", query=main_query, priority=10)]

    return await executor.execute(
        main_query=main_query,
        tasks=tasks,
        agent_fn=agent_fn,
    )
