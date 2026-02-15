"""Unified LLM Client for Multi-Provider System.

Provides a single interface for all three LLM providers:
- Gemini 3: Research, analysis, summarization
- ChatGPT 5.2: Document generation, creative tasks
- Opus 4.5: Legal analysis, complex reasoning

Features:
- Task-based automatic routing
- Manual provider selection
- Automatic fallback on errors
- Cost tracking across all providers
- Rate limit coordination
- Streaming support
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import time
from typing import Any

from .fallback_manager import FallbackManager
from .providers.base_provider import (
    BaseLLMProvider,
    CompletionRequest,
    CompletionResponse,
    CostInfo,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderType,
    StreamChunk,
    StreamEvent,
    TokenUsage,
)
from .providers.chatgpt52_provider import ChatGPT52Provider
from .providers.gemini3_provider import Gemini3Provider
from .providers.opus45_provider import Opus45Provider

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task types for automatic provider routing."""

    LEGAL_ANALYSIS = "legal_analysis"
    DOCUMENT_GENERATION = "document_generation"
    RESEARCH = "research"
    CODE_GENERATION = "code_generation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CONVERSATION = "conversation"
    CREATIVE_WRITING = "creative_writing"
    DATA_EXTRACTION = "data_extraction"
    GENERAL = "general"


# Task to provider routing (primary and fallbacks)
TASK_ROUTING: dict[TaskType, list[ProviderType]] = {
    TaskType.LEGAL_ANALYSIS: [
        ProviderType.ANTHROPIC,  # Opus 4.5 - best for legal
        ProviderType.OPENAI,  # ChatGPT 5.2 - fallback
        ProviderType.GEMINI,  # Gemini 3 - last resort
    ],
    TaskType.DOCUMENT_GENERATION: [
        ProviderType.OPENAI,  # ChatGPT 5.2 - best for docs
        ProviderType.ANTHROPIC,  # Opus 4.5 - fallback
        ProviderType.GEMINI,  # Gemini 3 - last resort
    ],
    TaskType.RESEARCH: [
        ProviderType.GEMINI,  # Gemini 3 - best for research (1M context)
        ProviderType.OPENAI,  # ChatGPT 5.2 - fallback
        ProviderType.ANTHROPIC,  # Opus 4.5 - last resort
    ],
    TaskType.CODE_GENERATION: [
        ProviderType.ANTHROPIC,  # Opus 4.5 - best for code
        ProviderType.GEMINI,  # Gemini 3 - fallback
        ProviderType.OPENAI,  # ChatGPT 5.2 - last resort
    ],
    TaskType.SUMMARIZATION: [
        ProviderType.GEMINI,  # Gemini 3 - best for summarization
        ProviderType.OPENAI,  # ChatGPT 5.2 - fallback
        ProviderType.ANTHROPIC,  # Opus 4.5 - last resort
    ],
    TaskType.TRANSLATION: [
        ProviderType.OPENAI,  # ChatGPT 5.2 - best for translation
        ProviderType.GEMINI,  # Gemini 3 - fallback
        ProviderType.ANTHROPIC,  # Opus 4.5 - last resort
    ],
    TaskType.CONVERSATION: [
        ProviderType.OPENAI,  # ChatGPT 5.2 - best for conversation
        ProviderType.ANTHROPIC,  # Opus 4.5 - fallback
        ProviderType.GEMINI,  # Gemini 3 - last resort
    ],
    TaskType.CREATIVE_WRITING: [
        ProviderType.OPENAI,  # ChatGPT 5.2 - best for creative
        ProviderType.ANTHROPIC,  # Opus 4.5 - fallback
        ProviderType.GEMINI,  # Gemini 3 - last resort
    ],
    TaskType.DATA_EXTRACTION: [
        ProviderType.ANTHROPIC,  # Opus 4.5 - best for structured extraction
        ProviderType.GEMINI,  # Gemini 3 - fallback
        ProviderType.OPENAI,  # ChatGPT 5.2 - last resort
    ],
    TaskType.GENERAL: [
        ProviderType.GEMINI,  # Gemini 3 - cost-effective default
        ProviderType.OPENAI,  # ChatGPT 5.2 - fallback
        ProviderType.ANTHROPIC,  # Opus 4.5 - last resort
    ],
}


