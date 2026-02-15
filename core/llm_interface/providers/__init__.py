"""Multi-Provider LLM System (v2.7).

This package provides a unified interface for multiple LLM providers:
- Gemini 3 (Google): Research, analysis, summarization
- ChatGPT 5.2 (OpenAI): Document generation, creative tasks
- Opus 4.5 (Anthropic): Legal analysis, complex reasoning

Each provider implements the BaseLLMProvider interface with:
- Async completion with streaming support
- Rate limiting per provider
- Token counting
- Cost tracking per request
- Provider-specific error handling

Usage:
    from core.llm_interface.providers import (
        Gemini3Provider,
        ChatGPT52Provider,
        Opus45Provider,
        UnifiedLLMClient,
    )

    # Use individual providers
    gemini = Gemini3Provider(api_key="...")
    response = await gemini.complete(CompletionRequest(prompt="..."))

    # Or use the unified client
    client = UnifiedLLMClient()
    response = await client.complete(
        prompt="Analyze this legal document...",
        task_type=TaskType.LEGAL_ANALYSIS,
    )
"""

from __future__ import annotations

# Base classes and types
from .base_provider import (
    # Provider base class
    BaseLLMProvider,
    CompletionRequest,
    CompletionResponse,
    CostInfo,
    ProviderAuthenticationError,
    ProviderContentFilterError,
    # Exceptions
    ProviderError,
    ProviderModelNotFoundError,
    ProviderQuotaExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    # Types
    ProviderType,
    StreamChunk,
    StreamEvent,
    # Rate limiting
    TokenBucketRateLimiter,
    # Data classes
    TokenUsage,
)
from .chatgpt52_provider import ChatGPT52Provider

# Provider implementations
from .gemini3_provider import Gemini3Provider
from .opus45_provider import Opus45Provider

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "ChatGPT52Provider",
    "CompletionRequest",
    "CompletionResponse",
    "CostInfo",
    # Providers
    "Gemini3Provider",
    "Opus45Provider",
    "ProviderAuthenticationError",
    "ProviderContentFilterError",
    # Exceptions
    "ProviderError",
    "ProviderModelNotFoundError",
    "ProviderQuotaExceededError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    # Types
    "ProviderType",
    "StreamChunk",
    "StreamEvent",
    # Rate limiting
    "TokenBucketRateLimiter",
    # Data classes
    "TokenUsage",
]
