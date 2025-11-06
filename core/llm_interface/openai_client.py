from __future__ import annotations

import os
from typing import Any

import structlog

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class OpenAIClient:
    """OpenAI client with support for GPT-5 and latest models (2025).

    GPT-5 Models (Released August 2025):
    - gpt-5: Best model for coding and agentic tasks (400K context: 272K input + 128K output)
      Pricing: $1.25/1M input, $10/1M output
    - gpt-5-mini: Balanced performance and cost (400K context)
      Pricing: $0.25/1M input, $2/1M output
    - gpt-5-nano: Most cost-efficient (400K context)
      Pricing: $0.05/1M input, $0.40/1M output

    GPT-5 Special Parameters:
    - verbosity: "low", "medium" (default), "high" - controls answer length
    - reasoning_effort: "minimal", "low", "medium" (default), "high" - controls thinking time
    - Supports custom tools with plaintext and context-free grammars
    - 90% cache discount for cached inputs

    Reasoning Models:
    - o3-mini: Exceptional STEM capabilities
    - o4-mini: Next-generation reasoning

    Multimodal Models:
    - (4o family deprecated in this project docs)

    API Parameters (GPT-5 Models):
    - temperature (float, 0.0-2.0): Randomness (default 1.0)
    - max_tokens (int): Maximum tokens in completion
    - verbosity (str): "low", "medium", "high" - answer length
    - reasoning_effort (str): "minimal", "low", "medium", "high" - thinking depth
    - top_p (float, 0.0-1.0): Nucleus sampling
    - frequency_penalty (float, -2.0-2.0): Reduce repetition
    - presence_penalty (float, -2.0-2.0): Encourage diversity
    """

    # GPT-5 model identifiers (2025 - Primary)
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"

    # Reasoning models
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"

    # Multimodal models intentionally omitted

    # GPT-5 models that support verbosity parameter
    GPT5_MODELS = {GPT_5, GPT_5_MINI, GPT_5_NANO, GPT_5_CHAT_LATEST}

    # Reasoning models that don't support temperature/top_p
    REASONING_MODELS = {O3_MINI, O4_MINI}

    def __init__(
        self,
        model: str = GPT_5,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        reasoning_effort: str = "medium",
        verbosity: str = "medium",
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI client with GPT-5 support.

        Args:
            model: Model identifier (default: gpt-5)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            temperature: Randomness (0.0-2.0, default 1.0) [not for reasoning models]
            max_tokens: Max tokens in completion (default 4096)
            top_p: Nucleus sampling (0.0-1.0, default 1.0) [not for reasoning models]
            frequency_penalty: Reduce repetition (-2.0 to 2.0, default 0) [not for reasoning models]
            presence_penalty: Encourage diversity (-2.0 to 2.0, default 0) [not for reasoning models]
            reasoning_effort: For GPT-5/reasoning: "minimal", "low", "medium", "high" (default "medium")
            verbosity: For GPT-5: "low", "medium", "high" (default "medium") - controls answer length
            **kwargs: Additional parameters
        """
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package not installed. Install with: pip install openai>=1.58.0"
            )

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.kwargs = kwargs

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter."
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.logger = structlog.get_logger(__name__)

    def _is_reasoning_model(self) -> bool:
        """Check if current model is a reasoning model (o-series)."""
        return self.model in self.REASONING_MODELS

    def _is_gpt5_model(self) -> bool:
        """Check if current model is a GPT-5 model."""
        return self.model in self.GPT5_MODELS

    @classmethod
    def _collect_text_fragments(cls, node: Any) -> list[str]:
        """Extract textual fragments from OpenAI message content structures."""

        fragments: list[str] = []

        if node is None:
            return fragments

        if isinstance(node, str):
            fragments.append(node)
            return fragments

        if isinstance(node, (tuple | list | set)):
            for item in node:
                fragments.extend(cls._collect_text_fragments(item))
            return fragments

        # Handle OpenAI SDK typing objects or dicts
        node_type = getattr(node, "type", None)
        if isinstance(node, dict):
            node_type = node.get("type", node_type)

        include_direct_text = node_type is None or node_type in {"text", "output_text"}

        text_attr = getattr(node, "text", None)
        if include_direct_text and isinstance(text_attr, str):
            fragments.append(text_attr)

        # Some SDK objects expose .value for text payloads
        value_attr = getattr(node, "value", None)
        if include_direct_text and isinstance(value_attr, str):
            fragments.append(value_attr)

        # Dict-like access (for tool call payloads or when converted to dict)
        if isinstance(node, dict):
            possible_text = node.get("text")
            if include_direct_text and isinstance(possible_text, str):
                fragments.append(possible_text)

            possible_content = node.get("content")
            if isinstance(possible_content, str):
                if include_direct_text:
                    fragments.append(possible_content)
            elif isinstance(possible_content, (list | tuple | set)):
                fragments.extend(cls._collect_text_fragments(possible_content))

        # Nested content attribute (ChatCompletionMessage.content, tool_result, etc.)
        content_attr = getattr(node, "content", None)
        if content_attr is not None and content_attr is not node:
            fragments.extend(cls._collect_text_fragments(content_attr))

        # Tool results may expose `result` or `arguments`
        result_attr = getattr(node, "result", None)
        if isinstance(result_attr, str):
            fragments.append(result_attr)
        elif isinstance(result_attr, (list | tuple | set)):
            fragments.extend(cls._collect_text_fragments(result_attr))

        arguments_attr = getattr(node, "arguments", None)
        if isinstance(arguments_attr, str):
            fragments.append(arguments_attr)
        elif isinstance(arguments_attr, (list | tuple | set)):
            fragments.extend(cls._collect_text_fragments(arguments_attr))

        return fragments

    @classmethod
    def _extract_output_text(cls, message: Any) -> str:
        """Convert OpenAI ChatCompletion message content to plain text."""

        if message is None:
            return ""

        content = getattr(message, "content", message)
        if isinstance(message, dict):
            content = message.get("content", content)

        fragments = cls._collect_text_fragments(content)
        normalized = [frag.strip() for frag in fragments if isinstance(frag, str) and frag.strip()]

        if not normalized and isinstance(message, dict):
            # Fallback: some responses may nest under direct text keys
            for key in ("text", "response", "output"):
                value = message.get(key)
                if isinstance(value, str) and value.strip():
                    normalized.append(value.strip())

        return "\n".join(normalized)

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Async completion using OpenAI Chat Completions API.

        Args:
            prompt: User prompt/message
            **params: Override default parameters

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason
        """
        # Merge default params with overrides
        max_tokens = params.get("max_tokens")
        if max_tokens is None:
            max_tokens = params.get("max_completion_tokens", self.max_tokens)
        temperature = params.get("temperature", self.temperature)
        top_p = params.get("top_p", self.top_p)
        frequency_penalty = params.get("frequency_penalty", self.frequency_penalty)
        presence_penalty = params.get("presence_penalty", self.presence_penalty)
        stop = params.get("stop", self.kwargs.get("stop"))
        reasoning_effort = params.get("reasoning_effort", self.reasoning_effort)
        verbosity = params.get("verbosity", self.verbosity)

        # Build API request parameters
        api_params: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # GPT-5 models support verbosity and reasoning_effort parameters
        if self._is_gpt5_model():
            # Add verbosity parameter for GPT-5
            if verbosity in {"low", "medium", "high"}:
                api_params["verbosity"] = verbosity

            # Add reasoning effort for GPT-5
            if reasoning_effort in {"minimal", "low", "medium", "high"}:
                api_params["reasoning_effort"] = reasoning_effort
            # GPT-5 chat-completions expects `max_completion_tokens`
            api_params["max_completion_tokens"] = max_tokens

        # Reasoning models (o-series) only support max_tokens and reasoning_effort
        elif self._is_reasoning_model():
            # Add reasoning effort for o-series models
            if reasoning_effort in {"low", "medium", "high"}:
                api_params["reasoning_effort"] = reasoning_effort
            # Keep output limit conservative for reasoning models
            api_params["max_tokens"] = max_tokens
        else:
            # Other models support standard parameters
            api_params["temperature"] = temperature
            api_params["top_p"] = top_p
            api_params["frequency_penalty"] = frequency_penalty
            api_params["presence_penalty"] = presence_penalty
            api_params["max_tokens"] = max_tokens

        if stop:
            api_params["stop"] = stop

        # Call OpenAI API
        try:
            self.logger.info(
                "llm.openai.request",
                model=self.model,
                prompt_length=len(prompt),
                is_gpt5=self._is_gpt5_model(),
                is_reasoning=self._is_reasoning_model(),
                params={k: v for k, v in api_params.items() if k != "messages"},
            )
            response = await self.client.chat.completions.create(**api_params)

            # Extract output text
            output_text = ""
            if response.choices and len(response.choices) > 0:
                output_text = self._extract_output_text(response.choices[0].message)

            result = {
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
            try:
                self.logger.info(
                    "llm.openai.response",
                    model=self.model,
                    finish_reason=result["finish_reason"],
                    usage=result["usage"],
                    output_length=len(output_text or ""),
                )
            except Exception:  # nosec B110 - logging is best-effort
                pass
            return result

        except Exception as e:
            self.logger.exception("llm.openai.error", model=self.model, error=str(e))
            return {
                "model": self.model,
                "prompt": prompt,
                "output": f"Error: {e!s}",
                "provider": "openai",
                "error": str(e),
            }
