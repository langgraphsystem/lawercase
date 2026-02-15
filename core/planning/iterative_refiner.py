"""Iterative Refiner for Adaptive Research Planning.

Refines research plans based on intermediate results:
- Coverage analysis
- Gap detection
- Plan adjustment
- Resource reallocation
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import re
from typing import Any

from .query_decomposer import DecomposedQuery, SubQuery, SubQueryPriority
from .strategy_selector import QueryComplexity, ResearchStrategy

logger = logging.getLogger(__name__)


class RefinementAction(str, Enum):
    """Types of plan refinement actions."""

    NONE = "none"  # No refinement needed
    BROADEN = "broaden"  # Add more sub-queries
    DEEPEN = "deepen"  # Increase depth limits
    NARROW = "narrow"  # Remove low-value queries
    REPRIORITIZE = "reprioritize"  # Change query priorities
    REDIRECT = "redirect"  # Change strategy entirely


class CoverageLevel(str, Enum):
    """Query coverage assessment levels."""

    NONE = "none"  # 0% covered
    PARTIAL = "partial"  # 1-50% covered
    MODERATE = "moderate"  # 51-80% covered
    GOOD = "good"  # 81-95% covered
    COMPLETE = "complete"  # 96-100% covered


@dataclass
class Finding:
    """A research finding from execution."""

    query_id: str
    content: str
    quality_score: float = 0.5  # 0-1
    relevance_score: float = 0.5  # 0-1
    source: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "content": self.content[:200],
            "quality_score": self.quality_score,
            "relevance_score": self.relevance_score,
            "source": self.source,
        }


@dataclass
class CoverageAssessment:
    """Assessment of how well findings cover the query."""

    level: CoverageLevel
    score: float  # 0-1
    covered_aspects: list[str]
    uncovered_aspects: list[str]
    gaps: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "score": self.score,
            "covered_aspects": self.covered_aspects,
            "uncovered_aspects": self.uncovered_aspects,
            "gaps": self.gaps,
        }


@dataclass
class RefinementResult:
    """Result of plan refinement."""

    action: RefinementAction
    original_plan: dict[str, Any]
    refined_plan: dict[str, Any]
    changes: list[str]
    reasoning: str
    coverage_before: float
    coverage_after: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "changes": self.changes,
            "reasoning": self.reasoning,
            "coverage_before": self.coverage_before,
            "coverage_after": self.coverage_after,
        }


@dataclass
class RefinementContext:
    """Context for plan refinement."""

    original_query: str
    decomposed: DecomposedQuery
    findings: list[Finding]
    iteration: int = 0
    max_iterations: int = 3
    time_remaining_seconds: float = 300
    budget_remaining: float = 1.0
    depth_limits: dict[str, int] = field(default_factory=dict)
    resource_allocation: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "time_remaining": self.time_remaining_seconds,
            "budget_remaining": self.budget_remaining,
            "findings_count": len(self.findings),
        }


class IterativeRefiner:
    """Refines research plans based on intermediate results.

    Features:
    - Coverage analysis
    - Gap detection
    - Dynamic plan adjustment
    - Resource reallocation
    - LLM-assisted refinement

    Usage:
        refiner = IterativeRefiner()

        context = RefinementContext(
            original_query="EB-1A requirements",
            decomposed=decomposed_query,
            findings=current_findings,
        )

        result = await refiner.refine(context)
        print(f"Action: {result.action}")
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        coverage_threshold: float = 0.7,
        enable_llm: bool = True,
    ) -> None:
        self._llm_caller = llm_caller
        self._coverage_threshold = coverage_threshold
        self._enable_llm = enable_llm

        # Refinement thresholds
        self._broaden_threshold = 0.5  # Below this, broaden
        self._deepen_threshold = 0.8  # Above this with few findings, deepen
        self._narrow_threshold = 0.3  # Quality below this, narrow

        self._stats = {
            "refinements_made": 0,
            "broaden_actions": 0,
            "deepen_actions": 0,
            "narrow_actions": 0,
            "no_action": 0,
        }

    async def refine(self, context: RefinementContext) -> RefinementResult:
        """Refine the research plan based on findings.

        Args:
            context: Refinement context with current state

        Returns:
            RefinementResult with action and updated plan
        """
        self._stats["refinements_made"] += 1

        # Assess current coverage
        coverage = self._assess_coverage(context)

        # Determine action
        action = self._determine_action(coverage, context)

        # Execute refinement
        if action == RefinementAction.BROADEN:
            result = await self._broaden_plan(context, coverage)
            self._stats["broaden_actions"] += 1

        elif action == RefinementAction.DEEPEN:
            result = self._deepen_plan(context, coverage)
            self._stats["deepen_actions"] += 1

        elif action == RefinementAction.NARROW:
            result = self._narrow_plan(context, coverage)
            self._stats["narrow_actions"] += 1

        elif action == RefinementAction.REPRIORITIZE:
            result = self._reprioritize_plan(context, coverage)

        elif action == RefinementAction.REDIRECT:
            result = await self._redirect_plan(context, coverage)

        else:
            self._stats["no_action"] += 1
            result = RefinementResult(
                action=RefinementAction.NONE,
                original_plan=context.decomposed.to_dict(),
                refined_plan=context.decomposed.to_dict(),
                changes=[],
                reasoning="Coverage is satisfactory, no refinement needed",
                coverage_before=coverage.score,
            )

        return result

    def _assess_coverage(self, context: RefinementContext) -> CoverageAssessment:
        """Assess how well findings cover the query."""
        if not context.decomposed.sub_queries:
            return CoverageAssessment(
                level=CoverageLevel.NONE,
                score=0.0,
                covered_aspects=[],
                uncovered_aspects=[],
                gaps=["No sub-queries to evaluate"],
                recommendations=["Decompose query first"],
            )

        covered_aspects: list[str] = []
        uncovered_aspects: list[str] = []
        gaps: list[str] = []

        # Check coverage for each sub-query
        for sq in context.decomposed.sub_queries:
            relevant_findings = [
                f for f in context.findings if f.query_id == sq.id or self._is_relevant(f, sq)
            ]

            if relevant_findings:
                avg_quality = sum(f.quality_score for f in relevant_findings) / len(
                    relevant_findings
                )
                if avg_quality >= 0.5:
                    covered_aspects.append(sq.text[:50])
                else:
                    uncovered_aspects.append(sq.text[:50])
                    gaps.append(f"Low quality findings for: {sq.text[:30]}")
            else:
                uncovered_aspects.append(sq.text[:50])
                gaps.append(f"No findings for: {sq.text[:30]}")

        # Calculate coverage score
        total = len(context.decomposed.sub_queries)
        covered = len(covered_aspects)
        score = covered / total if total > 0 else 0.0

        # Determine level
        if score == 0:
            level = CoverageLevel.NONE
        elif score < 0.5:
            level = CoverageLevel.PARTIAL
        elif score < 0.8:
            level = CoverageLevel.MODERATE
        elif score < 0.95:
            level = CoverageLevel.GOOD
        else:
            level = CoverageLevel.COMPLETE

        # Generate recommendations
        recommendations = self._generate_recommendations(level, gaps, context)

        return CoverageAssessment(
            level=level,
            score=score,
            covered_aspects=covered_aspects,
            uncovered_aspects=uncovered_aspects,
            gaps=gaps,
            recommendations=recommendations,
        )

    def _is_relevant(self, finding: Finding, sub_query: SubQuery) -> bool:
        """Check if finding is relevant to sub-query."""
        # Simple keyword overlap check
        finding_words = set(finding.content.lower().split())
        query_words = set(sub_query.text.lower().split())

        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why"}
        finding_words -= stop_words
        query_words -= stop_words

        overlap = len(finding_words & query_words)
        return overlap >= 2

    def _generate_recommendations(
        self,
        level: CoverageLevel,
        gaps: list[str],
        context: RefinementContext,
    ) -> list[str]:
        """Generate recommendations based on coverage."""
        recommendations: list[str] = []

        if level in (CoverageLevel.NONE, CoverageLevel.PARTIAL):
            recommendations.append("Add more sub-queries to cover missing aspects")
            if gaps:
                recommendations.append(f"Focus on: {gaps[0]}")

        elif level == CoverageLevel.MODERATE:
            recommendations.append("Deepen investigation of partially covered aspects")

        elif level == CoverageLevel.GOOD:
            if context.iteration < context.max_iterations:
                recommendations.append("Consider one more iteration for completeness")

        # Resource-based recommendations
        if context.time_remaining_seconds < 60:
            recommendations.append("Limited time remaining - prioritize critical queries")

        if context.budget_remaining < 0.3:
            recommendations.append("Budget constraints - narrow focus")

        return recommendations

    def _determine_action(
        self,
        coverage: CoverageAssessment,
        context: RefinementContext,
    ) -> RefinementAction:
        """Determine the refinement action to take."""
        # Check resource constraints
        if context.time_remaining_seconds < 30 or context.budget_remaining < 0.1:
            return RefinementAction.NONE  # No resources for refinement

        # Check iteration limit
        if context.iteration >= context.max_iterations:
            return RefinementAction.NONE

        # Coverage-based decision
        if coverage.score < self._broaden_threshold:
            return RefinementAction.BROADEN

        if coverage.score >= self._deepen_threshold:
            # Good coverage but check findings quality
            avg_quality = 0.0
            if context.findings:
                avg_quality = sum(f.quality_score for f in context.findings) / len(context.findings)

            if avg_quality < 0.6 and len(context.findings) < 5:
                return RefinementAction.DEEPEN

        # Check for quality issues
        if context.findings:
            low_quality = [f for f in context.findings if f.quality_score < self._narrow_threshold]
            if len(low_quality) > len(context.findings) * 0.5:
                return RefinementAction.REPRIORITIZE

        # Sufficient coverage
        if coverage.score >= self._coverage_threshold:
            return RefinementAction.NONE

        return RefinementAction.BROADEN

    async def _broaden_plan(
        self,
        context: RefinementContext,
        coverage: CoverageAssessment,
    ) -> RefinementResult:
        """Broaden the plan by adding sub-queries."""
        original_plan = context.decomposed.to_dict()
        changes: list[str] = []

        # Generate new sub-queries for gaps
        new_queries: list[SubQuery] = []

        if self._llm_caller and self._enable_llm and coverage.gaps:
            new_queries = await self._generate_gap_queries(context, coverage.gaps)

        # Fallback: generate from uncovered aspects
        if not new_queries and coverage.uncovered_aspects:
            for i, aspect in enumerate(coverage.uncovered_aspects[:3]):
                sq = SubQuery(
                    id=f"sq_new_{i}",
                    text=f"More details about: {aspect}",
                    priority=SubQueryPriority.HIGH,
                    estimated_complexity=QueryComplexity.MODERATE,
                )
                new_queries.append(sq)
                changes.append(f"Added query: {sq.text[:40]}")

        # Update decomposed query
        context.decomposed.sub_queries.extend(new_queries)

        return RefinementResult(
            action=RefinementAction.BROADEN,
            original_plan=original_plan,
            refined_plan=context.decomposed.to_dict(),
            changes=changes,
            reasoning=f"Coverage was {coverage.score:.0%}, added {len(new_queries)} queries",
            coverage_before=coverage.score,
        )

    async def _generate_gap_queries(
        self,
        context: RefinementContext,
        gaps: list[str],
    ) -> list[SubQuery]:
        """Generate queries to fill gaps using LLM."""
        if not self._llm_caller:
            return []

        gaps_str = "\n".join(f"- {g}" for g in gaps[:5])
        findings_summary = "\n".join(f"- {f.content[:100]}" for f in context.findings[:3])

        prompt = f"""Based on the original query and identified gaps, generate 3 additional sub-queries.

Original query: {context.original_query}

Current findings:
{findings_summary}

Identified gaps:
{gaps_str}

Generate 3 specific sub-queries to address these gaps.
Format: One query per line, numbered 1-3."""

        try:
            response = await self._llm_caller(prompt)

            queries: list[SubQuery] = []
            lines = response.strip().split("\n")

            for i, line in enumerate(lines):
                # Clean up line
                clean = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
                if clean and len(clean) > 10:
                    queries.append(
                        SubQuery(
                            id=f"sq_gap_{i}",
                            text=clean,
                            priority=SubQueryPriority.HIGH,
                            estimated_complexity=QueryComplexity.MODERATE,
                        )
                    )

            return queries[:3]

        except Exception as e:
            logger.warning(f"Gap query generation failed: {e}")
            return []

    def _deepen_plan(
        self,
        context: RefinementContext,
        coverage: CoverageAssessment,
    ) -> RefinementResult:
        """Deepen the plan by increasing depth limits."""
        original_plan = context.decomposed.to_dict()
        changes: list[str] = []

        # Increase depth limits for covered queries with low findings
        for sq in context.decomposed.sub_queries:
            current_depth = context.depth_limits.get(sq.id, 2)
            findings_for_query = [f for f in context.findings if f.query_id == sq.id]

            if len(findings_for_query) < 2 and current_depth < 5:
                new_depth = min(current_depth + 1, 5)
                context.depth_limits[sq.id] = new_depth
                changes.append(f"Increased depth for '{sq.text[:30]}' to {new_depth}")

        return RefinementResult(
            action=RefinementAction.DEEPEN,
            original_plan=original_plan,
            refined_plan=context.decomposed.to_dict(),
            changes=changes,
            reasoning=f"Good coverage ({coverage.score:.0%}) but need more depth",
            coverage_before=coverage.score,
        )

    def _narrow_plan(
        self,
        context: RefinementContext,
        coverage: CoverageAssessment,
    ) -> RefinementResult:
        """Narrow the plan by removing low-value queries."""
        original_plan = context.decomposed.to_dict()
        changes: list[str] = []

        # Identify low-performing queries
        removed_ids: set[str] = set()
        for sq in context.decomposed.sub_queries:
            if sq.priority == SubQueryPriority.LOW:
                findings = [f for f in context.findings if f.query_id == sq.id]
                if not findings or all(f.quality_score < 0.3 for f in findings):
                    removed_ids.add(sq.id)
                    changes.append(f"Removed low-value query: {sq.text[:30]}")

        # Update sub-queries
        context.decomposed.sub_queries = [
            sq for sq in context.decomposed.sub_queries if sq.id not in removed_ids
        ]

        return RefinementResult(
            action=RefinementAction.NARROW,
            original_plan=original_plan,
            refined_plan=context.decomposed.to_dict(),
            changes=changes,
            reasoning=f"Removed {len(removed_ids)} low-value queries to focus resources",
            coverage_before=coverage.score,
        )

    def _reprioritize_plan(
        self,
        context: RefinementContext,
        coverage: CoverageAssessment,
    ) -> RefinementResult:
        """Reprioritize queries based on findings."""
        original_plan = context.decomposed.to_dict()
        changes: list[str] = []

        # Analyze which queries produced good findings
        query_scores: dict[str, float] = {}
        for sq in context.decomposed.sub_queries:
            findings = [f for f in context.findings if f.query_id == sq.id]
            if findings:
                query_scores[sq.id] = sum(f.quality_score for f in findings) / len(findings)
            else:
                query_scores[sq.id] = 0.0

        # Update priorities
        sorted_queries = sorted(query_scores.items(), key=lambda x: x[1], reverse=True)

        for rank, (sq_id, _score) in enumerate(sorted_queries):
            sq = next((q for q in context.decomposed.sub_queries if q.id == sq_id), None)
            if sq:
                old_priority = sq.priority
                if rank < len(sorted_queries) * 0.25:
                    sq.priority = SubQueryPriority.CRITICAL
                elif rank < len(sorted_queries) * 0.5:
                    sq.priority = SubQueryPriority.HIGH
                elif rank < len(sorted_queries) * 0.75:
                    sq.priority = SubQueryPriority.MEDIUM
                else:
                    sq.priority = SubQueryPriority.LOW

                if sq.priority != old_priority:
                    changes.append(
                        f"Changed '{sq.text[:20]}' priority: {old_priority.value} → {sq.priority.value}"
                    )

        return RefinementResult(
            action=RefinementAction.REPRIORITIZE,
            original_plan=original_plan,
            refined_plan=context.decomposed.to_dict(),
            changes=changes,
            reasoning="Reprioritized based on finding quality",
            coverage_before=coverage.score,
        )

    async def _redirect_plan(
        self,
        context: RefinementContext,
        coverage: CoverageAssessment,
    ) -> RefinementResult:
        """Redirect the plan with a new strategy."""
        original_plan = context.decomposed.to_dict()

        # Determine new strategy based on coverage pattern
        if coverage.score < 0.2:
            # Very low coverage - try exploratory
            new_strategy = ResearchStrategy.EXPLORATORY
        elif len(coverage.uncovered_aspects) > len(coverage.covered_aspects):
            # More uncovered than covered - try breadth first
            new_strategy = ResearchStrategy.BREADTH_FIRST
        else:
            # Partial coverage - try balanced
            new_strategy = ResearchStrategy.BALANCED

        context.decomposed.suggested_strategy = new_strategy

        return RefinementResult(
            action=RefinementAction.REDIRECT,
            original_plan=original_plan,
            refined_plan=context.decomposed.to_dict(),
            changes=[f"Changed strategy to {new_strategy.value}"],
            reasoning=f"Low effectiveness with current strategy, switching to {new_strategy.value}",
            coverage_before=coverage.score,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get refiner statistics."""
        return self._stats


# Factory function
def create_iterative_refiner(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> IterativeRefiner:
    """Create an iterative refiner with optional LLM support."""
    return IterativeRefiner(llm_caller=llm_caller)


__all__ = [
    "CoverageAssessment",
    "CoverageLevel",
    "Finding",
    "IterativeRefiner",
    "RefinementAction",
    "RefinementContext",
    "RefinementResult",
    "create_iterative_refiner",
]
