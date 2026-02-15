"""Context relevance scoring utilities.

This module provides:
- Keyword-based relevance scoring
- Embedding-based semantic similarity
- Recency and importance weighting
- Context ranking and filtering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import re
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Protocol for embedding providers."""

    async def aembed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score between 0.0 and 1.0
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    a = np.array(vec1)
    b = np.array(vec2)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


@dataclass
class RelevanceMetrics:
    """Metrics for context relevance."""

    keyword_score: float = 0.0  # Keyword overlap score
    semantic_score: float = 0.0  # Semantic similarity (if embeddings available)
    recency_score: float = 0.0  # How recent is the information
    importance_score: float = 0.0  # Explicit importance marking
    overall_score: float = 0.0  # Combined score
    embedding: list[float] = field(default_factory=list)  # Cached embedding

    def calculate_overall(self, weights: dict[str, float] | None = None) -> float:
        """Calculate weighted overall score.

        Args:
            weights: Dictionary of weights for each metric

        Returns:
            Overall relevance score
        """
        if weights is None:
            weights = {
                "keyword": 0.25,
                "semantic": 0.40,  # Higher weight for semantic in production
                "recency": 0.20,
                "importance": 0.15,
            }

        self.overall_score = (
            self.keyword_score * weights.get("keyword", 0.25)
            + self.semantic_score * weights.get("semantic", 0.40)
            + self.recency_score * weights.get("recency", 0.20)
            + self.importance_score * weights.get("importance", 0.15)
        )

        return self.overall_score


