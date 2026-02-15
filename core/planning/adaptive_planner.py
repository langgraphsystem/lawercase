"""Adaptive Research Planning for Dynamic Research Strategy Selection.

Implements LLM-driven planning with:
- Strategy selection (depth vs breadth)
- Query decomposition
- Iterative refinement
- Dynamic depth adjustment
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResearchStrategy(str, Enum):
    """Research strategy types."""

    BREADTH_FIRST = "breadth_first"  # Explore many topics shallowly
    DEPTH_FIRST = "depth_first"  # Dive deep into fewer topics
    BALANCED = "balanced"  # Mix of breadth and depth
    FOCUSED = "focused"  # Single topic deep dive
    COMPARATIVE = "comparative"  # Compare multiple options
    EXPLORATORY = "exploratory"  # Open-ended exploration


class QueryComplexity(str, Enum):
    """Query complexity levels."""

    SIMPLE = "simple"  # Single fact lookup
    MODERATE = "moderate"  # Multi-aspect question
    COMPLEX = "complex"  # Multi-step reasoning
    EXPERT = "expert"  # Domain expertise required


@dataclass
class DecomposedQuery:
    """A decomposed query with sub-components."""

    original: str
    sub_queries: list[str] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    complexity: QueryComplexity = QueryComplexity.MODERATE
    estimated_depth: int = 2
    suggested_strategy: ResearchStrategy = ResearchStrategy.BALANCED

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "sub_queries": self.sub_queries,
            "dependencies": self.dependencies,
            "complexity": self.complexity.value,
            "estimated_depth": self.estimated_depth,
            "suggested_strategy": self.suggested_strategy.value,
        }


@dataclass
class PlanningContext:
    """Context for adaptive planning."""

    query: str
    domain: str = "general"
    constraints: dict[str, Any] = field(default_factory=dict)
    prior_findings: list[str] = field(default_factory=list)
    iteration: int = 0
    time_remaining_seconds: float = 300
    budget_remaining: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "domain": self.domain,
            "constraints": self.constraints,
            "iteration": self.iteration,
            "time_remaining_seconds": self.time_remaining_seconds,
            "budget_remaining": self.budget_remaining,
        }


@dataclass
class AdaptivePlan:
    """An adaptive research plan."""

    id: str
    query: str
    strategy: ResearchStrategy
    decomposed: DecomposedQuery
    execution_order: list[str]
    depth_limits: dict[str, int]
    resource_allocation: dict[str, float]
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "strategy": self.strategy.value,
            "decomposed": self.decomposed.to_dict(),
            "execution_order": self.execution_order,
            "depth_limits": self.depth_limits,
            "resource_allocation": self.resource_allocation,
            "created_at": self.created_at.isoformat(),
        }


class StrategySelector:
    """Selects optimal research strategy based on query analysis."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

        # Strategy selection rules
        self._keyword_strategies = {
            "compare": ResearchStrategy.COMPARATIVE,
            "difference": ResearchStrategy.COMPARATIVE,
            "vs": ResearchStrategy.COMPARATIVE,
            "explore": ResearchStrategy.EXPLORATORY,
            "what is": ResearchStrategy.FOCUSED,
            "how to": ResearchStrategy.DEPTH_FIRST,
            "why": ResearchStrategy.DEPTH_FIRST,
            "overview": ResearchStrategy.BREADTH_FIRST,
            "all": ResearchStrategy.BREADTH_FIRST,
            "list": ResearchStrategy.BREADTH_FIRST,
        }

    async def select_strategy(
        self,
        context: PlanningContext,
    ) -> ResearchStrategy:
        """Select optimal strategy for the query."""
        query_lower = context.query.lower()

        # Rule-based selection
        for keyword, strategy in self._keyword_strategies.items():
            if keyword in query_lower:
                return strategy

        # LLM-based selection if available
        if self._llm_caller:
            prompt = f"""Classify this research query into one of these strategies:
- breadth_first: explore many topics
- depth_first: dive deep into one topic
- balanced: mix of breadth and depth
- focused: single topic investigation
- comparative: compare options
- exploratory: open-ended exploration

Query: {context.query}
Domain: {context.domain}
Time budget: {context.time_remaining_seconds} seconds

Strategy (one word):"""
            try:
                response = await self._llm_caller(prompt)
                strategy_name = response.strip().lower().replace("-", "_")
                return ResearchStrategy(strategy_name)
            except Exception as e:
                logger.debug(f"LLM strategy selection failed: {e}")

        # Default
        return ResearchStrategy.BALANCED

    def estimate_complexity(self, query: str) -> QueryComplexity:
        """Estimate query complexity."""
        # Simple heuristics
        word_count = len(query.split())
        question_marks = query.count("?")
        has_technical_terms = any(
            term in query.lower()
            for term in ["algorithm", "implementation", "architecture", "policy", "regulation"]
        )

        if word_count < 5:
            return QueryComplexity.SIMPLE
        if word_count > 30 or question_marks > 1:
            return QueryComplexity.COMPLEX
        if has_technical_terms:
            return QueryComplexity.EXPERT
        return QueryComplexity.MODERATE


