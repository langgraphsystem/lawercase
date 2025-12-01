from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

try:
    from openai import APITimeoutError, AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore
    APITimeoutError = None  # type: ignore

from core.resilience import CircuitBreaker


class OpenAIClient:
    """OpenAI client with support for GPT-5.1 and latest models (November 2025).

    GPT-5.1 Models (Released November 12, 2025):
    - gpt-5.1-chat-latest: GPT-5.1 Instant with adaptive reasoning (NEW DEFAULT)
      Context: 272K input, 128K output (400K total)
      Pricing: $1.25/1M input, $10/1M output, $0.125/1M cached
    - gpt-5.1: GPT-5.1 Thinking (advanced reasoning)
      Context: 272K input, 128K output (400K total)
    - gpt-5.1-codex: Extended programming workloads
    - gpt-5.1-codex-mini: Lightweight coding model
    - gpt-5-mini: Balanced performance and cost
      Pricing: $0.25/1M input, $2/1M output
    - gpt-5-nano: Most cost-efficient
      Pricing: $0.05/1M input, $0.40/1M output

    Legacy GPT-5 Models (August 2025):
    - gpt-5-2025-08-07: Original GPT-5 stable version
    - gpt-5-chat-latest: Auto-updates to latest (currently gpt-5.1-chat-latest)

    GPT-5.1 Features:
    - Adaptive Reasoning: Dynamically adjusts thinking time based on task complexity
    - reasoning_effort: "none", "minimal", "low", "medium" (default), "high"
      Use "none" for latency-sensitive tasks (no reasoning overhead)
    - Extended Prompt Caching: 24h retention with prompt_cache_retention='24h'
    - New Developer Tools: apply_patch (code editing), shell (shell commands)
    - Function calling with tools parameter (March 2025 API)
    - 90% cache discount for repeated input tokens
    - Multimodal Input: Text, images, and files
    - Web Search: Built-in web search ($10/K searches)
    - Structured Outputs: JSON Schema support for response_format

    Reasoning Models:
    - o3-mini: Exceptional STEM capabilities
    - o4-mini: Next-generation reasoning

    API Parameters (GPT-5.1 Models):
    - temperature (float, 0.0-2.0): Randomness (default 1.0)
    - max_tokens (int): Maximum tokens in completion
    - verbosity (str): "low", "medium", "high" - answer length
    - reasoning_effort (str): "none", "minimal", "low", "medium", "high"
    - prompt_cache_retention (str): "24h" for extended caching
    - tools (list): Function calling tools (March 2025)
    - tool_choice (str|dict): "auto", "required", or specific tool
    - top_p (float, 0.0-1.0): Nucleus sampling
    - frequency_penalty (float, -2.0-2.0): Reduce repetition
    - presence_penalty (float, -2.0-2.0): Encourage diversity
    """

    # GPT-5.1 model identifiers (November 2025 - PRIMARY)
    GPT_5_1_INSTANT = "gpt-5.1-chat-latest"  # NEW DEFAULT
    GPT_5_1_THINKING = "gpt-5.1"
    GPT_5_1_CODEX = "gpt-5.1-codex"
    GPT_5_1_CODEX_MINI = "gpt-5.1-codex-mini"

    # GPT-5 model identifiers (August 2025 - Legacy)
    GPT_5 = "gpt-5-2025-08-07"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"  # Redirects to gpt-5.1-chat-latest

    # Reasoning models
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"

    # GPT-5.1 models that support adaptive reasoning
    GPT5_1_MODELS = {
        GPT_5_1_INSTANT,
        GPT_5_1_THINKING,
        GPT_5_1_CODEX,
        GPT_5_1_CODEX_MINI,
        "gpt-5.1",
        "gpt-5.1-chat-latest",
    }

    # All GPT-5 family models that support verbosity parameter
    GPT5_MODELS = GPT5_1_MODELS | {
        GPT_5,
        GPT_5_MINI,
        GPT_5_NANO,
        GPT_5_CHAT_LATEST,
        "gpt-5",
        "gpt-5-2025-08-07",
    }

    # Reasoning models that don't support temperature/top_p
    REASONING_MODELS = {O3_MINI, O4_MINI}

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        reasoning_effort: str = "medium",
        verbosity: str = "medium",
        prompt_cache_retention: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI client with GPT-5.1 support (November 2025).

        Args:
            model: Model identifier (default: gpt-5.1-chat-latest)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            temperature: Randomness (0.0-2.0, default 1.0) [not for reasoning models]
            max_tokens: Max tokens in completion (default 4096)
            top_p: Nucleus sampling (0.0-1.0, default 1.0) [not for reasoning models]
            frequency_penalty: Reduce repetition (-2.0 to 2.0, default 0) [not for reasoning models]
            presence_penalty: Encourage diversity (-2.0 to 2.0, default 0) [not for reasoning models]
            reasoning_effort: For GPT-5.1: "none", "minimal", "low", "medium", "high" (default "medium")
                Use "none" for latency-sensitive tasks without reasoning overhead
            verbosity: For GPT-5.1: "low", "medium", "high" (default "medium") - controls answer length
            prompt_cache_retention: Extended caching, e.g. "24h" (default: None)
            tools: List of function calling tools (March 2025 API format)
            tool_choice: "auto", "required", or specific tool dict
            **kwargs: Additional parameters
        """
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package not installed. Install with: pip install openai>=1.58.0"
            )

        # Default to GPT-5.1 Instant (November 2025)
        normalized_model = (model or "").strip()
        if not normalized_model:
            normalized_model = self.GPT_5_1_INSTANT
        self.model = normalized_model
        self._model_lower = normalized_model.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.prompt_cache_retention = prompt_cache_retention
        self.tools = tools
        self.tool_choice = tool_choice
        self.kwargs = kwargs

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter."
            )

        # Set timeout using httpx.Timeout for granular control (default: 60s total)
        # read: timeout for reading response, write: timeout for writing request
        # connect: timeout for connection, total: overall timeout
        timeout_seconds = float(os.getenv("OPENAI_TIMEOUT", "60.0"))
        timeout = httpx.Timeout(
            timeout=timeout_seconds,  # Total timeout
            read=timeout_seconds,  # Read timeout
            write=10.0,  # Write timeout
            connect=5.0,  # Connection timeout
        )
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.logger = structlog.get_logger(__name__)

        # Initialize circuit breaker for fault tolerance
        # Opens after 5 consecutive failures, closes after 3 successful calls in half-open state
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,  # Wait 60s before attempting recovery
            expected_exception=(Exception,),  # Catch all exceptions
            half_open_max_calls=3,
        )

        self.logger.info(
            "openai.client.initialized",
            model=self.model,
            timeout_total=timeout_seconds,
            timeout_read=timeout_seconds,
            timeout_write=10.0,
            timeout_connect=5.0,
            circuit_breaker_enabled=True,
            tools_enabled=bool(self.tools),
            prompt_cache_retention=self.prompt_cache_retention,
            reasoning_effort=self.reasoning_effort,
        )

    def _is_reasoning_model(self) -> bool:
        """Check if current model is a reasoning model (o-series)."""
        return self._model_lower in self.REASONING_MODELS

    def _is_gpt5_1_model(self) -> bool:
        """Check if current model is a GPT-5.1 model (November 2025)."""
        lower = getattr(self, "_model_lower", self.model.lower())
        return lower in self.GPT5_1_MODELS or "gpt-5.1" in lower or "gpt5.1" in lower

    def _is_gpt5_model(self) -> bool:
        """Check if current model is a GPT-5 family model."""
        lower = getattr(self, "_model_lower", self.model.lower())
        return lower in self.GPT5_MODELS or lower.startswith("gpt-5")

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

        def _extend(value: Any, allow_direct: bool = True) -> None:
            if isinstance(value, str):
                if allow_direct and value:
                    fragments.append(value)
            elif isinstance(value, dict):
                fragments.extend(cls._collect_text_fragments(value))
            elif isinstance(value, (list | tuple | set)):
                for element in value:
                    fragments.extend(cls._collect_text_fragments(element))
            elif value is not None:
                for attr in ("model_dump", "to_dict", "dict"):
                    func = getattr(value, attr, None)
                    if callable(func):
                        dumped = None
                        try:
                            dumped = func()
                        except Exception:
                            dumped = None
                        if isinstance(dumped, dict):
                            fragments.extend(cls._collect_text_fragments(dumped))
                            break
                        if isinstance(dumped, (list | tuple | set)):
                            for element in dumped:
                                fragments.extend(cls._collect_text_fragments(element))
                            break
                        break

        # Handle OpenAI SDK typing objects or dicts
        node_type = getattr(node, "type", None)
        if isinstance(node, dict):
            node_type = node.get("type", node_type)

        include_direct_text = node_type is None or node_type in {"text", "output_text"}

        text_attr = getattr(node, "text", None)
        _extend(text_attr, allow_direct=include_direct_text)

        # Some SDK objects expose .value for text payloads
        value_attr = getattr(node, "value", None)
        _extend(value_attr, allow_direct=include_direct_text)

        output_text_attr = getattr(node, "output_text", None)
        if output_text_attr is not None:
            _extend(output_text_attr, allow_direct=include_direct_text)

        # Dict-like access (for tool call payloads or when converted to dict)
        if isinstance(node, dict):
            possible_text = node.get("text")
            if possible_text is not None:
                _extend(possible_text, allow_direct=include_direct_text)

            possible_content = node.get("content")
            if possible_content is not None:
                _extend(
                    possible_content,
                    allow_direct=include_direct_text,
                )

            output_text_entry = node.get("output_text")
            if output_text_entry is not None:
                _extend(output_text_entry, allow_direct=include_direct_text)

        # Nested content attribute (ChatCompletionMessage.content, tool_result, etc.)
        content_attr = getattr(node, "content", None)
        if content_attr is not None and content_attr is not node:
            fragments.extend(cls._collect_text_fragments(content_attr))

        # Tool results may expose `result`, `arguments`, or `value`
        result_attr = getattr(node, "result", None)
        _extend(result_attr)

        arguments_attr = getattr(node, "arguments", None)
        _extend(arguments_attr)

        if isinstance(node, dict):
            value_entry = node.get("value")
            if value_entry is not None:
                _extend(value_entry, allow_direct=include_direct_text)
            annotations = node.get("annotations")
            if annotations is not None:
                _extend(annotations, allow_direct=False)

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
        """Async completion using OpenAI Chat Completions API with circuit breaker protection.

        This method is wrapped with a circuit breaker that:
        - Opens after 5 consecutive failures
        - Waits 60 seconds before attempting recovery
        - Requires 3 successful calls to fully close

        Args:
            prompt: User prompt/message
            **params: Override default parameters

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason

        Raises:
            ExternalServiceError: If circuit breaker is OPEN (service unavailable)
        """
        # Apply circuit breaker decorator to internal implementation
        protected_call = self._circuit_breaker(self._acomplete_impl)
        return await protected_call(prompt, **params)

    async def _acomplete_impl(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Internal implementation of async completion (circuit breaker protected).

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

            # Add reasoning effort for GPT-5/GPT-5.1
            # GPT-5.1 adds "none" for latency-sensitive tasks (no reasoning overhead)
            if reasoning_effort in {"none", "minimal", "low", "medium", "high"}:
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

        # Add function calling tools if provided (March 2025 API)
        tools = params.get("tools", self.tools)
        tool_choice = params.get("tool_choice", self.tool_choice)
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = tool_choice
            self.logger.debug(
                "llm.openai.tools",
                model=self.model,
                num_tools=len(tools),
                tool_choice=tool_choice,
            )

        # Add extended prompt caching if specified (GPT-5.1 feature)
        prompt_cache_retention = params.get("prompt_cache_retention", self.prompt_cache_retention)
        if prompt_cache_retention and self._is_gpt5_1_model():
            api_params["prompt_cache_retention"] = prompt_cache_retention
            self.logger.debug(
                "llm.openai.cache",
                model=self.model,
                retention=prompt_cache_retention,
            )

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

            # DEBUG: Log response structure for GPT-5
            if self.model.startswith("gpt-5"):
                try:
                    msg = response.choices[0].message if response.choices else None
                    self.logger.debug(
                        "gpt5.response.debug",
                        has_content=hasattr(msg, "content") if msg else False,
                        content_type=type(getattr(msg, "content", None)).__name__ if msg else None,
                        has_output_text=hasattr(msg, "output_text") if msg else False,
                        message_attrs=dir(msg) if msg else [],
                    )
                except Exception:  # nosec B110
                    pass

            # Extract output text
            output_text = ""
            if response.choices and len(response.choices) > 0:
                output_text = self._extract_output_text(response.choices[0].message)

            # Fallbacks for GPT-5 structured outputs if content looks empty
            if not output_text and response.choices and len(response.choices) > 0:
                msg = response.choices[0].message
                # 1) direct attribute commonly used by SDKs
                ot = getattr(msg, "output_text", None)
                if isinstance(ot, str) and ot.strip():
                    output_text = ot.strip()
                elif isinstance(ot, (list | tuple | set)):
                    output_text = "\n".join(self._collect_text_fragments(ot)).strip()

            if not output_text and response.choices and len(response.choices) > 0:
                # 2) dump message to dict and re-extract
                msg = response.choices[0].message
                dumped = None
                for attr in ("model_dump", "to_dict", "dict"):
                    func = getattr(msg, attr, None)
                    if callable(func):
                        try:
                            dumped = func()
                        except Exception:
                            dumped = None
                        if isinstance(dumped, dict):
                            break
                if isinstance(dumped, dict):
                    output_text = self._extract_output_text(dumped)

            if not output_text:
                # 3) scan the full response for output_text/text fragments
                def _safe_dump(obj):
                    for attr in ("model_dump", "to_dict", "dict"):
                        f = getattr(obj, attr, None)
                        if callable(f):
                            try:
                                d = f()
                            except Exception:
                                d = None
                            if isinstance(d, dict):
                                return d
                    return None

                resp_dump = _safe_dump(response) or {}
                if isinstance(resp_dump, dict):
                    # Prefer explicit keys first
                    keys = ("output_text", "output", "text")
                    parts = []

                    def _walk(x):
                        if isinstance(x, dict):
                            for k, v in x.items():
                                if k in keys:
                                    if isinstance(v, str) and v.strip():
                                        parts.append(v.strip())
                                    else:
                                        _walk(v)
                                elif isinstance(v, (dict | list | tuple | set)):
                                    _walk(v)
                        elif isinstance(x, (list | tuple | set)):
                            for it in x:
                                _walk(it)

                    _walk(resp_dump)
                    if parts and not output_text:
                        output_text = "\n".join(parts)

            if not output_text and response.choices and len(response.choices) > 0:
                try:
                    msg = response.choices[0].message
                    msg_dump = None
                    for attr in ("model_dump", "to_dict", "dict"):
                        func = getattr(msg, attr, None)
                        if callable(func):
                            try:
                                msg_dump = func()
                            except Exception:
                                msg_dump = None
                            if msg_dump is not None:
                                break
                    self.logger.warning(
                        "llm.openai.empty_output_text",
                        model=self.model,
                        finish_reason=response.choices[0].finish_reason,
                        message_type=getattr(msg, "type", None),
                        has_output_text=bool(getattr(msg, "output_text", None)),
                        content_type=type(getattr(msg, "content", None)).__name__,
                        dump_keys=list(msg_dump.keys()) if isinstance(msg_dump, dict) else None,
                    )
                except Exception:  # nosec B110 - logging is best-effort
                    pass

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

            # Handle tool calls (March 2025 function calling API)
            if response.choices and response.choices[0].message:
                message = response.choices[0].message
                if hasattr(message, "tool_calls") and message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ]
                    result["requires_tool_execution"] = True
                    self.logger.info(
                        "llm.openai.tool_calls",
                        model=self.model,
                        num_tool_calls=len(message.tool_calls),
                        tools=[tc.function.name for tc in message.tool_calls],
                    )

            try:
                self.logger.info(
                    "llm.openai.response",
                    model=self.model,
                    finish_reason=result["finish_reason"],
                    usage=result["usage"],
                    output_length=len(output_text or ""),
                    has_tool_calls=result.get("requires_tool_execution", False),
                )
            except Exception:  # nosec B110 - logging is best-effort
                pass
            return result

        except APITimeoutError as e:
            self.logger.error(
                "llm.openai.api_timeout",
                model=self.model,
                error=str(e),
                error_type="APITimeoutError",
            )
            return {
                "model": self.model,
                "prompt": prompt,
                "output": "OpenAI API request timed out. Please try again.",
                "provider": "openai",
                "error": f"APITimeoutError: {e!s}",
            }
        except TimeoutError as e:
            self.logger.error(
                "llm.openai.timeout",
                model=self.model,
                error=str(e),
                error_type="TimeoutError",
            )
            return {
                "model": self.model,
                "prompt": prompt,
                "output": "Request timed out. Please try again.",
                "provider": "openai",
                "error": f"Timeout: {e!s}",
            }
        except Exception as e:
            self.logger.exception("llm.openai.error", model=self.model, error=str(e))
            return {
                "model": self.model,
                "prompt": prompt,
                "output": f"Error: {e!s}",
                "provider": "openai",
                "error": str(e),
            }

    async def acomplete_multimodal(
        self,
        text: str,
        images: list[str] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Async multimodal completion with text and images (GPT-5.1 feature).

        GPT-5.1 supports multimodal input: text, images, and files.

        Args:
            text: Text prompt
            images: List of image URLs or base64-encoded images
            **params: Additional parameters

        Returns:
            dict with completion result

        Example:
            >>> result = await client.acomplete_multimodal(
            ...     text="What's in this image?",
            ...     images=["https://example.com/image.jpg"]
            ... )
        """
        # Build multimodal content
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]

        if images:
            for img in images:
                if img.startswith("data:"):
                    # Base64 encoded image
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": img},
                        }
                    )
                elif img.startswith("http"):
                    # URL image
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": img},
                        }
                    )
                else:
                    # Assume base64 without data prefix
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                        }
                    )

        # Build API request
        api_params: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
        }

        # Add GPT-5.1 specific parameters
        if self._is_gpt5_1_model():
            reasoning_effort = params.get("reasoning_effort", self.reasoning_effort)
            if reasoning_effort in {"none", "minimal", "low", "medium", "high"}:
                api_params["reasoning_effort"] = reasoning_effort

            max_tokens = params.get("max_tokens", self.max_tokens)
            api_params["max_completion_tokens"] = max_tokens

            prompt_cache_retention = params.get(
                "prompt_cache_retention", self.prompt_cache_retention
            )
            if prompt_cache_retention:
                api_params["prompt_cache_retention"] = prompt_cache_retention

        try:
            self.logger.info(
                "llm.openai.multimodal.request",
                model=self.model,
                text_length=len(text),
                num_images=len(images) if images else 0,
            )

            response = await self.client.chat.completions.create(**api_params)

            output_text = ""
            if response.choices and len(response.choices) > 0:
                output_text = self._extract_output_text(response.choices[0].message)

            return {
                "model": self.model,
                "prompt": text,
                "output": output_text,
                "provider": "openai",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": (
                        response.usage.completion_tokens if response.usage else 0
                    ),
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "finish_reason": (
                    response.choices[0].finish_reason if response.choices else "unknown"
                ),
            }

        except Exception as e:
            self.logger.exception("llm.openai.multimodal.error", model=self.model, error=str(e))
            return {
                "model": self.model,
                "prompt": text,
                "output": f"Error: {e!s}",
                "provider": "openai",
                "error": str(e),
            }
