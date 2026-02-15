"""Deep Research Bench - Quality Metrics and Evaluation.

Implements benchmarks for evaluating research quality:
- Completeness and coverage metrics
- Fact verification pipeline
- Citation accuracy validation
- Comparison with baselines
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Dimensions of research quality."""

    COMPLETENESS = "completeness"  # Coverage of topic
    ACCURACY = "accuracy"  # Factual correctness
    RELEVANCE = "relevance"  # Relevance to query
    COHERENCE = "coherence"  # Logical flow
    CITATION_QUALITY = "citation_quality"  # Source quality
    DEPTH = "depth"  # Analysis depth
    NOVELTY = "novelty"  # New insights


class VerificationStatus(str, Enum):
    """Status of fact verification."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


@dataclass
class QualityScore:
    """Quality score for a research output."""

    dimension: QualityDimension
    score: float  # 0-1
    confidence: float = 0.8
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "confidence": self.confidence,
            "evidence": self.evidence[:3],
            "metadata": self.metadata,
        }


@dataclass
class FactVerificationResult:
    """Result of verifying a fact."""

    fact: str
    status: VerificationStatus
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    confidence: float = 0.5
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": self.fact[:200],
            "status": self.status.value,
            "supporting_sources": len(self.supporting_sources),
            "contradicting_sources": len(self.contradicting_sources),
            "confidence": self.confidence,
        }


@dataclass
class CitationValidation:
    """Result of validating a citation."""

    citation: str
    is_valid: bool
    source_exists: bool
    content_matches: bool
    relevance_score: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation": self.citation[:100],
            "is_valid": self.is_valid,
            "source_exists": self.source_exists,
            "content_matches": self.content_matches,
            "relevance_score": self.relevance_score,
        }


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""

    query: str
    overall_score: float
    quality_scores: dict[QualityDimension, QualityScore]
    fact_verifications: list[FactVerificationResult]
    citation_validations: list[CitationValidation]
    comparison_to_baseline: dict[str, float]
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "overall_score": self.overall_score,
            "quality_scores": {k.value: v.to_dict() for k, v in self.quality_scores.items()},
            "fact_verification_count": len(self.fact_verifications),
            "citation_validation_count": len(self.citation_validations),
            "comparison_to_baseline": self.comparison_to_baseline,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class QualityEvaluator:
    """Evaluates research quality across dimensions."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

    async def evaluate(
        self,
        query: str,
        response: str,
        sources: list[str],
    ) -> dict[QualityDimension, QualityScore]:
        """Evaluate research quality across all dimensions."""
        scores = {}

        # Evaluate each dimension
        scores[QualityDimension.COMPLETENESS] = await self._evaluate_completeness(query, response)
        scores[QualityDimension.RELEVANCE] = await self._evaluate_relevance(query, response)
        scores[QualityDimension.COHERENCE] = await self._evaluate_coherence(response)
        scores[QualityDimension.DEPTH] = await self._evaluate_depth(response)
        scores[QualityDimension.CITATION_QUALITY] = await self._evaluate_citations(
            response, sources
        )

        return scores

    async def _evaluate_completeness(
        self,
        query: str,
        response: str,
    ) -> QualityScore:
        """Evaluate topic coverage completeness."""
        if self._llm_caller:
            prompt = f"""Rate how completely this response covers all aspects of the query.
Score from 0 (incomplete) to 10 (comprehensive).

Query: {query}
Response: {response[:1000]}

Score (just the number):"""
            try:
                result = await self._llm_caller(prompt)
                score = float(result.strip()) / 10
                return QualityScore(
                    dimension=QualityDimension.COMPLETENESS,
                    score=min(1.0, max(0.0, score)),
                    confidence=0.8,
                )
            except Exception:
                pass

        # Heuristic: based on response length and query terms
        query_terms = set(query.lower().split())
        response_lower = response.lower()
        covered = sum(1 for term in query_terms if term in response_lower)
        coverage = covered / len(query_terms) if query_terms else 0

        return QualityScore(
            dimension=QualityDimension.COMPLETENESS,
            score=coverage,
            confidence=0.6,
        )

    async def _evaluate_relevance(
        self,
        query: str,
        response: str,
    ) -> QualityScore:
        """Evaluate relevance to the query."""
        if self._llm_caller:
            prompt = f"""Rate how relevant this response is to the query.
Score from 0 (irrelevant) to 10 (highly relevant).

Query: {query}
Response: {response[:1000]}

Score (just the number):"""
            try:
                result = await self._llm_caller(prompt)
                score = float(result.strip()) / 10
                return QualityScore(
                    dimension=QualityDimension.RELEVANCE,
                    score=min(1.0, max(0.0, score)),
                    confidence=0.8,
                )
            except Exception:
                pass

        # Heuristic: keyword overlap
        query_words = set(query.lower().split())
        response_words = set(response.lower().split()[:500])
        overlap = len(query_words & response_words)

        return QualityScore(
            dimension=QualityDimension.RELEVANCE,
            score=min(1.0, overlap / max(len(query_words), 1)),
            confidence=0.5,
        )

    async def _evaluate_coherence(self, response: str) -> QualityScore:
        """Evaluate logical coherence and flow."""
        if self._llm_caller:
            prompt = f"""Rate the logical coherence and flow of this text.
Score from 0 (incoherent) to 10 (perfectly coherent).

Text: {response[:1000]}

Score (just the number):"""
            try:
                result = await self._llm_caller(prompt)
                score = float(result.strip()) / 10
                return QualityScore(
                    dimension=QualityDimension.COHERENCE,
                    score=min(1.0, max(0.0, score)),
                    confidence=0.7,
                )
            except Exception:
                pass

        # Heuristic: sentence structure
        sentences = response.split(".")
        avg_sentence_length = (
            sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        )
        # Ideal range: 15-25 words
        if 15 <= avg_sentence_length <= 25:
            coherence = 0.8
        elif 10 <= avg_sentence_length <= 30:
            coherence = 0.6
        else:
            coherence = 0.4

        return QualityScore(
            dimension=QualityDimension.COHERENCE,
            score=coherence,
            confidence=0.4,
        )

    async def _evaluate_depth(self, response: str) -> QualityScore:
        """Evaluate analysis depth."""
        # Heuristics for depth
        word_count = len(response.split())
        has_analysis_words = any(
            word in response.lower()
            for word in ["because", "therefore", "however", "although", "suggests", "indicates"]
        )
        has_examples = "for example" in response.lower() or "such as" in response.lower()
        has_data = any(char.isdigit() for char in response)

        score = 0.3  # Base
        if word_count > 200:
            score += 0.2
        if word_count > 500:
            score += 0.1
        if has_analysis_words:
            score += 0.2
        if has_examples:
            score += 0.1
        if has_data:
            score += 0.1

        return QualityScore(
            dimension=QualityDimension.DEPTH,
            score=min(1.0, score),
            confidence=0.5,
        )

    async def _evaluate_citations(
        self,
        response: str,
        sources: list[str],
    ) -> QualityScore:
        """Evaluate citation quality."""
        if not sources:
            return QualityScore(
                dimension=QualityDimension.CITATION_QUALITY,
                score=0.5,  # Neutral if no sources
                confidence=0.3,
            )

        # Check for diverse sources
        unique_domains = set()
        for source in sources:
            if "/" in source:
                domain = source.split("/")[2] if source.count("/") > 1 else source
                unique_domains.add(domain)

        diversity_score = min(len(unique_domains) / 5, 1.0)  # 5+ unique sources = 1.0

        # Check for authoritative sources
        authoritative_keywords = [".gov", ".edu", "arxiv", "pubmed", "nature", "science"]
        authority_count = sum(
            1 for s in sources if any(kw in s.lower() for kw in authoritative_keywords)
        )
        authority_score = min(authority_count / 3, 1.0)

        combined_score = 0.5 * diversity_score + 0.5 * authority_score

        return QualityScore(
            dimension=QualityDimension.CITATION_QUALITY,
            score=combined_score,
            confidence=0.6,
            metadata={"unique_domains": len(unique_domains), "authoritative": authority_count},
        )


