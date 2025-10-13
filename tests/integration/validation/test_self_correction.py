"""Integration tests for self-correcting agents."""

from __future__ import annotations

import asyncio

import pytest

from core.groupagents.self_correcting_mixin import SelfCorrectingAgent, SelfCorrectingMixin
from core.validation import (
    ConfidenceScorer,
    ConfidenceThreshold,
    QualityTracker,
    RetryConfig,
    RetryHandler,
    RetryStrategy,
)


# Confidence Scoring Tests
def test_confidence_scorer_basic():
    """Test basic confidence scoring."""
    scorer = ConfidenceScorer()

    metrics = scorer.score_output(
        output="The capital of France is Paris.",
        context={"query": "What is the capital of France?"},
    )

    assert 0.0 <= metrics.overall_confidence <= 1.0
    assert metrics.completeness_score > 0
    assert metrics.relevance_score > 0
    assert metrics.coherence_score > 0


def test_confidence_scorer_high_quality():
    """Test scoring of high-quality output."""
    scorer = ConfidenceScorer()

    metrics = scorer.score_output(
        output="The capital of France is Paris. It is located in the north-central part "
        "of the country and is known for its art, culture, and iconic landmarks.",
        context={"query": "What is the capital of France?"},
        expected_length=100,
    )

    assert metrics.overall_confidence > 0.7
    assert metrics.threshold in [ConfidenceThreshold.HIGH, ConfidenceThreshold.VERY_HIGH]
    assert not metrics.needs_correction


def test_confidence_scorer_low_quality():
    """Test scoring of low-quality output."""
    scorer = ConfidenceScorer()

    metrics = scorer.score_output(
        output="maybe paris?",
        context={"query": "What is the capital of France?"},
    )

    assert metrics.overall_confidence < 0.7
    assert metrics.needs_review or metrics.needs_correction
    assert len(metrics.suggestions) > 0


def test_confidence_scorer_format_json():
    """Test format scoring for JSON."""
    scorer = ConfidenceScorer()

    metrics = scorer.score_output(
        output='{"capital": "Paris", "country": "France"}',
        expected_format="json",
    )

    assert metrics.format_score > 0.7


def test_confidence_scorer_format_markdown():
    """Test format scoring for Markdown."""
    scorer = ConfidenceScorer()

    metrics = scorer.score_output(
        output="# Capital\n\nThe capital is **Paris**.",
        expected_format="markdown",
    )

    assert metrics.format_score > 0.7


