"""Parallel Executor for Agent Tasks.

Provides fan-out/fan-in patterns for parallel agent execution with:
- Configurable concurrency limits
- Task dependency management
- Result aggregation
- Timeout handling per task
- Graceful cancellation
- Progress tracking
- Error collection and reporting
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import time
from typing import Any, Generic, TypeVar
import uuid

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class TaskState(str, Enum):
    """State of a parallel task."""

    PENDING = "pending"
    WAITING = "waiting"  # Waiting for dependencies
    READY = "ready"  # Ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ExecutionPhase(str, Enum):
    """Phases of parallel execution."""

    INITIALIZING = "initializing"
    SCHEDULING = "scheduling"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ParallelTask(Generic[T]):
    """Represents a single task for parallel execution.

    Attributes:
        id: Unique task identifier
        name: Human-readable name
        coro_factory: Factory function to create the coroutine
        dependencies: List of task IDs this task depends on
        timeout: Task-specific timeout in seconds
        priority: Task priority (higher = more important)
        metadata: Additional task metadata
        retries: Number of retry attempts
        retry_delay: Delay between retries in seconds
    """

    id: str
    name: str
    coro_factory: Callable[[], Coroutine[Any, Any, T]]
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    priority: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    retry_delay: float = 1.0

    # Runtime state (managed internally)
    state: TaskState = TaskState.PENDING
    result: T | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempt: int = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ParallelTask):
            return self.id == other.id
        return False

    @property
    def execution_time(self) -> float:
        """Get task execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (datetime.now(UTC) - self.started_at).total_seconds()
        return 0.0

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in (
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
            TaskState.TIMED_OUT,
        )


@dataclass
class TaskError:
    """Error information for a failed task."""

    task_id: str
    task_name: str
    error_type: str
    error_message: str
    traceback: str | None = None
    attempt: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResult(Generic[T]):
    """Result of a single task execution."""

    task_id: str
    task_name: str
    state: TaskState
    result: T | None = None
    error: TaskError | None = None
    execution_time: float = 0.0
    wait_time: float = 0.0
    attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.state == TaskState.COMPLETED