class FactChecker:
    """Verifies factual claims in research output."""

    def __init__(
        self,
        verifier: Callable[[str], Coroutine[Any, Any, dict[str, Any]]] | None = None,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._verifier = verifier
        self._llm_caller = llm_caller

    async def extract_facts(self, text: str) -> list[str]:
        """Extract verifiable facts from text."""
        if self._llm_caller:
            prompt = f"""Extract specific, verifiable facts from this text.
List one fact per line. Only include objective claims that can be verified.

Text: {text[:1500]}

Facts:"""
            try:
                result = await self._llm_caller(prompt)
                facts = [
                    line.strip().lstrip("-•0123456789.) ")
                    for line in result.split("\n")
                    if line.strip() and len(line.strip()) > 10
                ]
                return facts[:10]
            except Exception:
                pass

        # Fallback: extract sentences with numbers or specific claims
        sentences = text.replace("\n", " ").split(".")
        facts = []
        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned) > 20 and (
                any(c.isdigit() for c in cleaned)
                or any(
                    word in cleaned.lower() for word in ["is", "are", "was", "were", "has", "have"]
                )
            ):
                facts.append(cleaned)
                if len(facts) >= 10:
                    break
        return facts

    async def verify_fact(self, fact: str) -> FactVerificationResult:
        """Verify a single fact."""
        if self._verifier:
            try:
                result = await self._verifier(fact)
                return FactVerificationResult(
                    fact=fact,
                    status=VerificationStatus(result.get("status", "unverified")),
                    supporting_sources=result.get("supporting", []),
                    contradicting_sources=result.get("contradicting", []),
                    confidence=result.get("confidence", 0.5),
                )
            except Exception:
                pass

        # Default: unverified
        return FactVerificationResult(
            fact=fact,
            status=VerificationStatus.UNVERIFIED,
            confidence=0.3,
            notes="No verification source available",
        )

    async def verify_all(self, facts: list[str]) -> list[FactVerificationResult]:
        """Verify multiple facts."""
        tasks = [self.verify_fact(fact) for fact in facts]
        return await asyncio.gather(*tasks)


