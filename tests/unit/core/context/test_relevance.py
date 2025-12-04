"""Tests for context relevance scoring module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.context.relevance import (ContextRelevanceScorer, RelevanceMetrics,
                                    cosine_similarity)


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        """Test cosine similarity of identical vectors."""
        vec = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.001

    def test_orthogonal_vectors(self) -> None:
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001

    def test_opposite_vectors(self) -> None:
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity + 1.0) < 0.001

    def test_empty_vectors(self) -> None:
        """Test cosine similarity with empty vectors."""
        assert cosine_similarity([], []) == 0.0
        assert cosine_similarity([1.0], []) == 0.0

    def test_different_length_vectors(self) -> None:
        """Test cosine similarity with different length vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_zero_vector(self) -> None:
        """Test cosine similarity with zero vector."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_similar_vectors(self) -> None:
        """Test cosine similarity of similar but not identical vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.1, 2.1, 3.1]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity > 0.99


class TestRelevanceMetrics:
    """Tests for RelevanceMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = RelevanceMetrics()
        assert metrics.keyword_score == 0.0
        assert metrics.semantic_score == 0.0
        assert metrics.recency_score == 0.0
        assert metrics.importance_score == 0.0
        assert metrics.overall_score == 0.0

    def test_calculate_overall_default_weights(self) -> None:
        """Test overall calculation with default weights."""
        metrics = RelevanceMetrics(
            keyword_score=1.0,
            semantic_score=1.0,
            recency_score=1.0,
            importance_score=1.0,
        )
        overall = metrics.calculate_overall()
        assert overall == 1.0
        assert metrics.overall_score == 1.0

    def test_calculate_overall_custom_weights(self) -> None:
        """Test overall calculation with custom weights."""
        metrics = RelevanceMetrics(
            keyword_score=1.0,
            semantic_score=0.0,
            recency_score=0.0,
            importance_score=0.0,
        )
        weights = {"keyword": 1.0, "semantic": 0.0, "recency": 0.0, "importance": 0.0}
        overall = metrics.calculate_overall(weights)
        assert overall == 1.0

    def test_calculate_overall_mixed_scores(self) -> None:
        """Test overall calculation with mixed scores."""
        metrics = RelevanceMetrics(
            keyword_score=0.8,
            semantic_score=0.6,
            recency_score=0.4,
            importance_score=0.2,
        )
        overall = metrics.calculate_overall()
        # Check that overall is a weighted average
        assert 0.0 < overall < 1.0


class TestContextRelevanceScorer:
    """Tests for ContextRelevanceScorer class."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_init_default(self) -> None:
        """Test default initialization."""
        scorer = ContextRelevanceScorer()
        assert scorer.embedder is None
        assert scorer.recency_half_life_hours == 24.0

    def test_init_custom_half_life(self) -> None:
        """Test initialization with custom half life."""
        scorer = ContextRelevanceScorer(recency_half_life_hours=48.0)
        assert scorer.recency_half_life_hours == 48.0


