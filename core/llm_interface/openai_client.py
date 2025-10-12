from __future__ import annotations

import os
from typing import Any

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class OpenAIClient:
    """OpenAI client with support for latest models (2025).

    Supported Models:
    - gpt-4.1: Latest GPT-4 with major improvements in coding and instruction following (1M context)
    - gpt-4.1-mini: Cost-efficient GPT-4.1 variant
    - o3-mini: Reasoning model with exceptional STEM capabilities (low/medium/high reasoning effort)
    - o4-mini: Next-generation reasoning model
    - gpt-4o: Multimodal model with vision, audio support
    - gpt-4o-mini: Cost-efficient multimodal model

    API Parameters (Standard Models):
    - temperature (float, 0.0-2.0): Randomness (default 1.0)
    - max_tokens (int): Maximum tokens to generate (deprecated, use max_completion_tokens)
    - max_completion_tokens (int): Maximum tokens in completion (preferred over max_tokens)
    - top_p (float, 0.0-1.0): Nucleus sampling
    - frequency_penalty (float, -2.0-2.0): Reduce repetition (default 0)
    - presence_penalty (float, -2.0-2.0): Encourage topic diversity (default 0)
    - stop (str or list[str]): Stop sequences

    Reasoning Models (o3-mini, o4-mini):
    - max_completion_tokens: Only supported parameter (no temperature, top_p, penalties)
    - reasoning_effort: "low", "medium", or "high" (controls thinking depth)
    """

    # Latest model identifiers (2025)
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    # Reasoning models that don't support temperature/top_p
    REASONING_MODELS = {O3_MINI, O4_MINI}

    def __init__(
        self,
        model: str = GPT_4_1,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_completion_tokens: int = 4096,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        reasoning_effort: str = "medium",
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI client.

        Args:
            model: Model identifier (default: gpt-4.1)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            temperature: Randomness (0.0-2.0, default 1.0) [not for reasoning models]
            max_completion_tokens: Max tokens in completion (default 4096)
            top_p: Nucleus sampling (0.0-1.0, default 1.0) [not for reasoning models]
            frequency_penalty: Reduce repetition (-2.0 to 2.0, default 0) [not for reasoning models]
            presence_penalty: Encourage diversity (-2.0 to 2.0, default 0) [not for reasoning models]
            reasoning_effort: For reasoning models: "low", "medium", "high" (default "medium")
            **kwargs: Additional parameters
        """
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package not installed. Install with: pip install openai>=1.58.0"
            )

        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.reasoning_effort = reasoning_effort
        self.kwargs = kwargs

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter."
            )

        self.client = AsyncOpenAI(api_key=api_key)

    def _is_reasoning_model(self) -> bool:
        """Check if current model is a reasoning model (o-series)."""
        return self.model in self.REASONING_MODELS

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Async completion using OpenAI Chat Completions API.

        Args:
            prompt: User prompt/message
            **params: Override default parameters

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason
        """
        # Merge default params with overrides
        max_completion_tokens = params.get("max_completion_tokens", self.max_completion_tokens)
        temperature = params.get("temperature", self.temperature)
        top_p = params.get("top_p", self.top_p)
        frequency_penalty = params.get("frequency_penalty", self.frequency_penalty)
        presence_penalty = params.get("presence_penalty", self.presence_penalty)
        stop = params.get("stop", self.kwargs.get("stop"))
        reasoning_effort = params.get("reasoning_effort", self.reasoning_effort)

        # Build API request parameters
        api_params: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_completion_tokens,
        }

        # Reasoning models only support max_completion_tokens and reasoning_effort
        if self._is_reasoning_model():
            # Add reasoning effort for o-series models
            if reasoning_effort in {"low", "medium", "high"}:
                # Note: API might use different parameter name, check latest docs
                api_params["reasoning_effort"] = reasoning_effort
        else:
            # Standard models support temperature, top_p, penalties
            api_params["temperature"] = temperature
            api_params["top_p"] = top_p
            api_params["frequency_penalty"] = frequency_penalty
            api_params["presence_penalty"] = presence_penalty

        if stop:
            api_params["stop"] = stop

        # Call OpenAI API
        try:
            response = await self.client.chat.completions.create(**api_params)

            # Extract output text
            output_text = ""
            if response.choices and len(response.choices) > 0:
                output_text = response.choices[0].message.content or ""

            return {
                "model": self.model,
                "prompt": prompt,
                "output": output_text,
                "provider": "openai",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": (
                    response.choices[0].finish_reason if response.choices else "unknown"
                ),
            }

        except Exception as e:
            return {
                "model": self.model,
                "prompt": prompt,
                "output": f"Error: {e!s}",
                "provider": "openai",
                "error": str(e),
            }
