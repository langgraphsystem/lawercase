"""Context relevance scoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RelevanceMetrics:
    """Metrics for context relevance."""

    keyword_score: float = 0.0  # Keyword overlap score
    semantic_score: float = 0.0  # Semantic similarity (if embeddings available)
    recency_score: float = 0.0  # How recent is the information
    importance_score: float = 0.0  # Explicit importance marking
    overall_score: float = 0.0  # Combined score

    def calculate_overall(self, weights: dict[str, float] | None = None) -> float:
        """Calculate weighted overall score.

        Args:
            weights: Dictionary of weights for each metric

        Returns:
            Overall relevance score
        """
        if weights is None:
            weights = {
                "keyword": 0.3,
                "semantic": 0.3,
                "recency": 0.2,
                "importance": 0.2,
            }

        self.overall_score = (
            self.keyword_score * weights.get("keyword", 0.3)
            + self.semantic_score * weights.get("semantic", 0.3)
            + self.recency_score * weights.get("recency", 0.2)
            + self.importance_score * weights.get("importance", 0.2)
        )

        return self.overall_score


class ContextRelevanceScorer:
    """Scores context relevance for adaptive selection."""

    def __init__(self) -> None:
        """Initialize relevance scorer."""
        logger.info("ContextRelevanceScorer initialized")

    def score_relevance(
        self,
        context: str,
        query: str,
        metadata: dict[str, Any] | None = None,
    ) -> RelevanceMetrics:
        """Score relevance of context to query.

        Args:
            context: Context text to score
            query: Query/task to compare against
            metadata: Optional metadata (timestamp, priority, etc.)

        Returns:
            RelevanceMetrics with scores
        """
        metrics = RelevanceMetrics()

        # Keyword score
        metrics.keyword_score = self._keyword_overlap_score(context, query)

        # Semantic score (simplified - would use embeddings in production)
        metrics.semantic_score = self._simple_semantic_score(context, query)

        # Recency score (if timestamp in metadata)
        if metadata and "timestamp" in metadata:
            metrics.recency_score = self._recency_score(metadata["timestamp"])

        # Importance score (if priority in metadata)
        if metadata and "priority" in metadata:
            metrics.importance_score = min(1.0, metadata["priority"] / 10.0)

        # Calculate overall
        metrics.calculate_overall()

        return metrics

    def _keyword_overlap_score(self, context: str, query: str) -> float:
        """Calculate keyword overlap score.

        Args:
            context: Context text
            query: Query text

        Returns:
            Score between 0.0 and 1.0
        """
        # Normalize and tokenize
        context_lower = context.lower()
        query_lower = query.lower()

        # Extract words (simple tokenization)
        context_words = set(re.findall(r"\b\w+\b", context_lower))
        query_words = set(re.findall(r"\b\w+\b", query_lower))

        # Remove common stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "are",
            "was",
            "were",
        }
        context_words -= stopwords
        query_words -= stopwords

        if not query_words:
            return 0.0

        # Calculate Jaccard similarity
        intersection = context_words & query_words
        union = context_words | query_words

        score = len(intersection) / len(union) if union else 0.0

        return min(1.0, score * 2.0)  # Scale up a bit

    def _simple_semantic_score(self, context: str, query: str) -> float:
        """Calculate simple semantic similarity.

        This is a simplified version. In production, use embedding-based similarity.

        Args:
            context: Context text
            query: Query text

        Returns:
            Score between 0.0 and 1.0
        """
        # Look for phrase matches (2-3 word sequences)
        context_lower = context.lower()
        query_words = re.findall(r"\b\w+\b", query.lower())

        if len(query_words) < 2:
            return 0.0

        match_count = 0
        total_phrases = 0

        # Check 2-word phrases
        for i in range(len(query_words) - 1):
            phrase = f"{query_words[i]} {query_words[i + 1]}"
            total_phrases += 1
            if phrase in context_lower:
                match_count += 1

        # Check 3-word phrases
        for i in range(len(query_words) - 2):
            phrase = f"{query_words[i]} {query_words[i + 1]} {query_words[i + 2]}"
            total_phrases += 1
            if phrase in context_lower:
                match_count += 2  # Weight longer phrases more

        score = match_count / total_phrases if total_phrases > 0 else 0.0

        return min(1.0, score)

    def _recency_score(self, timestamp: Any) -> float:
        """Calculate recency score.

        Args:
            timestamp: Timestamp (datetime or other)

        Returns:
            Score between 0.0 and 1.0 (1.0 = most recent)
        """
        # Simplified: in production, calculate based on actual time difference
        # For now, return default
        return 0.7

    def rank_contexts(
        self,
        contexts: list[tuple[str, dict[str, Any]]],
        query: str,
    ) -> list[tuple[str, RelevanceMetrics]]:
        """Rank multiple contexts by relevance.

        Args:
            contexts: List of (context_text, metadata) tuples
            query: Query to compare against

        Returns:
            Sorted list of (context, metrics) tuples (highest score first)
        """
        scored_contexts: list[tuple[str, RelevanceMetrics]] = []

        for context, metadata in contexts:
            metrics = self.score_relevance(context, query, metadata)
            scored_contexts.append((context, metrics))

        # Sort by overall score (descending)
        scored_contexts.sort(key=lambda x: x[1].overall_score, reverse=True)

        logger.debug(f"Ranked {len(scored_contexts)} contexts")

        return scored_contexts

    def filter_by_threshold(
        self,
        contexts: list[tuple[str, RelevanceMetrics]],
        threshold: float = 0.5,
    ) -> list[tuple[str, RelevanceMetrics]]:
        """Filter contexts by minimum relevance threshold.

        Args:
            contexts: List of (context, metrics) tuples
            threshold: Minimum overall score required

        Returns:
            Filtered list
        """
        filtered = [
            (ctx, metrics) for ctx, metrics in contexts if metrics.overall_score >= threshold
        ]

        logger.debug(
            f"Filtered to {len(filtered)}/{len(contexts)} contexts above threshold {threshold}"
        )

        return filtered
