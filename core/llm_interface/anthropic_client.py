from __future__ import annotations

import os
from typing import Any

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore


class AnthropicClient:
    """Anthropic Claude client with support for latest models (2025).

    Supported Models:
    - claude-sonnet-4-5-20250929: Highest intelligence, 200K context (1M beta)
    - claude-opus-4-1-20250805: Exceptional for complex specialized tasks
    - claude-3-5-haiku-20241022: Fast, cost-efficient model

    API Parameters:
    - temperature (float, 0.0-1.0): Randomness (default 1.0). Use 0.0 for analytical tasks, 1.0 for creative.
    - max_tokens (int): Maximum tokens to generate (required, up to 64,000 for Sonnet 4.5)
    - top_p (float, 0.0-1.0): Nucleus sampling (alternative to temperature)
    - top_k (int): Only sample from top K options (optional)
    - stop_sequences (list[str]): Sequences that stop generation

    Note: Use either temperature OR top_p, not both (Sonnet 4.5 enforces this).
    """

    # Latest model identifiers (2025)
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1-20250805"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"

    def __init__(
        self,
        model: str = CLAUDE_SONNET_4_5,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        top_p: float | None = None,
        top_k: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic client.

        Args:
            model: Model identifier (default: claude-sonnet-4-5-20250929)
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            temperature: Randomness (0.0-1.0, default 1.0)
            max_tokens: Max tokens to generate (default 4096)
            top_p: Nucleus sampling threshold (alternative to temperature)
            top_k: Top-K sampling (optional)
            **kwargs: Additional parameters
        """
        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic>=0.40.0"
            )

        self.model = model
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

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Async completion using Anthropic Messages API.

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
        api_params: dict[str, Any] = {
            "model": self.model,
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