class CitationValidator:
    """Validates citations and sources."""

    def __init__(
        self,
        url_checker: Callable[[str], Coroutine[Any, Any, bool]] | None = None,
    ):
        self._url_checker = url_checker

    async def validate(
        self,
        citation: str,
        context: str = "",
    ) -> CitationValidation:
        """Validate a single citation."""
        # Check if URL exists
        source_exists = True
        if citation.startswith("http"):
            if self._url_checker:
                try:
                    source_exists = await self._url_checker(citation)
                except Exception:
                    source_exists = False

        # Basic validation
        is_valid = bool(citation) and len(citation) > 5

        # Relevance score based on context match
        relevance = 0.5
        if context:
            citation_words = set(citation.lower().split())
            context_words = set(context.lower().split())
            overlap = len(citation_words & context_words)
            relevance = min(overlap / max(len(citation_words), 1), 1.0)

        return CitationValidation(
            citation=citation,
            is_valid=is_valid,
            source_exists=source_exists,
            content_matches=relevance > 0.3,
            relevance_score=relevance,
        )

    async def validate_all(
        self,
        citations: list[str],
        context: str = "",
    ) -> list[CitationValidation]:
        """Validate multiple citations."""
        tasks = [self.validate(c, context) for c in citations]
        return await asyncio.gather(*tasks)


class BaselineComparator:
    """Compares research output against baseline models."""

    def __init__(self):
        self._baselines: dict[str, Callable] = {}

    def register_baseline(
        self,
        name: str,
        baseline_fn: Callable[[str], Coroutine[Any, Any, str]],
    ) -> None:
        """Register a baseline model."""
        self._baselines[name] = baseline_fn

    async def compare(
        self,
        query: str,
        our_response: str,
        our_score: float,
        evaluator: QualityEvaluator,
    ) -> dict[str, float]:
        """Compare against baselines."""
        comparisons = {}

        for name, baseline_fn in self._baselines.items():
            try:
                baseline_response = await baseline_fn(query)
                baseline_scores = await evaluator.evaluate(query, baseline_response, [])

                baseline_overall = sum(s.score for s in baseline_scores.values()) / len(
                    baseline_scores
                )

                # Relative improvement
                if baseline_overall > 0:
                    improvement = (our_score - baseline_overall) / baseline_overall
                else:
                    improvement = our_score

                comparisons[name] = improvement
            except Exception as e:
                logger.warning(f"Baseline comparison failed for {name}: {e}")
                comparisons[name] = 0.0

        return comparisons


