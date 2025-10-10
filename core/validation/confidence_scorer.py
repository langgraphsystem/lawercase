"""Confidence Scoring System.

This module provides confidence scoring for agent outputs to determine
if results need self-correction or human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class ConfidenceThreshold(str, Enum):
    """Confidence thresholds for different actions."""

    VERY_LOW = "very_low"  # < 0.3 - требует переделки
    LOW = "low"  # 0.3-0.5 - требует проверки
    MEDIUM = "medium"  # 0.5-0.7 - приемлемо с предупреждением
    HIGH = "high"  # 0.7-0.9 - хорошо
    VERY_HIGH = "very_high"  # > 0.9 - отлично


@dataclass
class ConfidenceMetrics:
    """Confidence metrics for an agent output."""

    # Core metrics
    overall_confidence: float = 0.0  # 0-1

    # Component scores
    completeness_score: float = 0.0  # Полнота ответа
    relevance_score: float = 0.0  # Релевантность
    coherence_score: float = 0.0  # Связность и логика
    factual_score: float = 0.0  # Фактическая точность
    format_score: float = 0.0  # Соответствие формату

    # Meta information
    threshold: ConfidenceThreshold = ConfidenceThreshold.MEDIUM
    needs_review: bool = False
    needs_correction: bool = False
    suggestions: list[str] = field(default_factory=list)

    # Detailed breakdown
    metrics_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_confidence": self.overall_confidence,
            "completeness_score": self.completeness_score,
            "relevance_score": self.relevance_score,
            "coherence_score": self.coherence_score,
            "factual_score": self.factual_score,
            "format_score": self.format_score,
            "threshold": self.threshold.value,
            "needs_review": self.needs_review,
            "needs_correction": self.needs_correction,
            "suggestions": self.suggestions,
            "metrics_breakdown": self.metrics_breakdown,
        }


class ConfidenceScorer:
    """
    Confidence scoring system for agent outputs.

    Evaluates outputs across multiple dimensions and provides
    confidence score with actionable recommendations.

    Example:
        >>> scorer = ConfidenceScorer()
        >>> metrics = scorer.score_output(
        ...     output="The capital of France is Paris.",
        ...     context={"query": "What is the capital of France?"}
        ... )
        >>> print(metrics.overall_confidence)
        0.95
    """

    def __init__(
        self,
        completeness_weight: float = 0.25,
        relevance_weight: float = 0.25,
        coherence_weight: float = 0.2,
        factual_weight: float = 0.2,
        format_weight: float = 0.1,
    ):
        """
        Initialize confidence scorer.

        Args:
            completeness_weight: Weight for completeness score
            relevance_weight: Weight for relevance score
            coherence_weight: Weight for coherence score
            factual_weight: Weight for factual accuracy score
            format_weight: Weight for format compliance score
        """
        self.weights = {
            "completeness": completeness_weight,
            "relevance": relevance_weight,
            "coherence": coherence_weight,
            "factual": factual_weight,
            "format": format_weight,
        }

        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def score_output(
        self,
        output: str,
        context: dict[str, Any] | None = None,
        expected_length: int | None = None,
        expected_format: str | None = None,
    ) -> ConfidenceMetrics:
        """
        Score an agent output.

        Args:
            output: The agent's output text
            context: Context dict with query, sources, etc.
            expected_length: Expected output length (optional)
            expected_format: Expected format (json, markdown, etc.)

        Returns:
            ConfidenceMetrics with scores and recommendations

        Example:
            >>> metrics = scorer.score_output(
            ...     "The capital is Paris",
            ...     {"query": "What is the capital of France?"}
            ... )
        """
        context = context or {}
        metrics = ConfidenceMetrics()

        # Score components
        metrics.completeness_score = self._score_completeness(output, context, expected_length)
        metrics.relevance_score = self._score_relevance(output, context)
        metrics.coherence_score = self._score_coherence(output)
        metrics.factual_score = self._score_factual(output, context)
        metrics.format_score = self._score_format(output, expected_format)

        # Calculate overall confidence
        metrics.overall_confidence = (
            metrics.completeness_score * self.weights["completeness"]
            + metrics.relevance_score * self.weights["relevance"]
            + metrics.coherence_score * self.weights["coherence"]
            + metrics.factual_score * self.weights["factual"]
            + metrics.format_score * self.weights["format"]
        )

        # Determine threshold
        metrics.threshold = self._determine_threshold(metrics.overall_confidence)

        # Determine actions
        metrics.needs_review = metrics.overall_confidence < 0.7
        metrics.needs_correction = metrics.overall_confidence < 0.5

        # Generate suggestions
        metrics.suggestions = self._generate_suggestions(metrics, context)

        # Detailed breakdown
        metrics.metrics_breakdown = {
            "completeness": metrics.completeness_score,
            "relevance": metrics.relevance_score,
            "coherence": metrics.coherence_score,
            "factual": metrics.factual_score,
            "format": metrics.format_score,
        }

        return metrics

    def _score_completeness(
        self,
        output: str,
        context: dict[str, Any],
        expected_length: int | None,
    ) -> float:
        """Score completeness of the output."""
        score = 0.5  # Base score

        # Check length
        output_length = len(output.strip())
        if output_length == 0:
            return 0.0

        # If expected length provided
        if expected_length:
            length_ratio = min(output_length / expected_length, 1.0)
            score += length_ratio * 0.3

        # Check if query is addressed
        query = context.get("query", "")
        if query:
            # Simple keyword matching
            query_words = set(query.lower().split())
            output_words = set(output.lower().split())
            overlap = len(query_words & output_words) / max(len(query_words), 1)
            score += overlap * 0.2

        # Check for common completeness indicators
        if any(marker in output.lower() for marker in ["in conclusion", "summary", "finally"]):
            score += 0.1

        return min(score, 1.0)

    def _score_relevance(self, output: str, context: dict[str, Any]) -> float:
        """Score relevance to the query/context."""
        score = 0.5  # Base score

        query = context.get("query", "")
        if not query:
            return 0.7  # Default if no query provided

        # Keyword relevance
        query_keywords = set(query.lower().split())
        output_keywords = set(output.lower().split())

        if not output_keywords:
            return 0.0

        overlap = len(query_keywords & output_keywords)
        relevance_ratio = overlap / len(query_keywords) if query_keywords else 0.0

        score = 0.3 + relevance_ratio * 0.7

        # Check for direct answer indicators
        if any(phrase in output.lower() for phrase in ["the answer is", "is:", "result:"]):
            score = min(score + 0.1, 1.0)

        return min(score, 1.0)

    def _score_coherence(self, output: str) -> float:
        """Score coherence and logical flow."""
        score = 0.5  # Base score

        if not output.strip():
            return 0.0

        sentences = output.split(".")
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.3

        # Check for sentence count (too few or too many fragments)
        if 2 <= len(sentences) <= 10:
            score += 0.2

        # Check for transition words
        transitions = [
            "however",
            "therefore",
            "moreover",
            "furthermore",
            "additionally",
            "consequently",
            "thus",
            "hence",
        ]
        transition_count = sum(1 for t in transitions if t in output.lower())
        score += min(transition_count * 0.05, 0.2)

        # Check for proper capitalization
        properly_capitalized = sum(1 for s in sentences if s and s[0].isupper())
        if properly_capitalized == len(sentences):
            score += 0.1

        return min(score, 1.0)

    def _score_factual(self, output: str, context: dict[str, Any]) -> float:
        """Score factual accuracy (basic heuristics)."""
        score = 0.7  # Default score (neutral)

        # Check for uncertainty markers (lower confidence)
        uncertainty_markers = [
            "might",
            "maybe",
            "perhaps",
            "possibly",
            "unclear",
            "uncertain",
            "not sure",
        ]
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in output.lower())

        if uncertainty_count > 0:
            score -= min(uncertainty_count * 0.1, 0.3)

        # Check for confidence markers (higher confidence)
        confidence_markers = [
            "definitely",
            "certainly",
            "clearly",
            "undoubtedly",
            "confirmed",
        ]
        confidence_count = sum(1 for marker in confidence_markers if marker in output.lower())

        if confidence_count > 0:
            score += min(confidence_count * 0.05, 0.2)

        # Check for citations/sources (if available in context)
        sources = context.get("sources", [])
        if sources and any(source_ref in output for source_ref in ["[", "source", "according to"]):
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def _score_format(self, output: str, expected_format: str | None) -> float:
        """Score format compliance."""
        if not expected_format:
            return 0.8  # Neutral score if no format expected

        score = 0.5  # Base score

        if expected_format.lower() == "json":
            # Check for JSON-like structure
            if output.strip().startswith("{") and output.strip().endswith("}"):
                score += 0.3
            if '"' in output or "'" in output:
                score += 0.1
            if ":" in output:
                score += 0.1

        elif expected_format.lower() == "markdown":
            # Check for markdown elements
            if re.search(r"^#+\s", output, re.MULTILINE):  # Headers
                score += 0.2
            if "**" in output or "__" in output:  # Bold
                score += 0.1
            if "*" in output or "_" in output:  # Italic
                score += 0.1
            if re.search(r"\[.+\]\(.+\)", output):  # Links
                score += 0.1

        elif expected_format.lower() == "list":
            # Check for list structure
            if re.search(r"^[-*•]\s", output, re.MULTILINE):
                score += 0.3
            if re.search(r"^\d+\.\s", output, re.MULTILINE):
                score += 0.3

        return min(score, 1.0)

    def _determine_threshold(self, confidence: float) -> ConfidenceThreshold:
        """Determine confidence threshold."""
        if confidence < 0.3:
            return ConfidenceThreshold.VERY_LOW
        if confidence < 0.5:
            return ConfidenceThreshold.LOW
        if confidence < 0.7:
            return ConfidenceThreshold.MEDIUM
        if confidence < 0.9:
            return ConfidenceThreshold.HIGH
        return ConfidenceThreshold.VERY_HIGH

    def _generate_suggestions(
        self,
        metrics: ConfidenceMetrics,
        context: dict[str, Any],
    ) -> list[str]:
        """Generate actionable suggestions."""
        suggestions = []

        if metrics.completeness_score < 0.6:
            suggestions.append(
                "Output appears incomplete. Consider providing more detail or context."
            )

        if metrics.relevance_score < 0.6:
            suggestions.append("Output may not fully address the query. Review relevance.")

        if metrics.coherence_score < 0.6:
            suggestions.append(
                "Output lacks coherence. Consider improving logical flow and transitions."
            )

        if metrics.factual_score < 0.6:
            suggestions.append(
                "Factual confidence is low. Verify information and add citations if possible."
            )

        if metrics.format_score < 0.6:
            suggestions.append(
                "Output doesn't match expected format. Review formatting requirements."
            )

        if metrics.overall_confidence < 0.5:
            suggestions.append(
                "Overall confidence is low. Consider regenerating with different parameters."
            )

        return suggestions


# Global singleton
_confidence_scorer: ConfidenceScorer | None = None


def get_confidence_scorer() -> ConfidenceScorer:
    """
    Get global confidence scorer instance.

    Returns:
        ConfidenceScorer instance

    Example:
        >>> scorer = get_confidence_scorer()
        >>> metrics = scorer.score_output("output text")
    """
    global _confidence_scorer

    if _confidence_scorer is None:
        _confidence_scorer = ConfidenceScorer()

    return _confidence_scorer