# Retry Handler Tests
@pytest.mark.asyncio
async def test_retry_handler_success_first_try():
    """Test retry handler with immediate success."""
    handler = RetryHandler()
    call_count = 0

    async def mock_function(query: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"High quality response to {query}"

    config = RetryConfig(max_retries=3, min_confidence=0.5)

    result, metrics, info = await handler.retry_with_validation(
        mock_function,
        config,
        query="test",
        context={"query": "test"},
    )

    assert call_count == 1
    assert info["attempts"] == 1
    assert metrics.overall_confidence >= 0.5


@pytest.mark.asyncio
async def test_retry_handler_retry_until_success():
    """Test retry handler with retries."""
    handler = RetryHandler()
    call_count = 0

    async def mock_function_with_improvement(query: str) -> str:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return "bad"  # Low confidence
        if call_count == 2:
            return "maybe better?"  # Still low
        return f"A comprehensive and detailed response to {query}"  # High confidence

    config = RetryConfig(
        max_retries=3,
        min_confidence=0.6,
        strategy=RetryStrategy.IMMEDIATE,
    )

    result, metrics, info = await handler.retry_with_validation(
        mock_function_with_improvement,
        config,
        query="test",
        context={"query": "test"},
    )

    assert call_count >= 2
    assert info["attempts"] >= 2
    assert metrics.overall_confidence >= 0.6


@pytest.mark.asyncio
async def test_retry_handler_max_retries_exceeded():
    """Test retry handler when max retries exceeded."""
    handler = RetryHandler()

    async def mock_bad_function(query: str) -> str:
        return "bad"  # Always low confidence

    config = RetryConfig(
        max_retries=2,
        min_confidence=0.8,
        strategy=RetryStrategy.IMMEDIATE,
    )

    with pytest.raises(ValueError, match="Max retries"):
        await handler.retry_with_validation(
            mock_bad_function,
            config,
            query="test",
            context={"query": "test"},
        )


@pytest.mark.asyncio
async def test_retry_handler_timeout():
    """Test retry handler timeout."""
    handler = RetryHandler()

    async def mock_slow_function(query: str) -> str:
        await asyncio.sleep(0.5)
        return "response"

    config = RetryConfig(
        max_retries=10,
        min_confidence=0.9,  # Will never reach this
        strategy=RetryStrategy.FIXED_DELAY,
        base_delay=0.2,
        timeout=1.0,  # 1 second total timeout
    )

    with pytest.raises(TimeoutError):
        await handler.retry_with_validation(
            mock_slow_function,
            config,
            query="test",
            context={"query": "test"},
        )


# Quality Tracker Tests
def test_quality_tracker_record():
    """Test quality tracker recording."""
    tracker = QualityTracker()

    tracker.record_operation(
        agent_name="test_agent",
        confidence_score=0.85,
        retry_count=1,
        duration_seconds=2.5,
        success=True,
    )

    stats = tracker.get_agent_stats("test_agent")
    assert stats["total_operations"] == 1
    assert stats["successful_operations"] == 1
    assert stats["avg_confidence"] == 0.85


def test_quality_tracker_multiple_operations():
    """Test quality tracker with multiple operations."""
    tracker = QualityTracker()

    # Record several operations
    for i in range(5):
        tracker.record_operation(
            agent_name="test_agent",
            confidence_score=0.7 + i * 0.05,
            retry_count=i % 2,
            duration_seconds=1.0 + i * 0.5,
            success=i < 4,  # Last one fails
        )

    stats = tracker.get_agent_stats("test_agent")
    assert stats["total_operations"] == 5
    assert stats["successful_operations"] == 4
    assert stats["failed_operations"] == 1
    assert 0.7 <= stats["avg_confidence"] <= 0.9


def test_quality_tracker_trend_analysis():
    """Test quality trend analysis."""
    tracker = QualityTracker()

    # Create improving trend
    for i in range(20):
        confidence = 0.5 + (i / 40)  # Gradually improving
        tracker.record_operation(
            agent_name="test_agent",
            confidence_score=confidence,
            retry_count=max(0, 3 - i // 5),  # Decreasing retries
            duration_seconds=3.0 - (i / 10),  # Decreasing duration
            success=True,
        )

    trend = tracker.get_quality_trend("test_agent")
    assert trend["status"] == "analyzed"
    assert trend["confidence_trend"] == "improving"


def test_quality_tracker_anomaly_detection():
    """Test anomaly detection."""
    tracker = QualityTracker()

    # Record normal operations
    for _ in range(20):
        tracker.record_operation(
            agent_name="test_agent",
            confidence_score=0.8,
            retry_count=1,
            duration_seconds=2.0,
            success=True,
        )

    # Record anomalous operation
    tracker.record_operation(
        agent_name="test_agent",
        confidence_score=0.2,  # Very low
        retry_count=5,  # Very high
        duration_seconds=10.0,  # Very high
        success=False,
    )

    anomalies = tracker.detect_anomalies("test_agent", threshold=2.0)
    assert len(anomalies) > 0
    assert "unusual_confidence" in anomalies[0]["reasons"]


# Self-Correcting Mixin Tests
class TestAgent(SelfCorrectingMixin):
    """Test agent for mixin testing."""

    def __init__(self):
        super().__init__()
        self.call_count = 0

    async def process(self, query: str, quality: str = "high") -> str:
        """Process with configurable quality."""
        self.call_count += 1

        if quality == "high":
            return f"A comprehensive and detailed answer to {query} with proper formatting."
        if quality == "medium":
            return f"Answer to {query}."
        return "bad"


@pytest.mark.asyncio
async def test_self_correcting_mixin_success():
    """Test self-correcting mixin with successful operation."""
    agent = TestAgent()

    result = await agent.with_self_correction(
        agent.process,
        "test query",
        quality="high",
        min_confidence=0.6,
    )

    assert result["success"] is True
    assert "result" in result
    assert result["confidence"]["overall_confidence"] >= 0.6
    assert agent.call_count == 1


@pytest.mark.asyncio
async def test_self_correcting_mixin_retry():
    """Test self-correcting mixin with retry."""
    agent = TestAgent()

    # Start with low quality, agent will retry
    result = await agent.with_self_correction(
        agent.process,
        "test query",
        quality="low",
        min_confidence=0.8,
        max_retries=2,
    )

    # Should fail after retries with low quality
    assert result["success"] is False
    assert "error" in result
    assert agent.call_count == 2  # Initial + retries


@pytest.mark.asyncio
async def test_self_correcting_mixin_quality_stats():
    """Test quality stats tracking in mixin."""
    agent = TestAgent()

    # Perform several operations
    for _ in range(3):
        await agent.with_self_correction(
            agent.process,
            "test query",
            quality="high",
            min_confidence=0.6,
        )

    stats = agent.get_quality_stats()
    assert stats["total_operations"] == 3
    assert stats["successful_operations"] == 3


@pytest.mark.asyncio
async def test_self_correcting_agent_standalone():
    """Test standalone self-correcting agent."""
    agent = SelfCorrectingAgent()

    result = await agent.process_query("What is AI?", min_confidence=0.5)

    assert result["success"] is True
    assert "result" in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_validate_and_correct():
    """Test validate and correct functionality."""
    agent = TestAgent()

    result = await agent.validate_and_correct(
        output="short",
        context={"query": "Explain AI in detail"},
        max_corrections=2,
    )

    # Should identify low confidence
    assert "confidence" in result
    assert result["corrections_applied"] >= 0


def test_set_quality_thresholds():
    """Test setting quality thresholds."""
    agent = TestAgent()

    agent.set_quality_thresholds(min_confidence=0.85, max_retries=5)

    assert agent._default_min_confidence == 0.85
    assert agent._default_max_retries == 5


def test_score_output_method():
    """Test score_output method on agent."""
    agent = TestAgent()

    metrics = agent.score_output(
        "The capital of France is Paris",
        context={"query": "What is the capital of France?"},
    )

    assert "overall_confidence" in metrics
    assert 0.0 <= metrics["overall_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent self-correcting operations."""
    agent = TestAgent()

    # Run multiple operations concurrently
    tasks = [
        agent.with_self_correction(
            agent.process,
            f"query_{i}",
            quality="high",
            min_confidence=0.6,
        )
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(r["success"] for r in results)


def test_retry_stats():
    """Test retry handler statistics."""
    handler = RetryHandler()

    # Initially empty
    stats = handler.get_stats()
    assert stats["total_retries"] == 0

    handler.reset_stats()
    stats = handler.get_stats()
    assert stats["successful_retries"] == 0
