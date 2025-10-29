"""Re-ranking heuristics for hybrid retrieval results."""

from __future__ import annotations

from collections.abc import Iterable

from .hybrid import ScoredChunk
from .utils import clamp


class Reranker:
    """Lightweight reranker combining scores and metadata heuristics."""

    def __init__(self, *, freshness_boost: float = 0.1) -> None:
        self.freshness_boost = freshness_boost

    def rerank(self, query: str, scores: Iterable[ScoredChunk]) -> list[ScoredChunk]:
        """Apply heuristic boosts and return a new sorted list."""
        enriched: list[tuple[float, ScoredChunk]] = []

        for scored in scores:
            boost = self._metadata_boost(scored)
            combined = clamp(scored.combined_score + boost)
            enriched.append((combined, scored))

        enriched.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in enriched]

    def _metadata_boost(self, scored: ScoredChunk) -> float:
        metadata = scored.chunk.metadata
        freshness = metadata.get("updated_at") or metadata.get("created_at")
        if freshness:
            # Presence of timestamp metadata (value ignored) gets a small bump.
            return self.freshness_boost
        topic_tag = metadata.get("topic")
        if topic_tag and topic_tag.lower() in scored.chunk.text.lower():
            return self.freshness_boost / 2
        return 0.0


__all__ = ["Reranker"]
