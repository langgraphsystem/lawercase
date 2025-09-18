"""
Simple Embedder module для mega_agent_pro.

Provides basic embedding functionality:
- OpenAI embeddings integration
- Google Gemini embeddings
- Local embedding models (Sentence Transformers)
- Mock embedder for testing
- Simple caching layer
- RAG-ready interface
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Embedder
    "SimpleEmbedder",
    "EmbedRequest",
    "EmbedResponse",

    # Provider Types
    "EmbedProvider",
    "OpenAIEmbedder",
    "GeminiEmbedder",
    "LocalEmbedder",
    "MockEmbedder",

    # Enums
    "EmbedProviderType",

    # Factory
    "create_simple_embedder",
]

from .simple_embedder import (
    SimpleEmbedder,
    EmbedRequest,
    EmbedResponse,
    EmbedProvider,
    OpenAIEmbedder,
    GeminiEmbedder,
    LocalEmbedder,
    MockEmbedder,
    EmbedProviderType,
    create_simple_embedder,
)