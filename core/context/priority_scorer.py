"""Priority Scorer for context relevance ranking.

Scores and ranks context items by relevance to the query/task.
Supports multiple scoring strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class ScoringStrategy(str, Enum):
    """Available scoring strategies."""

    KEYWORD = "keyword"  # Keyword matching
    SEMANTIC = "semantic"  # Embedding similarity
    RECENCY = "recency"  # Time-based
    IMPORTANCE = "importance"  # Pre-assigned importance
    HYBRID = "hybrid"  # Combined strategies
    TASK_SPECIFIC = "task_specific"  # Task-aware scoring


@dataclass(slots=True)
class ScoredItem:
    """Item with relevance score."""

    content: str
    score: float  # 0.0 - 1.0
    source: str = ""
    item_type: str = "text"
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Component scores for debugging
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    recency_score: float = 0.0
    importance_score: float = 0.0


class BaseScoringStrategy(ABC):
    """Abstract base for scoring strategies."""

    @abstractmethod
    def score(self, item: str, query: str, **kwargs: Any) -> float:
        """Score an item against a query."""


class KeywordScorer(BaseScoringStrategy):
    """Score by keyword overlap."""

    def __init__(self, case_sensitive: bool = False) -> None:
        self.case_sensitive = case_sensitive

    def _tokenize(self, text: str) -> set[str]:
        """Simple word tokenization."""
        if not self.case_sensitive:
            text = text.lower()
        # Extract words (alphanumeric)
        words = re.findall(r"\b\w+\b", text)
        return set(words)

    def score(self, item: str, query: str, **kwargs: Any) -> float:
        """Score by Jaccard similarity of keywords."""
        item_tokens = self._tokenize(item)
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return 0.0

        intersection = item_tokens & query_tokens
        union = item_tokens | query_tokens

        if not union:
            return 0.0

        # Jaccard similarity
        jaccard = len(intersection) / len(union)

        # Also consider query coverage (how many query terms are found)
        coverage = len(intersection) / len(query_tokens) if query_tokens else 0

        # Weighted combination
        return 0.4 * jaccard + 0.6 * coverage


class RecencyScorer(BaseScoringStrategy):
    """Score by recency (newer = higher score)."""

    def __init__(self, decay_factor: float = 0.1) -> None:
        """
        Args:
            decay_factor: How quickly score decays with age (days)
        """
        self.decay_factor = decay_factor

    def score(self, item: str, query: str, **kwargs: Any) -> float:
        """Score by timestamp if available."""
        import time

        timestamp = kwargs.get("timestamp")
        if timestamp is None:
            return 0.5  # Neutral score if no timestamp

        # Calculate age in days
        now = time.time()
        age_days = (now - timestamp) / 86400

        # Exponential decay
        import math

        score = math.exp(-self.decay_factor * age_days)

        return min(1.0, max(0.0, score))


class ImportanceScorer(BaseScoringStrategy):
    """Score by pre-assigned importance."""

    # Importance weights by source type
    DEFAULT_WEIGHTS: dict[str, float] = {
        "user_input": 1.0,
        "case_data": 0.95,
        "legal_reference": 0.9,
        "policy": 0.85,
        "example": 0.8,
        "historical": 0.7,
        "general": 0.5,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or self.DEFAULT_WEIGHTS

    def score(self, item: str, query: str, **kwargs: Any) -> float:
        """Score by source type importance."""
        source_type = kwargs.get("source_type", "general")
        return self.weights.get(source_type, 0.5)


class TaskSpecificScorer(BaseScoringStrategy):
    """Score based on task type relevance."""

    # Task-specific keyword boosts
    TASK_KEYWORDS: dict[str, list[str]] = {
        "legal_analysis": [
            "statute",
            "regulation",
            "precedent",
            "court",
            "ruling",
            "cfr",
            "usc",
            "uscis",
            "criteria",
            "eligibility",
            "evidence",
        ],
        "document_generation": [
            "template",
            "format",
            "structure",
            "letter",
            "petition",
            "exhibit",
            "recommendation",
            "draft",
        ],
        "research": [
            "study",
            "research",
            "finding",
            "data",
            "statistic",
            "analysis",
            "report",
            "publication",
        ],
        "code_generation": [
            "function",
            "class",
            "method",
            "api",
            "implementation",
            "code",
            "algorithm",
            "test",
        ],
    }

    def score(self, item: str, query: str, **kwargs: Any) -> float:
        """Score by task-specific relevance."""
        task_type = kwargs.get("task_type", "general")
        keywords = self.TASK_KEYWORDS.get(task_type, [])

        if not keywords:
            return 0.5

        item_lower = item.lower()
        matches = sum(1 for kw in keywords if kw in item_lower)

        return min(1.0, matches / max(3, len(keywords) * 0.3))


class PriorityScorer:
    """Combined priority scoring with multiple strategies.

    Usage:
        scorer = PriorityScorer()

        items = ["Legal document about EB-1A...", "General info..."]
        scored = scorer.score_items(
            items=items,
            query="EB-1A eligibility criteria",
            task_type="legal_analysis"
        )

        # Get top items by score
        top_items = scorer.get_top_k(scored, k=5)
    """

    def __init__(
        self,
        strategy: ScoringStrategy = ScoringStrategy.HYBRID,
        weights: dict[str, float] | None = None,
    ) -> None:
        """Initialize priority scorer.

        Args:
            strategy: Primary scoring strategy
            weights: Weights for hybrid scoring
        """
        self.strategy = strategy
        self.weights = weights or {
            "keyword": 0.3,
            "semantic": 0.3,
            "recency": 0.1,
            "importance": 0.2,
            "task_specific": 0.1,
        }

        # Initialize sub-scorers
        self._keyword_scorer = KeywordScorer()
        self._recency_scorer = RecencyScorer()
        self._importance_scorer = ImportanceScorer()
        self._task_scorer = TaskSpecificScorer()

    def score_item(
        self,
        content: str,
        query: str,
        source: str = "",
        **kwargs: Any,
    ) -> ScoredItem:
        """Score a single item.

        Args:
            content: Item content to score
            query: Query to score against
            source: Source identifier
            **kwargs: Additional context (task_type, timestamp, etc.)

        Returns:
            ScoredItem with relevance score
        """
        # Calculate component scores
        keyword_score = self._keyword_scorer.score(content, query)
        recency_score = self._recency_scorer.score(content, query, **kwargs)
        importance_score = self._importance_scorer.score(content, query, **kwargs)
        task_score = self._task_scorer.score(content, query, **kwargs)

        # Semantic score placeholder (would need embeddings)
        semantic_score = keyword_score  # Fallback to keyword

        # Calculate final score based on strategy
        if self.strategy == ScoringStrategy.KEYWORD:
            final_score = keyword_score
        elif self.strategy == ScoringStrategy.RECENCY:
            final_score = recency_score
        elif self.strategy == ScoringStrategy.IMPORTANCE:
            final_score = importance_score
        elif self.strategy == ScoringStrategy.TASK_SPECIFIC:
            final_score = task_score
        else:  # HYBRID
            final_score = (
                self.weights.get("keyword", 0.3) * keyword_score
                + self.weights.get("semantic", 0.3) * semantic_score
                + self.weights.get("recency", 0.1) * recency_score
                + self.weights.get("importance", 0.2) * importance_score
                + self.weights.get("task_specific", 0.1) * task_score
            )

        # Estimate tokens (rough: ~4 chars per token)
        tokens = len(content) // 4

        return ScoredItem(
            content=content,
            score=min(1.0, max(0.0, final_score)),
            source=source,
            tokens=tokens,
            metadata=kwargs,
            keyword_score=keyword_score,
            semantic_score=semantic_score,
            recency_score=recency_score,
            importance_score=importance_score,
        )

    def score_items(
        self,
        items: list[str | dict[str, Any]],
        query: str,
        **kwargs: Any,
    ) -> list[ScoredItem]:
        """Score multiple items.

        Args:
            items: List of content strings or dicts with content/metadata
            query: Query to score against
            **kwargs: Default context for all items

        Returns:
            List of ScoredItems sorted by score (descending)
        """
        scored = []

        for item in items:
            if isinstance(item, str):
                content = item
                item_kwargs = kwargs.copy()
            else:
                content = item.get("content", str(item))
                item_kwargs = {**kwargs, **item}

            scored_item = self.score_item(
                content=content,
                query=query,
                source=item_kwargs.get("source", ""),
                **item_kwargs,
            )
            scored.append(scored_item)

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)

        return scored

    def get_top_k(
        self,
        scored_items: list[ScoredItem],
        k: int = 10,
        min_score: float = 0.0,
    ) -> list[ScoredItem]:
        """Get top K items by score.

        Args:
            scored_items: Pre-scored items
            k: Number of items to return
            min_score: Minimum score threshold

        Returns:
            Top K items above threshold
        """
        filtered = [item for item in scored_items if item.score >= min_score]
        return filtered[:k]

    def fit_to_budget(
        self,
        scored_items: list[ScoredItem],
        max_tokens: int,
        min_items: int = 1,
    ) -> list[ScoredItem]:
        """Select items that fit within token budget.

        Args:
            scored_items: Pre-scored and sorted items
            max_tokens: Maximum total tokens
            min_items: Minimum items to include (even if over budget)

        Returns:
            Items that fit within budget
        """
        selected = []
        total_tokens = 0

        for item in scored_items:
            if total_tokens + item.tokens <= max_tokens or len(selected) < min_items:
                selected.append(item)
                total_tokens += item.tokens
            else:
                break

        return selected
