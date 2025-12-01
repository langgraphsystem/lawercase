"""LLM Response Generator with streaming support.

Provides unified interface for LLM response generation:
- Multi-provider support (OpenAI, Anthropic, Google)
- Streaming responses
- Context assembly from RAG pipeline
- Cache integration
- Token counting and budget management
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ResponseFormat(str, Enum):
    """Response format options."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class LLMConfig:
    """Configuration for LLM generation."""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-5.1"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 60.0
    stream: bool = False
    response_format: ResponseFormat = ResponseFormat.TEXT


@dataclass
class Message:
    """Chat message."""

    role: str  # system, user, assistant
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of LLM generation."""

    content: str
    model: str
    provider: LLMProvider
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Chunk of streaming response."""

    content: str
    index: int
    finish_reason: str | None = None
    is_final: bool = False


class ResponseGenerator:
    """Unified LLM response generator with streaming support.

    Features:
    - Multi-provider support (OpenAI, Anthropic, Google)
    - Streaming and non-streaming responses
    - Automatic context assembly
    - Cache integration
    - Token counting
    - Error handling and retries

    Example:
        >>> generator = ResponseGenerator()
        >>> result = await generator.generate(
        ...     messages=[Message(role="user", content="What is EB-1A?")],
        ...     config=LLMConfig(stream=False)
        ... )
        >>> print(result.content)
    """

    def __init__(
        self,
        default_config: LLMConfig | None = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ):
        """Initialize response generator.

        Args:
            default_config: Default LLM configuration
            use_cache: Whether to use response caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.default_config = default_config or LLMConfig()
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl

        # Initialize clients lazily
        self._openai_client: Any = None
        self._anthropic_client: Any = None
        self._google_client: Any = None

        # Statistics
        self._stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "errors": 0,
        }

        self.logger = logger.bind(component="response_generator")

    def _get_openai_client(self) -> Any:
        """Get or create OpenAI client."""
        if self._openai_client is None:
            import os

            from openai import AsyncOpenAI

            self._openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        return self._openai_client

    def _get_anthropic_client(self) -> Any:
        """Get or create Anthropic client."""
        if self._anthropic_client is None:
            import os

            from anthropic import AsyncAnthropic

            self._anthropic_client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        return self._anthropic_client

    def _get_google_client(self) -> Any:
        """Get or create Google client."""
        if self._google_client is None:
            import os

            import google.generativeai as genai

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self._google_client = genai
        return self._google_client

    async def generate(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
        context: dict[str, Any] | None = None,
    ) -> GenerationResult:
        """Generate LLM response.

        Args:
            messages: Chat messages
            config: Generation configuration
            context: Additional context from RAG/memory

        Returns:
            Generation result with content and metadata

        Example:
            >>> result = await generator.generate(
            ...     messages=[
            ...         Message(role="system", content="You are a legal assistant."),
            ...         Message(role="user", content="Explain EB-1A visa.")
            ...     ]
            ... )
        """
        config = config or self.default_config
        start_time = time.perf_counter()

        # Check cache if enabled and not streaming
        if self.use_cache and not config.stream:
            cached = await self._check_cache(messages, config)
            if cached:
                self._stats["cache_hits"] += 1
                return cached

        # Build context-enhanced messages
        enhanced_messages = self._enhance_with_context(messages, context)

        try:
            # Route to appropriate provider
            if config.provider == LLMProvider.OPENAI:
                result = await self._generate_openai(enhanced_messages, config)
            elif config.provider == LLMProvider.ANTHROPIC:
                result = await self._generate_anthropic(enhanced_messages, config)
            elif config.provider == LLMProvider.GOOGLE:
                result = await self._generate_google(enhanced_messages, config)
            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

            # Calculate latency
            result.latency_ms = (time.perf_counter() - start_time) * 1000

            # Update stats
            self._stats["total_requests"] += 1
            self._stats["total_tokens"] += result.total_tokens

            # Cache result
            if self.use_cache and not config.stream:
                await self._cache_result(messages, config, result)

            self.logger.info(
                "generation_complete",
                provider=config.provider.value,
                model=config.model,
                tokens=result.total_tokens,
                latency_ms=result.latency_ms,
            )

            return result

        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error("generation_failed", error=str(e))
            raise

    async def generate_stream(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate streaming LLM response.

        Args:
            messages: Chat messages
            config: Generation configuration
            context: Additional context

        Yields:
            Stream chunks with content

        Example:
            >>> async for chunk in generator.generate_stream(messages):
            ...     print(chunk.content, end="", flush=True)
        """
        config = config or self.default_config
        config.stream = True

        # Build context-enhanced messages
        enhanced_messages = self._enhance_with_context(messages, context)

        try:
            if config.provider == LLMProvider.OPENAI:
                async for chunk in self._stream_openai(enhanced_messages, config):
                    yield chunk
            elif config.provider == LLMProvider.ANTHROPIC:
                async for chunk in self._stream_anthropic(enhanced_messages, config):
                    yield chunk
            elif config.provider == LLMProvider.GOOGLE:
                async for chunk in self._stream_google(enhanced_messages, config):
                    yield chunk
            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

            self._stats["total_requests"] += 1

        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error("stream_generation_failed", error=str(e))
            raise

    def _enhance_with_context(
        self,
        messages: list[Message],
        context: dict[str, Any] | None,
    ) -> list[Message]:
        """Enhance messages with RAG/memory context.

        Args:
            messages: Original messages
            context: Context from RAG pipeline

        Returns:
            Enhanced message list
        """
        if not context:
            return messages

        enhanced = list(messages)

        # Add context to system message or create one
        context_text = context.get("text", "")
        if context_text:
            context_block = (
                f"\n\n---\nRelevant Context:\n{context_text}\n---\n"
                "Use this context to inform your response."
            )

            # Find system message or add one
            for i, msg in enumerate(enhanced):
                if msg.role == "system":
                    enhanced[i] = Message(
                        role="system",
                        content=msg.content + context_block,
                        metadata=msg.metadata,
                    )
                    break
            else:
                # No system message, add one
                enhanced.insert(
                    0,
                    Message(
                        role="system",
                        content=f"You are a helpful assistant.{context_block}",
                    ),
                )

        return enhanced

    async def _generate_openai(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> GenerationResult:
        """Generate using OpenAI API."""
        client = self._get_openai_client()

        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        response = await client.chat.completions.create(
            model=config.model,
            messages=openai_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
            timeout=config.timeout,
        )

        choice = response.choices[0]
        usage = response.usage

        return GenerationResult(
            content=choice.message.content or "",
            model=config.model,
            provider=LLMProvider.OPENAI,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def _generate_anthropic(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> GenerationResult:
        """Generate using Anthropic API."""
        client = self._get_anthropic_client()

        # Extract system message
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        response = await client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=system,
            messages=anthropic_messages,
            temperature=config.temperature,
        )

        content = response.content[0].text if response.content else ""
        usage = response.usage

        return GenerationResult(
            content=content,
            model=config.model,
            provider=LLMProvider.ANTHROPIC,
            prompt_tokens=usage.input_tokens if usage else 0,
            completion_tokens=usage.output_tokens if usage else 0,
            total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
            finish_reason=response.stop_reason or "stop",
        )

    async def _generate_google(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> GenerationResult:
        """Generate using Google Generative AI."""
        genai = self._get_google_client()

        model = genai.GenerativeModel(config.model)

        # Convert messages to Google format
        history = []
        prompt = ""
        for msg in messages:
            if msg.role == "user":
                prompt = msg.content
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})
            elif msg.role == "system":
                # Prepend system message to prompt
                prompt = f"{msg.content}\n\n{prompt}"

        chat = model.start_chat(history=history)
        response = await asyncio.to_thread(
            chat.send_message,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
        )

        return GenerationResult(
            content=response.text,
            model=config.model,
            provider=LLMProvider.GOOGLE,
            finish_reason="stop",
        )

    async def _stream_openai(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using OpenAI API."""
        client = self._get_openai_client()

        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        stream = await client.chat.completions.create(
            model=config.model,
            messages=openai_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True,
        )

        index = 0
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                finish_reason = chunk.choices[0].finish_reason

                yield StreamChunk(
                    content=content,
                    index=index,
                    finish_reason=finish_reason,
                    is_final=finish_reason is not None,
                )
                index += 1

    async def _stream_anthropic(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using Anthropic API."""
        client = self._get_anthropic_client()

        # Extract system message
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        async with client.messages.stream(
            model=config.model,
            max_tokens=config.max_tokens,
            system=system,
            messages=anthropic_messages,
            temperature=config.temperature,
        ) as stream:
            index = 0
            async for text in stream.text_stream:
                yield StreamChunk(
                    content=text,
                    index=index,
                    is_final=False,
                )
                index += 1

            yield StreamChunk(
                content="",
                index=index,
                finish_reason="stop",
                is_final=True,
            )

    async def _stream_google(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using Google Generative AI."""
        genai = self._get_google_client()

        model = genai.GenerativeModel(config.model)

        # Convert messages
        prompt = ""
        for msg in messages:
            if msg.role in ("user", "system"):
                prompt += msg.content + "\n"

        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
            stream=True,
        )

        index = 0
        for chunk in response:
            yield StreamChunk(
                content=chunk.text,
                index=index,
                is_final=False,
            )
            index += 1

        yield StreamChunk(
            content="",
            index=index,
            finish_reason="stop",
            is_final=True,
        )

    async def _check_cache(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> GenerationResult | None:
        """Check cache for existing response."""
        try:
            from core.caching.llm_cache import LLMCache

            cache = LLMCache()
            prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

            cached = await cache.get(
                prompt=prompt,
                model=config.model,
                temperature=config.temperature,
            )

            if cached:
                return GenerationResult(
                    content=cached.get("content", ""),
                    model=config.model,
                    provider=config.provider,
                    cached=True,
                    metadata={"cache_hit": True},
                )

        except ImportError:
            pass
        except Exception as e:
            self.logger.warning("cache_check_failed", error=str(e))

        return None

    async def _cache_result(
        self,
        messages: list[Message],
        config: LLMConfig,
        result: GenerationResult,
    ) -> None:
        """Cache generation result."""
        try:
            from core.caching.llm_cache import LLMCache

            cache = LLMCache()
            prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)

            await cache.set(
                prompt=prompt,
                model=config.model,
                temperature=config.temperature,
                response={"content": result.content, "tokens": result.total_tokens},
                ttl=self.cache_ttl,
            )

        except ImportError:
            pass
        except Exception as e:
            self.logger.warning("cache_set_failed", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """Get generator statistics."""
        return dict(self._stats)


# Convenience factory function
def create_response_generator(
    provider: LLMProvider = LLMProvider.OPENAI,
    model: str | None = None,
    **kwargs: Any,
) -> ResponseGenerator:
    """Create configured response generator.

    Args:
        provider: LLM provider
        model: Model name (uses provider default if not specified)
        **kwargs: Additional configuration

    Returns:
        Configured ResponseGenerator instance

    Example:
        >>> generator = create_response_generator(
        ...     provider=LLMProvider.ANTHROPIC,
        ...     model="claude-3-5-sonnet-20241022"
        ... )
    """
    default_models = {
        LLMProvider.OPENAI: "gpt-5.1",
        LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        LLMProvider.GOOGLE: "gemini-1.5-flash",
    }

    config = LLMConfig(
        provider=provider,
        model=model or default_models.get(provider, "gpt-5.1"),
        **kwargs,
    )

    return ResponseGenerator(default_config=config)


__all__ = [
    "GenerationResult",
    "LLMConfig",
    "LLMProvider",
    "Message",
    "ResponseFormat",
    "ResponseGenerator",
    "StreamChunk",
    "create_response_generator",
]
