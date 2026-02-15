"""OpenAI ChatGPT 5.2 Provider for document generation and creative tasks.

ChatGPT 5.2 Models (December 2025):
- gpt-5.2-turbo: Latest flagship with improved reasoning
- gpt-5.2-mini: Faster and more affordable

Strengths:
- Document generation
- Creative writing
- Conversation and dialogue
- Translation
- Instruction following
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import logging
import os
from typing import Any

from .base_provider import (
    BaseLLMProvider,
    CompletionRequest,
    CompletionResponse,
    ProviderAuthenticationError,
    ProviderContentFilterError,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderQuotaExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderType,
    StreamChunk,
    StreamEvent,
    TokenUsage,
)

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import httpx
    from openai import APITimeoutError, AsyncOpenAI, AuthenticationError, RateLimitError

    OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None  # type: ignore
    APITimeoutError = None  # type: ignore
    RateLimitError = None  # type: ignore
    AuthenticationError = None  # type: ignore
    httpx = None  # type: ignore
    OPENAI_AVAILABLE = False

# Try to import tiktoken for accurate token counting
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None  # type: ignore
    TIKTOKEN_AVAILABLE = False


class ChatGPT52Provider(BaseLLMProvider):
    """OpenAI ChatGPT 5.2 provider for document generation and creative tasks.

    Optimized for:
    - Document generation (letters, reports, contracts)
    - Creative writing
    - Conversation and dialogue
    - Translation
    - Instruction following

    Model IDs:
    - gpt-5.2-turbo: Full capability model (default)
    - gpt-5.2-mini: Fast and efficient

    Example:
        provider = ChatGPT52Provider(
            api_key="your-api-key",
            model_id="gpt-5.2-turbo",
        )

        response = await provider.complete(CompletionRequest(
            prompt="Write a formal business letter...",
            max_tokens=2000,
        ))
    """

    # Provider identification
    provider_type = ProviderType.OPENAI
    model_id = "gpt-5.2-turbo"

    # Available models
    GPT_5_2_TURBO = "gpt-5.2-turbo"
    GPT_5_2_MINI = "gpt-5.2-mini"

    # Pricing (per 1K tokens) - January 2026
    PRICING = {
        "gpt-5.2-turbo": {"input": 0.01, "output": 0.03},
        "gpt-5.2-mini": {"input": 0.003, "output": 0.012},
        "gpt-5.2": {"input": 0.01, "output": 0.03},
    }

    # Default pricing
    cost_per_1k_input = 0.01
    cost_per_1k_output = 0.03

    # Limits
    max_context_tokens = 128000
    max_output_tokens = 16384

    # Rate limits (default)
    requests_per_minute = 500
    tokens_per_minute = 200000

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        timeout: float = 120.0,
        organization: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ):
        """Initialize ChatGPT 5.2 provider.

        Args:
            api_key: OpenAI API key (or OPENAI_API_KEY env var)
            model_id: Model identifier (default: gpt-5.2-turbo)
            requests_per_minute: Override default request rate limit
            tokens_per_minute: Override default token rate limit
            timeout: Request timeout in seconds
            organization: OpenAI organization ID
            base_url: Custom API base URL
            **kwargs: Additional options
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. " "Install with: pip install openai>=1.58.0"
            )

        # Resolve API key
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ProviderAuthenticationError(
                message="OpenAI API key required. Set OPENAI_API_KEY env var.",
                provider=ProviderType.OPENAI,
            )

        # Set model-specific pricing
        resolved_model = model_id or self.GPT_5_2_TURBO
        if resolved_model in self.PRICING:
            self.cost_per_1k_input = self.PRICING[resolved_model]["input"]
            self.cost_per_1k_output = self.PRICING[resolved_model]["output"]

        self.organization = organization or os.getenv("OPENAI_ORGANIZATION")
        self.base_url = base_url

        # Initialize tokenizer
        self._tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base for GPT-5.2 (assumed similar to GPT-4)
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

        super().__init__(
            api_key=resolved_api_key,
            model_id=resolved_model,
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
            timeout=timeout,
            **kwargs,
        )

    def _initialize_client(self) -> None:
        """Initialize the OpenAI client."""
        # Build timeout configuration
        timeout_config = httpx.Timeout(
            timeout=self.timeout,
            read=self.timeout,
            write=30.0,
            connect=10.0,
        )

        # Create async client
        client_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": timeout_config,
        }
        if self.organization:
            client_kwargs["organization"] = self.organization
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = AsyncOpenAI(**client_kwargs)

        logger.info(
            "ChatGPT 5.2 provider initialized",
            extra={"model": self.model_id},
        )

    def _build_messages(
        self,
        request: CompletionRequest,
    ) -> list[dict[str, str]]:
        """Build message array from request.

        Args:
            request: Completion request

        Returns:
            List of message dicts
        """
        messages: list[dict[str, str]] = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": request.system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": request.prompt,
            }
        )

        return messages

    def _handle_error(self, error: Exception) -> None:
        """Convert OpenAI errors to provider errors.

        Args:
            error: Original exception

        Raises:
            ProviderError: Converted provider error
        """
        error_str = str(error).lower()

        if AuthenticationError and isinstance(error, AuthenticationError):
            raise ProviderAuthenticationError(
                message=f"OpenAI authentication failed: {error}",
                provider=ProviderType.OPENAI,
                model=self.model_id,
            ) from error

        if RateLimitError and isinstance(error, RateLimitError):
            retry_after = None
            if hasattr(error, "retry_after"):
                retry_after = float(error.retry_after)
            raise ProviderRateLimitError(
                message=f"OpenAI rate limit exceeded: {error}",
                provider=ProviderType.OPENAI,
                model=self.model_id,
                retry_after=retry_after,
            ) from error

        if APITimeoutError and isinstance(error, APITimeoutError):
            raise ProviderTimeoutError(
                message=f"OpenAI request timed out: {error}",
                provider=ProviderType.OPENAI,
                model=self.model_id,
                timeout=self.timeout,
            ) from error

        if isinstance(error, TimeoutError | asyncio.TimeoutError):
            raise ProviderTimeoutError(
                message=f"OpenAI request timed out: {error}",
                provider=ProviderType.OPENAI,
                model=self.model_id,
                timeout=self.timeout,
            ) from error

        if "not found" in error_str or "404" in error_str:
            raise ProviderModelNotFoundError(
                message=f"OpenAI model not found: {error}",
                provider=ProviderType.OPENAI,
                model=self.model_id,
            ) from error

        if "content_filter" in error_str or "content policy" in error_str:
            raise ProviderContentFilterError(
                message=f"OpenAI content filtered: {error}",
                provider=ProviderType.OPENAI,
                filter_reason=str(error),
            ) from error

        if "quota" in error_str or "billing" in error_str or "insufficient" in error_str:
            raise ProviderQuotaExceededError(
                message=f"OpenAI quota exceeded: {error}",
                provider=ProviderType.OPENAI,
            ) from error

        # Generic error
        raise ProviderError(
            message=f"OpenAI error: {error}",
            provider=ProviderType.OPENAI,
            model=self.model_id,
            recoverable=True,
        ) from error

    async def _complete_impl(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Execute completion using OpenAI API.

        Args:
            request: Completion request

        Returns:
            Completion response
        """
        messages = self._build_messages(request)

        # Build API parameters
        api_params: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_completion_tokens": min(request.max_tokens, self.max_output_tokens),
            "temperature": request.temperature,
        }

        if request.top_p is not None:
            api_params["top_p"] = request.top_p
        if request.stop_sequences:
            api_params["stop"] = request.stop_sequences

        try:
            response = await self._client.chat.completions.create(**api_params)

            # Extract content
            output_text = ""
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message.content:
                    output_text = message.content

            # Extract usage
            usage = TokenUsage()
            if response.usage:
                usage = TokenUsage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            # Extract finish reason
            finish_reason = "stop"
            if response.choices and len(response.choices) > 0:
                finish_reason = response.choices[0].finish_reason or "stop"

            # Calculate cost
            cost = self.calculate_cost(usage)

            return CompletionResponse(
                content=output_text,
                model=self.model_id,
                provider=ProviderType.OPENAI,
                usage=usage,
                cost=cost,
                finish_reason=finish_reason,
                metadata={"response_id": response.id},
            )

        except Exception as e:
            self._handle_error(e)
            raise

    async def _stream_impl(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Execute streaming completion using OpenAI API.

        Args:
            request: Completion request

        Yields:
            Stream chunks
        """
        messages = self._build_messages(request)

        # Build API parameters
        api_params: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_completion_tokens": min(request.max_tokens, self.max_output_tokens),
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if request.top_p is not None:
            api_params["top_p"] = request.top_p
        if request.stop_sequences:
            api_params["stop"] = request.stop_sequences

        try:
            stream = await self._client.chat.completions.create(**api_params)

            accumulated_text = ""
            final_usage: TokenUsage | None = None

            async for chunk in stream:
                # Extract delta text
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        accumulated_text += delta.content
                        yield StreamChunk(
                            event=StreamEvent.TEXT_DELTA,
                            content=accumulated_text,
                            delta=delta.content,
                        )

                # Extract usage from final chunk
                if chunk.usage:
                    final_usage = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                    )

            # Emit usage
            if final_usage:
                yield StreamChunk(
                    event=StreamEvent.USAGE,
                    content=accumulated_text,
                    usage=final_usage,
                )

            # Emit done
            yield StreamChunk(
                event=StreamEvent.DONE,
                content=accumulated_text,
            )

        except Exception as e:
            yield StreamChunk(
                event=StreamEvent.ERROR,
                content="",
                metadata={"error": str(e)},
            )
            self._handle_error(e)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: estimate based on characters
        # Average ~4 characters per token for English
        return len(text) // 4

    async def generate_document(
        self,
        document_type: str,
        instructions: str,
        context: str | None = None,
        style: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResponse:
        """Generate a document.

        Optimized for document generation tasks.

        Args:
            document_type: Type of document (letter, report, contract, etc.)
            instructions: Specific instructions for the document
            context: Additional context or data to include
            style: Writing style (formal, casual, technical)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature

        Returns:
            Completion response with generated document
        """
        style_instruction = ""
        if style:
            style_instruction = f"Write in a {style} style. "

        prompt = f"""Generate a {document_type} following these instructions:

{instructions}
"""
        if context:
            prompt += f"""
Context and data to include:
{context}
"""
        prompt += f"""
{style_instruction}Ensure the document is well-structured and professional."""

        system_prompt = f"""You are an expert document writer specializing in creating high-quality {document_type}s.
Follow the user's instructions precisely and produce a polished, professional document."""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    async def creative_write(
        self,
        prompt: str,
        genre: str | None = None,
        tone: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.9,
    ) -> CompletionResponse:
        """Generate creative writing.

        Args:
            prompt: Creative writing prompt
            genre: Genre (fiction, poetry, screenplay, etc.)
            tone: Desired tone
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (higher for more creativity)

        Returns:
            Completion response with creative writing
        """
        system_parts = ["You are a talented creative writer."]
        if genre:
            system_parts.append(f"You specialize in {genre}.")
        if tone:
            system_parts.append(f"Write with a {tone} tone.")

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt=" ".join(system_parts),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
        preserve_formatting: bool = True,
        max_tokens: int = 4096,
    ) -> CompletionResponse:
        """Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language
            source_language: Source language (auto-detected if not specified)
            preserve_formatting: Whether to preserve original formatting
            max_tokens: Maximum output tokens

        Returns:
            Completion response with translation
        """
        source_info = f"from {source_language} " if source_language else ""
        formatting_note = " Preserve the original formatting." if preserve_formatting else ""

        prompt = f"""Translate the following text {source_info}to {target_language}.{formatting_note}

Text to translate:
{text}

Translation:"""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                temperature=0.3,
                max_tokens=max_tokens,
            )
        )

    async def converse(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        persona: str | None = None,
        max_tokens: int = 1024,
    ) -> CompletionResponse:
        """Engage in conversation.

        Args:
            user_message: User's message
            conversation_history: Previous messages [{"role": "user/assistant", "content": "..."}]
            persona: AI persona to adopt
            max_tokens: Maximum output tokens

        Returns:
            Completion response with AI reply
        """
        system_prompt = persona or "You are a helpful, friendly AI assistant."

        # Build full prompt with history
        prompt_parts = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.capitalize()}: {content}")

        prompt_parts.append(f"User: {user_message}")
        prompt_parts.append("Assistant:")

        return await self.complete(
            CompletionRequest(
                prompt="\n\n".join(prompt_parts),
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=max_tokens,
            )
        )
