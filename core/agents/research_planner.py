"""Research Planner - Standalone module for research planning.

Re-exports ResearchPlanner from deep_research_agent and provides
additional planning utilities.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from .deep_research_agent import (
    ResearchPlan,
    ResearchPlanner as BaseResearchPlanner,
    ResearchQuestion,
    SourceType,
)

logger = structlog.get_logger(__name__)


class PlanningStrategy(str, Enum):
    """Research planning strategies."""

    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    BALANCED = "balanced"
    FOCUSED = "focused"
    COMPARATIVE = "comparative"
    EXPLORATORY = "exploratory"


@dataclass
class PlanningConfig:
    """Configuration for research planning."""

    strategy: PlanningStrategy = PlanningStrategy.BALANCED
    max_sub_questions: int = 5
    max_depth: int = 3
    time_budget_seconds: float = 300
    max_findings: int = 50
    prioritize_academic: bool = False
    require_citations: bool = True
    domain: str = "general"


@dataclass
class PlanEvaluation:
    """Evaluation of a research plan's effectiveness."""

    plan_id: str
    completeness: float  # 0-1: coverage of main question aspects
    feasibility: float  # 0-1: likelihood of finding relevant info
    efficiency: float  # 0-1: how well resources are allocated
    overall_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.overall_score = (
            self.completeness * 0.4 + self.feasibility * 0.3 + self.efficiency * 0.3
        )