class TestKeywordOverlapScore:
    """Tests for keyword overlap scoring."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_exact_match(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for exact matching text."""
        context = "immigration visa application"
        query = "immigration visa application"
        metrics = scorer.score_relevance(context, query)
        assert metrics.keyword_score > 0.5

    def test_partial_match(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for partial matching text."""
        context = "immigration visa application process"
        query = "visa application"
        metrics = scorer.score_relevance(context, query)
        assert metrics.keyword_score > 0.0

    def test_no_match(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for non-matching text."""
        context = "weather forecast tomorrow sunny"
        query = "immigration visa application"
        metrics = scorer.score_relevance(context, query)
        assert metrics.keyword_score == 0.0

    def test_stopwords_removed(self, scorer: ContextRelevanceScorer) -> None:
        """Test that stopwords don't affect score."""
        context = "the visa is for immigration"
        query = "visa for immigration"
        metrics = scorer.score_relevance(context, query)
        # Should match on non-stopwords
        assert metrics.keyword_score > 0.0


class TestSimpleSemanticScore:
    """Tests for simple semantic scoring (phrase matching)."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_phrase_match(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for phrase matching."""
        context = "The visa application process is complex"
        query = "visa application process"
        metrics = scorer.score_relevance(context, query)
        assert metrics.semantic_score > 0.0

    def test_no_phrase_match(self, scorer: ContextRelevanceScorer) -> None:
        """Test score when no phrases match."""
        context = "visa document form"
        query = "application processing time"
        metrics = scorer.score_relevance(context, query)
        # May still have some score from partial matches
        assert metrics.semantic_score >= 0.0

    def test_single_word_query(self, scorer: ContextRelevanceScorer) -> None:
        """Test score with single word query."""
        context = "visa application process"
        query = "visa"
        metrics = scorer.score_relevance(context, query)
        # Single word can't form phrases
        assert metrics.semantic_score == 0.0


class TestRecencyScore:
    """Tests for recency scoring."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer(recency_half_life_hours=24.0)

    def test_recent_timestamp(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for recent timestamp."""
        recent = datetime.now(UTC) - timedelta(hours=1)
        metrics = scorer.score_relevance("context", "query", metadata={"timestamp": recent})
        assert metrics.recency_score > 0.9

    def test_old_timestamp(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for old timestamp."""
        old = datetime.now(UTC) - timedelta(days=7)
        metrics = scorer.score_relevance("context", "query", metadata={"timestamp": old})
        assert metrics.recency_score < 0.5

    def test_string_timestamp(self, scorer: ContextRelevanceScorer) -> None:
        """Test score with ISO string timestamp."""
        recent = datetime.now(UTC).isoformat()
        metrics = scorer.score_relevance("context", "query", metadata={"timestamp": recent})
        assert metrics.recency_score > 0.9

    def test_no_timestamp(self, scorer: ContextRelevanceScorer) -> None:
        """Test score without timestamp."""
        metrics = scorer.score_relevance("context", "query", metadata={})
        assert metrics.recency_score == 0.0


class TestImportanceScore:
    """Tests for importance scoring from metadata."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_priority_high(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for high priority."""
        metrics = scorer.score_relevance("context", "query", metadata={"priority": 10})
        assert metrics.importance_score == 1.0

    def test_priority_low(self, scorer: ContextRelevanceScorer) -> None:
        """Test score for low priority."""
        metrics = scorer.score_relevance("context", "query", metadata={"priority": 3})
        assert metrics.importance_score == 0.3

    def test_salience_metadata(self, scorer: ContextRelevanceScorer) -> None:
        """Test score from salience metadata."""
        metrics = scorer.score_relevance("context", "query", metadata={"salience": 0.75})
        assert metrics.importance_score == 0.75

    def test_importance_metadata(self, scorer: ContextRelevanceScorer) -> None:
        """Test score from importance metadata."""
        metrics = scorer.score_relevance("context", "query", metadata={"importance": 0.6})
        assert metrics.importance_score == 0.6


class TestRankContexts:
    """Tests for context ranking."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_rank_by_relevance(self, scorer: ContextRelevanceScorer) -> None:
        """Test ranking contexts by relevance."""
        contexts = [
            ("unrelated content about weather", {}),
            ("visa application immigration process", {}),
            ("some other topic entirely", {}),
        ]
        query = "visa immigration application"
        ranked = scorer.rank_contexts(contexts, query)

        # Most relevant should be first
        assert len(ranked) == 3
        assert "visa" in ranked[0][0]

    def test_rank_empty_list(self, scorer: ContextRelevanceScorer) -> None:
        """Test ranking empty context list."""
        ranked = scorer.rank_contexts([], "query")
        assert ranked == []


class TestFilterByThreshold:
    """Tests for threshold filtering."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    def test_filter_low_scores(self, scorer: ContextRelevanceScorer) -> None:
        """Test filtering out low-scoring contexts."""
        contexts = [
            ("visa application", {"priority": 10}),
            ("weather forecast", {}),
        ]
        query = "visa application"
        ranked = scorer.rank_contexts(contexts, query)
        filtered = scorer.filter_by_threshold(ranked, threshold=0.3)

        # Should filter out low-relevance items
        assert len(filtered) <= len(ranked)

    def test_filter_all(self, scorer: ContextRelevanceScorer) -> None:
        """Test filtering with high threshold."""
        ranked = [
            ("context", RelevanceMetrics(overall_score=0.2)),
        ]
        filtered = scorer.filter_by_threshold(ranked, threshold=0.9)
        assert len(filtered) == 0

    def test_filter_none(self, scorer: ContextRelevanceScorer) -> None:
        """Test filtering with low threshold."""
        ranked = [
            ("context", RelevanceMetrics(overall_score=0.8)),
        ]
        filtered = scorer.filter_by_threshold(ranked, threshold=0.1)
        assert len(filtered) == 1


class TestAsyncMethods:
    """Tests for async relevance scoring methods."""

    @pytest.fixture
    def scorer(self) -> ContextRelevanceScorer:
        return ContextRelevanceScorer()

    @pytest.mark.asyncio
    async def test_ascore_relevance(self, scorer: ContextRelevanceScorer) -> None:
        """Test async score_relevance."""
        metrics = await scorer.ascore_relevance(
            "visa application process", "immigration visa", metadata={"priority": 8}
        )
        assert metrics.keyword_score > 0.0
        assert metrics.importance_score == 0.8

    @pytest.mark.asyncio
    async def test_arank_contexts(self, scorer: ContextRelevanceScorer) -> None:
        """Test async context ranking."""
        contexts = [
            ("visa application", {}),
            ("weather report", {}),
        ]
        ranked = await scorer.arank_contexts(contexts, "visa immigration")
        assert len(ranked) == 2
        # Most relevant first
        assert "visa" in ranked[0][0]