class DeepResearchBench:
    """Main benchmark suite for deep research evaluation."""

    def __init__(
        self,
        evaluator: QualityEvaluator | None = None,
        fact_checker: FactChecker | None = None,
        citation_validator: CitationValidator | None = None,
        baseline_comparator: BaselineComparator | None = None,
    ):
        self.evaluator = evaluator or QualityEvaluator()
        self.fact_checker = fact_checker or FactChecker()
        self.citation_validator = citation_validator or CitationValidator()
        self.baseline_comparator = baseline_comparator or BaselineComparator()

        self._results: list[BenchmarkResult] = []
        self._stats = {
            "benchmarks_run": 0,
            "avg_score": 0.0,
            "best_score": 0.0,
            "worst_score": 1.0,
        }

    async def benchmark(
        self,
        query: str,
        response: str,
        sources: list[str],
        facts_to_verify: list[str] | None = None,
        citations_to_validate: list[str] | None = None,
    ) -> BenchmarkResult:
        """Run full benchmark on research output."""
        import time

        start_time = time.monotonic()

        # Evaluate quality
        quality_scores = await self.evaluator.evaluate(query, response, sources)

        # Verify facts
        if facts_to_verify is None:
            facts_to_verify = await self.fact_checker.extract_facts(response)
        fact_verifications = await self.fact_checker.verify_all(facts_to_verify[:10])

        # Validate citations
        citations_to_validate = citations_to_validate or sources
        citation_validations = await self.citation_validator.validate_all(
            citations_to_validate[:10], response
        )

        # Calculate overall score
        quality_avg = sum(s.score for s in quality_scores.values()) / len(quality_scores)
        fact_score = sum(
            1
            for f in fact_verifications
            if f.status in [VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED]
        ) / max(len(fact_verifications), 1)
        citation_score = sum(1 for c in citation_validations if c.is_valid) / max(
            len(citation_validations), 1
        )

        overall_score = 0.5 * quality_avg + 0.3 * fact_score + 0.2 * citation_score

        # Compare to baselines
        comparison = await self.baseline_comparator.compare(
            query, response, overall_score, self.evaluator
        )

        execution_time = (time.monotonic() - start_time) * 1000

        result = BenchmarkResult(
            query=query,
            overall_score=overall_score,
            quality_scores=quality_scores,
            fact_verifications=fact_verifications,
            citation_validations=citation_validations,
            comparison_to_baseline=comparison,
            execution_time_ms=execution_time,
        )

        self._results.append(result)
        self._update_stats(overall_score)

        return result

    def _update_stats(self, score: float) -> None:
        """Update running statistics."""
        self._stats["benchmarks_run"] += 1
        n = self._stats["benchmarks_run"]

        # Running average
        old_avg = self._stats["avg_score"]
        self._stats["avg_score"] = old_avg + (score - old_avg) / n

        # Best/worst
        self._stats["best_score"] = max(self._stats["best_score"], score)
        self._stats["worst_score"] = min(self._stats["worst_score"], score)

    def get_stats(self) -> dict[str, Any]:
        """Get benchmark statistics."""
        return self._stats

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """Get benchmark results sorted by score."""
        sorted_results = sorted(
            self._results,
            key=lambda r: r.overall_score,
            reverse=True,
        )
        return [r.to_dict() for r in sorted_results[:10]]


# Factory functions
def create_deep_research_bench(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> DeepResearchBench:
    """Create a Deep Research Bench with default configuration."""
    evaluator = QualityEvaluator(llm_caller=llm_caller)
    fact_checker = FactChecker(llm_caller=llm_caller)

    return DeepResearchBench(
        evaluator=evaluator,
        fact_checker=fact_checker,
    )


__all__ = [
    "BaselineComparator",
    "BenchmarkResult",
    "CitationValidation",
    "CitationValidator",
    "DeepResearchBench",
    "FactChecker",
    "FactVerificationResult",
    "QualityDimension",
    "QualityEvaluator",
    "QualityScore",
    "VerificationStatus",
    "create_deep_research_bench",
]
