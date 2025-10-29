"""Retry logic for external service calls.

This module provides simple, user-friendly retry decorators built on top
of the comprehensive resilience.py module.

Usage:
    from core.retry import with_retry, with_llm_retry

    @with_llm_retry
    async def call_openai(prompt: str):
        # Your LLM call here
        pass

    @with_retry(max_attempts=5, exceptions=(DatabaseError,))
    async def database_operation():
        # Your database call here
        pass
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from tenacity import (before_sleep_log, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from core.exceptions import (DatabaseError, ExternalServiceError, LLMError,
                             LLMRateLimitError, LLMTimeoutError)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    *,
    max_attempts: int = 3,
    exceptions: tuple[type[Exception], ...] = (ExternalServiceError,),
    wait_min: float = 1,
    wait_max: float = 10,
    log_level: int = logging.WARNING,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        exceptions: Tuple of exception types to retry on
        wait_min: Minimum wait time between retries in seconds (default: 1)
        wait_max: Maximum wait time between retries in seconds (default: 10)
        log_level: Log level for retry messages (default: WARNING)

    Returns:
        Decorator function

    Example:
        @with_retry(max_attempts=5, exceptions=(ExternalServiceError,))
        async def call_external_api(url: str):
            response = await http_client.get(url)
            if response.status_code >= 500:
                raise ExternalServiceError(f"API error: {response.status_code}")
            return response.json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, log_level),
        reraise=True,
    )


def with_llm_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Specialized retry decorator for LLM API calls.

    Handles common LLM errors:
    - LLMError: General LLM errors
    - LLMRateLimitError: Rate limit exceeded (longer backoff)
    - LLMTimeoutError: Request timeout
    - ExternalServiceError: Generic external service errors

    Uses longer backoff times suitable for LLM APIs which often have
    rate limits and temporary outages.

    Args:
        func: Async function to decorate

    Returns:
        Decorated function with retry logic

    Example:
        @with_llm_retry
        async def analyze_with_gpt5(text: str) -> str:
            from core.llm_interface.openai_client import OpenAIClient
            client = OpenAIClient(model="gpt-5-mini")
            result = await client.acomplete(text)
            return result.get("output", "")
    """

    @with_retry(
        max_attempts=3,
        exceptions=(LLMError, LLMRateLimitError, LLMTimeoutError, ExternalServiceError),
        wait_min=2,
        wait_max=30,
        log_level=logging.WARNING,
    )
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


def with_database_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Specialized retry decorator for database operations.

    Handles database connection errors and temporary failures.

    Args:
        func: Async function to decorate

    Returns:
        Decorated function with retry logic

    Example:
        @with_database_retry
        async def fetch_user(user_id: str):
            async with db.session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalar_one()
    """

    @with_retry(
        max_attempts=3,
        exceptions=(DatabaseError, ExternalServiceError),
        wait_min=0.5,
        wait_max=5,
        log_level=logging.WARNING,
    )
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


# Legacy compatibility - import from resilience.py if needed
try:
    from core.resilience import (CircuitBreaker, RateLimiter, RetryConfig,
                                 Timeout, get_database_circuit_breaker,
                                 get_llm_circuit_breaker, retry_async)

    __all__ = [
        # Simple decorators
        "with_retry",
        "with_llm_retry",
        "with_database_retry",
        # Advanced patterns from resilience.py
        "retry_async",
        "CircuitBreaker",
        "RateLimiter",
        "Timeout",
        "RetryConfig",
        "get_llm_circuit_breaker",
        "get_database_circuit_breaker",
    ]
except ImportError:
    __all__ = [
        "with_database_retry",
        "with_llm_retry",
        "with_retry",
    ]
