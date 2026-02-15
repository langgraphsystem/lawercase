"""High level LLM integration helpers.

Provides unified interface for LLM providers:
- UnifiedLLMClient: Multi-provider client with automatic routing (v2.7)
- TaskRouter: Task-based routing to Gemini 3 / ChatGPT 5.2 / Opus 4.5
- IntelligentRouter: Cost-aware routing with caching
- FallbackManager: Circuit breaker pattern for resilience

Multi-Provider System (v2.7):
- Gemini 3: Research, analysis, summarization (1M context)
- ChatGPT 5.2: Document generation, creative tasks
- Opus 4.5: Legal analysis, complex reasoning
"""

from __future__ import annotations

from .fallback_manager import CircuitState, FallbackManager, ProviderHealth
from .intelligent_router import IntelligentRouter, LLMRequest
from .providers import (
    # Base classes
    BaseLLMProvider,
    ChatGPT52Provider,
    CompletionRequest,
    CompletionResponse,
    CostInfo,
    # Providers
    Gemini3Provider,
    Opus45Provider,
    ProviderAuthenticationError,
    ProviderContentFilterError,
    # Exceptions
    ProviderError,
    ProviderModelNotFoundError,
    ProviderQuotaExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderType,
    StreamChunk,
    StreamEvent,
    TokenBucketRateLimiter,
    TokenUsage,
)
from .task_router import (
    MODEL_CONFIGS,
    TASK_ROUTING,
    ModelProvider,
    TaskRequest,
    TaskResponse,
    TaskRouter,
    TaskType,
)

# Multi-Provider System (v2.7)
from .unified_llm_client import (
    TASK_ROUTING as UNIFIED_TASK_ROUTING,
    TaskType as UnifiedTaskType,
    UnifiedLLMClient,
    UnifiedRequest,
    UnifiedResponse,
)

__all__ = [
    "MODEL_CONFIGS",
    "TASK_ROUTING",
    "UNIFIED_TASK_ROUTING",
    # Provider base classes
    "BaseLLMProvider",
    "ChatGPT52Provider",
    "CircuitState",
    "CompletionRequest",
    "CompletionResponse",
    "CostInfo",
    # Fallback
    "FallbackManager",
    # Individual providers
    "Gemini3Provider",
    # Intelligent Router (legacy)
    "IntelligentRouter",
    "LLMRequest",
    "ModelProvider",
    "Opus45Provider",
    "ProviderAuthenticationError",
    "ProviderContentFilterError",
    # Provider errors
    "ProviderError",
    "ProviderHealth",
    "ProviderModelNotFoundError",
    "ProviderQuotaExceededError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderType",
    "StreamChunk",
    "StreamEvent",
    "TaskRequest",
    "TaskResponse",
    # Task Router
    "TaskRouter",
    "TaskType",
    "TokenBucketRateLimiter",
    "TokenUsage",
    # Unified LLM Client (v2.7)
    "UnifiedLLMClient",
    "UnifiedRequest",
    "UnifiedResponse",
    "UnifiedTaskType",
]
