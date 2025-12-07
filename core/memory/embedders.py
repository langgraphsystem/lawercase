"""Local embedding providers used by the memory manager."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib

import numpy as np


class DeterministicEmbedder:
    """Hash-based embedder suitable for development and unit tests.

    This embedder avoids network calls while still producing non-zero vectors,
    enabling semantic components (RAG, memory retrieval) to operate in dev/test.
    """

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim = embedding_dim

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], byteorder="little", signed=False) or 7
            rng = np.random.default_rng(seed=seed)
            vectors.append(rng.random(self.embedding_dim, dtype=np.float32).tolist())
        return vectors


def batch_cosine_similarity(
    query: Sequence[float], embeddings: Sequence[Sequence[float]]
) -> list[float]:
    """Compute cosine similarity between query vector and a batch."""
    query_vec = np.asarray(query, dtype=np.float32)
    denom_query = np.linalg.norm(query_vec)
    if denom_query == 0:
        return [0.0 for _ in embeddings]

    similarities: list[float] = []
    for embedding in embeddings:
        emb_vec = np.asarray(embedding, dtype=np.float32)
        denom_emb = np.linalg.norm(emb_vec)
        if denom_emb == 0:
            similarities.append(0.0)
            continue
        similarities.append(float(np.dot(query_vec, emb_vec) / (denom_query * denom_emb)))
    return similarities


__all__ = ["DeterministicEmbedder", "batch_cosine_similarity"]
