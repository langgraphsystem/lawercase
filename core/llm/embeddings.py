from __future__ import annotations

from ..config import get_settings
from .gemini_embedder import GeminiEmbedder


def get_default_embedder() -> GeminiEmbedder | None:
    """Factory: returns a real embedder if feature-flag is enabled, else None.

    Callers (e.g., MemoryManager bootstrap) can pass this to enable embeddings.
    """
    s = get_settings().gemini
    if not s.enabled:
        return None
    if not s.api_key:
        return None
    return GeminiEmbedder(
        api_key=s.api_key,
        model=s.embedding_model,  # expected 'gemini-embedding-001'
        output_dimensionality=s.output_dim,
    )
