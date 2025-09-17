"""
Real embeddings integration module for mega_agent_pro.

Provides production-ready embedding services with:
- Multiple provider support (Gemini, OpenAI, Azure, Local)
- Semantic caching for cost optimization
- Rate limiting and retry logic
- Graceful fallback between providers
- Batch processing for efficiency
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    "EmbeddingManager",
    "EmbeddingProvider",
    "EmbeddingModel",
    "EmbeddingConfig",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "RealEmbedder",
    "create_gemini_config",
    "create_openai_config",
    "create_local_config",
]

from .embeddings_manager import (
    EmbeddingConfig,
    EmbeddingManager,
    EmbeddingModel,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    RealEmbedder,
    create_gemini_config,
    create_local_config,
    create_openai_config,
)