@dataclass
class ExecutionResult(Generic[T]):
    """Aggregated result of parallel execution.

    Contains all task results, errors, and execution statistics.
    """

    execution_id: str
    phase: ExecutionPhase
    task_results: list[TaskResult[T]]
    total_time: float
    started_at: datetime
    completed_at: datetime | None = None
    aggregated_result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tasks(self) -> int:
        """Total number of tasks."""
        return len(self.task_results)

    @property
    def completed_count(self) -> int:
        """Number of successfully completed tasks."""
        return sum(1 for r in self.task_results if r.state == TaskState.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Number of failed tasks."""
        return sum(
            1 for r in self.task_results if r.state in (TaskState.FAILED, TaskState.TIMED_OUT)
        )

    @property
    def cancelled_count(self) -> int:
        """Number of cancelled tasks."""
        return sum(1 for r in self.task_results if r.state == TaskState.CANCELLED)

    @property
    def success_rate(self) -> float:
        """Success rate as a ratio."""
        if not self.task_results:
            return 0.0
        return self.completed_count / len(self.task_results)

    @property
    def errors(self) -> list[TaskError]:
        """Get all errors from failed tasks."""
        return [r.error for r in self.task_results if r.error is not None]

    @property
    def successful_results(self) -> list[T]:
        """Get all successful results."""
        return [r.result for r in self.task_results if r.success and r.result is not None]

    def get_result(self, task_id: str) -> TaskResult[T] | None:
        """Get result for a specific task."""
        for result in self.task_results:
            if result.task_id == task_id:
                return result
        return None


class TaskDependencyGraph:
    """Manages task dependencies and execution order.

    Provides topological sorting and dependency resolution for
    parallel task execution.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ParallelTask] = {}
        self._dependents: dict[str, set[str]] = {}  # task_id -> tasks that depend on it
        self._lock = asyncio.Lock()

    def add_task(self, task: ParallelTask) -> None:
        """Add a task to the graph."""
        self._tasks[task.id] = task
        if task.id not in self._dependents:
            self._dependents[task.id] = set()

        # Register as dependent for each dependency
        for dep_id in task.dependencies:
            if dep_id not in self._dependents:
                self._dependents[dep_id] = set()
            self._dependents[dep_id].add(task.id)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the graph."""
        if task_id in self._tasks:
            task = self._tasks.pop(task_id)
            # Remove from dependents
            for dep_id in task.dependencies:
                if dep_id in self._dependents:
                    self._dependents[dep_id].discard(task_id)
            # Remove its dependents entry
            self._dependents.pop(task_id, None)

    def get_task(self, task_id: str) -> ParallelTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[ParallelTask]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_ready_tasks(self) -> list[ParallelTask]:
        """Get tasks that are ready to execute.

        A task is ready if:
        - It is in PENDING or READY state
        - All its dependencies are completed
        """
        ready = []
        for task in self._tasks.values():
            if task.state not in (TaskState.PENDING, TaskState.READY):
                continue

            # Check if all dependencies are completed
            deps_satisfied = all(
                self._tasks.get(dep_id) is not None
                and self._tasks[dep_id].state == TaskState.COMPLETED
                for dep_id in task.dependencies
            )

            if deps_satisfied:
                task.state = TaskState.READY
                ready.append(task)

        # Sort by priority (higher first)
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    def get_dependent_tasks(self, task_id: str) -> list[ParallelTask]:
        """Get tasks that depend on the given task."""
        dependent_ids = self._dependents.get(task_id, set())
        return [self._tasks[tid] for tid in dependent_ids if tid in self._tasks]

    def has_cycle(self) -> bool:
        """Check if the dependency graph has cycles."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self._tasks.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task_id in self._tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def validate(self) -> list[str]:
        """Validate the dependency graph.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check for cycles
        if self.has_cycle():
            errors.append("Dependency graph contains cycles")

        # Check for missing dependencies
        for task in self._tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self._tasks:
                    errors.append(f"Task {task.id} depends on non-existent task {dep_id}")

        return errors

    def topological_sort(self) -> list[ParallelTask]:
        """Get tasks in topological order (dependencies first).

        Returns:
            List of tasks in execution order

        Raises:
            ValueError: If graph has cycles
        """
        if self.has_cycle():
            raise ValueError("Cannot sort: dependency graph has cycles")

        in_degree: dict[str, int] = dict.fromkeys(self._tasks, 0)
        for task in self._tasks.values():
            for dep_id in task.dependencies:
                if dep_id in in_degree:
                    in_degree[task.id] += 1

        # Start with tasks that have no dependencies
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            # Sort by priority within the same level
            queue.sort(key=lambda tid: self._tasks[tid].priority, reverse=True)
            task_id = queue.pop(0)
            result.append(self._tasks[task_id])

            # Reduce in-degree for dependent tasks
            for dependent_id in self._dependents.get(task_id, set()):
                if dependent_id in in_degree:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return result

    def get_execution_levels(self) -> list[list[ParallelTask]]:
        """Get tasks grouped by execution level.

        Tasks at the same level can be executed in parallel.

        Returns:
            List of task groups (levels)
        """
        if self.has_cycle():
            raise ValueError("Cannot determine levels: graph has cycles")

        levels: list[list[ParallelTask]] = []
        remaining = set(self._tasks.keys())

        while remaining:
            # Find tasks whose dependencies are all satisfied
            level = []
            for task_id in list(remaining):
                task = self._tasks[task_id]
                deps_satisfied = all(dep_id not in remaining for dep_id in task.dependencies)
                if deps_satisfied:
                    level.append(task)

            if not level:
                raise ValueError("Could not determine execution level - possible cycle")

            # Sort by priority within level
            level.sort(key=lambda t: t.priority, reverse=True)
            levels.append(level)

            # Remove processed tasks
            for task in level:
                remaining.remove(task.id)

        return levels

    def clear(self) -> None:
        """Clear all tasks from the graph."""
        self._tasks.clear()
        self._dependents.clear()


@dataclass
class ExecutorConfig:
    """Configuration for ParallelExecutor."""

    max_concurrent: int = 10
    default_timeout: float = 300.0
    fail_fast: bool = False  # Stop on first failure
    cancel_on_failure: bool = False  # Cancel pending tasks on failure
    collect_all_errors: bool = True  # Collect errors from all failed tasks
    progress_interval: float = 1.0  # Progress callback interval


class ResultAggregator(ABC, Generic[T, R]):
    """Abstract base class for result aggregation.

    Override to implement custom result aggregation logic.
    """

    @abstractmethod
    async def aggregate(self, results: list[TaskResult[T]]) -> R:
        """Aggregate task results into a final result.

        Args:
            results: List of task results

        Returns:
            Aggregated result
        """


class DefaultAggregator(ResultAggregator[T, list[T]]):
    """Default aggregator that returns successful results as a list."""

    async def aggregate(self, results: list[TaskResult[T]]) -> list[T]:
        """Return list of successful results."""
        return [r.result for r in results if r.success and r.result is not None]


class DictAggregator(ResultAggregator[T, dict[str, T]]):
    """Aggregator that returns results as a dictionary keyed by task ID."""

    async def aggregate(self, results: list[TaskResult[T]]) -> dict[str, T]:
        """Return dictionary of task_id -> result."""
        return {r.task_id: r.result for r in results if r.success and r.result is not None}


class ParallelExecutor(Generic[T]):
    """Main executor for parallel task execution.

    Features:
    - Fan-out/fan-in patterns
    - Configurable concurrency limits
    - Task dependency management
    - Timeout handling per task
    - Graceful cancellation
    - Progress tracking
    - Error collection and reporting

    Usage:
        executor = ParallelExecutor(max_concurrent=5)

        # Add tasks
        executor.add_task(ParallelTask(
            id="task1",
            name="First Task",
            coro_factory=lambda: async_operation(),
        ))

        executor.add_task(ParallelTask(
            id="task2",
            name="Second Task",
            coro_factory=lambda: another_operation(),
            dependencies=["task1"],  # Depends on task1
        ))

        # Execute
        result = await executor.execute()

        print(f"Success rate: {result.success_rate:.1%}")
    """

    def __init__(
        self,
        config: ExecutorConfig | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        if config:
            self.config = config
        else:
            self.config = ExecutorConfig(max_concurrent=max_concurrent or 10)

        self._graph = TaskDependencyGraph()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._lock = asyncio.Lock()

        # Execution state
        self._execution_id: str = ""
        self._phase = ExecutionPhase.INITIALIZING
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, TaskResult[T]] = {}
        self._errors: list[TaskError] = []
        self._cancelled = False
        self._start_time: float = 0

        # Progress tracking
        self._progress_callback: Callable[[str, float, dict[str, Any]], None] | None = None
        self._progress_task: asyncio.Task | None = None

    def add_task(self, task: ParallelTask[T]) -> None:
        """Add a task for execution."""
        self._graph.add_task(task)

    def add_tasks(self, tasks: list[ParallelTask[T]]) -> None:
        """Add multiple tasks for execution."""
        for task in tasks:
            self._graph.add_task(task)

    def set_progress_callback(
        self,
        callback: Callable[[str, float, dict[str, Any]], None],
    ) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function(message, progress, details) to call
        """
        self._progress_callback = callback

    async def execute(
        self,
        aggregator: ResultAggregator[T, R] | None = None,
    ) -> ExecutionResult[T]:
        """Execute all tasks with dependency resolution.

        Args:
            aggregator: Optional custom result aggregator

        Returns:
            ExecutionResult with all task results

        Raises:
            ValueError: If dependency graph is invalid
        """
        self._execution_id = str(uuid.uuid4())[:8]
        self._phase = ExecutionPhase.INITIALIZING
        self._start_time = time.perf_counter()
        self._cancelled = False
        self._results.clear()
        self._errors.clear()
        started_at = datetime.now(UTC)

        logger.info(
            "parallel_executor.start",
            execution_id=self._execution_id,
            task_count=len(self._graph.get_all_tasks()),
            max_concurrent=self.config.max_concurrent,
        )

        # Validate graph
        validation_errors = self._graph.validate()
        if validation_errors:
            raise ValueError(f"Invalid dependency graph: {validation_errors}")

        # Start progress tracking
        self._start_progress_tracking()

        try:
            self._phase = ExecutionPhase.SCHEDULING

            # Get execution levels for parallel execution
            levels = self._graph.get_execution_levels()

            self._phase = ExecutionPhase.EXECUTING

            # Execute each level in parallel
            for level_idx, level in enumerate(levels):
                if self._cancelled:
                    break

                self._report_progress(
                    f"Executing level {level_idx + 1}/{len(levels)}",
                    self._calculate_progress(),
                )

                # Fan-out: Execute tasks in this level concurrently
                await self._execute_level(level)

                # Check for failures if fail_fast is enabled
                if self.config.fail_fast and self._errors:
                    logger.warning(
                        "parallel_executor.fail_fast",
                        errors=len(self._errors),
                    )
                    break

            self._phase = ExecutionPhase.AGGREGATING

            # Collect results
            task_results = list(self._results.values())

            # Aggregate if aggregator provided
            aggregated = None
            if aggregator:
                try:
                    aggregated = await aggregator.aggregate(task_results)
                except Exception as e:
                    logger.error("parallel_executor.aggregation_failed", error=str(e))

            total_time = time.perf_counter() - self._start_time

            if self._cancelled:
                self._phase = ExecutionPhase.CANCELLED
            elif self._errors and self.config.fail_fast:
                self._phase = ExecutionPhase.FAILED
            else:
                self._phase = ExecutionPhase.COMPLETED

            result = ExecutionResult(
                execution_id=self._execution_id,
                phase=self._phase,
                task_results=task_results,
                total_time=total_time,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                aggregated_result=aggregated,
                metadata={
                    "max_concurrent": self.config.max_concurrent,
                    "levels": len(levels),
                    "fail_fast": self.config.fail_fast,
                },
            )

            logger.info(
                "parallel_executor.complete",
                execution_id=self._execution_id,
                total_tasks=result.total_tasks,
                completed=result.completed_count,
                failed=result.failed_count,
                success_rate=result.success_rate,
                total_time=total_time,
            )

            return result

        finally:
            self._stop_progress_tracking()
            self._running_tasks.clear()

    async def _execute_level(self, tasks: list[ParallelTask[T]]) -> None:
        """Execute all tasks in a level concurrently."""
        if not tasks:
            return

        # Create asyncio tasks for tracking and cancellation
        async_tasks: list[asyncio.Task] = []
        for task in tasks:
            async_task = asyncio.create_task(self._execute_task(task))
            async_tasks.append(async_task)
            self._running_tasks[task.id] = async_task

        # Fan-out: Wait for all tasks to complete
        try:
            await asyncio.gather(*async_tasks, return_exceptions=True)
        finally:
            # Clean up tracked tasks
            for task in tasks:
                self._running_tasks.pop(task.id, None)

    async def _execute_task(self, task: ParallelTask[T]) -> None:
        """Execute a single task with retry and timeout handling."""
        if self._cancelled:
            self._complete_task(task, TaskState.CANCELLED, error="Execution cancelled")
            return

        # Check dependencies one more time
        for dep_id in task.dependencies:
            dep_result = self._results.get(dep_id)
            if not dep_result or not dep_result.success:
                self._complete_task(
                    task,
                    TaskState.CANCELLED,
                    error=f"Dependency {dep_id} failed or was cancelled",
                )
                return

        wait_start = time.perf_counter()

        async with self._semaphore:
            wait_time = time.perf_counter() - wait_start
            task.state = TaskState.RUNNING
            task.started_at = datetime.now(UTC)

            # Retry loop
            for attempt in range(task.retries + 1):
                task.attempt = attempt + 1

                try:
                    # Execute with timeout
                    coro = task.coro_factory()
                    result = await asyncio.wait_for(
                        coro,
                        timeout=task.timeout,
                    )

                    # Success
                    self._complete_task(
                        task,
                        TaskState.COMPLETED,
                        result=result,
                        wait_time=wait_time,
                    )
                    return

                except TimeoutError:
                    if attempt >= task.retries:
                        self._complete_task(
                            task,
                            TaskState.TIMED_OUT,
                            error=f"Timeout after {task.timeout}s",
                            wait_time=wait_time,
                        )
                        self._handle_task_failure(task)
                        return
                    logger.warning(
                        "parallel_executor.task_timeout_retry",
                        task_id=task.id,
                        attempt=attempt + 1,
                        max_retries=task.retries,
                    )
                    await asyncio.sleep(task.retry_delay)

                except asyncio.CancelledError:
                    self._complete_task(
                        task,
                        TaskState.CANCELLED,
                        error="Task cancelled",
                        wait_time=wait_time,
                    )
                    return

                except Exception as e:
                    if attempt >= task.retries:
                        import traceback

                        tb = traceback.format_exc()
                        self._complete_task(
                            task,
                            TaskState.FAILED,
                            error=str(e),
                            traceback=tb,
                            wait_time=wait_time,
                        )
                        self._handle_task_failure(task)
                        return
                    logger.warning(
                        "parallel_executor.task_error_retry",
                        task_id=task.id,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    await asyncio.sleep(task.retry_delay)

    def _complete_task(
        self,
        task: ParallelTask[T],
        state: TaskState,
        result: T | None = None,
        error: str | None = None,
        traceback: str | None = None,
        wait_time: float = 0.0,
    ) -> None:
        """Record task completion."""
        task.state = state
        task.result = result
        task.error = error
        task.completed_at = datetime.now(UTC)

        task_error = None
        if error:
            task_error = TaskError(
                task_id=task.id,
                task_name=task.name,
                error_type=state.value,
                error_message=error,
                traceback=traceback,
                attempt=task.attempt,
            )
            if self.config.collect_all_errors:
                self._errors.append(task_error)

        task_result = TaskResult(
            task_id=task.id,
            task_name=task.name,
            state=state,
            result=result,
            error=task_error,
            execution_time=task.execution_time,
            wait_time=wait_time,
            attempts=task.attempt,
            metadata=task.metadata,
        )

        self._results[task.id] = task_result

        logger.info(
            "parallel_executor.task_complete",
            task_id=task.id,
            state=state.value,
            execution_time=task.execution_time,
        )

    def _handle_task_failure(self, task: ParallelTask[T]) -> None:
        """Handle task failure - potentially cancel dependent tasks."""
        if self.config.cancel_on_failure:
            # Mark dependent tasks as cancelled
            dependents = self._graph.get_dependent_tasks(task.id)
            for dep in dependents:
                if not dep.is_terminal:
                    self._complete_task(
                        dep,
                        TaskState.CANCELLED,
                        error=f"Cancelled due to dependency {task.id} failure",
                    )

    async def cancel(self) -> None:
        """Cancel execution of all pending tasks."""
        self._cancelled = True

        # Get current running tasks under lock
        async with self._lock:
            tasks_to_cancel = list(self._running_tasks.items())

        # Cancel running asyncio tasks
        for _task_id, asyncio_task in tasks_to_cancel:
            if not asyncio_task.done():
                asyncio_task.cancel()

        # Wait for cancellation to complete
        for _task_id, asyncio_task in tasks_to_cancel:
            try:
                await asyncio_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        # Mark pending tasks as cancelled
        for task in self._graph.get_all_tasks():
            if not task.is_terminal:
                self._complete_task(
                    task,
                    TaskState.CANCELLED,
                    error="Execution cancelled by user",
                )

        logger.info("parallel_executor.cancelled", execution_id=self._execution_id)

    def _calculate_progress(self) -> float:
        """Calculate overall progress as a ratio."""
        all_tasks = self._graph.get_all_tasks()
        if not all_tasks:
            return 1.0

        completed = sum(1 for t in all_tasks if t.is_terminal)
        return completed / len(all_tasks)

    def _report_progress(self, message: str, progress: float) -> None:
        """Report progress via callback."""
        if self._progress_callback:
            try:
                details = {
                    "execution_id": self._execution_id,
                    "phase": self._phase.value,
                    "completed": sum(1 for t in self._graph.get_all_tasks() if t.is_terminal),
                    "total": len(self._graph.get_all_tasks()),
                    "errors": len(self._errors),
                }
                self._progress_callback(message, progress, details)
            except Exception:
                pass

    def _start_progress_tracking(self) -> None:
        """Start background progress tracking."""
        if self._progress_callback is None:
            return

        async def progress_loop():
            while not self._cancelled and self._phase == ExecutionPhase.EXECUTING:
                self._report_progress(
                    f"Executing ({self._phase.value})",
                    self._calculate_progress(),
                )
                await asyncio.sleep(self.config.progress_interval)

        task = asyncio.create_task(progress_loop())
        self._progress_task = task

    def _stop_progress_tracking(self) -> None:
        """Stop background progress tracking."""
        if self._progress_task:
            self._progress_task.cancel()
            self._progress_task = None

    def get_status(self) -> dict[str, Any]:
        """Get current execution status."""
        all_tasks = self._graph.get_all_tasks()
        by_state: dict[str, int] = {}
        for task in all_tasks:
            state = task.state.value
            by_state[state] = by_state.get(state, 0) + 1

        return {
            "execution_id": self._execution_id,
            "phase": self._phase.value,
            "total_tasks": len(all_tasks),
            "by_state": by_state,
            "progress": self._calculate_progress(),
            "errors": len(self._errors),
            "elapsed_time": time.perf_counter() - self._start_time if self._start_time else 0,
        }

    def clear(self) -> None:
        """Clear all tasks and reset executor."""
        self._graph.clear()
        self._results.clear()
        self._errors.clear()
        self._running_tasks.clear()
        self._cancelled = False
        self._phase = ExecutionPhase.INITIALIZING


class FanOutFanIn(Generic[T, R]):
    """Convenience class for simple fan-out/fan-in patterns.

    Usage:
        async def process_item(item: str) -> str:
            return item.upper()

        fan = FanOutFanIn(max_concurrent=5)
        results = await fan.execute(
            items=["a", "b", "c"],
            processor=process_item,
        )
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: float = 300.0,
        fail_fast: bool = False,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.fail_fast = fail_fast

    async def execute(
        self,
        items: list[T],
        processor: Callable[[T], Coroutine[Any, Any, R]],
        aggregator: ResultAggregator[R, Any] | None = None,
    ) -> ExecutionResult[R]:
        """Execute processor on all items in parallel.

        Args:
            items: Items to process
            processor: Async function to apply to each item
            aggregator: Optional result aggregator

        Returns:
            ExecutionResult with all results
        """
        config = ExecutorConfig(
            max_concurrent=self.max_concurrent,
            default_timeout=self.timeout,
            fail_fast=self.fail_fast,
        )

        executor: ParallelExecutor[R] = ParallelExecutor(config=config)

        for i, item in enumerate(items):
            # Capture item in closure correctly
            def make_factory(it: T) -> Callable[[], Coroutine[Any, Any, R]]:
                return lambda: processor(it)

            task: ParallelTask[R] = ParallelTask(
                id=f"item_{i}",
                name=f"Process item {i}",
                coro_factory=make_factory(item),
                timeout=self.timeout,
                metadata={"index": i, "item": str(item)[:100]},
            )
            executor.add_task(task)

        return await executor.execute(aggregator=aggregator)

    async def map(
        self,
        items: list[T],
        processor: Callable[[T], Coroutine[Any, Any, R]],
    ) -> list[R]:
        """Map processor over items, returning list of results.

        Args:
            items: Items to process
            processor: Async function to apply

        Returns:
            List of results (only successful ones)
        """
        result = await self.execute(items, processor, DefaultAggregator())
        return result.aggregated_result or []


# Convenience functions
def create_parallel_executor(
    max_concurrent: int = 10,
    timeout: float = 300.0,
    fail_fast: bool = False,
) -> ParallelExecutor:
    """Create a configured ParallelExecutor."""
    config = ExecutorConfig(
        max_concurrent=max_concurrent,
        default_timeout=timeout,
        fail_fast=fail_fast,
    )
    return ParallelExecutor(config=config)


async def parallel_execute(
    tasks: list[ParallelTask[T]],
    max_concurrent: int = 10,
    fail_fast: bool = False,
) -> ExecutionResult[T]:
    """Execute tasks in parallel (convenience function).

    Args:
        tasks: List of tasks to execute
        max_concurrent: Maximum concurrent tasks
        fail_fast: Stop on first failure

    Returns:
        ExecutionResult
    """
    executor: ParallelExecutor[T] = create_parallel_executor(
        max_concurrent=max_concurrent,
        fail_fast=fail_fast,
    )
    executor.add_tasks(tasks)
    return await executor.execute()


async def fan_out_fan_in(
    items: list[T],
    processor: Callable[[T], Coroutine[Any, Any, R]],
    max_concurrent: int = 10,
) -> list[R]:
    """Simple fan-out/fan-in (convenience function).

    Args:
        items: Items to process
        processor: Async function to apply
        max_concurrent: Maximum concurrency

    Returns:
        List of successful results
    """
    fan = FanOutFanIn[T, R](max_concurrent=max_concurrent)
    return await fan.map(items, processor)
