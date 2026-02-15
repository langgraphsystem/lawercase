"""Subagent Spawner - Manages spawning and coordination of research subagents.

Provides:
- Dynamic subagent creation for parallel research
- Resource management and limits
- Result aggregation
- Lifecycle management
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class SubagentStatus(str, Enum):
    """Status of a subagent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SubagentType(str, Enum):
    """Types of subagents."""

    WEB_SEARCHER = "web_searcher"
    DATABASE_SEARCHER = "database_searcher"
    DOCUMENT_ANALYZER = "document_analyzer"
    FACT_CHECKER = "fact_checker"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"


@dataclass
class SubagentConfig:
    """Configuration for a subagent."""

    type: SubagentType
    timeout_seconds: float = 60.0
    max_retries: int = 2
    priority: int = 1  # Lower = higher priority
    resources: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentTask:
    """A task assigned to a subagent."""

    task_id: str
    subagent_id: str
    query: str
    context: dict[str, Any] = field(default_factory=dict)
    config: SubagentConfig | None = None
    status: SubagentStatus = SubagentStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "subagent_id": self.subagent_id,
            "query": self.query[:100],
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Subagent:
    """Represents a spawned subagent."""

    id: str
    type: SubagentType
    status: SubagentStatus = SubagentStatus.PENDING
    current_task: SubagentTask | None = None
    completed_tasks: int = 0
    failed_tasks: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SpawnerStats:
    """Statistics for the subagent spawner."""

    total_spawned: int = 0
    active_subagents: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    avg_task_time: float = 0.0


