"""Concurrency Manager for Parallel Execution.

Manages concurrency limits and resource allocation:
- Dynamic concurrency adjustment
- Priority-based scheduling
- Rate limiting
- Queue management
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class QueuePriority(int, Enum):
    """Priority levels for task queue."""

    CRITICAL = 10
    HIGH = 7
    NORMAL = 5
    LOW = 3
    BACKGROUND = 1


@dataclass
class QueuedTask(Generic[T]):
    """Task in the execution queue."""

    id: str
    coro: Coroutine[Any, Any, T]
    priority: QueuePriority = QueuePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: QueuedTask) -> bool:
        """Compare by priority (higher first), then by creation time."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


@dataclass
class ExecutionResult(Generic[T]):
    """Result of task execution."""

    task_id: str
    success: bool
    result: T | None = None
    error: str | None = None
    execution_time: float = 0.0
    wait_time: float = 0.0


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrency management."""

    max_concurrent: int = 10
    min_concurrent: int = 1
    queue_size: int = 1000
    default_timeout: float = 300.0
    adaptive: bool = True
    cooldown_period: float = 1.0  # Seconds between scaling decisions


class AdaptiveSemaphore:
    """Semaphore with adaptive concurrency adjustment."""

    def __init__(
        self,
        initial: int = 10,
        min_value: int = 1,
        max_value: int = 50,
    ) -> None:
        self._value = initial
        self._min = min_value
        self._max = max_value
        self._semaphore = asyncio.Semaphore(initial)
        self._lock = asyncio.Lock()

        # Metrics for adaptive adjustment
        self._success_count = 0
        self._failure_count = 0
        self._latencies: list[float] = []

    @property
    def value(self) -> int:
        """Current concurrency limit."""
        return self._value

    async def acquire(self) -> None:
        """Acquire semaphore."""
        await self._semaphore.acquire()

    def release(self) -> None:
        """Release semaphore."""
        self._semaphore.release()

    async def __aenter__(self) -> AdaptiveSemaphore:
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.release()

    def record_success(self, latency: float) -> None:
        """Record successful execution."""
        self._success_count += 1
        self._latencies.append(latency)
        if len(self._latencies) > 100:
            self._latencies.pop(0)

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failure_count += 1

    async def adjust(self) -> int:
        """Adjust concurrency based on metrics.

        Returns:
            New concurrency value
        """
        async with self._lock:
            total = self._success_count + self._failure_count
            if total < 10:
                return self._value

            failure_rate = self._failure_count / total
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0

            new_value = self._value

            # Increase if doing well
            if failure_rate < 0.05 and avg_latency < 1.0:
                new_value = min(self._max, self._value + 1)
            # Decrease if struggling
            elif failure_rate > 0.2 or avg_latency > 5.0:
                new_value = max(self._min, self._value - 2)
            elif failure_rate > 0.1 or avg_latency > 3.0:
                new_value = max(self._min, self._value - 1)

            if new_value != self._value:
                logger.info(
                    "adaptive_semaphore.adjusted",
                    old=self._value,
                    new=new_value,
                    failure_rate=failure_rate,
                    avg_latency=avg_latency,
                )
                self._value = new_value
                # Recreate semaphore
                self._semaphore = asyncio.Semaphore(new_value)

            # Reset counters
            self._success_count = 0
            self._failure_count = 0

            return new_value


class ConcurrencyManager:
    """Manage concurrent task execution.

    Features:
    - Priority queue for tasks
    - Adaptive concurrency limits
    - Rate limiting
    - Execution metrics

    Usage:
        manager = ConcurrencyManager(max_concurrent=10)

        # Submit tasks
        result = await manager.submit(
            my_async_task(),
            priority=QueuePriority.HIGH,
        )

        # Or use context manager
        async with manager.acquire():
            # Do work with concurrency limit
            pass
    """

    def __init__(self, config: ConcurrencyConfig | None = None) -> None:
        self.config = config or ConcurrencyConfig()

        self._semaphore = AdaptiveSemaphore(
            initial=self.config.max_concurrent,
            min_value=self.config.min_concurrent,
            max_value=self.config.max_concurrent * 2,
        )

        self._queue: asyncio.PriorityQueue[QueuedTask] = asyncio.PriorityQueue(
            maxsize=self.config.queue_size
        )

        self._active_tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, ExecutionResult] = {}
        self._task_counter = 0
        self._running = False
        self._worker_task: asyncio.Task | None = None

        # Rate limiting
        self._last_adjustment = datetime.now(UTC)

    @property
    def active_count(self) -> int:
        """Number of currently active tasks."""
        return len(self._active_tasks)

    @property
    def queue_size(self) -> int:
        """Number of tasks in queue."""
        return self._queue.qsize()

    @property
    def concurrency_limit(self) -> int:
        """Current concurrency limit."""
        return self._semaphore.value

    async def acquire(self) -> AdaptiveSemaphore:
        """Acquire concurrency slot."""
        await self._semaphore.acquire()
        return self._semaphore

    def release(self) -> None:
        """Release concurrency slot."""
        self._semaphore.release()

    async def submit(
        self,
        coro: Coroutine[Any, Any, T],
        priority: QueuePriority = QueuePriority.NORMAL,
        timeout: float | None = None,
        task_id: str | None = None,
    ) -> ExecutionResult[T]:
        """Submit task for execution.

        Args:
            coro: Coroutine to execute
            priority: Task priority
            timeout: Execution timeout
            task_id: Optional task ID

        Returns:
            ExecutionResult
        """
        import time

        self._task_counter += 1
        task_id = task_id or f"task_{self._task_counter}"
        timeout = timeout or self.config.default_timeout
        submit_time = time.perf_counter()

        try:
            async with self._semaphore:
                wait_time = time.perf_counter() - submit_time
                start_time = time.perf_counter()

                try:
                    result = await asyncio.wait_for(coro, timeout=timeout)
                    execution_time = time.perf_counter() - start_time

                    self._semaphore.record_success(execution_time)

                    return ExecutionResult(
                        task_id=task_id,
                        success=True,
                        result=result,
                        execution_time=execution_time,
                        wait_time=wait_time,
                    )

                except TimeoutError:
                    self._semaphore.record_failure()
                    return ExecutionResult(
                        task_id=task_id,
                        success=False,
                        error=f"Timeout after {timeout}s",
                        execution_time=time.perf_counter() - start_time,
                        wait_time=wait_time,
                    )

                except Exception as e:
                    self._semaphore.record_failure()
                    return ExecutionResult(
                        task_id=task_id,
                        success=False,
                        error=str(e),
                        execution_time=time.perf_counter() - start_time,
                        wait_time=wait_time,
                    )

        finally:
            # Periodic adjustment
            await self._maybe_adjust()

    async def submit_batch(
        self,
        coros: list[Coroutine[Any, Any, T]],
        priority: QueuePriority = QueuePriority.NORMAL,
    ) -> list[ExecutionResult[T]]:
        """Submit batch of tasks."""
        tasks = [self.submit(coro, priority=priority) for coro in coros]
        return await asyncio.gather(*tasks)

    async def enqueue(
        self,
        coro: Coroutine[Any, Any, T],
        priority: QueuePriority = QueuePriority.NORMAL,
        timeout: float | None = None,
    ) -> str:
        """Add task to queue (non-blocking).

        Returns task ID for later retrieval.
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"

        task = QueuedTask(
            id=task_id,
            coro=coro,
            priority=priority,
            timeout=timeout,
        )

        await self._queue.put(task)
        return task_id

    async def get_result(self, task_id: str, timeout: float = 60.0) -> ExecutionResult | None:
        """Get result for a queued task."""
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            if task_id in self._results:
                return self._results.pop(task_id)
            await asyncio.sleep(0.1)

        return None

    def start_worker(self) -> None:
        """Start background worker for queue processing."""
        if self._running:
            return

        self._running = True
        task = asyncio.create_task(self._worker_loop())
        self._worker_task = task
        logger.info("concurrency_manager.worker_started")

    def stop_worker(self) -> None:
        """Stop background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        logger.info("concurrency_manager.worker_stopped")

    async def _worker_loop(self) -> None:
        """Background worker for queue processing."""
        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except TimeoutError:
                    continue

                # Execute task
                result = await self.submit(
                    task.coro,
                    priority=task.priority,
                    timeout=task.timeout,
                    task_id=task.id,
                )

                self._results[task.id] = result
                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("concurrency_manager.worker_error", error=str(e))

    async def _maybe_adjust(self) -> None:
        """Periodically adjust concurrency limits."""
        if not self.config.adaptive:
            return

        now = datetime.now(UTC)
        elapsed = (now - self._last_adjustment).total_seconds()

        if elapsed >= self.config.cooldown_period:
            await self._semaphore.adjust()
            self._last_adjustment = now

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "active_tasks": self.active_count,
            "queue_size": self.queue_size,
            "concurrency_limit": self.concurrency_limit,
            "total_submitted": self._task_counter,
            "adaptive": self.config.adaptive,
        }


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        rate: float = 10.0,  # Requests per second
        burst: int = 20,  # Maximum burst size
    ) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, returns wait time."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_update
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            self._last_update = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0

            # Calculate wait time
            wait_time = (tokens - self._tokens) / self.rate
            await asyncio.sleep(wait_time)

            self._tokens = 0
            self._last_update = asyncio.get_event_loop().time()
            return wait_time


# Convenience functions
def create_concurrency_manager(
    max_concurrent: int = 10,
    adaptive: bool = True,
) -> ConcurrencyManager:
    """Create configured concurrency manager."""
    config = ConcurrencyConfig(
        max_concurrent=max_concurrent,
        adaptive=adaptive,
    )
    return ConcurrencyManager(config=config)
