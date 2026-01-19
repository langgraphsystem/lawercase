from __future__ import annotations

import os
from typing import Any

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore

from core.resilience import CircuitBreaker


class AnthropicClient:
    """Anthropic Claude client with support for latest models (January 2026).

    Claude 4.5 Series (Latest - November 2025):
    - claude-opus-4-5-20251101: Industry leader in coding, agents, computer use ($5/$25 per 1M tokens)
    - claude-sonnet-4-5-20250929: Most capable for coding/agents, 200K context (1M beta) ($3/$15)
    - claude-haiku-4-5-20251001: Near-frontier coding, matches Sonnet 4 ($1/$5)

    Claude 4.1 Series (August 2025):
    - claude-opus-4-1-20250805: 74.5% SWE-bench, agentic tasks, reasoning

    Claude 4 Series (May 2025):
    - claude-sonnet-4-20250522: Default model for most users
    - claude-opus-4-20250522: Complex specialized tasks

    API Parameters:
    - temperature (float, 0.0-1.0): Randomness (default 1.0)
    - max_tokens (int): Maximum tokens (up to 64,000)
    - top_p (float): Nucleus sampling (alternative to temperature)
    - top_k (int): Top-K sampling

    Extended Thinking: Available on Opus 4.5, Sonnet 4.5, Haiku 4.5

    Sources:
    - https://platform.claude.com/docs/en/about-claude/models/overview
    - https://www.anthropic.com/news/claude-opus-4-5
    """

    # Claude 4.5 models (November 2025 - Latest)
    CLAUDE_OPUS_4_5 = "claude-opus-4-5-20251101"  # Latest flagship
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"

    # Claude 4.1 models (August 2025)
    CLAUDE_OPUS_4_1 = "claude-opus-4-1-20250805"

    # Claude 4 models (May 2025)
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"

    # Model sets for validation
    CLAUDE_4_5_MODELS = {
        CLAUDE_OPUS_4_5,
        CLAUDE_SONNET_4_5,
        CLAUDE_HAIKU_4_5,
    }

    CLAUDE_4_MODELS = {
        CLAUDE_OPUS_4_1,
        CLAUDE_SONNET_4,
        CLAUDE_OPUS_4,
    }

    ALL_MODELS = CLAUDE_4_5_MODELS | CLAUDE_4_MODELS

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        top_p: float | None = None,
        top_k: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic Claude client (January 2026).

        Args:
            model: Model identifier (default: claude-opus-4-5-20251124 - latest flagship)
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            temperature: Randomness (0.0-1.0, default 1.0)
            max_tokens: Max tokens to generate (default 4096, up to 64,000)
            top_p: Nucleus sampling threshold (alternative to temperature)
            top_k: Top-K sampling (optional)
            **kwargs: Additional parameters

        Recommended models:
            - CLAUDE_OPUS_4_5: Best quality, coding, agents ($5/$25 per 1M)
            - CLAUDE_SONNET_4_5: Great balance of quality/cost ($3/$15 per 1M)
            - CLAUDE_HAIKU_4_5: Fast, cost-efficient ($1/$5 per 1M)
        """
        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic>=0.40.0"
            )

        self.model = (model or os.getenv("ANTHROPIC_MODEL") or self.CLAUDE_SONNET_4_5).strip()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.kwargs = kwargs

        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter."
            )

        self.client = AsyncAnthropic(api_key=api_key)

        # Initialize circuit breaker for fault tolerance
        # Opens after 5 consecutive failures, closes after 3 successful calls in half-open state
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,  # Wait 60s before attempting recovery
            expected_exception=(Exception,),  # Catch all exceptions
            half_open_max_calls=3,
        )

        # LLMProvider interface compliance
        self.name = "anthropic"
        self.cost_per_token = 0.0  # Handled by CostOptimizer externally

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Async completion using Anthropic Messages API with circuit breaker protection.

        This method is wrapped with a circuit breaker that:
        - Opens after 5 consecutive failures
        - Waits 60 seconds before attempting recovery
        - Requires 3 successful calls to fully close

        Args:
            prompt: User prompt/message
            **params: Override default parameters (temperature, max_tokens, etc.)

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason

        Raises:
            ExternalServiceError: If circuit breaker is OPEN (service unavailable)
        """
        # Apply circuit breaker decorator to internal implementation
        protected_call = self._circuit_breaker(self._acomplete_impl)
        protected_call = self._circuit_breaker(self._acomplete_impl)
        return await protected_call(prompt, **params)

    async def ainvoke(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Alias for acomplete to satisfy LLMProvider interface."""
        # Adapter to match LLMRouter expectation
        result = await self.acomplete(prompt, **kwargs)
        # Map 'output' to 'text' as expected by LLMRouter
        return {
            "text": result.get("output", ""),
            "tokens_used": result.get("usage", {}).get("output_tokens", 0),
            "provider": self.name,
            "model": result.get("model"),
        }

    async def _acomplete_impl(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Internal implementation of async completion (circuit breaker protected).

        Args:
            prompt: User prompt/message
            **params: Override default parameters (temperature, max_tokens, etc.)

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason
        """
        # Merge default params with overrides
        temperature = params.get("temperature", self.temperature)
        max_tokens = params.get("max_tokens", self.max_tokens)
        top_p = params.get("top_p", self.top_p)
        top_k = params.get("top_k", self.top_k)
        stop_sequences = params.get("stop_sequences", self.kwargs.get("stop_sequences"))

        # Build API request parameters
        model = params.get("model")
        if not model:
            model = params.get("preferred_model", self.model)

        api_params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add temperature OR top_p (not both for Sonnet 4.5)
        if top_p is not None:
            api_params["top_p"] = top_p
        else:
            api_params["temperature"] = temperature

        if top_k is not None:
            api_params["top_k"] = top_k
        if stop_sequences:
            api_params["stop_sequences"] = stop_sequences

        # Call Anthropic API
        try:
            response = await self.client.messages.create(**api_params)

            # Extract output text
            output_text = ""
            if response.content and len(response.content) > 0:
                output_text = response.content[0].text

            return {
                "model": self.model,
                "prompt": prompt,
                "output": output_text,
                "provider": "anthropic",
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "finish_reason": response.stop_reason,
            }

        except Exception as e:
            return {
                "model": self.model,
                "prompt": prompt,
                "output": f"Error: {e!s}",
                "provider": "anthropic",
                "error": str(e),
            }