class SubagentSpawner:
    """Manages spawning and coordination of research subagents.

    Features:
    - Dynamic subagent creation
    - Parallel task execution
    - Resource limiting
    - Result aggregation

    Usage:
        >>> spawner = SubagentSpawner(max_concurrent=5)
        >>> tasks = [
        ...     SubagentTask(task_id="1", subagent_id="", query="Search topic A"),
        ...     SubagentTask(task_id="2", subagent_id="", query="Search topic B"),
        ... ]
        >>> results = await spawner.spawn_and_execute(tasks, search_func)
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: float = 60.0,
        enable_retry: bool = True,
    ):
        """Initialize subagent spawner.

        Args:
            max_concurrent: Maximum concurrent subagents
            default_timeout: Default task timeout in seconds
            enable_retry: Whether to retry failed tasks
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.enable_retry = enable_retry

        self._subagents: dict[str, Subagent] = {}
        self._tasks: dict[str, SubagentTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = SpawnerStats()

        self.logger = logger.bind(component="SubagentSpawner")

    async def spawn_subagent(
        self,
        subagent_type: SubagentType,
        config: SubagentConfig | None = None,
    ) -> Subagent:
        """Spawn a new subagent.

        Args:
            subagent_type: Type of subagent to spawn
            config: Optional configuration

        Returns:
            Spawned Subagent instance
        """
        subagent_id = f"subagent_{subagent_type.value}_{uuid4().hex[:8]}"

        subagent = Subagent(
            id=subagent_id,
            type=subagent_type,
            status=SubagentStatus.PENDING,
        )

        self._subagents[subagent_id] = subagent
        self._stats.total_spawned += 1
        self._stats.active_subagents += 1

        self.logger.info(
            "subagent.spawned",
            subagent_id=subagent_id,
            type=subagent_type.value,
        )

        return subagent

    async def spawn_and_execute(
        self,
        tasks: list[SubagentTask],
        executor: Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]],
        subagent_type: SubagentType = SubagentType.WEB_SEARCHER,
    ) -> list[SubagentTask]:
        """Spawn subagents and execute tasks in parallel.

        Args:
            tasks: List of tasks to execute
            executor: Async function to execute each task
            subagent_type: Type of subagents to spawn

        Returns:
            List of completed tasks with results
        """
        self.logger.info(
            "spawner.execute_batch",
            task_count=len(tasks),
            subagent_type=subagent_type.value,
        )

        # Assign subagents to tasks
        for task in tasks:
            subagent = await self.spawn_subagent(subagent_type)
            task.subagent_id = subagent.id
            self._tasks[task.task_id] = task

        # Execute all tasks concurrently with semaphore
        async def execute_with_limit(task: SubagentTask) -> SubagentTask:
            async with self._semaphore:
                return await self._execute_task(task, executor)

        # Run tasks
        completed_tasks = await asyncio.gather(
            *[execute_with_limit(task) for task in tasks],
            return_exceptions=True,
        )

        # Process results
        results = []
        for i, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                tasks[i].status = SubagentStatus.FAILED
                tasks[i].error = str(result)
                self._stats.failed_tasks += 1
            elif isinstance(result, SubagentTask):
                results.append(result)
            else:
                results.append(tasks[i])

        return results

    async def _execute_task(
        self,
        task: SubagentTask,
        executor: Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]],
    ) -> SubagentTask:
        """Execute a single task with a subagent.

        Args:
            task: Task to execute
            executor: Async executor function

        Returns:
            Completed task with result
        """
        subagent = self._subagents.get(task.subagent_id)
        if subagent:
            subagent.status = SubagentStatus.RUNNING
            subagent.current_task = task

        task.status = SubagentStatus.RUNNING
        task.started_at = datetime.now(UTC)

        timeout = task.config.timeout_seconds if task.config else self.default_timeout

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                executor(task.query, task.context),
                timeout=timeout,
            )

            task.result = result
            task.status = SubagentStatus.COMPLETED
            task.completed_at = datetime.now(UTC)

            if subagent:
                subagent.completed_tasks += 1
                subagent.status = SubagentStatus.COMPLETED

            self._stats.completed_tasks += 1

            # Update timing stats
            duration = (task.completed_at - task.started_at).total_seconds()
            self._stats.total_execution_time += duration
            self._stats.avg_task_time = self._stats.total_execution_time / max(
                self._stats.completed_tasks, 1
            )

            self.logger.info(
                "task.completed",
                task_id=task.task_id,
                duration=duration,
            )

        except TimeoutError:
            task.status = SubagentStatus.TIMEOUT
            task.error = f"Task timed out after {timeout}s"
            task.completed_at = datetime.now(UTC)

            if subagent:
                subagent.failed_tasks += 1
                subagent.status = SubagentStatus.TIMEOUT

            self._stats.failed_tasks += 1

            self.logger.warning(
                "task.timeout",
                task_id=task.task_id,
                timeout=timeout,
            )

            # Retry if enabled
            if self.enable_retry and task.config:
                max_retries = task.config.max_retries
                retries = task.context.get("_retries", 0)

                if retries < max_retries:
                    task.context["_retries"] = retries + 1
                    task.status = SubagentStatus.PENDING
                    self.logger.info(
                        "task.retry",
                        task_id=task.task_id,
                        retry=retries + 1,
                    )
                    return await self._execute_task(task, executor)

        except Exception as e:
            task.status = SubagentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(UTC)

            if subagent:
                subagent.failed_tasks += 1
                subagent.status = SubagentStatus.FAILED

            self._stats.failed_tasks += 1

            self.logger.error(
                "task.failed",
                task_id=task.task_id,
                error=str(e),
            )

        finally:
            if subagent:
                subagent.current_task = None
                self._stats.active_subagents -= 1

        return task

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancelled, False if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status == SubagentStatus.RUNNING:
            task.status = SubagentStatus.CANCELLED
            task.completed_at = datetime.now(UTC)

            subagent = self._subagents.get(task.subagent_id)
            if subagent:
                subagent.status = SubagentStatus.CANCELLED
                self._stats.active_subagents -= 1

            self.logger.info("task.cancelled", task_id=task_id)
            return True

        return False

    async def cancel_all(self) -> int:
        """Cancel all running tasks.

        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        for task_id, task in self._tasks.items():
            if task.status == SubagentStatus.RUNNING:
                if await self.cancel_task(task_id):
                    cancelled += 1

        self.logger.info("spawner.cancel_all", cancelled=cancelled)
        return cancelled

    def get_stats(self) -> dict[str, Any]:
        """Get spawner statistics."""
        return {
            "total_spawned": self._stats.total_spawned,
            "active_subagents": self._stats.active_subagents,
            "completed_tasks": self._stats.completed_tasks,
            "failed_tasks": self._stats.failed_tasks,
            "success_rate": (
                self._stats.completed_tasks
                / max(self._stats.completed_tasks + self._stats.failed_tasks, 1)
            ),
            "avg_task_time": self._stats.avg_task_time,
            "total_execution_time": self._stats.total_execution_time,
        }

    def get_subagent(self, subagent_id: str) -> Subagent | None:
        """Get a subagent by ID."""
        return self._subagents.get(subagent_id)

    def get_task(self, task_id: str) -> SubagentTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_active_subagents(self) -> list[Subagent]:
        """List all active subagents."""
        return [sa for sa in self._subagents.values() if sa.status == SubagentStatus.RUNNING]

    def list_pending_tasks(self) -> list[SubagentTask]:
        """List all pending tasks."""
        return [t for t in self._tasks.values() if t.status == SubagentStatus.PENDING]


def create_subagent_spawner(
    max_concurrent: int = 5,
    default_timeout: float = 60.0,
) -> SubagentSpawner:
    """Create a subagent spawner with default configuration."""
    return SubagentSpawner(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout,
    )


__all__ = [
    "SpawnerStats",
    "Subagent",
    "SubagentConfig",
    "SubagentSpawner",
    "SubagentStatus",
    "SubagentTask",
    "SubagentType",
    "create_subagent_spawner",
]