class QueryDecomposer:
    """Decomposes complex queries into sub-queries."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

    async def decompose(
        self,
        query: str,
        max_sub_queries: int = 5,
        context: PlanningContext | None = None,
    ) -> DecomposedQuery:
        """Decompose a query into sub-queries."""
        complexity = StrategySelector().estimate_complexity(query)

        if complexity == QueryComplexity.SIMPLE:
            return DecomposedQuery(
                original=query,
                sub_queries=[query],
                complexity=complexity,
                estimated_depth=1,
            )

        if self._llm_caller:
            prior_context = ""
            if context and context.prior_findings:
                prior_context = f"\nPrior findings: {'; '.join(context.prior_findings[:3])}"

            prompt = f"""Decompose this research query into {max_sub_queries} sub-queries.
The sub-queries should be independent and cover different aspects.
{prior_context}

Query: {query}

Sub-queries (one per line, in order of importance):"""

            try:
                response = await self._llm_caller(prompt)
                lines = [item.strip() for item in response.split("\n") if item.strip()]
                sub_queries = []
                for line in lines[:max_sub_queries]:
                    clean = line.lstrip("0123456789.-) ").strip()
                    if clean and len(clean) > 5:
                        sub_queries.append(clean)

                # Identify dependencies
                dependencies = await self._identify_dependencies(sub_queries)

                return DecomposedQuery(
                    original=query,
                    sub_queries=sub_queries,
                    dependencies=dependencies,
                    complexity=complexity,
                    estimated_depth=self._estimate_depth(complexity, len(sub_queries)),
                )
            except Exception as e:
                logger.error(f"Query decomposition failed: {e}")

        # Fallback: simple decomposition
        return DecomposedQuery(
            original=query,
            sub_queries=[query],
            complexity=complexity,
            estimated_depth=2,
        )

    async def _identify_dependencies(
        self,
        sub_queries: list[str],
    ) -> dict[str, list[str]]:
        """Identify dependencies between sub-queries."""
        # Simple heuristic: assume sequential dependencies for now
        dependencies: dict[str, list[str]] = {}
        for i, query in enumerate(sub_queries[1:], 1):
            # Each query depends on previous (simplification)
            dependencies[query] = [sub_queries[i - 1]]
        return dependencies

    def _estimate_depth(
        self,
        complexity: QueryComplexity,
        num_sub_queries: int,
    ) -> int:
        """Estimate required depth of investigation."""
        base_depth = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MODERATE: 2,
            QueryComplexity.COMPLEX: 3,
            QueryComplexity.EXPERT: 4,
        }
        return min(base_depth[complexity] + (num_sub_queries // 3), 5)


class IterativeRefiner:
    """Refines plans based on intermediate results."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

    async def refine(
        self,
        plan: AdaptivePlan,
        findings: list[str],
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Refine plan based on findings."""
        # Check if we need to adjust strategy
        coverage = self._assess_coverage(plan, findings)

        if coverage < 0.5:
            # Need to broaden search
            plan = await self._broaden_plan(plan, findings, context)
        elif coverage > 0.8 and len(findings) < 10:
            # Good coverage but need more depth
            plan = await self._deepen_plan(plan, findings, context)

        # Adjust resource allocation based on time remaining
        plan = self._adjust_resources(plan, context)

        return plan

    def _assess_coverage(
        self,
        plan: AdaptivePlan,
        findings: list[str],
    ) -> float:
        """Assess how well findings cover the query."""
        if not plan.decomposed.sub_queries:
            return 0.0

        covered = 0
        for sub_query in plan.decomposed.sub_queries:
            query_words = set(sub_query.lower().split())
            for finding in findings:
                finding_words = set(finding.lower().split())
                if len(query_words & finding_words) > 2:
                    covered += 1
                    break

        return covered / len(plan.decomposed.sub_queries)

    async def _broaden_plan(
        self,
        plan: AdaptivePlan,
        findings: list[str],
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Broaden the plan to cover more aspects."""
        if self._llm_caller:
            prompt = f"""The current research hasn't covered all aspects.
Generate 3 additional sub-queries to explore.

Original query: {plan.query}
Current sub-queries: {plan.decomposed.sub_queries}
Findings so far: {findings[:3]}

New sub-queries (one per line):"""
            try:
                response = await self._llm_caller(prompt)
                new_queries = [
                    item.strip().lstrip("0123456789.-) ")
                    for item in response.split("\n")
                    if item.strip()
                ][:3]
                plan.decomposed.sub_queries.extend(new_queries)
                plan.execution_order.extend(new_queries)
            except Exception:
                pass

        return plan

    async def _deepen_plan(
        self,
        plan: AdaptivePlan,
        findings: list[str],
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Deepen the plan for more detailed investigation."""
        # Increase depth limits
        for query in plan.decomposed.sub_queries:
            current_limit = plan.depth_limits.get(query, 2)
            plan.depth_limits[query] = min(current_limit + 1, 5)

        return plan

    def _adjust_resources(
        self,
        plan: AdaptivePlan,
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Adjust resource allocation based on remaining time/budget."""
        time_factor = min(context.time_remaining_seconds / 300, 1.0)
        budget_factor = min(context.budget_remaining, 1.0)

        # Scale down depth limits if running low on resources
        if time_factor < 0.3 or budget_factor < 0.3:
            for query in plan.depth_limits:
                plan.depth_limits[query] = max(1, plan.depth_limits[query] - 1)

        return plan


class AdaptivePlanner:
    """Main adaptive planner coordinating all components."""

    def __init__(
        self,
        strategy_selector: StrategySelector | None = None,
        query_decomposer: QueryDecomposer | None = None,
        refiner: IterativeRefiner | None = None,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.strategy_selector = strategy_selector or StrategySelector(llm_caller)
        self.query_decomposer = query_decomposer or QueryDecomposer(llm_caller)
        self.refiner = refiner or IterativeRefiner(llm_caller)

        self._plans: dict[str, AdaptivePlan] = {}
        self._stats = {
            "plans_created": 0,
            "plans_refined": 0,
            "strategies_used": {},
        }

    async def create_plan(
        self,
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Create an adaptive research plan."""
        # Select strategy
        strategy = await self.strategy_selector.select_strategy(context)

        # Decompose query
        max_sub = self._get_max_sub_queries(strategy)
        decomposed = await self.query_decomposer.decompose(
            context.query,
            max_sub_queries=max_sub,
            context=context,
        )

        # Set suggested strategy
        decomposed.suggested_strategy = strategy

        # Determine execution order
        execution_order = self._determine_execution_order(decomposed, strategy)

        # Set depth limits based on strategy
        depth_limits = self._get_depth_limits(decomposed, strategy)

        # Allocate resources
        resource_allocation = self._allocate_resources(
            decomposed, context.time_remaining_seconds, context.budget_remaining
        )

        plan_id = f"plan_{hash(context.query) % 100000}_{context.iteration}"
        plan = AdaptivePlan(
            id=plan_id,
            query=context.query,
            strategy=strategy,
            decomposed=decomposed,
            execution_order=execution_order,
            depth_limits=depth_limits,
            resource_allocation=resource_allocation,
        )

        self._plans[plan_id] = plan
        self._stats["plans_created"] += 1
        self._stats["strategies_used"][strategy.value] = (
            self._stats["strategies_used"].get(strategy.value, 0) + 1
        )

        return plan

    async def refine_plan(
        self,
        plan: AdaptivePlan,
        findings: list[str],
        context: PlanningContext,
    ) -> AdaptivePlan:
        """Refine an existing plan."""
        refined = await self.refiner.refine(plan, findings, context)
        self._stats["plans_refined"] += 1
        return refined

    def _get_max_sub_queries(self, strategy: ResearchStrategy) -> int:
        """Get max sub-queries based on strategy."""
        limits = {
            ResearchStrategy.BREADTH_FIRST: 8,
            ResearchStrategy.DEPTH_FIRST: 3,
            ResearchStrategy.BALANCED: 5,
            ResearchStrategy.FOCUSED: 2,
            ResearchStrategy.COMPARATIVE: 4,
            ResearchStrategy.EXPLORATORY: 6,
        }
        return limits.get(strategy, 5)

    def _determine_execution_order(
        self,
        decomposed: DecomposedQuery,
        strategy: ResearchStrategy,
    ) -> list[str]:
        """Determine execution order based on strategy."""
        if strategy == ResearchStrategy.DEPTH_FIRST:
            # Respect dependencies
            return self._topological_sort(
                decomposed.sub_queries,
                decomposed.dependencies,
            )
        # Execute in priority order
        return list(decomposed.sub_queries)

    def _topological_sort(
        self,
        queries: list[str],
        dependencies: dict[str, list[str]],
    ) -> list[str]:
        """Topologically sort queries based on dependencies."""
        visited: set[str] = set()
        result: list[str] = []

        def visit(query: str) -> None:
            if query in visited:
                return
            visited.add(query)
            for dep in dependencies.get(query, []):
                if dep in queries:
                    visit(dep)
            result.append(query)

        for query in queries:
            visit(query)

        return result

    def _get_depth_limits(
        self,
        decomposed: DecomposedQuery,
        strategy: ResearchStrategy,
    ) -> dict[str, int]:
        """Get depth limits for each sub-query."""
        base_depth = {
            ResearchStrategy.BREADTH_FIRST: 1,
            ResearchStrategy.DEPTH_FIRST: 4,
            ResearchStrategy.BALANCED: 2,
            ResearchStrategy.FOCUSED: 5,
            ResearchStrategy.COMPARATIVE: 2,
            ResearchStrategy.EXPLORATORY: 2,
        }

        depth = base_depth.get(strategy, 2)
        return dict.fromkeys(decomposed.sub_queries, depth)

    def _allocate_resources(
        self,
        decomposed: DecomposedQuery,
        time_budget: float,
        budget: float,
    ) -> dict[str, float]:
        """Allocate resources to sub-queries."""
        if not decomposed.sub_queries:
            return {}

        # Equal allocation for now
        per_query = 1.0 / len(decomposed.sub_queries)
        return dict.fromkeys(decomposed.sub_queries, per_query)

    def get_stats(self) -> dict[str, Any]:
        """Get planning statistics."""
        return self._stats


# Factory functions
def create_adaptive_planner(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> AdaptivePlanner:
    """Create an adaptive planner with default configuration."""
    return AdaptivePlanner(llm_caller=llm_caller)


__all__ = [
    "AdaptivePlan",
    "AdaptivePlanner",
    "DecomposedQuery",
    "IterativeRefiner",
    "PlanningContext",
    "QueryComplexity",
    "QueryDecomposer",
    "ResearchStrategy",
    "StrategySelector",
    "create_adaptive_planner",
]
