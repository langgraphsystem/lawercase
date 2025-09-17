from __future__ import annotations

import hashlib
import math
from typing import Dict, Iterable, List


class SimpleEmbedder:
    """Light-weight deterministic embedder with caching."""

    def __init__(self, *, embedding_dim: int | None = None) -> None:
        self._cache: Dict[str, List[float]] = {}
        self._embedding_dim = embedding_dim or 384

    def _hash_to_vector(self, text: str) -> List[float]:
        digest = hashlib.sha1(text.encode("utf-8")).digest()
        values = [digest[i % len(digest)] for i in range(self._embedding_dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    async def aembed(self, texts: Iterable[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            cached = self._cache.get(text)
            if cached is None:
                cached = self._hash_to_vector(text)
                self._cache[text] = cached
            vectors.append(cached)
        return vectors

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim
