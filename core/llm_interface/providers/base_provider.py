"""Abstract base class for LLM providers.

Defines the interface that all LLM providers must implement:
- Async completion with streaming support
- Token counting
- Cost tracking
- Rate limiting
- Error handling with provider-specific exceptions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class StreamEvent(str, Enum):
    """Stream event types."""

    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    USAGE = "usage"
    DONE = "done"
    ERROR = "error"


@dataclass(slots=True)
class TokenUsage:
    """Token usage tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass(slots=True)
class CostInfo:
    """Cost information for a request."""

    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.total_cost == 0.0:
            self.total_cost = self.input_cost + self.output_cost


@dataclass(slots=True)
class StreamChunk:
    """A chunk from a streaming response."""

    event: StreamEvent
    content: str = ""
    delta: str = ""
    usage: TokenUsage | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompletionRequest:
    """Standard completion request."""

    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompletionResponse:
    """Standard completion response."""

    content: str
    model: str
    provider: ProviderType
    usage: TokenUsage
    cost: CostInfo
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(
        self,
        message: str,
        provider: ProviderType | None = None,
        model: str | None = None,
        recoverable: bool = True,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        provider_str = f"[{self.provider.value}]" if self.provider else ""
        model_str = f"({self.model})" if self.model else ""
        return f"{provider_str}{model_str} {self.message}"


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded for provider."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: ProviderType | None = None,
        model: str | None = None,
        retry_after: float | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message,
            provider=provider,
            model=model,
            recoverable=True,
            retry_after=retry_after,
            **kwargs,
        )


