"""Hybrid retrieval combining lexical and semantic similarity."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .ingestion import DocumentChunk, DocumentStore, SupportsEmbed
from .utils import clamp, cosine_similarity, tokenize


@dataclass(slots=True)
class ScoredChunk:
    """Container for chunk scores used across retrieval/rerank stages."""

    chunk: DocumentChunk
    keyword_score: float
    semantic_score: float

    @property
    def combined_score(self) -> float:
        return clamp((self.keyword_score + self.semantic_score) / 2.0)


class HybridRetriever:
    """Perform lexical and semantic search over the document store."""

    def __init__(
        self,
        *,
        store: DocumentStore,
        embedder: SupportsEmbed,
        alpha: float = 0.6,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.alpha = clamp(alpha)

    async def search(self, query: str, *, top_k: int = 5) -> list[ScoredChunk]:
        if top_k <= 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        [query_vector] = await self.embedder.aembed([query])
        keyword_scores = self._keyword_scores(query_tokens)
        semantic_scores = self._semantic_scores(query_vector)

        scored: list[ScoredChunk] = []
        for chunk_id, keyword_score in keyword_scores.items():
            semantic_score = semantic_scores.get(chunk_id, 0.0)
            combined = self._mix_scores(keyword_score, semantic_score)
            if combined <= 0.0:
                continue
            chunk = self.store.get_chunk(chunk_id)
            if not chunk:
                continue
            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    keyword_score=keyword_score,
                    semantic_score=semantic_score,
                )
            )
        scored.sort(key=lambda entry: entry.combined_score, reverse=True)
        return scored[:top_k]

    def _keyword_scores(self, query_tokens: list[str]) -> dict[str, float]:
        query_token_set = set(query_tokens)
        scores: dict[str, float] = {}

        for chunk in self.store.iter_chunks():
            chunk_tokens = tokenize(chunk.text)
            if not chunk_tokens:
                continue
            overlap = query_token_set.intersection(chunk_tokens)
            if not overlap:
                continue
            chunk_score = len(overlap) / math.sqrt(len(chunk_tokens))
            scores[chunk.chunk_id] = clamp(chunk_score)
        return scores

    def _semantic_scores(self, query_vector: Sequence[float]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for chunk in self.store.iter_chunks():
            if not chunk.embedding:
                continue
            scores[chunk.chunk_id] = clamp(cosine_similarity(query_vector, chunk.embedding))
        return scores

    def _mix_scores(self, keyword: float, semantic: float) -> float:
        return clamp((1 - self.alpha) * keyword + self.alpha * semantic)


__all__ = ["HybridRetriever", "ScoredChunk"]
