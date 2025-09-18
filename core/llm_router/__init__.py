"""
LLM Router module для mega_agent_pro.

Provides intelligent routing between different LLM providers:
- OpenAI GPT models
- Google Gemini models
- Anthropic Claude models
- Local models (Ollama/HuggingFace)
- Mock/Stub providers for testing
- Load balancing и failover
- Cost optimization
- Rate limiting и quota management
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Router
    "LLMRouter",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",

    # Providers
    "OpenAIProvider",
    "GeminiProvider",
    "ClaudeProvider",
    "LocalProvider",
    "MockProvider",

    # Enums
    "ProviderType",
    "ModelType",
    "Priority",

    # Factory
    "create_llm_router",
]

from .llm_router import (
    LLMRouter,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    OpenAIProvider,
    GeminiProvider,
    ClaudeProvider,
    LocalProvider,
    MockProvider,
    ProviderType,
    ModelType,
    Priority,
    create_llm_router,
)