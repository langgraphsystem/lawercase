"""Resilience patterns for production systems.

This module provides:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Bulkhead isolation
- Fallback strategies
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum
from functools import wraps
import logging
import time
from typing import Any, TypeVar

from core.exceptions import ExternalServiceError, LLMRateLimitError, LLMTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryStrategy(str, Enum):
    """Retry strategies."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Prevents cascading failures by temporarily disabling calls to failing services.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered

    Example:
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            expected_exception=ExternalServiceError
        )

        @breaker
        async def call_external_api():
            # Your API call here
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type[Exception] = Exception,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open)
            expected_exception: Exception type to count as failure
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        # Check if we should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")

        return self._state

    def _record_success(self) -> None:
        """Record successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                # Service recovered, close circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        else:
            self._failure_count = 0

    def _record_failure(self) -> None:
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery, reopen circuit
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened during recovery")
        elif self._failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            self._state = CircuitState.OPEN
            logger.error(f"Circuit breaker OPENED after {self._failure_count} failures")

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorator for async functions."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                raise ExternalServiceError(
                    message="Circuit breaker is OPEN - service unavailable",
                    details={
                        "failure_count": self._failure_count,
                        "retry_after": self.timeout,
                    },
                )

            try:
                result = await func(*args, **kwargs)
                self._record_success()
                return result

            except self.expected_exception as e:
                self._record_failure()
                logger.error(
                    f"Circuit breaker recorded failure: {e}",
                    extra={"state": self.state.value, "failures": self._failure_count},
                )
                raise

        return wrapper


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        retry_on: tuple[type[Exception], ...] = (Exception,),
        backoff_factor: float = 1.0,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to prevent thundering herd
            strategy: Retry strategy (exponential, linear, constant)
            retry_on: Tuple of exceptions to retry on
            backoff_factor: Multiplier for delay calculation
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.strategy = strategy
        self.retry_on = retry_on
        self.backoff_factor = backoff_factor

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        import random

        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.exponential_base**attempt) * self.backoff_factor
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay + (attempt * self.backoff_factor)
        else:  # CONSTANT
            delay = self.initial_delay

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> T:
    """Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries exhausted

    Example:
        result = await retry_async(
            my_async_func,
            arg1, arg2,
            config=RetryConfig(max_attempts=5, initial_delay=2.0)
        )
    """
    if config is None:
        config = RetryConfig()

    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry successful on attempt {attempt + 1}/{config.max_attempts}")
            return result

        except config.retry_on as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}",
                extra={"exception_type": type(e).__name__},
            )

            # Don't sleep after last attempt
            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        f"All {config.max_attempts} retry attempts exhausted",
        extra={"last_exception": str(last_exception)},
    )
    raise last_exception if last_exception else Exception("Retry failed")


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for async functions with retry logic.

    Example:
        @retry(max_attempts=5, initial_delay=2.0)
        async def fetch_data():
            # Your async function
            pass
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                strategy=strategy,
                retry_on=retry_on,
            )
            return await retry_async(func, *args, config=config, **kwargs)

        return wrapper

    return decorator


class Timeout:
    """Timeout context manager for async operations.

    Example:
        async with Timeout(seconds=30):
            result = await slow_operation()
    """

    def __init__(self, seconds: float, operation: str = "Operation"):
        """Initialize timeout.

        Args:
            seconds: Timeout in seconds
            operation: Description of operation (for error messages)
        """
        self.seconds = seconds
        self.operation = operation
        self._task: asyncio.Task | None = None

    async def __aenter__(self) -> Timeout:
        """Enter timeout context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit timeout context."""
        return False

    async def run(self, coro: Awaitable[T]) -> T:
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=self.seconds)
        except TimeoutError:
            raise LLMTimeoutError(
                message=f"{self.operation} timed out after {self.seconds} seconds",
                timeout=int(self.seconds),
            )


class RateLimiter:
    """Token bucket rate limiter.

    Example:
        limiter = RateLimiter(rate=10, per=60)  # 10 requests per minute

        async def my_function():
            async with limiter:
                # Your rate-limited code here
                pass
    """

    def __init__(self, rate: int, per: float = 60.0):
        """Initialize rate limiter.

        Args:
            rate: Number of tokens per time period
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = float(rate)
        self.last_check = time.time()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> RateLimiter:
        """Enter rate limiter context."""
        async with self._lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current

            # Add new tokens based on time passed
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = float(self.rate)

            # Check if we have tokens available
            if self.allowance < 1.0:
                # Calculate how long to wait
                wait_time = (1.0 - self.allowance) * (self.per / self.rate)
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit rate limiter context."""
        return False


class Bulkhead:
    """Bulkhead pattern for resource isolation.

    Limits concurrent execution to prevent resource exhaustion.

    Example:
        bulkhead = Bulkhead(max_concurrent=5)

        @bulkhead
        async def resource_intensive_operation():
            # Your operation here
            pass
    """

    def __init__(self, max_concurrent: int):
        """Initialize bulkhead.

        Args:
            max_concurrent: Maximum concurrent executions
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.active_count = 0

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorator for bulkhead isolation."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async with self.semaphore:
                self.active_count += 1
                try:
                    logger.debug(f"Bulkhead active: {self.active_count}/{self.max_concurrent}")
                    return await func(*args, **kwargs)
                finally:
                    self.active_count -= 1

        return wrapper


# Predefined configurations for common use cases
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL,
    retry_on=(LLMTimeoutError, LLMRateLimitError, ExternalServiceError),
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL,
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL,
)


# Global circuit breakers for common services
class CircuitBreakers:
    """Global circuit breaker registry."""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get(
        cls,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ) -> CircuitBreaker:
        """Get or create circuit breaker by name."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                timeout=timeout,
                expected_exception=expected_exception,
            )
        return cls._breakers[name]

    @classmethod
    def reset(cls, name: str | None = None) -> None:
        """Reset circuit breaker(s)."""
        if name:
            if name in cls._breakers:
                cls._breakers[name]._failure_count = 0
                cls._breakers[name]._state = CircuitState.CLOSED
        else:
            cls._breakers.clear()


# Convenience functions
def get_llm_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for LLM calls."""
    return CircuitBreakers.get(
        "llm",
        failure_threshold=5,
        timeout=60,
        expected_exception=ExternalServiceError,
    )


def get_database_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for database calls."""
    return CircuitBreakers.get(
        "database",
        failure_threshold=10,
        timeout=30,
        expected_exception=Exception,
    )
