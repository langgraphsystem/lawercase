"""Backpressure Handler for Graceful Degradation.

Manages system load with:
- Circuit breaker pattern
- Load shedding
- Graceful degradation
- Retry with backoff
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import random
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """State of circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class LoadLevel(str, Enum):
    """System load levels."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes to close from half-open
    timeout: float = 60.0  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state


@dataclass
class BackpressureConfig:
    """Configuration for backpressure handling."""

    # Load thresholds (0-1)
    elevated_threshold: float = 0.6
    high_threshold: float = 0.8
    critical_threshold: float = 0.95

    # Degradation settings
    enable_load_shedding: bool = True
    shed_probability_high: float = 0.3
    shed_probability_critical: float = 0.7

    # Retry settings
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0


class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    Features:
    - Automatic failure detection
    - Fast failure for known issues
    - Gradual recovery testing

    Usage:
        breaker = CircuitBreaker()

        try:
            result = await breaker.execute(my_async_fn())
        except CircuitOpenError:
            # Handle circuit open
            pass
    """

    def __init__(
        self,
        name: str = "default",
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self._state == CircuitState.CLOSED

    async def execute(
        self,
        coro: Coroutine[Any, Any, T],
    ) -> T:
        """Execute with circuit breaker protection.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of coroutine

        Raises:
            CircuitOpenError: If circuit is open
        """
        await self._check_state()

        if self._state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit {self.name} is open")

        try:
            result = await coro
            await self._record_success()
            return result

        except Exception as e:
            await self._record_failure()
            raise

    async def _check_state(self) -> None:
        """Check and possibly update circuit state."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time:
                    elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info(
                            "circuit_breaker.half_open",
                            name=self.name,
                        )

    async def _record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(
                        "circuit_breaker.closed",
                        name=self.name,
                    )
            else:
                self._failure_count = max(0, self._failure_count - 1)

    async def _record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(UTC)

            if self._state == CircuitState.HALF_OPEN:
                # Immediate re-open on half-open failure
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(
                    "circuit_breaker.reopened",
                    name=self.name,
                )

            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker.opened",
                    name=self.name,
                    failures=self._failure_count,
                )

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": (
                self._last_failure_time.isoformat() if self._last_failure_time else None
            ),
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""


class BackpressureHandler:
    """Handle system backpressure with graceful degradation.

    Features:
    - Load monitoring
    - Load shedding
    - Retry with exponential backoff
    - Circuit breakers per resource

    Usage:
        handler = BackpressureHandler()

        # Check load before processing
        if handler.should_shed():
            return fallback_response()

        # Execute with retry
        result = await handler.execute_with_retry(my_async_fn())

        # Use circuit breaker
        async with handler.circuit("api_calls"):
            result = await api_call()
    """

    def __init__(self, config: BackpressureConfig | None = None) -> None:
        self.config = config or BackpressureConfig()

        self._circuits: dict[str, CircuitBreaker] = {}
        self._current_load = 0.0
        self._request_count = 0
        self._shed_count = 0

        # Load tracking
        self._active_requests = 0
        self._max_concurrent = 100
        self._lock = asyncio.Lock()

    @property
    def load_level(self) -> LoadLevel:
        """Current load level."""
        if self._current_load >= self.config.critical_threshold:
            return LoadLevel.CRITICAL
        if self._current_load >= self.config.high_threshold:
            return LoadLevel.HIGH
        if self._current_load >= self.config.elevated_threshold:
            return LoadLevel.ELEVATED
        return LoadLevel.NORMAL

    def update_load(self, load: float) -> None:
        """Update current load metric (0-1)."""
        self._current_load = max(0.0, min(1.0, load))

    def should_shed(self) -> bool:
        """Check if request should be shed (rejected)."""
        if not self.config.enable_load_shedding:
            return False

        level = self.load_level

        if level == LoadLevel.CRITICAL:
            if random.random() < self.config.shed_probability_critical:
                self._shed_count += 1
                return True

        elif level == LoadLevel.HIGH:
            if random.random() < self.config.shed_probability_high:
                self._shed_count += 1
                return True

        return False

    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    async def execute_with_retry(
        self,
        coro_factory: Callable[[], Coroutine[Any, Any, T]],
        max_retries: int | None = None,
        circuit_name: str | None = None,
    ) -> T:
        """Execute with retry and backoff.

        Args:
            coro_factory: Factory function that creates the coroutine
            max_retries: Maximum retry attempts
            circuit_name: Optional circuit breaker to use

        Returns:
            Result of successful execution

        Raises:
            Exception: If all retries fail
        """
        max_retries = max_retries or self.config.max_retries
        circuit = self.get_circuit(circuit_name) if circuit_name else None

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                # Check load shedding
                if attempt > 0 and self.should_shed():
                    raise LoadSheddingError("Request shed due to high load")

                # Create fresh coroutine for each attempt
                coro = coro_factory()

                if circuit:
                    result = await circuit.execute(coro)
                else:
                    result = await coro

                return result

            except CircuitOpenError:
                raise

            except LoadSheddingError:
                raise

            except Exception as e:
                last_error = e

                if attempt < max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        "backpressure.retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

        raise last_error or RuntimeError("All retries failed")

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with jitter."""
        delay = self.config.base_delay * (self.config.exponential_base**attempt)
        delay = min(delay, self.config.max_delay)
        # Add jitter (0.5-1.5x)
        jitter = 0.5 + random.random()
        return delay * jitter

    async def track_request(self) -> RequestTracker:
        """Track a request for load calculation."""
        return RequestTracker(self)

    def get_stats(self) -> dict[str, Any]:
        """Get backpressure statistics."""
        return {
            "load_level": self.load_level.value,
            "current_load": self._current_load,
            "active_requests": self._active_requests,
            "total_requests": self._request_count,
            "shed_requests": self._shed_count,
            "shed_rate": self._shed_count / max(1, self._request_count),
            "circuits": {name: circuit.get_stats() for name, circuit in self._circuits.items()},
        }


class RequestTracker:
    """Context manager for tracking requests."""

    def __init__(self, handler: BackpressureHandler) -> None:
        self._handler = handler

    async def __aenter__(self) -> RequestTracker:
        async with self._handler._lock:
            self._handler._active_requests += 1
            self._handler._request_count += 1
            # Update load based on active requests
            self._handler._current_load = (
                self._handler._active_requests / self._handler._max_concurrent
            )
        return self

    async def __aexit__(self, *args: Any) -> None:
        async with self._handler._lock:
            self._handler._active_requests -= 1
            self._handler._current_load = (
                self._handler._active_requests / self._handler._max_concurrent
            )


class LoadSheddingError(Exception):
    """Raised when request is shed due to high load."""


class GracefulDegrader:
    """Manage graceful degradation strategies.

    Provides fallback responses when services are unavailable.
    """

    def __init__(self) -> None:
        self._fallbacks: dict[str, Callable[..., Any]] = {}
        self._degradation_level = 0

    def register_fallback(
        self,
        name: str,
        fallback: Callable[..., Any],
    ) -> None:
        """Register fallback for a service."""
        self._fallbacks[name] = fallback

    async def execute_with_fallback(
        self,
        name: str,
        primary: Coroutine[Any, Any, T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute with fallback on failure."""
        try:
            return await primary
        except Exception as e:
            logger.warning(
                "graceful_degrader.fallback",
                name=name,
                error=str(e),
            )

            fallback = self._fallbacks.get(name)
            if fallback:
                result = fallback(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result

            raise

    def set_degradation_level(self, level: int) -> None:
        """Set system degradation level (0 = normal)."""
        self._degradation_level = level

    @property
    def degradation_level(self) -> int:
        """Current degradation level."""
        return self._degradation_level


# Convenience functions
def create_backpressure_handler(
    enable_load_shedding: bool = True,
    max_retries: int = 3,
) -> BackpressureHandler:
    """Create configured backpressure handler."""
    config = BackpressureConfig(
        enable_load_shedding=enable_load_shedding,
        max_retries=max_retries,
    )
    return BackpressureHandler(config=config)


async def with_retry(
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
) -> T:
    """Execute with retry (convenience function)."""
    handler = BackpressureHandler()
    return await handler.execute_with_retry(coro_factory, max_retries=max_retries)
