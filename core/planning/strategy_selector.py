"""Strategy Selector for Adaptive Research Planning.

Selects optimal research strategies based on:
- Query analysis
- Domain classification
- Resource constraints
- Prior results
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
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


class DomainType(str, Enum):
    """Research domain types."""

    GENERAL = "general"
    LEGAL = "legal"
    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    BUSINESS = "business"
    MEDICAL = "medical"


@dataclass
class StrategyContext:
    """Context for strategy selection."""

    query: str
    domain: DomainType = DomainType.GENERAL
    time_budget_seconds: float = 300
    cost_budget: float = 1.0
    depth_preference: float = 0.5  # 0=breadth, 1=depth
    prior_strategies: list[ResearchStrategy] = field(default_factory=list)
    prior_results_quality: float | None = None
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "domain": self.domain.value,
            "time_budget": self.time_budget_seconds,
            "cost_budget": self.cost_budget,
            "depth_preference": self.depth_preference,
        }


@dataclass
class StrategyRecommendation:
    """Strategy recommendation with reasoning."""

    strategy: ResearchStrategy
    confidence: float  # 0-1
    reasoning: str
    alternative: ResearchStrategy | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternative": self.alternative.value if self.alternative else None,
            "parameters": self.parameters,
        }


class StrategySelector:
    """Selects optimal research strategy based on query analysis.

    Features:
    - Rule-based selection with keyword matching
    - LLM-based selection for complex queries
    - Domain-specific strategy tuning
    - Adaptive selection based on prior results

    Usage:
        selector = StrategySelector()

        context = StrategyContext(
            query="Compare EB-1A and EB-2 NIW requirements",
            domain=DomainType.LEGAL,
        )

        recommendation = await selector.select(context)
        print(f"Strategy: {recommendation.strategy}")
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        enable_llm_selection: bool = True,
    ) -> None:
        self._llm_caller = llm_caller
        self._enable_llm = enable_llm_selection

        # Keyword-based strategy mapping
        self._keyword_strategies: dict[str, ResearchStrategy] = {
            # Comparative
            "compare": ResearchStrategy.COMPARATIVE,
            "difference": ResearchStrategy.COMPARATIVE,
            "vs": ResearchStrategy.COMPARATIVE,
            "versus": ResearchStrategy.COMPARATIVE,
            "better": ResearchStrategy.COMPARATIVE,
            "choose between": ResearchStrategy.COMPARATIVE,
            # Exploratory
            "explore": ResearchStrategy.EXPLORATORY,
            "possibilities": ResearchStrategy.EXPLORATORY,
            "options": ResearchStrategy.EXPLORATORY,
            "what can": ResearchStrategy.EXPLORATORY,
            # Focused/Depth
            "what is": ResearchStrategy.FOCUSED,
            "define": ResearchStrategy.FOCUSED,
            "explain": ResearchStrategy.DEPTH_FIRST,
            "how to": ResearchStrategy.DEPTH_FIRST,
            "why does": ResearchStrategy.DEPTH_FIRST,
            "how does": ResearchStrategy.DEPTH_FIRST,
            "step by step": ResearchStrategy.DEPTH_FIRST,
            "in detail": ResearchStrategy.DEPTH_FIRST,
            # Breadth
            "overview": ResearchStrategy.BREADTH_FIRST,
            "summary": ResearchStrategy.BREADTH_FIRST,
            "list": ResearchStrategy.BREADTH_FIRST,
            "types of": ResearchStrategy.BREADTH_FIRST,
            "categories": ResearchStrategy.BREADTH_FIRST,
            "examples of": ResearchStrategy.BREADTH_FIRST,
            "all": ResearchStrategy.BREADTH_FIRST,
        }

        # Domain-specific strategy preferences
        self._domain_preferences: dict[DomainType, ResearchStrategy] = {
            DomainType.LEGAL: ResearchStrategy.DEPTH_FIRST,
            DomainType.SCIENTIFIC: ResearchStrategy.DEPTH_FIRST,
            DomainType.TECHNICAL: ResearchStrategy.BALANCED,
            DomainType.BUSINESS: ResearchStrategy.BALANCED,
            DomainType.MEDICAL: ResearchStrategy.DEPTH_FIRST,
            DomainType.GENERAL: ResearchStrategy.BALANCED,
        }

        # Patterns for complexity detection
        self._complex_patterns = [
            r"\b(and|or)\b.*\b(and|or)\b",  # Multiple conjunctions
            r"\?.*\?",  # Multiple questions
            r"(how|why|what).*\b(if|when|because)\b",  # Conditional questions
        ]

        # Stats
        self._stats = {
            "selections_made": 0,
            "llm_selections": 0,
            "rule_selections": 0,
            "strategies_used": {},
        }

    async def select(self, context: StrategyContext) -> StrategyRecommendation:
        """Select optimal strategy for the given context.

        Args:
            context: Strategy selection context

        Returns:
            Strategy recommendation with confidence and reasoning
        """
        self._stats["selections_made"] += 1
        query_lower = context.query.lower()

        # Try rule-based selection first
        rule_result = self._rule_based_select(query_lower, context)
        if rule_result and rule_result.confidence >= 0.8:
            self._stats["rule_selections"] += 1
            self._record_strategy(rule_result.strategy)
            return rule_result

        # Try LLM-based selection for complex queries
        if self._llm_caller and self._enable_llm:
            complexity = self.estimate_complexity(context.query)
            if complexity in (QueryComplexity.COMPLEX, QueryComplexity.EXPERT):
                llm_result = await self._llm_based_select(context)
                if llm_result:
                    self._stats["llm_selections"] += 1
                    self._record_strategy(llm_result.strategy)
                    return llm_result

        # Fall back to domain preference or rule result
        if rule_result:
            self._stats["rule_selections"] += 1
            self._record_strategy(rule_result.strategy)
            return rule_result

        # Default to domain preference
        strategy = self._domain_preferences.get(context.domain, ResearchStrategy.BALANCED)
        self._record_strategy(strategy)

        return StrategyRecommendation(
            strategy=strategy,
            confidence=0.5,
            reasoning=f"Default strategy for {context.domain.value} domain",
            parameters=self._get_strategy_parameters(strategy, context),
        )

    def _rule_based_select(
        self,
        query_lower: str,
        context: StrategyContext,
    ) -> StrategyRecommendation | None:
        """Select strategy using rule-based matching."""
        matched_strategy: ResearchStrategy | None = None
        matched_keyword: str | None = None

        for keyword, strategy in self._keyword_strategies.items():
            if keyword in query_lower:
                matched_strategy = strategy
                matched_keyword = keyword
                break

        if not matched_strategy:
            return None

        # Adjust confidence based on context
        confidence = 0.75
        if context.prior_strategies:
            # If same strategy was used before with good results
            if (
                matched_strategy in context.prior_strategies
                and context.prior_results_quality
                and context.prior_results_quality > 0.7
            ):
                confidence = 0.9

        # Consider resource constraints
        if context.time_budget_seconds < 60 and matched_strategy == ResearchStrategy.DEPTH_FIRST:
            # Not enough time for depth-first
            return StrategyRecommendation(
                strategy=ResearchStrategy.FOCUSED,
                confidence=0.7,
                reasoning="Limited time budget; switching from depth_first to focused",
                alternative=matched_strategy,
                parameters=self._get_strategy_parameters(ResearchStrategy.FOCUSED, context),
            )

        return StrategyRecommendation(
            strategy=matched_strategy,
            confidence=confidence,
            reasoning=f"Matched keyword '{matched_keyword}' in query",
            parameters=self._get_strategy_parameters(matched_strategy, context),
        )

    async def _llm_based_select(
        self,
        context: StrategyContext,
    ) -> StrategyRecommendation | None:
        """Select strategy using LLM."""
        if not self._llm_caller:
            return None

        prompt = f"""Analyze this research query and recommend the best strategy.

Query: {context.query}
Domain: {context.domain.value}
Time budget: {context.time_budget_seconds} seconds
Cost budget: {context.cost_budget}

Available strategies:
- breadth_first: Explore many topics quickly (good for overviews)
- depth_first: Deep investigation of one topic (good for detailed analysis)
- balanced: Mix of breadth and depth (good for moderate complexity)
- focused: Single aspect deep dive (good for specific questions)
- comparative: Compare multiple options (good for decision making)
- exploratory: Open-ended exploration (good for unknown areas)

Respond with:
STRATEGY: <strategy_name>
CONFIDENCE: <0-1>
REASONING: <brief explanation>"""

        try:
            response = await self._llm_caller(prompt)

            # Parse response
            strategy_match = re.search(r"STRATEGY:\s*(\w+)", response)
            confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", response)
            reasoning_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", response, re.DOTALL)

            if strategy_match:
                strategy_name = strategy_match.group(1).lower().strip()
                try:
                    strategy = ResearchStrategy(strategy_name)
                except ValueError:
                    strategy = ResearchStrategy.BALANCED

                confidence = float(confidence_match.group(1)) if confidence_match else 0.7
                reasoning = (
                    reasoning_match.group(1).strip() if reasoning_match else "LLM recommendation"
                )

                return StrategyRecommendation(
                    strategy=strategy,
                    confidence=min(confidence, 0.95),  # Cap LLM confidence
                    reasoning=f"LLM analysis: {reasoning}",
                    parameters=self._get_strategy_parameters(strategy, context),
                )

        except Exception as e:
            logger.warning(f"LLM strategy selection failed: {e}")

        return None

    def estimate_complexity(self, query: str) -> QueryComplexity:
        """Estimate query complexity level.

        Args:
            query: The research query

        Returns:
            Estimated complexity level
        """
        word_count = len(query.split())
        question_marks = query.count("?")

        # Check for complex patterns
        pattern_matches = sum(
            1 for pattern in self._complex_patterns if re.search(pattern, query, re.IGNORECASE)
        )

        # Technical terms indicating expertise needed
        technical_terms = [
            "algorithm",
            "implementation",
            "architecture",
            "policy",
            "regulation",
            "statute",
            "jurisprudence",
            "methodology",
            "framework",
            "protocol",
            "specification",
            "compliance",
        ]
        has_technical = any(term in query.lower() for term in technical_terms)

        # Score complexity
        score = 0
        score += min(word_count // 10, 3)  # Longer queries = more complex
        score += question_marks  # Multiple questions
        score += pattern_matches * 2
        score += 2 if has_technical else 0

        if score <= 1:
            return QueryComplexity.SIMPLE
        if score <= 3:
            return QueryComplexity.MODERATE
        if score <= 5:
            return QueryComplexity.COMPLEX
        return QueryComplexity.EXPERT

    def _get_strategy_parameters(
        self,
        strategy: ResearchStrategy,
        context: StrategyContext,
    ) -> dict[str, Any]:
        """Get recommended parameters for strategy."""
        base_params: dict[str, Any] = {
            "max_iterations": 3,
            "parallel_queries": 1,
        }

        if strategy == ResearchStrategy.BREADTH_FIRST:
            base_params.update(
                {
                    "max_sub_queries": 8,
                    "depth_limit": 1,
                    "parallel_queries": 4,
                }
            )
        elif strategy == ResearchStrategy.DEPTH_FIRST:
            base_params.update(
                {
                    "max_sub_queries": 3,
                    "depth_limit": 4,
                    "parallel_queries": 1,
                }
            )
        elif strategy == ResearchStrategy.BALANCED:
            base_params.update(
                {
                    "max_sub_queries": 5,
                    "depth_limit": 2,
                    "parallel_queries": 2,
                }
            )
        elif strategy == ResearchStrategy.FOCUSED:
            base_params.update(
                {
                    "max_sub_queries": 2,
                    "depth_limit": 5,
                    "parallel_queries": 1,
                }
            )
        elif strategy == ResearchStrategy.COMPARATIVE:
            base_params.update(
                {
                    "max_sub_queries": 4,
                    "depth_limit": 2,
                    "parallel_queries": 4,
                    "comparison_mode": True,
                }
            )
        elif strategy == ResearchStrategy.EXPLORATORY:
            base_params.update(
                {
                    "max_sub_queries": 6,
                    "depth_limit": 2,
                    "parallel_queries": 3,
                    "allow_tangents": True,
                }
            )

        # Adjust for resource constraints
        time_factor = min(context.time_budget_seconds / 300, 1.0)
        cost_factor = min(context.cost_budget, 1.0)
        resource_factor = min(time_factor, cost_factor)

        if resource_factor < 0.5:
            base_params["max_sub_queries"] = max(1, base_params["max_sub_queries"] // 2)
            base_params["depth_limit"] = max(1, base_params["depth_limit"] - 1)

        return base_params

    def _record_strategy(self, strategy: ResearchStrategy) -> None:
        """Record strategy usage for stats."""
        key = strategy.value
        self._stats["strategies_used"][key] = self._stats["strategies_used"].get(key, 0) + 1

    def get_stats(self) -> dict[str, Any]:
        """Get selector statistics."""
        return self._stats


# Factory function
def create_strategy_selector(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> StrategySelector:
    """Create a strategy selector with optional LLM support."""
    return StrategySelector(llm_caller=llm_caller)


__all__ = [
    "DomainType",
    "QueryComplexity",
    "ResearchStrategy",
    "StrategyContext",
    "StrategyRecommendation",
    "StrategySelector",
    "create_strategy_selector",
]
