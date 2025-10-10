"""Retry Handler for Validation Loops.

This module provides automatic retry logic with configurable strategies
for self-correcting agents.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import time
from typing import Any

from .confidence_scorer import ConfidenceMetrics, ConfidenceScorer


class RetryStrategy(str, Enum):
    """Retry strategies."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


@dataclass
class RetryConfig:
    """Configuration for retry handler."""

    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    min_confidence: float = 0.7  # Minimum acceptable confidence
    timeout: float | None = None  # Total timeout in seconds

    # Improvement strategies
    add_context_on_retry: bool = True
    increase_temperature: bool = False
    use_different_model: bool = False


class RetryHandler:
    """
    Handles retry logic for self-correcting agents.

    Features:
    - Multiple retry strategies
    - Confidence-based validation
    - Automatic parameter adjustment
    - Timeout management
    - Detailed retry metrics

    Example:
        >>> handler = RetryHandler()
        >>> result = await handler.retry_with_validation(
        ...     func=my_agent_function,
        ...     config=RetryConfig(max_retries=3),
        ...     validation_func=my_validator
        ... )
    """

    def __init__(self, confidence_scorer: ConfidenceScorer | None = None):
        """
        Initialize retry handler.

        Args:
            confidence_scorer: Optional custom confidence scorer
        """
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "avg_attempts": 0.0,
        }

    async def retry_with_validation(
        self,
        func: Callable,
        config: RetryConfig,
        validation_func: Callable[[Any], bool] | None = None,
        *args,
        **kwargs,
    ) -> tuple[Any, ConfidenceMetrics, dict[str, Any]]:
        """
        Execute function with automatic retry and validation.

        Args:
            func: Async function to execute
            config: Retry configuration
            validation_func: Optional custom validation function
            *args: Arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Tuple of (result, confidence_metrics, retry_info)

        Raises:
            TimeoutError: If total timeout is exceeded
            Exception: If max retries exceeded without success

        Example:
            >>> async def my_agent(query):
            ...     return "response"
            >>> result, metrics, info = await handler.retry_with_validation(
            ...     my_agent,
            ...     RetryConfig(max_retries=3),
            ...     query="test"
            ... )
        """
        start_time = time.time()
        attempts = 0
        last_error = None
        retry_info = {
            "attempts": 0,
            "total_duration": 0.0,
            "retries": [],
            "final_confidence": 0.0,
        }

        while attempts < config.max_retries:
            # Check timeout
            if config.timeout:
                elapsed = time.time() - start_time
                if elapsed > config.timeout:
                    raise TimeoutError(
                        f"Retry timeout exceeded: {elapsed:.2f}s > {config.timeout}s"
                    )

            attempts += 1
            attempt_start = time.time()

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Extract output text
                if isinstance(result, dict):
                    output = result.get("output", result.get("content", str(result)))
                else:
                    output = str(result)

                # Score confidence
                confidence_metrics = self.confidence_scorer.score_output(
                    output=output,
                    context=kwargs.get("context"),
                )

                # Record retry info
                attempt_duration = time.time() - attempt_start
                retry_info["retries"].append(
                    {
                        "attempt": attempts,
                        "confidence": confidence_metrics.overall_confidence,
                        "duration": attempt_duration,
                        "threshold": confidence_metrics.threshold.value,
                    }
                )

                # Custom validation
                if validation_func:
                    is_valid = validation_func(result)
                    if not is_valid:
                        last_error = ValueError("Custom validation failed")
                        if attempts < config.max_retries:
                            await self._apply_retry_strategy(config, attempts)
                            kwargs = self._adjust_parameters(kwargs, config, attempts)
                            continue
                        raise last_error

                # Check confidence threshold
                if confidence_metrics.overall_confidence >= config.min_confidence:
                    # Success!
                    retry_info["attempts"] = attempts
                    retry_info["total_duration"] = time.time() - start_time
                    retry_info["final_confidence"] = confidence_metrics.overall_confidence

                    self._update_stats(attempts, success=True)

                    return result, confidence_metrics, retry_info

                # Confidence too low, retry if possible
                if attempts < config.max_retries:
                    # Apply retry strategy
                    await self._apply_retry_strategy(config, attempts)

                    # Adjust parameters for next attempt
                    kwargs = self._adjust_parameters(kwargs, config, attempts)

                    last_error = ValueError(
                        f"Confidence {confidence_metrics.overall_confidence:.2f} "
                        f"below threshold {config.min_confidence}"
                    )
                else:
                    # Max retries exceeded
                    retry_info["attempts"] = attempts
                    retry_info["total_duration"] = time.time() - start_time
                    retry_info["final_confidence"] = confidence_metrics.overall_confidence

                    self._update_stats(attempts, success=False)

                    raise ValueError(
                        f"Max retries ({config.max_retries}) exceeded. "
                        f"Final confidence: {confidence_metrics.overall_confidence:.2f}"
                    )

            except Exception as e:
                last_error = e
                if attempts >= config.max_retries:
                    self._update_stats(attempts, success=False)
                    raise

                # Retry on exception
                await self._apply_retry_strategy(config, attempts)

        # Should not reach here, but just in case
        self._update_stats(attempts, success=False)
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected retry loop exit")

    async def _apply_retry_strategy(
        self,
        config: RetryConfig,
        attempt: int,
    ) -> None:
        """Apply retry delay based on strategy."""
        if config.strategy == RetryStrategy.NO_RETRY:
            return

        if config.strategy == RetryStrategy.IMMEDIATE:
            return  # No delay

        if config.strategy == RetryStrategy.FIXED_DELAY:
            await asyncio.sleep(config.base_delay)
            return

        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = min(config.base_delay * (2 ** (attempt - 1)), config.max_delay)
            await asyncio.sleep(delay)
            return

    def _adjust_parameters(
        self,
        kwargs: dict[str, Any],
        config: RetryConfig,
        attempt: int,
    ) -> dict[str, Any]:
        """Adjust function parameters for retry."""
        new_kwargs = kwargs.copy()

        # Add retry context
        if config.add_context_on_retry:
            if "context" not in new_kwargs:
                new_kwargs["context"] = {}

            new_kwargs["context"]["retry_attempt"] = attempt
            new_kwargs["context"]["retry_reason"] = "Improving quality"

        # Increase temperature for more diverse output
        if config.increase_temperature and "temperature" in new_kwargs:
            current_temp = new_kwargs.get("temperature", 0.7)
            new_kwargs["temperature"] = min(current_temp + 0.1, 1.0)

        # TODO: Model switching logic
        if config.use_different_model:
            # Would implement model fallback here
            pass

        return new_kwargs

    def _update_stats(self, attempts: int, success: bool) -> None:
        """Update retry statistics."""
        self.retry_stats["total_retries"] += attempts - 1

        if success:
            self.retry_stats["successful_retries"] += 1
        else:
            self.retry_stats["failed_retries"] += 1

        total_operations = (
            self.retry_stats["successful_retries"] + self.retry_stats["failed_retries"]
        )

        if total_operations > 0:
            self.retry_stats["avg_attempts"] = (
                self.retry_stats["total_retries"] + total_operations
            ) / total_operations

    def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        return self.retry_stats.copy()

    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self.retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "avg_attempts": 0.0,
        }


# Context manager for retry operations
class RetryContext:
    """
    Context manager for retry operations.

    Example:
        >>> async with RetryContext(handler, config) as retry:
        ...     result = await retry(my_function, arg1, arg2)
    """

    def __init__(self, handler: RetryHandler, config: RetryConfig):
        """Initialize retry context."""
        self.handler = handler
        self.config = config

    async def __aenter__(self):
        """Enter context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        return False  # Don't suppress exceptions

    async def __call__(self, func: Callable, *args, **kwargs):
        """Execute function with retry."""
        return await self.handler.retry_with_validation(func, self.config, *args, **kwargs)
