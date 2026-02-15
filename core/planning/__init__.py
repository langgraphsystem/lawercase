"""Adaptive Research Planning Module.

Provides dynamic research strategy selection and planning:
- AdaptivePlanner: LLM-driven planning with strategy selection
- QueryDecomposer: Break complex queries into sub-queries
- StrategySelector: Select optimal research strategies
- IterativeRefiner: Refine plans based on findings

Usage:
    from core.planning import (
        AdaptivePlanner,
        StrategySelector,
        QueryDecomposer,
        IterativeRefiner,
        create_adaptive_planner,
    )

    # Create planner with LLM support
    planner = create_adaptive_planner(llm_caller=my_llm)

    # Create research plan
    context = PlanningContext(query="EB-1A requirements")
    plan = await planner.create_plan(context)
"""

from __future__ import annotations

# Core adaptive planner (integrated classes)
from .adaptive_planner import (
    AdaptivePlan,
    AdaptivePlanner,
    DecomposedQuery as AdaptiveDecomposedQuery,
    IterativeRefiner as AdaptiveIterativeRefiner,
    PlanningContext,
    QueryComplexity,
    QueryDecomposer as AdaptiveQueryDecomposer,
    ResearchStrategy,
    StrategySelector as AdaptiveStrategySelector,
    create_adaptive_planner,
)

# Standalone iterative refiner module
from .iterative_refiner import (
    CoverageAssessment,
    CoverageLevel,
    Finding,
    IterativeRefiner,
    RefinementAction,
    RefinementContext,
    RefinementResult,
    create_iterative_refiner,
)

# Standalone query decomposer module
from .query_decomposer import (
    DecomposedQuery,
    DecompositionStrategy,
    QueryDecomposer,
    SubQuery,
    SubQueryPriority,
    create_query_decomposer,
)

# Standalone strategy selector module
from .strategy_selector import (
    DomainType,
    QueryComplexity as SelectorQueryComplexity,
    ResearchStrategy as SelectorResearchStrategy,
    StrategyContext,
    StrategyRecommendation,
    StrategySelector,
    create_strategy_selector,
)

__all__ = [
    "AdaptiveDecomposedQuery",
    "AdaptiveIterativeRefiner",
    # Adaptive Planner (integrated)
    "AdaptivePlan",
    "AdaptivePlanner",
    "AdaptiveQueryDecomposer",
    "AdaptiveStrategySelector",
    # Iterative Refiner (standalone)
    "CoverageAssessment",
    "CoverageLevel",
    # Query Decomposer (standalone)
    "DecomposedQuery",
    "DecompositionStrategy",
    # Strategy Selector (standalone)
    "DomainType",
    "Finding",
    "IterativeRefiner",
    "PlanningContext",
    "QueryComplexity",
    "QueryDecomposer",
    "RefinementAction",
    "RefinementContext",
    "RefinementResult",
    "ResearchStrategy",
    "SelectorQueryComplexity",
    "SelectorResearchStrategy",
    "StrategyContext",
    "StrategyRecommendation",
    "StrategySelector",
    "SubQuery",
    "SubQueryPriority",
    "create_adaptive_planner",
    "create_iterative_refiner",
    "create_query_decomposer",
    "create_strategy_selector",
]