class EnhancedResearchPlanner(BaseResearchPlanner):
    """Enhanced Research Planner with additional capabilities.

    Extends base planner with:
    - Strategy-aware planning
    - Plan evaluation
    - Adaptive refinement
    - Domain-specific adjustments
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        config: PlanningConfig | None = None,
    ):
        super().__init__(llm_caller=llm_caller)
        self.config = config or PlanningConfig()
        self._plan_history: list[ResearchPlan] = []

    async def create_strategic_plan(
        self,
        question: str,
        context: str = "",
        strategy: PlanningStrategy | None = None,
    ) -> ResearchPlan:
        """Create a research plan using specified strategy.

        Args:
            question: Main research question
            context: Additional context
            strategy: Planning strategy to use

        Returns:
            ResearchPlan with strategy-appropriate sub-questions
        """
        strategy = strategy or self.config.strategy

        # Adjust parameters based on strategy
        params = self._get_strategy_params(strategy)

        # Create base plan
        plan = await self.create_plan(
            question=question,
            context=context,
            max_sub_questions=params["max_sub_questions"],
            max_depth=params["max_depth"],
        )

        # Set strategy
        plan.strategy = strategy.value
        plan.time_budget_seconds = params["time_budget"]
        plan.max_findings = params["max_findings"]

        # Apply domain adjustments
        plan = await self._apply_domain_adjustments(plan)

        self._plan_history.append(plan)
        logger.info(
            "research_planner.plan_created",
            plan_id=plan.id,
            strategy=strategy.value,
            sub_questions=len(plan.sub_questions),
        )

        return plan

    def _get_strategy_params(self, strategy: PlanningStrategy) -> dict[str, Any]:
        """Get planning parameters for strategy."""
        params = {
            PlanningStrategy.BREADTH_FIRST: {
                "max_sub_questions": 8,
                "max_depth": 1,
                "time_budget": 180,
                "max_findings": 40,
            },
            PlanningStrategy.DEPTH_FIRST: {
                "max_sub_questions": 3,
                "max_depth": 4,
                "time_budget": 360,
                "max_findings": 30,
            },
            PlanningStrategy.BALANCED: {
                "max_sub_questions": 5,
                "max_depth": 2,
                "time_budget": 300,
                "max_findings": 50,
            },
            PlanningStrategy.FOCUSED: {
                "max_sub_questions": 2,
                "max_depth": 5,
                "time_budget": 240,
                "max_findings": 20,
            },
            PlanningStrategy.COMPARATIVE: {
                "max_sub_questions": 4,
                "max_depth": 2,
                "time_budget": 300,
                "max_findings": 40,
            },
            PlanningStrategy.EXPLORATORY: {
                "max_sub_questions": 6,
                "max_depth": 2,
                "time_budget": 240,
                "max_findings": 60,
            },
        }
        return params.get(strategy, params[PlanningStrategy.BALANCED])

    async def _apply_domain_adjustments(self, plan: ResearchPlan) -> ResearchPlan:
        """Apply domain-specific adjustments to plan."""
        domain = self.config.domain

        # Domain-specific source priorities
        source_priorities = {
            "legal": [SourceType.DATABASE, SourceType.DOCUMENT, SourceType.ACADEMIC],
            "scientific": [SourceType.ACADEMIC, SourceType.DATABASE, SourceType.WEB],
            "technical": [SourceType.WEB, SourceType.DOCUMENT, SourceType.DATABASE],
            "business": [SourceType.WEB, SourceType.DATABASE, SourceType.DOCUMENT],
            "general": [SourceType.WEB, SourceType.DATABASE, SourceType.ACADEMIC],
        }

        priorities = source_priorities.get(domain, source_priorities["general"])

        # Assign source types to sub-questions
        for _i, q in enumerate(plan.sub_questions):
            q.source_types = priorities[:2]  # Top 2 sources for each question

        return plan

    async def evaluate_plan(self, plan: ResearchPlan) -> PlanEvaluation:
        """Evaluate a research plan's quality.

        Args:
            plan: Plan to evaluate

        Returns:
            PlanEvaluation with scores and recommendations
        """
        recommendations = []

        # Completeness: based on sub-questions coverage
        sub_q_count = len(plan.sub_questions)
        completeness = min(sub_q_count / 5, 1.0)  # 5 questions = good coverage

        if sub_q_count < 3:
            recommendations.append("Add more sub-questions for comprehensive coverage")

        # Feasibility: based on source types and depth
        has_web = any(
            SourceType.WEB in q.source_types for q in plan.sub_questions if q.source_types
        )
        has_academic = any(
            SourceType.ACADEMIC in q.source_types for q in plan.sub_questions if q.source_types
        )

        feasibility = 0.7
        if has_web:
            feasibility += 0.15
        if has_academic:
            feasibility += 0.15
        feasibility = min(feasibility, 1.0)

        if not has_web and not has_academic:
            recommendations.append("Add web or academic sources for better coverage")

        # Efficiency: based on time/findings ratio and depth
        time_per_finding = plan.time_budget_seconds / max(plan.max_findings, 1)
        efficiency = min(time_per_finding / 10, 1.0)  # 10s per finding = good efficiency

        if time_per_finding > 15:
            recommendations.append("Consider increasing parallel searches for efficiency")

        return PlanEvaluation(
            plan_id=plan.id,
            completeness=completeness,
            feasibility=feasibility,
            efficiency=efficiency,
            recommendations=recommendations,
        )

    async def optimize_plan(
        self,
        plan: ResearchPlan,
        evaluation: PlanEvaluation | None = None,
    ) -> ResearchPlan:
        """Optimize a plan based on evaluation.

        Args:
            plan: Plan to optimize
            evaluation: Optional pre-computed evaluation

        Returns:
            Optimized ResearchPlan
        """
        if evaluation is None:
            evaluation = await self.evaluate_plan(plan)

        # Optimization based on scores
        if evaluation.completeness < 0.6:
            # Add more sub-questions
            additional = await self._generate_sub_questions(
                plan.main_question,
                "",
                max_count=3,
            )
            plan.sub_questions.extend(additional)

        if evaluation.feasibility < 0.6:
            # Add web sources to questions without them
            for q in plan.sub_questions:
                if not q.source_types:
                    q.source_types = [SourceType.WEB, SourceType.DATABASE]

        if evaluation.efficiency < 0.6:
            # Reduce time budget or increase parallelism
            plan.time_budget_seconds = min(plan.time_budget_seconds, 300)

        logger.info(
            "research_planner.plan_optimized",
            plan_id=plan.id,
            original_score=evaluation.overall_score,
        )

        return plan

    def get_plan_history(self) -> list[dict[str, Any]]:
        """Get history of created plans."""
        return [p.to_dict() for p in self._plan_history]


# Re-export base classes
ResearchPlanner = EnhancedResearchPlanner

__all__ = [
    "BaseResearchPlanner",
    "EnhancedResearchPlanner",
    "PlanEvaluation",
    "PlanningConfig",
    "PlanningStrategy",
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchQuestion",
]