@dataclass(slots=True)
class UnifiedRequest:
    """Request for the unified LLM client."""

    prompt: str
    task_type: TaskType = TaskType.GENERAL
    preferred_provider: ProviderType | None = None
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UnifiedResponse:
    """Response from the unified LLM client."""

    content: str
    provider: ProviderType
    model: str
    task_type: TaskType
    usage: TokenUsage
    cost: CostInfo
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    fallback_used: bool = False
    fallback_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedLLMClient:
    """Unified client for all LLM providers.

    Provides automatic routing based on task type, fallback handling,
    and unified cost/usage tracking across all providers.

    Example:
        client = UnifiedLLMClient()

        # Automatic routing based on task
        response = await client.complete(
            prompt="Analyze this contract...",
            task_type=TaskType.LEGAL_ANALYSIS,
        )

        # Manual provider selection
        response = await client.complete(
            prompt="Write a story...",
            preferred_provider=ProviderType.OPENAI,
        )

        # Streaming
        async for chunk in client.stream(
            prompt="Research this topic...",
            task_type=TaskType.RESEARCH,
        ):
            print(chunk.delta, end="")
    """

    def __init__(
        self,
        gemini_api_key: str | None = None,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        enable_fallback: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize unified LLM client.

        Args:
            gemini_api_key: Google API key (or GEMINI_API_KEY env var)
            openai_api_key: OpenAI API key (or OPENAI_API_KEY env var)
            anthropic_api_key: Anthropic API key (or ANTHROPIC_API_KEY env var)
            enable_fallback: Enable automatic fallback to other providers
            max_retries: Maximum retries per provider
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.enable_fallback = enable_fallback
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize providers
        self._providers: dict[ProviderType, BaseLLMProvider | None] = {
            ProviderType.GEMINI: None,
            ProviderType.OPENAI: None,
            ProviderType.ANTHROPIC: None,
        }
        self._available: dict[ProviderType, bool] = {
            ProviderType.GEMINI: False,
            ProviderType.OPENAI: False,
            ProviderType.ANTHROPIC: False,
        }

        # Try to initialize Gemini 3
        try:
            api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self._providers[ProviderType.GEMINI] = Gemini3Provider(api_key=api_key)
                self._available[ProviderType.GEMINI] = True
                logger.info("Gemini 3 provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini 3: {e}")

        # Try to initialize ChatGPT 5.2
        try:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._providers[ProviderType.OPENAI] = ChatGPT52Provider(api_key=api_key)
                self._available[ProviderType.OPENAI] = True
                logger.info("ChatGPT 5.2 provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGPT 5.2: {e}")

        # Try to initialize Opus 4.5
        try:
            api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self._providers[ProviderType.ANTHROPIC] = Opus45Provider(api_key=api_key)
                self._available[ProviderType.ANTHROPIC] = True
                logger.info("Opus 4.5 provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Opus 4.5: {e}")

        # Initialize fallback manager
        self._fallback_manager = FallbackManager(
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=60.0,
        )

        # Statistics
        self._total_requests = 0
        self._total_fallbacks = 0
        self._total_cost = 0.0
        self._costs_by_provider: dict[ProviderType, float] = dict.fromkeys(ProviderType, 0.0)
        self._requests_by_provider: dict[ProviderType, int] = dict.fromkeys(ProviderType, 0)
        self._requests_by_task: dict[TaskType, int] = dict.fromkeys(TaskType, 0)

    def _get_provider_chain(
        self,
        task_type: TaskType,
        preferred_provider: ProviderType | None = None,
    ) -> list[ProviderType]:
        """Get ordered list of providers to try.

        Args:
            task_type: Task type for routing
            preferred_provider: Manually preferred provider

        Returns:
            List of providers to try in order
        """
        chain: list[ProviderType] = []

        # If preferred provider specified and available, start with it
        if preferred_provider and self._available.get(preferred_provider):
            if self._fallback_manager.is_available(preferred_provider.value):
                chain.append(preferred_provider)

        # Add task-based routing
        task_chain = TASK_ROUTING.get(task_type, TASK_ROUTING[TaskType.GENERAL])
        for provider in task_chain:
            if provider not in chain and self._available.get(provider):
                if self._fallback_manager.is_available(provider.value):
                    chain.append(provider)

        return chain

    def _build_request(
        self,
        unified_request: UnifiedRequest,
    ) -> CompletionRequest:
        """Convert unified request to provider request.

        Args:
            unified_request: Unified request

        Returns:
            Provider completion request
        """
        return CompletionRequest(
            prompt=unified_request.prompt,
            system_prompt=unified_request.system_prompt,
            temperature=unified_request.temperature,
            max_tokens=unified_request.max_tokens,
            top_p=unified_request.top_p,
            top_k=unified_request.top_k,
            stop_sequences=unified_request.stop_sequences,
            stream=unified_request.stream,
            metadata=unified_request.metadata,
        )

    async def _try_provider(
        self,
        provider_type: ProviderType,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Try to execute request with a specific provider.

        Args:
            provider_type: Provider to use
            request: Completion request

        Returns:
            Completion response

        Raises:
            ProviderError: If provider fails
        """
        provider = self._providers.get(provider_type)
        if not provider:
            raise ProviderError(
                message=f"Provider {provider_type.value} not initialized",
                provider=provider_type,
                recoverable=False,
            )

        for attempt in range(self.max_retries):
            try:
                response = await provider.complete(request)

                # Record success
                self._fallback_manager.record_success(provider_type.value)

                return response

            except ProviderRateLimitError as e:
                # Wait for rate limit
                wait_time = e.retry_after or (self.retry_delay * (2**attempt))
                logger.warning(
                    f"Rate limit for {provider_type.value}, waiting {wait_time}s",
                )
                await asyncio.sleep(wait_time)

            except ProviderTimeoutError as e:
                # Retry with exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Timeout for {provider_type.value}, retrying in {wait_time}s",
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self._fallback_manager.record_failure(provider_type.value)
                    raise

            except ProviderError:
                # Non-recoverable error, record failure and raise
                self._fallback_manager.record_failure(provider_type.value)
                raise

        # All retries exhausted
        self._fallback_manager.record_failure(provider_type.value)
        raise ProviderError(
            message=f"All retries exhausted for {provider_type.value}",
            provider=provider_type,
            recoverable=True,
        )

    async def complete(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        preferred_provider: ProviderType | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float | None = None,
        top_k: int | None = None,
        stop_sequences: list[str] | None = None,
        **kwargs: Any,
    ) -> UnifiedResponse:
        """Execute completion with automatic routing and fallback.

        Args:
            prompt: User prompt
            task_type: Task type for routing
            preferred_provider: Manually preferred provider
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            top_p: Nucleus sampling
            top_k: Top-K sampling
            stop_sequences: Stop sequences
            **kwargs: Additional metadata

        Returns:
            Unified response
        """
        unified_request = UnifiedRequest(
            prompt=prompt,
            task_type=task_type,
            preferred_provider=preferred_provider,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            stop_sequences=stop_sequences,
            metadata=kwargs,
        )

        return await self.complete_request(unified_request)

    async def complete_request(
        self,
        request: UnifiedRequest,
    ) -> UnifiedResponse:
        """Execute completion request with automatic routing and fallback.

        Args:
            request: Unified request

        Returns:
            Unified response
        """
        start_time = time.perf_counter()
        self._total_requests += 1
        self._requests_by_task[request.task_type] += 1

        provider_request = self._build_request(request)
        provider_chain = self._get_provider_chain(
            request.task_type,
            request.preferred_provider,
        )

        if not provider_chain:
            return UnifiedResponse(
                content="",
                provider=ProviderType.GEMINI,
                model="none",
                task_type=request.task_type,
                usage=TokenUsage(),
                cost=CostInfo(),
                error="No LLM providers available. Check API keys.",
            )

        fallback_count = 0
        last_error: str | None = None

        for provider_type in provider_chain:
            try:
                response = await self._try_provider(provider_type, provider_request)

                # Update statistics
                self._requests_by_provider[provider_type] += 1
                self._costs_by_provider[provider_type] += response.cost.total_cost
                self._total_cost += response.cost.total_cost
                if fallback_count > 0:
                    self._total_fallbacks += 1

                latency_ms = (time.perf_counter() - start_time) * 1000

                return UnifiedResponse(
                    content=response.content,
                    provider=provider_type,
                    model=response.model,
                    task_type=request.task_type,
                    usage=response.usage,
                    cost=response.cost,
                    finish_reason=response.finish_reason,
                    latency_ms=latency_ms,
                    fallback_used=fallback_count > 0,
                    fallback_count=fallback_count,
                    metadata=response.metadata,
                )

            except ProviderError as e:
                last_error = str(e)
                logger.warning(
                    f"Provider {provider_type.value} failed: {e}",
                    extra={"task_type": request.task_type.value},
                )

                # Try next provider if fallback enabled
                if self.enable_fallback:
                    fallback_count += 1
                    continue
                break

        # All providers failed
        latency_ms = (time.perf_counter() - start_time) * 1000
        return UnifiedResponse(
            content="",
            provider=provider_chain[0] if provider_chain else ProviderType.GEMINI,
            model="none",
            task_type=request.task_type,
            usage=TokenUsage(),
            cost=CostInfo(),
            latency_ms=latency_ms,
            fallback_used=fallback_count > 0,
            fallback_count=fallback_count,
            error=f"All providers failed. Last error: {last_error}",
        )

    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        preferred_provider: ProviderType | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Execute streaming completion.

        Args:
            prompt: User prompt
            task_type: Task type for routing
            preferred_provider: Manually preferred provider
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            **kwargs: Additional parameters

        Yields:
            Stream chunks
        """
        provider_chain = self._get_provider_chain(task_type, preferred_provider)

        if not provider_chain:
            yield StreamChunk(
                event=StreamEvent.ERROR,
                content="",
                metadata={"error": "No LLM providers available"},
            )
            return

        provider_type = provider_chain[0]
        provider = self._providers.get(provider_type)

        if not provider:
            yield StreamChunk(
                event=StreamEvent.ERROR,
                content="",
                metadata={"error": f"Provider {provider_type.value} not initialized"},
            )
            return

        request = CompletionRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            metadata=kwargs,
        )

        try:
            async for chunk in provider.stream(request):
                yield chunk
        except Exception as e:
            yield StreamChunk(
                event=StreamEvent.ERROR,
                content="",
                metadata={"error": str(e)},
            )

    def get_available_providers(self) -> list[ProviderType]:
        """Get list of available providers.

        Returns:
            List of available provider types
        """
        return [pt for pt, available in self._available.items() if available]

    def get_recommended_provider(self, task_type: TaskType) -> ProviderType | None:
        """Get recommended provider for a task type.

        Args:
            task_type: Task type

        Returns:
            Recommended provider or None if none available
        """
        chain = self._get_provider_chain(task_type)
        return chain[0] if chain else None

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics.

        Returns:
            Statistics dictionary
        """
        provider_stats = {}
        for provider_type, provider in self._providers.items():
            if provider:
                provider_stats[provider_type.value] = provider.get_stats()

        return {
            "total_requests": self._total_requests,
            "total_fallbacks": self._total_fallbacks,
            "fallback_rate": (
                self._total_fallbacks / self._total_requests if self._total_requests > 0 else 0.0
            ),
            "total_cost_usd": self._total_cost,
            "available_providers": [pt.value for pt in self.get_available_providers()],
            "requests_by_provider": {
                pt.value: count for pt, count in self._requests_by_provider.items()
            },
            "costs_by_provider": {pt.value: cost for pt, cost in self._costs_by_provider.items()},
            "requests_by_task": {tt.value: count for tt, count in self._requests_by_task.items()},
            "provider_stats": provider_stats,
            "fallback_manager": self._fallback_manager.get_summary(),
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._total_requests = 0
        self._total_fallbacks = 0
        self._total_cost = 0.0
        self._costs_by_provider = dict.fromkeys(ProviderType, 0.0)
        self._requests_by_provider = dict.fromkeys(ProviderType, 0)
        self._requests_by_task = dict.fromkeys(TaskType, 0)

        for provider in self._providers.values():
            if provider:
                provider.reset_stats()

        self._fallback_manager.reset_all()

    # Convenience methods for specific tasks

    async def legal_analysis(
        self,
        document: str,
        analysis_type: str = "comprehensive",
        focus_areas: list[str] | None = None,
        jurisdiction: str | None = None,
        max_tokens: int = 8000,
    ) -> UnifiedResponse:
        """Analyze a legal document.

        Uses Opus 4.5 as primary provider.

        Args:
            document: Legal document text
            analysis_type: Type of analysis
            focus_areas: Areas to focus on
            jurisdiction: Relevant jurisdiction
            max_tokens: Maximum output tokens

        Returns:
            Unified response with analysis
        """
        opus = self._providers.get(ProviderType.ANTHROPIC)
        if opus and isinstance(opus, Opus45Provider):
            response = await opus.analyze_legal_document(
                document=document,
                analysis_type=analysis_type,
                focus_areas=focus_areas,
                jurisdiction=jurisdiction,
                max_tokens=max_tokens,
            )
            return UnifiedResponse(
                content=response.content,
                provider=ProviderType.ANTHROPIC,
                model=response.model,
                task_type=TaskType.LEGAL_ANALYSIS,
                usage=response.usage,
                cost=response.cost,
                finish_reason=response.finish_reason,
                latency_ms=response.latency_ms,
            )

        # Fallback to generic completion
        return await self.complete(
            prompt=f"Analyze this legal document:\n\n{document}",
            task_type=TaskType.LEGAL_ANALYSIS,
            max_tokens=max_tokens,
        )

    async def generate_document(
        self,
        document_type: str,
        instructions: str,
        context: str | None = None,
        style: str | None = None,
        max_tokens: int = 4096,
    ) -> UnifiedResponse:
        """Generate a document.

        Uses ChatGPT 5.2 as primary provider.

        Args:
            document_type: Type of document
            instructions: Generation instructions
            context: Additional context
            style: Writing style
            max_tokens: Maximum output tokens

        Returns:
            Unified response with generated document
        """
        chatgpt = self._providers.get(ProviderType.OPENAI)
        if chatgpt and isinstance(chatgpt, ChatGPT52Provider):
            response = await chatgpt.generate_document(
                document_type=document_type,
                instructions=instructions,
                context=context,
                style=style,
                max_tokens=max_tokens,
            )
            return UnifiedResponse(
                content=response.content,
                provider=ProviderType.OPENAI,
                model=response.model,
                task_type=TaskType.DOCUMENT_GENERATION,
                usage=response.usage,
                cost=response.cost,
                finish_reason=response.finish_reason,
                latency_ms=response.latency_ms,
            )

        # Fallback to generic completion
        return await self.complete(
            prompt=f"Generate a {document_type}:\n\n{instructions}",
            task_type=TaskType.DOCUMENT_GENERATION,
            max_tokens=max_tokens,
        )

    async def research(
        self,
        query: str,
        context: str | None = None,
        depth: str = "standard",
        max_tokens: int = 4096,
    ) -> UnifiedResponse:
        """Conduct research on a topic.

        Uses Gemini 3 as primary provider.

        Args:
            query: Research query
            context: Additional context
            depth: Research depth
            max_tokens: Maximum output tokens

        Returns:
            Unified response with research findings
        """
        gemini = self._providers.get(ProviderType.GEMINI)
        if gemini and isinstance(gemini, Gemini3Provider):
            response = await gemini.research(
                query=query,
                context=context,
                depth=depth,
                max_tokens=max_tokens,
            )
            return UnifiedResponse(
                content=response.content,
                provider=ProviderType.GEMINI,
                model=response.model,
                task_type=TaskType.RESEARCH,
                usage=response.usage,
                cost=response.cost,
                finish_reason=response.finish_reason,
                latency_ms=response.latency_ms,
            )

        # Fallback to generic completion
        return await self.complete(
            prompt=f"Research the following topic:\n\n{query}",
            task_type=TaskType.RESEARCH,
            max_tokens=max_tokens,
        )

    async def summarize(
        self,
        text: str,
        style: str = "concise",
        max_length: int = 500,
    ) -> UnifiedResponse:
        """Summarize text.

        Uses Gemini 3 as primary provider.

        Args:
            text: Text to summarize
            style: Summary style
            max_length: Maximum summary length

        Returns:
            Unified response with summary
        """
        gemini = self._providers.get(ProviderType.GEMINI)
        if gemini and isinstance(gemini, Gemini3Provider):
            response = await gemini.summarize(
                text=text,
                style=style,
                max_length=max_length,
            )
            return UnifiedResponse(
                content=response.content,
                provider=ProviderType.GEMINI,
                model=response.model,
                task_type=TaskType.SUMMARIZATION,
                usage=response.usage,
                cost=response.cost,
                finish_reason=response.finish_reason,
                latency_ms=response.latency_ms,
            )

        # Fallback to generic completion
        return await self.complete(
            prompt=f"Summarize the following text ({style}):\n\n{text}",
            task_type=TaskType.SUMMARIZATION,
            max_tokens=max_length,
        )

    async def generate_code(
        self,
        task: str,
        language: str,
        context: str | None = None,
        max_tokens: int = 4000,
    ) -> UnifiedResponse:
        """Generate code.

        Uses Opus 4.5 as primary provider.

        Args:
            task: Code task description
            language: Programming language
            context: Additional context
            max_tokens: Maximum output tokens

        Returns:
            Unified response with generated code
        """
        opus = self._providers.get(ProviderType.ANTHROPIC)
        if opus and isinstance(opus, Opus45Provider):
            response = await opus.generate_code(
                task=task,
                language=language,
                context=context,
                max_tokens=max_tokens,
            )
            return UnifiedResponse(
                content=response.content,
                provider=ProviderType.ANTHROPIC,
                model=response.model,
                task_type=TaskType.CODE_GENERATION,
                usage=response.usage,
                cost=response.cost,
                finish_reason=response.finish_reason,
                latency_ms=response.latency_ms,
            )

        # Fallback to generic completion
        return await self.complete(
            prompt=f"Write {language} code to: {task}",
            task_type=TaskType.CODE_GENERATION,
            max_tokens=max_tokens,
        )
