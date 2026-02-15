"""Resource Pool for LLM and API Calls.

Manages pooled resources with:
- Connection pooling
- Health checking
- Load balancing
- Resource lifecycle
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ResourceState(str, Enum):
    """State of a pooled resource."""

    AVAILABLE = "available"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    WARMING = "warming"
    CLOSED = "closed"


@dataclass
class ResourceStats:
    """Statistics for a resource."""

    total_uses: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_used: datetime | None = None
    last_error: datetime | None = None
    consecutive_errors: int = 0


@dataclass
class PooledResource(Generic[T]):
    """Wrapper for pooled resource."""

    id: str
    resource: T
    state: ResourceState = ResourceState.AVAILABLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    stats: ResourceStats = field(default_factory=ResourceStats)
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_used(self, latency_ms: float) -> None:
        """Record successful use."""
        self.stats.total_uses += 1
        self.stats.last_used = datetime.now(UTC)
        self.stats.consecutive_errors = 0
        # Running average
        n = self.stats.total_uses
        self.stats.avg_latency_ms = (self.stats.avg_latency_ms * (n - 1) + latency_ms) / n

    def mark_error(self) -> None:
        """Record error."""
        self.stats.total_errors += 1
        self.stats.last_error = datetime.now(UTC)
        self.stats.consecutive_errors += 1


class ResourceFactory(ABC, Generic[T]):
    """Factory for creating pooled resources."""

    @abstractmethod
    async def create(self) -> T:
        """Create a new resource."""

    @abstractmethod
    async def destroy(self, resource: T) -> None:
        """Destroy a resource."""

    @abstractmethod
    async def validate(self, resource: T) -> bool:
        """Validate resource health."""


@dataclass
class PoolConfig:
    """Configuration for resource pool."""

    min_size: int = 2
    max_size: int = 10
    max_idle_time: float = 300.0  # Seconds
    health_check_interval: float = 60.0
    acquire_timeout: float = 30.0
    max_consecutive_errors: int = 3


class ResourcePool(Generic[T]):
    """Generic resource pool with health checking.

    Features:
    - Automatic resource creation/destruction
    - Health checking
    - Load balancing
    - Statistics tracking

    Usage:
        # Create factory
        class MyFactory(ResourceFactory[MyClient]):
            async def create(self) -> MyClient:
                return MyClient()

            async def destroy(self, resource: MyClient) -> None:
                await resource.close()

            async def validate(self, resource: MyClient) -> bool:
                return await resource.ping()

        # Create pool
        pool = ResourcePool(MyFactory(), min_size=2, max_size=10)
        await pool.initialize()

        # Use resource
        async with pool.acquire() as resource:
            result = await resource.do_something()
    """

    def __init__(
        self,
        factory: ResourceFactory[T],
        config: PoolConfig | None = None,
    ) -> None:
        self.factory = factory
        self.config = config or PoolConfig()

        self._resources: dict[str, PooledResource[T]] = {}
        self._available: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._resource_counter = 0

        self._health_task: asyncio.Task | None = None
        self._initialized = False

    @property
    def size(self) -> int:
        """Current pool size."""
        return len(self._resources)

    @property
    def available_count(self) -> int:
        """Number of available resources."""
        return self._available.qsize()

    @property
    def in_use_count(self) -> int:
        """Number of resources in use."""
        return sum(1 for r in self._resources.values() if r.state == ResourceState.IN_USE)

    async def initialize(self) -> None:
        """Initialize pool with minimum resources."""
        if self._initialized:
            return

        async with self._lock:
            for _ in range(self.config.min_size):
                await self._create_resource()

        self._start_health_check()
        self._initialized = True

        logger.info(
            "resource_pool.initialized",
            min_size=self.config.min_size,
            current_size=self.size,
        )

    async def shutdown(self) -> None:
        """Shutdown pool and cleanup resources."""
        self._stop_health_check()

        async with self._lock:
            for resource in list(self._resources.values()):
                await self._destroy_resource(resource.id)

        self._initialized = False
        logger.info("resource_pool.shutdown")

    async def acquire(self) -> ResourceContext[T]:
        """Acquire a resource from the pool.

        Returns:
            ResourceContext for use with async with
        """
        if not self._initialized:
            await self.initialize()

        resource_id = await self._get_available_resource()
        return ResourceContext(self, resource_id)

    async def _get_available_resource(self) -> str:
        """Get an available resource, creating if needed."""
        try:
            # Try to get from available queue
            resource_id = await asyncio.wait_for(
                self._available.get(),
                timeout=0.1,
            )

            resource = self._resources.get(resource_id)
            if resource and resource.state == ResourceState.AVAILABLE:
                resource.state = ResourceState.IN_USE
                return resource_id

        except TimeoutError:
            pass

        # Need to create or wait
        async with self._lock:
            # Check if we can create more
            if self.size < self.config.max_size:
                resource_id = await self._create_resource()
                self._resources[resource_id].state = ResourceState.IN_USE
                return resource_id

        # Wait for available resource
        try:
            resource_id = await asyncio.wait_for(
                self._available.get(),
                timeout=self.config.acquire_timeout,
            )
            self._resources[resource_id].state = ResourceState.IN_USE
            return resource_id

        except TimeoutError:
            raise TimeoutError(f"Could not acquire resource within {self.config.acquire_timeout}s")

    async def release(self, resource_id: str, error: bool = False) -> None:
        """Release a resource back to the pool."""
        resource = self._resources.get(resource_id)
        if not resource:
            return

        if error:
            resource.mark_error()

            if resource.stats.consecutive_errors >= self.config.max_consecutive_errors:
                resource.state = ResourceState.UNHEALTHY
                logger.warning(
                    "resource_pool.resource_unhealthy",
                    resource_id=resource_id,
                    consecutive_errors=resource.stats.consecutive_errors,
                )
                replacement_task = asyncio.create_task(self._replace_unhealthy(resource_id))
                replacement_task.add_done_callback(
                    lambda t: t.exception() if not t.cancelled() else None
                )
                return

        resource.state = ResourceState.AVAILABLE
        await self._available.put(resource_id)

    async def _create_resource(self) -> str:
        """Create a new pooled resource."""
        self._resource_counter += 1
        resource_id = f"resource_{self._resource_counter}"

        try:
            raw_resource = await self.factory.create()

            self._resources[resource_id] = PooledResource(
                id=resource_id,
                resource=raw_resource,
                state=ResourceState.AVAILABLE,
            )

            await self._available.put(resource_id)

            logger.debug("resource_pool.created", resource_id=resource_id)
            return resource_id

        except Exception as e:
            logger.error("resource_pool.create_failed", error=str(e))
            raise

    async def _destroy_resource(self, resource_id: str) -> None:
        """Destroy a pooled resource."""
        resource = self._resources.pop(resource_id, None)
        if resource:
            try:
                await self.factory.destroy(resource.resource)
            except Exception as e:
                logger.warning(
                    "resource_pool.destroy_failed",
                    resource_id=resource_id,
                    error=str(e),
                )

    async def _replace_unhealthy(self, resource_id: str) -> None:
        """Replace an unhealthy resource."""
        await self._destroy_resource(resource_id)

        async with self._lock:
            if self.size < self.config.min_size:
                await self._create_resource()

    def _start_health_check(self) -> None:
        """Start background health checking."""
        if self._health_task is not None:
            return

        async def health_loop():
            while True:
                await asyncio.sleep(self.config.health_check_interval)
                await self._health_check()

        self._health_task = asyncio.create_task(health_loop())

    def _stop_health_check(self) -> None:
        """Stop background health checking."""
        if self._health_task:
            self._health_task.cancel()
            self._health_task = None

    async def _health_check(self) -> None:
        """Check health of all resources."""
        now = datetime.now(UTC)

        for resource in list(self._resources.values()):
            # Skip in-use resources
            if resource.state == ResourceState.IN_USE:
                continue

            # Check idle time
            if resource.stats.last_used:
                idle_time = (now - resource.stats.last_used).total_seconds()
                if idle_time > self.config.max_idle_time and self.size > self.config.min_size:
                    await self._destroy_resource(resource.id)
                    continue

            try:
                is_healthy = await self.factory.validate(resource.resource)
                if not is_healthy:
                    resource.state = ResourceState.UNHEALTHY
                    health_task = asyncio.create_task(self._replace_unhealthy(resource.id))
                    health_task.add_done_callback(
                        lambda t: t.exception() if not t.cancelled() else None
                    )
            except Exception:
                resource.state = ResourceState.UNHEALTHY
                health_task = asyncio.create_task(self._replace_unhealthy(resource.id))
                health_task.add_done_callback(
                    lambda t: t.exception() if not t.cancelled() else None
                )

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        total_uses = sum(r.stats.total_uses for r in self._resources.values())
        total_errors = sum(r.stats.total_errors for r in self._resources.values())

        return {
            "size": self.size,
            "available": self.available_count,
            "in_use": self.in_use_count,
            "total_uses": total_uses,
            "total_errors": total_errors,
            "error_rate": total_errors / max(1, total_uses),
            "min_size": self.config.min_size,
            "max_size": self.config.max_size,
        }


class ResourceContext(Generic[T]):
    """Context manager for pooled resource."""

    def __init__(self, pool: ResourcePool[T], resource_id: str) -> None:
        self._pool = pool
        self._resource_id = resource_id
        self._resource: T | None = None
        self._error = False
        self._start_time: float = 0

    async def __aenter__(self) -> T:
        import time

        self._start_time = time.perf_counter()

        pooled = self._pool._resources.get(self._resource_id)
        if pooled:
            self._resource = pooled.resource
            return pooled.resource

        raise RuntimeError("Resource not found")

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        import time

        if exc_type is not None:
            self._error = True

        # Record stats
        latency = (time.perf_counter() - self._start_time) * 1000
        pooled = self._pool._resources.get(self._resource_id)
        if pooled and not self._error:
            pooled.mark_used(latency)

        await self._pool.release(self._resource_id, error=self._error)


# LLM-specific resource factory
class LLMClientFactory(ResourceFactory[Any]):
    """Factory for LLM client resources."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-opus-4-5-20251101",
    ) -> None:
        self.provider = provider
        self.model = model

    async def create(self) -> Any:
        """Create LLM client."""
        if self.provider == "anthropic":
            import anthropic

            return anthropic.AsyncAnthropic()

        if self.provider == "openai":
            import openai

            return openai.AsyncOpenAI()

        if self.provider == "google":
            import google.generativeai as genai

            return genai

        raise ValueError(f"Unknown provider: {self.provider}")

    async def destroy(self, resource: Any) -> None:
        """Destroy LLM client."""
        if hasattr(resource, "close"):
            await resource.close()

    async def validate(self, resource: Any) -> bool:
        """Validate LLM client."""
        # Simple validation - just check if client exists
        return resource is not None


# Convenience functions
def create_llm_pool(
    provider: str = "anthropic",
    min_size: int = 2,
    max_size: int = 10,
) -> ResourcePool:
    """Create LLM client pool."""
    factory = LLMClientFactory(provider=provider)
    config = PoolConfig(min_size=min_size, max_size=max_size)
    return ResourcePool(factory, config)
