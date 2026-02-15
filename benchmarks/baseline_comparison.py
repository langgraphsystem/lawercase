"""Baseline Comparison - Compare research output against baseline models.

Provides comprehensive baseline comparison:
- Multiple baseline model support
- Statistical comparison metrics
- A/B testing framework
- Performance tracking over time
- Leaderboard generation
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import statistics
from typing import Any

import structlog

from .deep_research_bench import (
    QualityEvaluator,
)

logger = structlog.get_logger(__name__)


class ComparisonMetric(str, Enum):
    """Metrics for baseline comparison."""

    OVERALL_SCORE = "overall_score"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    CITATION_QUALITY = "citation_quality"
    LATENCY = "latency"
    TOKEN_EFFICIENCY = "token_efficiency"


class SignificanceLevel(str, Enum):
    """Statistical significance levels."""

    HIGHLY_SIGNIFICANT = "highly_significant"  # p < 0.01
    SIGNIFICANT = "significant"  # p < 0.05
    MARGINAL = "marginal"  # p < 0.1
    NOT_SIGNIFICANT = "not_significant"  # p >= 0.1


@dataclass
class BaselineModel:
    """Configuration for a baseline model."""

    name: str
    model_id: str
    caller: Callable[[str], Coroutine[Any, Any, str]]
    description: str = ""
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "description": self.description,
            "is_active": self.is_active,
        }


@dataclass
class ComparisonResult:
    """Result of comparing against a single baseline."""

    baseline_name: str
    our_score: float
    baseline_score: float
    improvement: float  # Relative improvement (positive = we're better)
    absolute_diff: float  # Absolute difference
    metric_comparisons: dict[str, tuple[float, float]]  # metric -> (our, baseline)
    our_latency_ms: float | None = None
    baseline_latency_ms: float | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_better(self) -> bool:
        return self.improvement > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_name": self.baseline_name,
            "our_score": self.our_score,
            "baseline_score": self.baseline_score,
            "improvement": self.improvement,
            "improvement_percent": f"{self.improvement * 100:.1f}%",
            "absolute_diff": self.absolute_diff,
            "is_better": self.is_better,
            "our_latency_ms": self.our_latency_ms,
            "baseline_latency_ms": self.baseline_latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StatisticalComparison:
    """Statistical comparison over multiple samples."""

    baseline_name: str
    sample_count: int
    our_mean: float
    our_std: float
    baseline_mean: float
    baseline_std: float
    improvement_mean: float
    improvement_std: float
    effect_size: float  # Cohen's d
    significance: SignificanceLevel
    p_value: float | None
    confidence_interval: tuple[float, float]
    wins: int
    losses: int
    ties: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_name": self.baseline_name,
            "sample_count": self.sample_count,
            "our_mean": self.our_mean,
            "our_std": self.our_std,
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
            "improvement_mean": self.improvement_mean,
            "improvement_percent": f"{self.improvement_mean * 100:.1f}%",
            "effect_size": self.effect_size,
            "significance": self.significance.value,
            "p_value": self.p_value,
            "confidence_interval_95": self.confidence_interval,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "win_rate": self.wins / self.sample_count if self.sample_count > 0 else 0,
        }


@dataclass
class LeaderboardEntry:
    """Entry in the comparison leaderboard."""

    model_name: str
    model_type: str  # "ours" or "baseline"
    avg_score: float
    std_score: float
    sample_count: int
    avg_latency_ms: float
    win_rate_vs_baselines: float
    rank: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "avg_score": self.avg_score,
            "std_score": self.std_score,
            "sample_count": self.sample_count,
            "avg_latency_ms": self.avg_latency_ms,
            "win_rate_vs_baselines": self.win_rate_vs_baselines,
        }


class EnhancedBaselineComparator:
    """Enhanced baseline comparator with statistical analysis.

    Features:
    - Multiple baseline model management
    - Statistical significance testing
    - Effect size calculation
    - Win/loss tracking
    - Leaderboard generation
    - Historical trend analysis

    Usage:
        >>> comparator = EnhancedBaselineComparator(evaluator)
        >>> comparator.register_baseline("gpt-4", gpt4_caller)
        >>> comparator.register_baseline("claude", claude_caller)
        >>> result = await comparator.compare_single(
        ...     query="What is machine learning?",
        ...     our_response="Machine learning is...",
        ...     our_score=0.85,
        ... )
        >>> stats = comparator.get_statistical_comparison("gpt-4")
    """

    def __init__(
        self,
        evaluator: QualityEvaluator | None = None,
        tie_threshold: float = 0.02,
    ) -> None:
        """Initialize baseline comparator.

        Args:
            evaluator: Quality evaluator for scoring
            tie_threshold: Score difference below which is considered a tie
        """
        self.evaluator = evaluator or QualityEvaluator()
        self.tie_threshold = tie_threshold

        # Baseline registry
        self._baselines: dict[str, BaselineModel] = {}

        # Comparison history
        self._history: list[ComparisonResult] = []
        self._our_scores: list[float] = []
        self._baseline_scores: dict[str, list[float]] = {}

        # Stats
        self._stats = {
            "total_comparisons": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_ties": 0,
        }

        self.logger = logger.bind(component="BaselineComparator")

    def register_baseline(
        self,
        name: str,
        caller: Callable[[str], Coroutine[Any, Any, str]],
        model_id: str = "",
        description: str = "",
    ) -> None:
        """Register a baseline model.

        Args:
            name: Baseline name
            caller: Async function to call the baseline
            model_id: Model identifier
            description: Model description
        """
        self._baselines[name] = BaselineModel(
            name=name,
            model_id=model_id or name,
            caller=caller,
            description=description,
        )
        self._baseline_scores[name] = []

        self.logger.info(
            "baseline.registered",
            name=name,
            model_id=model_id,
        )

    def unregister_baseline(self, name: str) -> bool:
        """Unregister a baseline model."""
        if name in self._baselines:
            del self._baselines[name]
            return True
        return False

    def list_baselines(self) -> list[dict[str, Any]]:
        """List all registered baselines."""
        return [b.to_dict() for b in self._baselines.values()]

    async def compare_single(
        self,
        query: str,
        our_response: str,
        our_score: float,
        our_latency_ms: float | None = None,
        sources: list[str] | None = None,
        baselines: list[str] | None = None,
    ) -> dict[str, ComparisonResult]:
        """Compare our response against baselines.

        Args:
            query: The query/question
            our_response: Our response
            our_score: Our overall score
            our_latency_ms: Our latency in milliseconds
            sources: Sources used
            baselines: Specific baselines to compare (default: all)

        Returns:
            Dict mapping baseline names to comparison results
        """
        import time

        baselines_to_use = baselines or list(self._baselines.keys())
        results = {}

        for baseline_name in baselines_to_use:
            baseline = self._baselines.get(baseline_name)
            if not baseline or not baseline.is_active:
                continue

            try:
                # Get baseline response
                start_time = time.monotonic()
                baseline_response = await baseline.caller(query)
                baseline_latency = (time.monotonic() - start_time) * 1000

                # Evaluate baseline
                baseline_scores = await self.evaluator.evaluate(
                    query, baseline_response, sources or []
                )
                baseline_score = sum(s.score for s in baseline_scores.values()) / len(
                    baseline_scores
                )

                # Calculate metrics
                improvement = (
                    (our_score - baseline_score) / baseline_score
                    if baseline_score > 0
                    else our_score
                )
                absolute_diff = our_score - baseline_score

                # Metric comparisons
                metric_comparisons = {}
                for dim, score in baseline_scores.items():
                    metric_comparisons[dim.value] = (our_score, score.score)

                result = ComparisonResult(
                    baseline_name=baseline_name,
                    our_score=our_score,
                    baseline_score=baseline_score,
                    improvement=improvement,
                    absolute_diff=absolute_diff,
                    metric_comparisons=metric_comparisons,
                    our_latency_ms=our_latency_ms,
                    baseline_latency_ms=baseline_latency,
                )

                results[baseline_name] = result
                self._record_comparison(result)

            except Exception as e:
                self.logger.error(
                    "baseline.comparison_failed",
                    baseline=baseline_name,
                    error=str(e),
                )

        # Record our score
        self._our_scores.append(our_score)

        return results

    async def compare_batch(
        self,
        queries: list[str],
        our_responses: list[str],
        our_scores: list[float],
        sources_list: list[list[str]] | None = None,
        baselines: list[str] | None = None,
    ) -> list[dict[str, ComparisonResult]]:
        """Compare batch of queries against baselines.

        Args:
            queries: List of queries
            our_responses: List of our responses
            our_scores: List of our scores
            sources_list: List of sources for each query
            baselines: Baselines to compare

        Returns:
            List of comparison result dicts
        """
        if sources_list is None:
            sources_list = [[] for _ in queries]

        tasks = [
            self.compare_single(q, r, s, sources=src, baselines=baselines)
            for q, r, s, src in zip(queries, our_responses, our_scores, sources_list, strict=False)
        ]

        return await asyncio.gather(*tasks)

    def _record_comparison(self, result: ComparisonResult) -> None:
        """Record comparison for statistics."""
        self._history.append(result)

        if result.baseline_name not in self._baseline_scores:
            self._baseline_scores[result.baseline_name] = []
        self._baseline_scores[result.baseline_name].append(result.baseline_score)

        self._stats["total_comparisons"] += 1

        if result.absolute_diff > self.tie_threshold:
            self._stats["total_wins"] += 1
        elif result.absolute_diff < -self.tie_threshold:
            self._stats["total_losses"] += 1
        else:
            self._stats["total_ties"] += 1

    def get_statistical_comparison(
        self,
        baseline_name: str,
    ) -> StatisticalComparison | None:
        """Get statistical comparison for a baseline.

        Args:
            baseline_name: Name of baseline

        Returns:
            StatisticalComparison or None if insufficient data
        """
        baseline_scores = self._baseline_scores.get(baseline_name, [])
        if len(baseline_scores) < 2 or len(self._our_scores) < 2:
            return None

        # Use matching pairs
        n = min(len(self._our_scores), len(baseline_scores))
        our = self._our_scores[-n:]
        base = baseline_scores[-n:]

        # Calculate statistics
        our_mean = statistics.mean(our)
        our_std = statistics.stdev(our) if len(our) > 1 else 0
        base_mean = statistics.mean(base)
        base_std = statistics.stdev(base) if len(base) > 1 else 0

        # Calculate improvements
        improvements = [(o - b) / b if b > 0 else o for o, b in zip(our, base, strict=False)]
        improvement_mean = statistics.mean(improvements)
        improvement_std = statistics.stdev(improvements) if len(improvements) > 1 else 0

        # Effect size (Cohen's d)
        pooled_std = ((our_std**2 + base_std**2) / 2) ** 0.5
        effect_size = (our_mean - base_mean) / pooled_std if pooled_std > 0 else 0

        # Simple significance estimation based on effect size and sample size
        # (Proper implementation would use scipy.stats.ttest_rel)
        p_value = self._estimate_p_value(effect_size, n)
        significance = self._determine_significance(p_value)

        # Confidence interval (rough estimate)
        se = improvement_std / (n**0.5) if n > 0 else 0
        ci_low = improvement_mean - 1.96 * se
        ci_high = improvement_mean + 1.96 * se

        # Win/loss/tie counts
        wins = sum(1 for o, b in zip(our, base, strict=False) if o - b > self.tie_threshold)
        losses = sum(1 for o, b in zip(our, base, strict=False) if b - o > self.tie_threshold)
        ties = n - wins - losses

        return StatisticalComparison(
            baseline_name=baseline_name,
            sample_count=n,
            our_mean=our_mean,
            our_std=our_std,
            baseline_mean=base_mean,
            baseline_std=base_std,
            improvement_mean=improvement_mean,
            improvement_std=improvement_std,
            effect_size=effect_size,
            significance=significance,
            p_value=p_value,
            confidence_interval=(ci_low, ci_high),
            wins=wins,
            losses=losses,
            ties=ties,
        )

    def _estimate_p_value(self, effect_size: float, n: int) -> float:
        """Estimate p-value from effect size and sample size."""
        # Simplified estimation without scipy
        # t = d * sqrt(n)
        t = abs(effect_size) * (n**0.5)

        # Rough p-value estimation
        if t > 3.5:
            return 0.001
        if t > 2.5:
            return 0.01
        if t > 2.0:
            return 0.05
        if t > 1.5:
            return 0.1
        return min(1.0, 2 * (1 - t / 4))  # Rough estimate

    def _determine_significance(self, p_value: float) -> SignificanceLevel:
        """Determine significance level from p-value."""
        if p_value < 0.01:
            return SignificanceLevel.HIGHLY_SIGNIFICANT
        if p_value < 0.05:
            return SignificanceLevel.SIGNIFICANT
        if p_value < 0.1:
            return SignificanceLevel.MARGINAL
        return SignificanceLevel.NOT_SIGNIFICANT

    def get_leaderboard(self, include_baselines: bool = True) -> list[LeaderboardEntry]:
        """Generate leaderboard of models.

        Args:
            include_baselines: Whether to include baselines

        Returns:
            Sorted list of leaderboard entries
        """
        entries = []

        # Our entry
        if self._our_scores:
            our_entry = LeaderboardEntry(
                model_name="MegaAgent",
                model_type="ours",
                avg_score=statistics.mean(self._our_scores),
                std_score=statistics.stdev(self._our_scores) if len(self._our_scores) > 1 else 0,
                sample_count=len(self._our_scores),
                avg_latency_ms=0,  # Would need to track this
                win_rate_vs_baselines=(
                    self._stats["total_wins"] / max(self._stats["total_comparisons"], 1)
                ),
                rank=0,
            )
            entries.append(our_entry)

        # Baseline entries
        if include_baselines:
            for name, scores in self._baseline_scores.items():
                if not scores:
                    continue

                entry = LeaderboardEntry(
                    model_name=name,
                    model_type="baseline",
                    avg_score=statistics.mean(scores),
                    std_score=statistics.stdev(scores) if len(scores) > 1 else 0,
                    sample_count=len(scores),
                    avg_latency_ms=0,
                    win_rate_vs_baselines=0,
                    rank=0,
                )
                entries.append(entry)

        # Sort by average score
        entries.sort(key=lambda e: e.avg_score, reverse=True)

        # Assign ranks
        for i, entry in enumerate(entries):
            entry.rank = i + 1

        return entries

    def get_history(
        self,
        baseline_name: str | None = None,
        limit: int = 100,
    ) -> list[ComparisonResult]:
        """Get comparison history.

        Args:
            baseline_name: Filter by baseline
            limit: Maximum entries

        Returns:
            List of comparison results
        """
        history = self._history

        if baseline_name:
            history = [h for h in history if h.baseline_name == baseline_name]

        return history[-limit:]

    def get_trends(
        self,
        baseline_name: str,
        window_size: int = 10,
    ) -> dict[str, list[float]]:
        """Get trends over time for a baseline.

        Args:
            baseline_name: Baseline to analyze
            window_size: Rolling window size

        Returns:
            Dict with trend data
        """
        history = self.get_history(baseline_name)

        if len(history) < window_size:
            return {
                "improvements": [h.improvement for h in history],
                "our_scores": [h.our_score for h in history],
                "baseline_scores": [h.baseline_score for h in history],
            }

        # Rolling averages
        improvements = []
        our_scores = []
        baseline_scores = []

        for i in range(len(history) - window_size + 1):
            window = history[i : i + window_size]
            improvements.append(statistics.mean(h.improvement for h in window))
            our_scores.append(statistics.mean(h.our_score for h in window))
            baseline_scores.append(statistics.mean(h.baseline_score for h in window))

        return {
            "improvements": improvements,
            "our_scores": our_scores,
            "baseline_scores": baseline_scores,
        }

    def export_report(self, output_format: str = "json") -> str:
        """Export comparison report.

        Args:
            output_format: Output format (json, markdown)

        Returns:
            Formatted report
        """
        report = {
            "stats": self._stats,
            "leaderboard": [e.to_dict() for e in self.get_leaderboard()],
            "statistical_comparisons": {},
            "recent_history": [h.to_dict() for h in self.get_history(limit=20)],
        }

        for baseline_name in self._baselines:
            stats = self.get_statistical_comparison(baseline_name)
            if stats:
                report["statistical_comparisons"][baseline_name] = stats.to_dict()

        if output_format == "json":
            return json.dumps(report, indent=2)

        if output_format == "markdown":
            lines = [
                "# Baseline Comparison Report",
                "",
                "## Summary Statistics",
                "",
                f"- Total Comparisons: {self._stats['total_comparisons']}",
                f"- Wins: {self._stats['total_wins']}",
                f"- Losses: {self._stats['total_losses']}",
                f"- Ties: {self._stats['total_ties']}",
                f"- Win Rate: {self._stats['total_wins'] / max(self._stats['total_comparisons'], 1):.1%}",
                "",
                "## Leaderboard",
                "",
                "| Rank | Model | Type | Avg Score | Std | Samples |",
                "|------|-------|------|-----------|-----|---------|",
            ]

            for entry in self.get_leaderboard():
                lines.append(
                    f"| {entry.rank} | {entry.model_name} | {entry.model_type} | "
                    f"{entry.avg_score:.3f} | {entry.std_score:.3f} | {entry.sample_count} |"
                )

            lines.extend(
                [
                    "",
                    "## Statistical Comparisons",
                    "",
                ]
            )

            for baseline_name, stats_dict in report["statistical_comparisons"].items():
                lines.extend(
                    [
                        f"### vs {baseline_name}",
                        "",
                        f"- Sample Count: {stats_dict['sample_count']}",
                        f"- Improvement: {stats_dict['improvement_percent']}",
                        f"- Effect Size (Cohen's d): {stats_dict['effect_size']:.3f}",
                        f"- Significance: {stats_dict['significance']}",
                        f"- Win/Loss/Tie: {stats_dict['wins']}/{stats_dict['losses']}/{stats_dict['ties']}",
                        "",
                    ]
                )

            return "\n".join(lines)

        raise ValueError(f"Unknown format: {output_format}")

    def get_stats(self) -> dict[str, Any]:
        """Get comparator statistics."""
        return {
            **self._stats,
            "baseline_count": len(self._baselines),
            "our_samples": len(self._our_scores),
            "history_size": len(self._history),
        }

    def reset(self) -> None:
        """Reset all comparison data."""
        self._history.clear()
        self._our_scores.clear()
        for scores in self._baseline_scores.values():
            scores.clear()
        self._stats = {
            "total_comparisons": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_ties": 0,
        }


# Re-export for compatibility
BaselineComparator = EnhancedBaselineComparator

__all__ = [
    "BaselineComparator",
    "BaselineModel",
    "ComparisonMetric",
    "ComparisonResult",
    "EnhancedBaselineComparator",
    "LeaderboardEntry",
    "SignificanceLevel",
    "StatisticalComparison",
]
