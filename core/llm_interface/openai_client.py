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
    - gpt-5-2025-08-07: Latest stable version (DEFAULT)
    - gpt-5-chat-latest: Always latest GPT-5 version (auto-updates)
    - gpt-5: Alias for latest stable (currently resolves to gpt-5-2025-08-07)
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
    GPT_5 = "gpt-5-2025-08-07"  # Latest stable version
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"

    # Reasoning models
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"

    # Multimodal models intentionally omitted

    # GPT-5 models that support verbosity parameter
    GPT5_MODELS = {GPT_5, GPT_5_MINI, GPT_5_NANO, GPT_5_CHAT_LATEST, "gpt-5", "gpt-5-2025-08-07"}

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
            model: Model identifier (default: gpt-5-2025-08-07)
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

        # Set timeout to prevent hanging requests (default: 60 seconds)
        timeout = float(os.getenv("OPENAI_TIMEOUT", "60.0"))
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.logger = structlog.get_logger(__name__)
        self.logger.info("openai.client.initialized", model=self.model, timeout=timeout)

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

        except TimeoutError as e:
            self.logger.error(
                "llm.openai.timeout",
                model=self.model,
                error=str(e),
                timeout=getattr(self.client, "_timeout", "unknown"),
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
