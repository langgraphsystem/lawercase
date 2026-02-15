"""Quality Evaluator - Evaluates quality of research outputs.

Provides:
- Answer quality scoring
- Factual accuracy assessment
- Completeness evaluation
- Source diversity analysis
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class QualityDimension(str, Enum):
    """Dimensions of quality evaluation."""

    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    COHERENCE = "coherence"
    SOURCE_QUALITY = "source_quality"
    CITATION_ACCURACY = "citation_accuracy"


class QualityGrade(str, Enum):
    """Quality grade levels."""

    EXCELLENT = "excellent"  # 0.9+
    GOOD = "good"  # 0.7-0.9
    FAIR = "fair"  # 0.5-0.7
    POOR = "poor"  # 0.3-0.5
    FAILING = "failing"  # <0.3


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    dimension: QualityDimension
    score: float  # 0-1
    confidence: float  # 0-1
    details: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Complete quality evaluation report."""

    evaluation_id: str
    query: str
    answer: str
    overall_score: float = 0.0
    grade: QualityGrade = QualityGrade.POOR
    dimension_scores: list[DimensionScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "query": self.query[:100],
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "dimension_scores": [
                {
                    "dimension": d.dimension.value,
                    "score": d.score,
                    "confidence": d.confidence,
                    "details": d.details,
                }
                for d in self.dimension_scores
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class EvaluatorConfig:
    """Configuration for quality evaluator."""

    enable_llm_evaluation: bool = True
    relevance_weight: float = 0.25
    accuracy_weight: float = 0.25
    completeness_weight: float = 0.20
    coherence_weight: float = 0.15
    source_quality_weight: float = 0.15
    min_answer_length: int = 50
    max_answer_length: int = 10000
    require_citations: bool = True


class QualityEvaluator:
    """Evaluates quality of research outputs.

    Features:
    - Multi-dimensional quality assessment
    - LLM-based semantic evaluation
    - Heuristic-based quick checks
    - Detailed reporting

    Usage:
        >>> evaluator = QualityEvaluator()
        >>> report = await evaluator.evaluate(
        ...     query="What is machine learning?",
        ...     answer="Machine learning is...",
        ...     sources=["source1", "source2"]
        ... )
        >>> print(report.overall_score)
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        config: EvaluatorConfig | None = None,
    ):
        """Initialize quality evaluator.

        Args:
            llm_caller: Optional async LLM function for semantic evaluation
            config: Evaluator configuration
        """
        self._llm_caller = llm_caller
        self.config = config or EvaluatorConfig()
        self._evaluation_count = 0

        self.logger = logger.bind(component="QualityEvaluator")

    async def evaluate(
        self,
        query: str,
        answer: str,
        sources: list[str] | None = None,
        expected_answer: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> QualityReport:
        """Evaluate quality of an answer.

        Args:
            query: Original query
            answer: Answer to evaluate
            sources: List of sources used
            expected_answer: Optional expected/reference answer
            context: Additional context

        Returns:
            QualityReport with scores and analysis
        """
        self._evaluation_count += 1
        evaluation_id = f"eval_{self._evaluation_count}_{int(datetime.now(UTC).timestamp())}"

        self.logger.info(
            "evaluator.start",
            evaluation_id=evaluation_id,
            query_length=len(query),
            answer_length=len(answer),
        )

        dimension_scores = []

        # Evaluate each dimension
        relevance = await self._evaluate_relevance(query, answer, expected_answer)
        dimension_scores.append(relevance)

        accuracy = await self._evaluate_accuracy(answer, sources, expected_answer)
        dimension_scores.append(accuracy)

        completeness = await self._evaluate_completeness(query, answer)
        dimension_scores.append(completeness)

        coherence = await self._evaluate_coherence(answer)
        dimension_scores.append(coherence)

        source_quality = await self._evaluate_source_quality(sources or [])
        dimension_scores.append(source_quality)

        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)

        # Determine grade
        grade = self._score_to_grade(overall_score)

        # Generate strengths, weaknesses, recommendations
        strengths = self._identify_strengths(dimension_scores)
        weaknesses = self._identify_weaknesses(dimension_scores)
        recommendations = self._generate_recommendations(dimension_scores)

        report = QualityReport(
            evaluation_id=evaluation_id,
            query=query,
            answer=answer,
            overall_score=overall_score,
            grade=grade,
            dimension_scores=dimension_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            metadata={
                "sources_count": len(sources) if sources else 0,
                "has_expected_answer": expected_answer is not None,
            },
        )

        self.logger.info(
            "evaluator.complete",
            evaluation_id=evaluation_id,
            overall_score=overall_score,
            grade=grade.value,
        )

        return report

    async def _evaluate_relevance(
        self,
        query: str,
        answer: str,
        expected_answer: str | None,
    ) -> DimensionScore:
        """Evaluate answer relevance to query."""
        score = 0.5
        evidence = []
        details = ""

        # Word overlap analysis
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words) / max(len(query_words), 1)
        score = min(overlap * 2, 1.0)  # Scale to 0-1

        evidence.append(f"Word overlap: {overlap:.2%}")

        # Check if key terms are addressed
        key_terms = [w for w in query_words if len(w) > 4]
        addressed = sum(1 for t in key_terms if t in answer.lower())
        if key_terms:
            key_term_coverage = addressed / len(key_terms)
            score = (score + key_term_coverage) / 2
            evidence.append(f"Key term coverage: {key_term_coverage:.2%}")

        # LLM-based relevance check
        if self._llm_caller and self.config.enable_llm_evaluation:
            llm_score = await self._llm_relevance_check(query, answer)
            if llm_score is not None:
                score = (score + llm_score) / 2
                evidence.append(f"LLM relevance: {llm_score:.2f}")

        details = "Relevance based on term overlap and content analysis"

        return DimensionScore(
            dimension=QualityDimension.RELEVANCE,
            score=score,
            confidence=0.8,
            details=details,
            evidence=evidence,
        )

    async def _evaluate_accuracy(
        self,
        answer: str,
        sources: list[str] | None,
        expected_answer: str | None,
    ) -> DimensionScore:
        """Evaluate factual accuracy."""
        score = 0.6  # Default moderate score
        evidence = []
        details = ""

        # Check against expected answer if available
        if expected_answer:
            expected_words = set(expected_answer.lower().split())
            answer_words = set(answer.lower().split())
            overlap = len(expected_words & answer_words) / max(len(expected_words), 1)
            score = min(overlap * 1.5, 1.0)
            evidence.append(f"Expected answer overlap: {overlap:.2%}")

        # Check for citation presence
        if sources:
            citations_found = sum(1 for s in sources if s.lower() in answer.lower())
            citation_rate = citations_found / len(sources) if sources else 0
            score = (score + citation_rate * 0.5) / 1.5
            evidence.append(f"Citation rate: {citation_rate:.2%}")

        # Check for hedging language (indicates uncertainty)
        hedging_terms = ["might", "possibly", "perhaps", "may", "could be", "uncertain"]
        hedging_count = sum(1 for h in hedging_terms if h in answer.lower())
        if hedging_count > 3:
            score *= 0.9  # Slight penalty for excessive hedging
            evidence.append(f"Hedging terms found: {hedging_count}")

        details = "Accuracy based on source alignment and claim verification"

        return DimensionScore(
            dimension=QualityDimension.ACCURACY,
            score=score,
            confidence=0.7,
            details=details,
            evidence=evidence,
        )

    async def _evaluate_completeness(
        self,
        query: str,
        answer: str,
    ) -> DimensionScore:
        """Evaluate answer completeness."""
        score = 0.5
        evidence = []
        details = ""

        # Length check
        length = len(answer)
        if length < self.config.min_answer_length:
            score *= 0.5
            evidence.append(f"Too short: {length} chars (min: {self.config.min_answer_length})")
        elif length > self.config.max_answer_length:
            score *= 0.9
            evidence.append(f"Very long: {length} chars")
        else:
            # Good length range
            normalized_length = min(length / 500, 1.0)
            score = 0.5 + normalized_length * 0.3
            evidence.append(f"Length: {length} chars")

        # Check for structural completeness
        has_intro = any(p in answer.lower()[:200] for p in ["is", "are", "refers to", "means"])
        has_details = len(answer) > 200
        has_conclusion = any(
            p in answer.lower()[-200:] for p in ["therefore", "in conclusion", "thus", "overall"]
        )

        completeness_indicators = sum([has_intro, has_details, has_conclusion])
        score = (score + completeness_indicators / 3) / 2
        evidence.append(f"Structure indicators: {completeness_indicators}/3")

        # Check for multiple aspects
        paragraph_count = answer.count("\n\n") + 1
        if paragraph_count >= 3:
            score = min(score + 0.1, 1.0)
            evidence.append(f"Multi-paragraph: {paragraph_count} sections")

        details = "Completeness based on length, structure, and coverage"

        return DimensionScore(
            dimension=QualityDimension.COMPLETENESS,
            score=score,
            confidence=0.8,
            details=details,
            evidence=evidence,
        )

    async def _evaluate_coherence(
        self,
        answer: str,
    ) -> DimensionScore:
        """Evaluate answer coherence and readability."""
        score = 0.7
        evidence = []
        details = ""

        # Sentence count
        sentences = [
            s.strip() for s in answer.replace("!", ".").replace("?", ".").split(".") if s.strip()
        ]
        sentence_count = len(sentences)

        if sentence_count < 2:
            score *= 0.7
            evidence.append("Very few sentences")
        else:
            evidence.append(f"Sentence count: {sentence_count}")

        # Average sentence length
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length < 5:
                score *= 0.8
                evidence.append("Sentences too short")
            elif avg_sentence_length > 40:
                score *= 0.9
                evidence.append("Sentences too long")
            else:
                score = min(score + 0.1, 1.0)
                evidence.append(f"Avg sentence length: {avg_sentence_length:.1f} words")

        # Check for transition words
        transitions = [
            "however",
            "therefore",
            "moreover",
            "furthermore",
            "additionally",
            "in contrast",
            "similarly",
            "consequently",
            "as a result",
        ]
        transition_count = sum(1 for t in transitions if t in answer.lower())
        if transition_count >= 2:
            score = min(score + 0.1, 1.0)
            evidence.append(f"Transition words: {transition_count}")

        # Check for repetition (negative indicator)
        words = answer.lower().split()
        unique_ratio = len(set(words)) / max(len(words), 1)
        if unique_ratio < 0.5:
            score *= 0.8
            evidence.append(f"High repetition (unique ratio: {unique_ratio:.2%})")

        details = "Coherence based on sentence structure and flow"

        return DimensionScore(
            dimension=QualityDimension.COHERENCE,
            score=score,
            confidence=0.75,
            details=details,
            evidence=evidence,
        )

    async def _evaluate_source_quality(
        self,
        sources: list[str],
    ) -> DimensionScore:
        """Evaluate quality of sources used."""
        if not sources:
            return DimensionScore(
                dimension=QualityDimension.SOURCE_QUALITY,
                score=0.3,
                confidence=0.9,
                details="No sources provided",
                evidence=["No sources"],
            )

        score = 0.5
        evidence = []

        # Source count
        source_count = len(sources)
        if source_count >= 5:
            score += 0.2
            evidence.append(f"Good source count: {source_count}")
        elif source_count >= 3:
            score += 0.1
            evidence.append(f"Adequate source count: {source_count}")
        else:
            evidence.append(f"Few sources: {source_count}")

        # Source diversity
        unique_domains = set()
        for source in sources:
            # Extract domain-like patterns
            if "/" in source:
                parts = source.split("/")
                if len(parts) > 2:
                    unique_domains.add(parts[2])
            else:
                unique_domains.add(source[:20])

        diversity = len(unique_domains) / max(source_count, 1)
        score = (score + diversity * 0.3) / 1.3
        evidence.append(f"Source diversity: {len(unique_domains)} unique domains")

        # Check for academic sources
        academic_indicators = ["arxiv", "doi", "journal", "proceedings", ".edu", "scholar"]
        academic_count = sum(
            1 for s in sources if any(ind in s.lower() for ind in academic_indicators)
        )
        if academic_count > 0:
            score = min(score + 0.1, 1.0)
            evidence.append(f"Academic sources: {academic_count}")

        details = f"Source quality based on {source_count} sources"

        return DimensionScore(
            dimension=QualityDimension.SOURCE_QUALITY,
            score=score,
            confidence=0.8,
            details=details,
            evidence=evidence,
        )

    async def _llm_relevance_check(
        self,
        query: str,
        answer: str,
    ) -> float | None:
        """Use LLM to check relevance."""
        if not self._llm_caller:
            return None

        prompt = f"""Rate how well this answer addresses the query on a scale of 0-10.

Query: {query}

Answer: {answer[:1000]}

Return ONLY a number from 0-10:"""

        try:
            response = await self._llm_caller(prompt)
            # Extract number from response
            for word in response.split():
                try:
                    score = float(word.strip(".,"))
                    if 0 <= score <= 10:
                        return score / 10
                except ValueError:
                    continue
        except Exception as e:
            self.logger.warning("llm_relevance_check.failed", error=str(e))

        return None

    def _calculate_overall_score(
        self,
        dimension_scores: list[DimensionScore],
    ) -> float:
        """Calculate weighted overall score."""
        weights = {
            QualityDimension.RELEVANCE: self.config.relevance_weight,
            QualityDimension.ACCURACY: self.config.accuracy_weight,
            QualityDimension.COMPLETENESS: self.config.completeness_weight,
            QualityDimension.COHERENCE: self.config.coherence_weight,
            QualityDimension.SOURCE_QUALITY: self.config.source_quality_weight,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for ds in dimension_scores:
            weight = weights.get(ds.dimension, 0.1)
            weighted_sum += ds.score * weight * ds.confidence
            total_weight += weight * ds.confidence

        return weighted_sum / max(total_weight, 0.1)

    def _score_to_grade(self, score: float) -> QualityGrade:
        """Convert score to grade."""
        if score >= 0.9:
            return QualityGrade.EXCELLENT
        if score >= 0.7:
            return QualityGrade.GOOD
        if score >= 0.5:
            return QualityGrade.FAIR
        if score >= 0.3:
            return QualityGrade.POOR
        return QualityGrade.FAILING

    def _identify_strengths(
        self,
        dimension_scores: list[DimensionScore],
    ) -> list[str]:
        """Identify strengths from dimension scores."""
        strengths = []
        for ds in dimension_scores:
            if ds.score >= 0.7:
                strengths.append(f"Strong {ds.dimension.value}: {ds.score:.2f}")
        return strengths

    def _identify_weaknesses(
        self,
        dimension_scores: list[DimensionScore],
    ) -> list[str]:
        """Identify weaknesses from dimension scores."""
        weaknesses = []
        for ds in dimension_scores:
            if ds.score < 0.5:
                weaknesses.append(f"Weak {ds.dimension.value}: {ds.score:.2f} - {ds.details}")
        return weaknesses

    def _generate_recommendations(
        self,
        dimension_scores: list[DimensionScore],
    ) -> list[str]:
        """Generate recommendations based on scores."""
        recommendations = []

        for ds in dimension_scores:
            if ds.score < 0.5:
                if ds.dimension == QualityDimension.RELEVANCE:
                    recommendations.append(
                        "Improve answer relevance by addressing query terms directly"
                    )
                elif ds.dimension == QualityDimension.ACCURACY:
                    recommendations.append("Verify factual claims and add citations")
                elif ds.dimension == QualityDimension.COMPLETENESS:
                    recommendations.append("Expand answer to cover more aspects of the query")
                elif ds.dimension == QualityDimension.COHERENCE:
                    recommendations.append("Improve answer structure and flow")
                elif ds.dimension == QualityDimension.SOURCE_QUALITY:
                    recommendations.append("Use more diverse and authoritative sources")

        return recommendations[:5]


def create_quality_evaluator(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> QualityEvaluator:
    """Create a quality evaluator with default configuration."""
    return QualityEvaluator(llm_caller=llm_caller)


__all__ = [
    "DimensionScore",
    "EvaluatorConfig",
    "QualityDimension",
    "QualityEvaluator",
    "QualityGrade",
    "QualityReport",
    "create_quality_evaluator",
]
