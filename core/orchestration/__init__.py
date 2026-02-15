"""Orchestration Package.

Provides workflow orchestration and parallel execution:
- ParallelResearchExecutor: Fan-out/fan-in research execution
- ParallelExecutor: Generic parallel task execution with dependencies
- ConcurrencyManager: Adaptive concurrency management
- ResourcePool: Connection pooling for LLM clients
- BackpressureHandler: Circuit breaker and graceful degradation

Usage:
    from core.orchestration import (
        ParallelResearchExecutor,
        parallel_research,
        ParallelExecutor,
        ParallelTask,
        TaskDependencyGraph,
        ConcurrencyManager,
        BackpressureHandler,
        CircuitBreaker,
    )

    # Parallel research
    executor = ParallelResearchExecutor(max_concurrent=5)
    result = await executor.execute(main_query, tasks, agent_fn)

    # Generic parallel execution with dependencies
    executor = ParallelExecutor(max_concurrent=5)
    executor.add_task(ParallelTask(
        id="task1",
        name="First Task",
        coro_factory=lambda: my_async_fn(),
    ))
    result = await executor.execute()

    # Concurrency management
    manager = ConcurrencyManager(max_concurrent=10)
    result = await manager.submit(my_coro())

    # Backpressure handling
    handler = BackpressureHandler()
    result = await handler.execute_with_retry(lambda: my_coro())
"""

from __future__ import annotations

from .backpressure_handler import (
    BackpressureConfig,
    BackpressureHandler,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    GracefulDegrader,
    LoadLevel,
    LoadSheddingError,
    RequestTracker,
    create_backpressure_handler,
    with_retry,
)
from .concurrency_manager import (
    AdaptiveSemaphore,
    ConcurrencyConfig,
    ConcurrencyManager,
    ExecutionResult,
    QueuedTask,
    QueuePriority,
    RateLimiter,
    create_concurrency_manager,
)
from .dynamic_router import (
    DEFAULT_AGENT_PROFILES,
    AgentCapability,
    AgentProfile,
    DynamicRouter,
    RoutingDecision,
    RoutingRequest,
    RoutingStrategy,
    create_default_router,
)
from .parallel_executor import (
    DefaultAggregator,
    DictAggregator,
    ExecutionPhase,
    ExecutionResult as ParallelExecutionResult,
    ExecutorConfig,
    FanOutFanIn,
    ParallelExecutor,
    ParallelTask,
    ResultAggregator,
    TaskDependencyGraph,
    TaskError,
    TaskResult as ParallelTaskResult,
    TaskState,
    create_parallel_executor as create_generic_parallel_executor,
    fan_out_fan_in,
    parallel_execute,
)
from .parallel_research import (
    ParallelResearchExecutor,
    ResearchPhase,
    ResearchPlan,
    ResearchPlanner,
    ResearchResult,
    ResearchTask,
    TaskResult,
    TaskStatus,
    create_parallel_executor,
    parallel_research,
)
from .resource_pool import (
    LLMClientFactory,
    PoolConfig,
    PooledResource,
    ResourceContext,
    ResourceFactory,
    ResourcePool,
    ResourceState,
    ResourceStats,
    create_llm_pool,
)

__all__ = [
    "DEFAULT_AGENT_PROFILES",
    "AdaptiveSemaphore",
    "AgentCapability",
    "AgentProfile",
    "BackpressureConfig",
    # Backpressure Handler
    "BackpressureHandler",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "ConcurrencyConfig",
    # Concurrency Manager
    "ConcurrencyManager",
    "DefaultAggregator",
    "DictAggregator",
    # Dynamic Router
    "DynamicRouter",
    "ExecutionPhase",
    "ExecutionResult",
    "ExecutorConfig",
    "FanOutFanIn",
    "GracefulDegrader",
    "LLMClientFactory",
    "LoadLevel",
    "LoadSheddingError",
    "ParallelExecutionResult",
    # Parallel Executor
    "ParallelExecutor",
    # Parallel Research
    "ParallelResearchExecutor",
    "ParallelTask",
    "ParallelTaskResult",
    "PoolConfig",
    "PooledResource",
    "QueuePriority",
    "QueuedTask",
    "RateLimiter",
    "RequestTracker",
    "ResearchPhase",
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchResult",
    "ResearchTask",
    "ResourceContext",
    "ResourceFactory",
    # Resource Pool
    "ResourcePool",
    "ResourceState",
    "ResourceStats",
    "ResultAggregator",
    "RoutingDecision",
    "RoutingRequest",
    "RoutingStrategy",
    "TaskDependencyGraph",
    "TaskError",
    "TaskResult",
    "TaskState",
    "TaskStatus",
    "create_backpressure_handler",
    "create_concurrency_manager",
    "create_default_router",
    "create_generic_parallel_executor",
    "create_llm_pool",
    "create_parallel_executor",
    "fan_out_fan_in",
    "parallel_execute",
    "parallel_research",
    "with_retry",
]
