"""Self-Correcting Mixin for Agents.

This module provides a mixin class that adds self-correction capabilities
to any agent through confidence scoring and automatic retry logic.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from core.validation import (RetryConfig, RetryHandler, get_confidence_scorer,
                             get_quality_tracker)


class SelfCorrectingMixin:
    """
    Mixin that adds self-correction capabilities to agents.

    Features:
    - Automatic confidence scoring
    - Retry logic with validation
    - Quality metrics tracking
    - Performance monitoring

    Usage:
        class MyAgent(SelfCorrectingMixin, BaseAgent):
            async def process(self, input_data):
                return await self.with_self_correction(
                    self._internal_process,
                    input_data,
                    min_confidence=0.8
                )

    Example:
        >>> class ResearchAgent(SelfCorrectingMixin):
        ...     async def research(self, query: str):
        ...         return await self.with_self_correction(
        ...             self._do_research,
        ...             query,
        ...             max_retries=3
        ...         )
    """

    def __init__(self, *args, **kwargs):
        """Initialize self-correcting mixin."""
        super().__init__(*args, **kwargs)

        # Initialize components
        self._confidence_scorer = get_confidence_scorer()
        self._quality_tracker = get_quality_tracker()
        self._retry_handler = RetryHandler(self._confidence_scorer)

        # Agent-specific config
        self._agent_name = f"{self.__class__.__name__}_{id(self)}"
        self._default_min_confidence = 0.7
        self._default_max_retries = 3

    async def with_self_correction(
        self,
        func: Callable,
        *args,
        min_confidence: float | None = None,
        max_retries: int | None = None,
        retry_strategy: str = "exponential_backoff",
        timeout: float | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Execute function with self-correction.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            min_confidence: Minimum acceptable confidence (default: 0.7)
            max_retries: Maximum retry attempts (default: 3)
            retry_strategy: Retry strategy (default: exponential_backoff)
            timeout: Total timeout in seconds
            context: Additional context for scoring
            **kwargs: Keyword arguments for func

        Returns:
            Dictionary with result, confidence metrics, and retry info

        Example:
            >>> result = await agent.with_self_correction(
            ...     agent._internal_process,
            ...     "input data",
            ...     min_confidence=0.8,
            ...     max_retries=5
            ... )
            >>> print(result["confidence"]["overall_confidence"])
            0.85
        """
        start_time = time.time()
        operation_id = f"{self._agent_name}_{int(time.time() * 1000)}"

        # Use defaults if not provided
        min_confidence = min_confidence or self._default_min_confidence
        max_retries = max_retries or self._default_max_retries

        # Create retry config
        from core.validation.retry_handler import RetryStrategy

        retry_config = RetryConfig(
            max_retries=max_retries,
            strategy=RetryStrategy(retry_strategy),
            min_confidence=min_confidence,
            timeout=timeout,
            add_context_on_retry=True,
        )

        # Add context to kwargs
        if context:
            if "context" in kwargs:
                kwargs["context"].update(context)
            else:
                kwargs["context"] = context

        try:
            # Execute with retry logic
            (
                result,
                confidence_metrics,
                retry_info,
            ) = await self._retry_handler.retry_with_validation(
                func,
                retry_config,
                *args,
                **kwargs,
            )

            # Record successful operation
            duration = time.time() - start_time
            self._quality_tracker.record_operation(
                agent_name=self._agent_name,
                confidence_score=confidence_metrics.overall_confidence,
                retry_count=retry_info["attempts"] - 1,  # Retries = attempts - 1
                duration_seconds=duration,
                success=True,
                operation_id=operation_id,
            )

            return {
                "success": True,
                "result": result,
                "confidence": confidence_metrics.to_dict(),
                "retry_info": retry_info,
                "duration_seconds": duration,
                "operation_id": operation_id,
            }

        except Exception as e:
            # Record failed operation
            duration = time.time() - start_time

            # Get last confidence if available
            last_confidence = 0.0
            if hasattr(e, "__context__"):
                last_confidence = getattr(e.__context__, "confidence", 0.0)

            self._quality_tracker.record_operation(
                agent_name=self._agent_name,
                confidence_score=last_confidence,
                retry_count=max_retries,
                duration_seconds=duration,
                success=False,
                operation_id=operation_id,
                error_type=type(e).__name__,
            )

            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": duration,
                "operation_id": operation_id,
            }

    def score_output(
        self,
        output: str,
        context: dict[str, Any] | None = None,
        expected_format: str | None = None,
    ) -> dict[str, Any]:
        """
        Score an output without retry logic.

        Args:
            output: Output text to score
            context: Context for scoring
            expected_format: Expected output format

        Returns:
            Confidence metrics dictionary

        Example:
            >>> metrics = agent.score_output(
            ...     "The answer is 42",
            ...     context={"query": "What is the answer?"}
            ... )
        """
        confidence_metrics = self._confidence_scorer.score_output(
            output=output,
            context=context,
            expected_format=expected_format,
        )

        return confidence_metrics.to_dict()

    def get_quality_stats(self) -> dict[str, Any]:
        """
        Get quality statistics for this agent.

        Returns:
            Dictionary with quality statistics

        Example:
            >>> stats = agent.get_quality_stats()
            >>> print(stats["avg_confidence"])
            0.85
        """
        return self._quality_tracker.get_agent_stats(self._agent_name)

    def get_quality_trend(self, window_size: int = 100) -> dict[str, Any]:
        """
        Get quality trend analysis for this agent.

        Args:
            window_size: Number of recent operations to analyze

        Returns:
            Dictionary with trend analysis

        Example:
            >>> trend = agent.get_quality_trend()
            >>> print(trend["confidence_trend"])
            'improving'
        """
        return self._quality_tracker.get_quality_trend(
            agent_name=self._agent_name,
            window_size=window_size,
        )

    def detect_performance_issues(self) -> list[dict[str, Any]]:
        """
        Detect performance issues for this agent.

        Returns:
            List of detected anomalies

        Example:
            >>> issues = agent.detect_performance_issues()
            >>> for issue in issues:
            ...     print(issue["reasons"])
        """
        return self._quality_tracker.detect_anomalies(agent_name=self._agent_name)

    async def validate_and_correct(
        self,
        output: str,
        context: dict[str, Any] | None = None,
        correction_func: Callable | None = None,
        max_corrections: int = 2,
    ) -> dict[str, Any]:
        """
        Validate output and apply corrections if needed.

        Args:
            output: Output to validate
            context: Context for validation
            correction_func: Optional custom correction function
            max_corrections: Maximum correction attempts

        Returns:
            Dictionary with validated/corrected output and metrics

        Example:
            >>> result = await agent.validate_and_correct(
            ...     "incomplete answer",
            ...     context={"query": "Explain AI"},
            ...     max_corrections=3
            ... )
        """
        # Score initial output
        metrics = self._confidence_scorer.score_output(output, context)

        # If confidence is good, return as is
        if metrics.overall_confidence >= self._default_min_confidence:
            return {
                "success": True,
                "output": output,
                "corrections_applied": 0,
                "confidence": metrics.to_dict(),
            }

        # Apply corrections
        current_output = output
        corrections_applied = 0

        for attempt in range(max_corrections):  # noqa: B007
            if correction_func:
                # Use custom correction function
                try:
                    corrected = await correction_func(current_output, metrics)
                    current_output = corrected
                    corrections_applied += 1
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Correction failed: {e}",
                        "output": current_output,
                        "corrections_applied": corrections_applied,
                    }

            # Re-score
            metrics = self._confidence_scorer.score_output(current_output, context)

            # Check if now acceptable
            if metrics.overall_confidence >= self._default_min_confidence:
                return {
                    "success": True,
                    "output": current_output,
                    "corrections_applied": corrections_applied,
                    "confidence": metrics.to_dict(),
                }

        # Max corrections reached
        return {
            "success": False,
            "output": current_output,
            "corrections_applied": corrections_applied,
            "confidence": metrics.to_dict(),
            "suggestions": metrics.suggestions,
        }

    def set_quality_thresholds(
        self,
        min_confidence: float = 0.7,
        max_retries: int = 3,
    ) -> None:
        """
        Set quality thresholds for this agent.

        Args:
            min_confidence: Minimum acceptable confidence (0-1)
            max_retries: Maximum retry attempts

        Example:
            >>> agent.set_quality_thresholds(min_confidence=0.85, max_retries=5)
        """
        self._default_min_confidence = min_confidence
        self._default_max_retries = max_retries


# Example agent using the mixin
class SelfCorrectingAgent(SelfCorrectingMixin):
    """
    Example self-correcting agent.

    Demonstrates how to use the SelfCorrectingMixin in a standalone agent.
    """

    async def process_query(
        self,
        query: str,
        min_confidence: float = 0.8,
    ) -> dict[str, Any]:
        """
        Process a query with self-correction.

        Args:
            query: Query to process
            min_confidence: Minimum acceptable confidence

        Returns:
            Result dictionary with confidence metrics
        """
        return await self.with_self_correction(
            self._internal_process,
            query,
            min_confidence=min_confidence,
            context={"query": query},
        )

    async def _internal_process(self, query: str, **kwargs) -> str:
        """
        Internal processing logic (to be overridden).

        Args:
            query: Query to process
            **kwargs: Additional context

        Returns:
            Processed result
        """
        # Placeholder implementation
        await asyncio.sleep(0.1)
        return f"Processed: {query}"