class ContextRelevanceScorer:
    """Scores context relevance for adaptive selection.

    Supports:
    - Keyword overlap scoring (Jaccard similarity)
    - Embedding-based semantic similarity
    - Recency-based scoring with exponential decay
    - Importance weighting from metadata
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        weights: dict[str, float] | None = None,
        recency_half_life_hours: float = 24.0,
    ) -> None:
        """Initialize relevance scorer.

        Args:
            embedder: Optional embedder for semantic similarity
            weights: Custom weights for scoring components
            recency_half_life_hours: Hours for recency score to halve
        """
        self.embedder = embedder
        self.weights = weights
        self.recency_half_life_hours = recency_half_life_hours
        self._embedding_cache: dict[str, list[float]] = {}
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

        # Importance score (from priority, salience, or importance in metadata)
        if metadata:
            if "priority" in metadata:
                metrics.importance_score = min(1.0, metadata["priority"] / 10.0)
            elif "salience" in metadata:
                metrics.importance_score = float(metadata["salience"])
            elif "importance" in metadata:
                metrics.importance_score = float(metadata["importance"])

        # Calculate overall
        metrics.calculate_overall(self.weights)

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
        """Calculate recency score using exponential decay.

        Args:
            timestamp: Timestamp (datetime, str, or float)

        Returns:
            Score between 0.0 and 1.0 (1.0 = most recent)
        """
        now = datetime.now(UTC)

        # Parse timestamp
        if isinstance(timestamp, datetime):
            ts = timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        elif isinstance(timestamp, str):
            try:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                return 0.5  # Default if unparseable
        elif isinstance(timestamp, int | float):
            ts = datetime.fromtimestamp(timestamp, tz=UTC)
        else:
            return 0.5  # Default for unknown types

        # Calculate age in hours
        age_hours = (now - ts).total_seconds() / 3600.0

        if age_hours <= 0:
            return 1.0

        # Exponential decay
        import math

        decay = math.pow(0.5, age_hours / self.recency_half_life_hours)

        return max(0.1, decay)  # Floor at 0.1

    async def ascore_relevance(
        self,
        context: str,
        query: str,
        metadata: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> RelevanceMetrics:
        """Async score relevance with embedding-based semantic similarity.

        Args:
            context: Context text to score
            query: Query/task to compare against
            metadata: Optional metadata (timestamp, priority, embedding)
            query_embedding: Pre-computed query embedding

        Returns:
            RelevanceMetrics with scores
        """
        metrics = RelevanceMetrics()

        # Keyword score (sync)
        metrics.keyword_score = self._keyword_overlap_score(context, query)

        # Semantic score with embeddings
        if self.embedder:
            metrics.semantic_score = await self._embedding_semantic_score(
                context, query, metadata, query_embedding
            )
        else:
            metrics.semantic_score = self._simple_semantic_score(context, query)

        # Recency score
        if metadata and "timestamp" in metadata:
            metrics.recency_score = self._recency_score(metadata["timestamp"])

        # Importance score
        if metadata:
            if "priority" in metadata:
                metrics.importance_score = min(1.0, metadata["priority"] / 10.0)
            elif "salience" in metadata:
                metrics.importance_score = float(metadata["salience"])
            elif "importance" in metadata:
                metrics.importance_score = float(metadata["importance"])

        # Calculate overall
        metrics.calculate_overall(self.weights)

        return metrics

    async def _embedding_semantic_score(
        self,
        context: str,
        query: str,
        metadata: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> float:
        """Calculate semantic similarity using embeddings.

        Args:
            context: Context text
            query: Query text
            metadata: Optional metadata containing pre-computed embedding
            query_embedding: Pre-computed query embedding

        Returns:
            Cosine similarity score between 0.0 and 1.0
        """
        if not self.embedder:
            return self._simple_semantic_score(context, query)

        # Get context embedding (from metadata cache or compute)
        context_embedding: list[float] = []
        if metadata and "embedding" in metadata:
            context_embedding = metadata["embedding"]
        elif context in self._embedding_cache:
            context_embedding = self._embedding_cache[context]
        else:
            try:
                embeddings = await self.embedder.aembed([context])
                if embeddings and embeddings[0]:
                    context_embedding = embeddings[0]
                    # Cache for future use
                    self._embedding_cache[context] = context_embedding
            except Exception as e:
                logger.warning(f"Failed to compute context embedding: {e}")
                return self._simple_semantic_score(context, query)

        # Get query embedding
        if query_embedding is None:
            if query in self._embedding_cache:
                query_embedding = self._embedding_cache[query]
            else:
                try:
                    embeddings = await self.embedder.aembed([query])
                    if embeddings and embeddings[0]:
                        query_embedding = embeddings[0]
                        self._embedding_cache[query] = query_embedding
                except Exception as e:
                    logger.warning(f"Failed to compute query embedding: {e}")
                    return self._simple_semantic_score(context, query)

        if not context_embedding or not query_embedding:
            return self._simple_semantic_score(context, query)

        similarity = cosine_similarity(context_embedding, query_embedding)
        logger.debug(f"Embedding similarity: {similarity:.3f}")

        return similarity

    async def arank_contexts(
        self,
        contexts: list[tuple[str, dict[str, Any]]],
        query: str,
    ) -> list[tuple[str, RelevanceMetrics]]:
        """Async rank multiple contexts by relevance with embeddings.

        Args:
            contexts: List of (context_text, metadata) tuples
            query: Query to compare against

        Returns:
            Sorted list of (context, metrics) tuples (highest score first)
        """
        # Pre-compute query embedding once
        query_embedding: list[float] | None = None
        if self.embedder:
            try:
                embeddings = await self.embedder.aembed([query])
                if embeddings and embeddings[0]:
                    query_embedding = embeddings[0]
            except Exception as e:
                logger.warning(f"Failed to compute query embedding: {e}")

        scored_contexts: list[tuple[str, RelevanceMetrics]] = []

        for context, metadata in contexts:
            metrics = await self.ascore_relevance(context, query, metadata, query_embedding)
            scored_contexts.append((context, metrics))

        # Sort by overall score (descending)
        scored_contexts.sort(key=lambda x: x[1].overall_score, reverse=True)

        logger.debug(f"Ranked {len(scored_contexts)} contexts with embeddings")

        return scored_contexts

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