class ProviderTimeoutError(ProviderError):
    """Request timeout for provider."""

    def __init__(
        self,
        message: str = "Request timed out",
        provider: ProviderType | None = None,
        model: str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if timeout:
            details["timeout_seconds"] = timeout
        super().__init__(
            message=message,
            provider=provider,
            model=model,
            recoverable=True,
            details=details,
            **kwargs,
        )


class ProviderAuthenticationError(ProviderError):
    """Authentication failed for provider."""

    def __init__(
        self,
        message: str = "Authentication failed",
        provider: ProviderType | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message,
            provider=provider,
            recoverable=False,
            **kwargs,
        )


class ProviderQuotaExceededError(ProviderError):
    """Quota exceeded for provider."""

    def __init__(
        self,
        message: str = "Quota exceeded",
        provider: ProviderType | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message,
            provider=provider,
            recoverable=False,
            **kwargs,
        )


class ProviderModelNotFoundError(ProviderError):
    """Model not found or unavailable."""

    def __init__(
        self,
        message: str = "Model not found",
        provider: ProviderType | None = None,
        model: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message,
            provider=provider,
            model=model,
            recoverable=False,
            **kwargs,
        )


class ProviderContentFilterError(ProviderError):
    """Content was filtered by provider."""

    def __init__(
        self,
        message: str = "Content filtered",
        provider: ProviderType | None = None,
        filter_reason: str | None = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if filter_reason:
            details["filter_reason"] = filter_reason
        super().__init__(
            message=message,
            provider=provider,
            recoverable=False,
            details=details,
            **kwargs,
        )


class TokenBucketRateLimiter:
    """Token bucket rate limiter for controlling request rates."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100000,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            tokens_per_minute: Maximum tokens per minute
        """
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute

        # Request bucket
        self._request_tokens = float(requests_per_minute)
        self._request_last_update = time.monotonic()
        self._request_rate = requests_per_minute / 60.0  # tokens per second

        # Token bucket
        self._token_tokens = float(tokens_per_minute)
        self._token_last_update = time.monotonic()
        self._token_rate = tokens_per_minute / 60.0  # tokens per second

        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> float:
        """Acquire permission to make a request.

        Args:
            estimated_tokens: Estimated tokens for the request

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        async with self._lock:
            current_time = time.monotonic()
            wait_time = 0.0

            # Refill request bucket
            elapsed = current_time - self._request_last_update
            self._request_tokens = min(
                float(self.requests_per_minute),
                self._request_tokens + elapsed * self._request_rate,
            )
            self._request_last_update = current_time

            # Check request limit
            if self._request_tokens < 1.0:
                wait_time = max(wait_time, (1.0 - self._request_tokens) / self._request_rate)

            # Refill token bucket
            elapsed = current_time - self._token_last_update
            self._token_tokens = min(
                float(self.tokens_per_minute),
                self._token_tokens + elapsed * self._token_rate,
            )
            self._token_last_update = current_time

            # Check token limit
            if self._token_tokens < estimated_tokens:
                wait_time = max(
                    wait_time,
                    (estimated_tokens - self._token_tokens) / self._token_rate,
                )

            if wait_time > 0:
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Update timestamps after wait
                current_time = time.monotonic()
                self._request_last_update = current_time
                self._token_last_update = current_time

            # Consume tokens
            self._request_tokens -= 1.0
            self._token_tokens -= estimated_tokens

            return wait_time

    def record_usage(self, actual_tokens: int, estimated_tokens: int) -> None:
        """Record actual token usage to adjust bucket.

        Args:
            actual_tokens: Actual tokens used
            estimated_tokens: Originally estimated tokens
        """
        # Adjust bucket based on actual vs estimated
        diff = estimated_tokens - actual_tokens
        if diff > 0:
            # Used fewer tokens than estimated, add back
            self._token_tokens = min(
                float(self.tokens_per_minute),
                self._token_tokens + diff,
            )


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers must implement:
    - complete(): Async completion
    - stream(): Async streaming completion
    - count_tokens(): Token counting
    - calculate_cost(): Cost calculation

    Features:
    - Rate limiting
    - Cost tracking
    - Token counting
    - Error handling with retries
    - Streaming support
    """

    # Provider identification
    provider_type: ProviderType
    model_id: str

    # Pricing (per 1K tokens)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    # Limits
    max_context_tokens: int = 100000
    max_output_tokens: int = 4096

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000

    def __init__(
        self,
        api_key: str,
        model_id: str | None = None,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        timeout: float = 120.0,
        **kwargs: Any,
    ):
        """Initialize provider.

        Args:
            api_key: API key for the provider
            model_id: Model identifier (uses default if not specified)
            requests_per_minute: Override default request rate limit
            tokens_per_minute: Override default token rate limit
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific options
        """
        self.api_key = api_key
        if model_id:
            self.model_id = model_id

        if requests_per_minute:
            self.requests_per_minute = requests_per_minute
        if tokens_per_minute:
            self.tokens_per_minute = tokens_per_minute

        self.timeout = timeout
        self.options = kwargs

        # Initialize rate limiter
        self._rate_limiter = TokenBucketRateLimiter(
            requests_per_minute=self.requests_per_minute,
            tokens_per_minute=self.tokens_per_minute,
        )

        # Cost tracking
        self._total_cost = 0.0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._request_count = 0

        # Initialize client (implemented by subclasses)
        self._client: Any = None
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider-specific client."""

    @abstractmethod
    async def _complete_impl(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Internal implementation of completion.

        Args:
            request: Completion request

        Returns:
            Completion response
        """

    @abstractmethod
    async def _stream_impl(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Internal implementation of streaming completion.

        Args:
            request: Completion request

        Yields:
            Stream chunks
        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """

    def calculate_cost(self, usage: TokenUsage) -> CostInfo:
        """Calculate cost for token usage.

        Args:
            usage: Token usage information

        Returns:
            Cost information
        """
        input_cost = (usage.input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (usage.output_tokens / 1000) * self.cost_per_1k_output
        return CostInfo(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            currency="USD",
        )

    async def complete(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Execute completion with rate limiting and cost tracking.

        Args:
            request: Completion request

        Returns:
            Completion response
        """
        # Estimate tokens for rate limiting
        estimated_input = self.count_tokens(request.prompt)
        if request.system_prompt:
            estimated_input += self.count_tokens(request.system_prompt)
        estimated_output = min(request.max_tokens, self.max_output_tokens)
        estimated_total = estimated_input + estimated_output

        # Apply rate limiting
        await self._rate_limiter.acquire(estimated_total)

        start_time = time.perf_counter()

        try:
            # Execute completion
            response = await self._complete_impl(request)

            # Calculate latency
            response.latency_ms = (time.perf_counter() - start_time) * 1000

            # Update rate limiter with actual usage
            actual_total = response.usage.total_tokens
            self._rate_limiter.record_usage(actual_total, estimated_total)

            # Track costs
            self._total_cost += response.cost.total_cost
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._request_count += 1

            logger.info(
                "LLM completion",
                extra={
                    "provider": self.provider_type.value,
                    "model": self.model_id,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "cost_usd": response.cost.total_cost,
                    "latency_ms": response.latency_ms,
                },
            )

            return response

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "LLM completion failed",
                extra={
                    "provider": self.provider_type.value,
                    "model": self.model_id,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
            )
            raise

    async def stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Execute streaming completion with rate limiting.

        Args:
            request: Completion request (stream will be set to True)

        Yields:
            Stream chunks
        """
        request.stream = True

        # Estimate tokens for rate limiting
        estimated_input = self.count_tokens(request.prompt)
        if request.system_prompt:
            estimated_input += self.count_tokens(request.system_prompt)
        estimated_output = min(request.max_tokens, self.max_output_tokens)
        estimated_total = estimated_input + estimated_output

        # Apply rate limiting
        await self._rate_limiter.acquire(estimated_total)

        start_time = time.perf_counter()
        total_output = ""

        try:
            async for chunk in self._stream_impl(request):
                if chunk.event == StreamEvent.TEXT_DELTA:
                    total_output += chunk.delta

                if chunk.event == StreamEvent.USAGE and chunk.usage:
                    # Update rate limiter with actual usage
                    actual_total = chunk.usage.total_tokens
                    self._rate_limiter.record_usage(actual_total, estimated_total)

                    # Track costs
                    cost = self.calculate_cost(chunk.usage)
                    self._total_cost += cost.total_cost
                    self._total_input_tokens += chunk.usage.input_tokens
                    self._total_output_tokens += chunk.usage.output_tokens
                    self._request_count += 1

                yield chunk

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "LLM stream completed",
                extra={
                    "provider": self.provider_type.value,
                    "model": self.model_id,
                    "output_length": len(total_output),
                    "latency_ms": latency_ms,
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "LLM stream failed",
                extra={
                    "provider": self.provider_type.value,
                    "model": self.model_id,
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
            )
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get provider statistics.

        Returns:
            Dictionary with usage statistics
        """
        return {
            "provider": self.provider_type.value,
            "model": self.model_id,
            "total_requests": self._request_count,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "total_cost_usd": self._total_cost,
            "avg_input_tokens": (
                self._total_input_tokens / self._request_count if self._request_count > 0 else 0
            ),
            "avg_output_tokens": (
                self._total_output_tokens / self._request_count if self._request_count > 0 else 0
            ),
            "avg_cost_usd": (
                self._total_cost / self._request_count if self._request_count > 0 else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset provider statistics."""
        self._total_cost = 0.0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._request_count = 0

    @property
    def name(self) -> str:
        """Get provider name."""
        return f"{self.provider_type.value}-{self.model_id}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_id!r})"
