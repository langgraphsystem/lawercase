"""Cost Optimization and Tracking for LLM Operations.

This module provides comprehensive cost tracking, budget management,
and intelligent model routing based on cost considerations.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ModelTier(str, Enum):
    """Model performance and cost tiers."""

    ULTRA = "ultra"  # Most expensive, best quality
    HIGH = "high"  # Expensive, high quality
    MEDIUM = "medium"  # Moderate cost, good quality
    LOW = "low"  # Cheap, basic quality
    CACHE = "cache"  # Cached response, minimal cost


@dataclass
class ModelCost:
    """Cost configuration for a model."""

    model_name: str
    tier: ModelTier
    cost_per_1k_input_tokens: float  # USD
    cost_per_1k_output_tokens: float  # USD
    cost_per_request: float = 0.0  # Base cost per request
    avg_latency_ms: float = 1000.0  # Average latency
    quality_score: float = 0.8  # Quality score (0-1)


# Default model costs (примерные цены)
DEFAULT_MODEL_COSTS = {
    "claude-3-opus": ModelCost(
        model_name="claude-3-opus",
        tier=ModelTier.ULTRA,
        cost_per_1k_input_tokens=0.015,
        cost_per_1k_output_tokens=0.075,
        avg_latency_ms=2000,
        quality_score=0.95,
    ),
    "claude-3-sonnet": ModelCost(
        model_name="claude-3-sonnet",
        tier=ModelTier.HIGH,
        cost_per_1k_input_tokens=0.003,
        cost_per_1k_output_tokens=0.015,
        avg_latency_ms=1500,
        quality_score=0.90,
    ),
    "claude-3-haiku": ModelCost(
        model_name="claude-3-haiku",
        tier=ModelTier.MEDIUM,
        cost_per_1k_input_tokens=0.00025,
        cost_per_1k_output_tokens=0.00125,
        avg_latency_ms=800,
        quality_score=0.85,
    ),
    # OpenAI GPT-5 family (2025 pricing; approximate)
    "gpt-5": ModelCost(
        model_name="gpt-5",
        tier=ModelTier.ULTRA,
        cost_per_1k_input_tokens=0.00125,  # $1.25 / 1M
        cost_per_1k_output_tokens=0.010,  # $10 / 1M
        avg_latency_ms=2000,
        quality_score=0.97,
    ),
    "gpt-5-mini": ModelCost(
        model_name="gpt-5-mini",
        tier=ModelTier.HIGH,
        cost_per_1k_input_tokens=0.00025,  # $0.25 / 1M
        cost_per_1k_output_tokens=0.002,  # $2 / 1M
        avg_latency_ms=1200,
        quality_score=0.94,
    ),
    "gpt-5-nano": ModelCost(
        model_name="gpt-5-nano",
        tier=ModelTier.MEDIUM,
        cost_per_1k_input_tokens=0.00005,  # $0.05 / 1M
        cost_per_1k_output_tokens=0.0004,  # $0.40 / 1M
        avg_latency_ms=800,
        quality_score=0.90,
    ),
}


@dataclass
class CostRecord:
    """Record of a single LLM operation cost."""

    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool = False
    operation_type: str = "completion"
    metadata: dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """
    Tracks LLM operation costs and provides analytics.

    Features:
    - Real-time cost tracking
    - Budget monitoring and alerts
    - Cost breakdown by model/operation
    - Trend analysis
    - Cost projections

    Example:
        >>> tracker = CostTracker(daily_budget_usd=100.0)
        >>> tracker.record_operation(
        ...     model="claude-3-sonnet",
        ...     input_tokens=1000,
        ...     output_tokens=500,
        ...     latency_ms=1200
        ... )
    """

    def __init__(
        self,
        daily_budget_usd: float | None = None,
        monthly_budget_usd: float | None = None,
        alert_threshold_pct: float = 0.8,
        history_size: int = 10000,
    ):
        """
        Initialize cost tracker.

        Args:
            daily_budget_usd: Daily budget limit
            monthly_budget_usd: Monthly budget limit
            alert_threshold_pct: Alert when reaching % of budget
            history_size: Number of records to keep in memory
        """
        self.daily_budget = daily_budget_usd
        self.monthly_budget = monthly_budget_usd
        self.alert_threshold = alert_threshold_pct
        self.history_size = history_size

        # Cost tracking
        self.records: deque[CostRecord] = deque(maxlen=history_size)
        self.model_costs = DEFAULT_MODEL_COSTS.copy()

        # Daily/monthly totals
        self.daily_costs: dict[str, float] = {}  # date -> cost
        self.monthly_costs: dict[str, float] = {}  # month -> cost

        # Statistics
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_operations = 0

        # Per-model stats
        self.model_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "operations": 0,
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "avg_latency": 0.0,
            }
        )

    def record_operation(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cached: bool = False,
        operation_type: str = "completion",
        **metadata: Any,
    ) -> float:
        """
        Record an LLM operation and return its cost.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Operation latency
            cached: Whether response was cached
            operation_type: Type of operation
            **metadata: Additional metadata

        Returns:
            Cost in USD

        Example:
            >>> cost = tracker.record_operation(
            ...     model="claude-3-sonnet",
            ...     input_tokens=1000,
            ...     output_tokens=500,
            ...     latency_ms=1200
            ... )
            >>> print(f"Cost: ${cost:.4f}")
        """
        # Calculate cost
        if cached:
            cost = 0.0  # Cached responses are free
        else:
            model_cost = self.model_costs.get(model)
            if model_cost:
                input_cost = (input_tokens / 1000) * model_cost.cost_per_1k_input_tokens
                output_cost = (output_tokens / 1000) * model_cost.cost_per_1k_output_tokens
                cost = input_cost + output_cost + model_cost.cost_per_request
            else:
                # Unknown model, estimate
                cost = (input_tokens + output_tokens) / 1000 * 0.002

        # Create record
        record = CostRecord(
            timestamp=datetime.utcnow(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            cached=cached,
            operation_type=operation_type,
            metadata=metadata,
        )

        self.records.append(record)

        # Update totals
        self.total_cost_usd += cost
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_operations += 1

        # Update daily/monthly
        date_key = record.timestamp.strftime("%Y-%m-%d")
        month_key = record.timestamp.strftime("%Y-%m")

        self.daily_costs[date_key] = self.daily_costs.get(date_key, 0.0) + cost
        self.monthly_costs[month_key] = self.monthly_costs.get(month_key, 0.0) + cost

        # Update model stats
        stats = self.model_stats[model]
        stats["operations"] += 1
        stats["total_cost"] += cost
        stats["input_tokens"] += input_tokens
        stats["output_tokens"] += output_tokens
        stats["avg_latency"] = (
            stats["avg_latency"] * (stats["operations"] - 1) + latency_ms
        ) / stats["operations"]

        # Check budget alerts
        self._check_budget_alerts()

        return cost

    def _check_budget_alerts(self) -> None:
        """Check if budget thresholds are exceeded."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        this_month = datetime.utcnow().strftime("%Y-%m")

        # Daily budget check
        if self.daily_budget:
            today_cost = self.daily_costs.get(today, 0.0)
            if today_cost >= self.daily_budget * self.alert_threshold:
                print(f"⚠️  Daily budget alert: ${today_cost:.2f} / ${self.daily_budget:.2f}")

        # Monthly budget check
        if self.monthly_budget:
            month_cost = self.monthly_costs.get(this_month, 0.0)
            if month_cost >= self.monthly_budget * self.alert_threshold:
                print(f"⚠️  Monthly budget alert: ${month_cost:.2f} / ${self.monthly_budget:.2f}")

    def get_daily_cost(self, date: str | None = None) -> float:
        """Get cost for a specific day (or today)."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return self.daily_costs.get(date, 0.0)

    def get_monthly_cost(self, month: str | None = None) -> float:
        """Get cost for a specific month (or current month)."""
        if month is None:
            month = datetime.utcnow().strftime("%Y-%m")
        return self.monthly_costs.get(month, 0.0)

    def get_model_stats(self, model: str) -> dict[str, Any]:
        """Get statistics for a specific model."""
        return dict(self.model_stats.get(model, {}))

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary."""
        today_cost = self.get_daily_cost()
        month_cost = self.get_monthly_cost()

        return {
            "total_cost_usd": self.total_cost_usd,
            "total_operations": self.total_operations,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_cost_per_operation": (
                self.total_cost_usd / self.total_operations if self.total_operations > 0 else 0
            ),
            "today_cost": today_cost,
            "monthly_cost": month_cost,
            "daily_budget": self.daily_budget,
            "monthly_budget": self.monthly_budget,
            "daily_budget_remaining": (
                self.daily_budget - today_cost if self.daily_budget else None
            ),
            "monthly_budget_remaining": (
                self.monthly_budget - month_cost if self.monthly_budget else None
            ),
        }

    def get_cost_by_model(self) -> dict[str, float]:
        """Get total cost breakdown by model."""
        return {model: stats["total_cost"] for model, stats in self.model_stats.items()}

    def project_monthly_cost(self) -> float:
        """Project end-of-month cost based on current usage."""
        today = datetime.utcnow()
        days_in_month = 30  # Simplified
        day_of_month = today.day

        if day_of_month == 0:
            return 0.0

        month_cost = self.get_monthly_cost()
        daily_avg = month_cost / day_of_month
        projected = daily_avg * days_in_month

        return projected


class CostOptimizer:
    """
    Intelligent cost optimization through model selection.

    Features:
    - Quality-aware model routing
    - Budget-based model selection
    - Cost-performance optimization
    - Automatic tier downgrade when approaching budget

    Example:
        >>> optimizer = CostOptimizer(tracker)
        >>> model = optimizer.select_model(
        ...     task_complexity="medium",
        ...     required_quality=0.8,
        ...     max_cost_usd=0.01
        ... )
    """

    def __init__(
        self,
        cost_tracker: CostTracker,
        enable_auto_optimization: bool = True,
    ):
        """
        Initialize cost optimizer.

        Args:
            cost_tracker: CostTracker instance
            enable_auto_optimization: Enable automatic optimization
        """
        self.tracker = cost_tracker
        self.enable_auto_optimization = enable_auto_optimization
        self.model_costs = DEFAULT_MODEL_COSTS

    def select_model(
        self,
        task_complexity: str = "medium",
        required_quality: float = 0.8,
        max_cost_usd: float | None = None,
        max_latency_ms: float | None = None,
    ) -> str:
        """
        Select optimal model based on constraints.

        Args:
            task_complexity: Task complexity (low/medium/high/ultra)
            required_quality: Minimum quality score (0-1)
            max_cost_usd: Maximum cost per request
            max_latency_ms: Maximum acceptable latency

        Returns:
            Selected model name

        Example:
            >>> model = optimizer.select_model(
            ...     task_complexity="high",
            ...     required_quality=0.9,
            ...     max_cost_usd=0.05
            ... )
        """
        # Map complexity to minimum tier
        complexity_to_tier = {
            "low": ModelTier.LOW,
            "medium": ModelTier.MEDIUM,
            "high": ModelTier.HIGH,
            "ultra": ModelTier.ULTRA,
        }
        min_tier = complexity_to_tier.get(task_complexity, ModelTier.MEDIUM)

        # Filter models by constraints
        candidates = []
        for model_name, model_cost in self.model_costs.items():
            # Check tier
            tier_order = [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH, ModelTier.ULTRA]
            if tier_order.index(model_cost.tier) < tier_order.index(min_tier):
                continue

            # Check quality
            if model_cost.quality_score < required_quality:
                continue

            # Check latency
            if max_latency_ms and model_cost.avg_latency_ms > max_latency_ms:
                continue

            # Estimate cost
            avg_tokens = 2000  # Estimated average
            est_cost = (avg_tokens / 1000) * (
                model_cost.cost_per_1k_input_tokens + model_cost.cost_per_1k_output_tokens
            )

            # Check cost
            if max_cost_usd and est_cost > max_cost_usd:
                continue

            candidates.append((model_name, model_cost, est_cost))

        if not candidates:
            # Fallback to cheapest model that meets quality
            for model_name, model_cost in sorted(
                self.model_costs.items(),
                key=lambda x: x[1].cost_per_1k_input_tokens,
            ):
                if model_cost.quality_score >= required_quality:
                    return model_name
            # Ultimate fallback: cheapest GPT-5 tier
            return "gpt-5-nano"

        # Sort by cost (prefer cheaper)
        candidates.sort(key=lambda x: x[2])

        # If budget constrained, check remaining budget
        if self.enable_auto_optimization and self.tracker.daily_budget:
            remaining = self.tracker.daily_budget - self.tracker.get_daily_cost()
            if remaining < self.tracker.daily_budget * 0.2:  # Less than 20% remaining
                # Prefer cheaper models
                return candidates[0][0]

        # Return best cost-performance balance
        return candidates[0][0]

    def get_recommendations(self) -> list[dict[str, Any]]:
        """
        Get cost optimization recommendations.

        Returns:
            List of optimization recommendations

        Example:
            >>> recommendations = optimizer.get_recommendations()
            >>> for rec in recommendations:
            ...     print(rec["suggestion"])
        """
        recommendations = []

        # Check if spending is high
        summary = self.tracker.get_summary()
        if summary["monthly_budget"] and summary["monthly_cost"] > summary["monthly_budget"] * 0.8:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "budget",
                    "suggestion": "Approaching monthly budget limit. Consider using lower-tier models.",
                    "estimated_savings": summary["monthly_cost"] * 0.3,
                }
            )

        # Check model usage
        cost_by_model = self.tracker.get_cost_by_model()
        if cost_by_model:
            most_expensive_model = max(cost_by_model.items(), key=lambda x: x[1])
            if most_expensive_model[1] > summary["total_cost_usd"] * 0.5:
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "model_usage",
                        "suggestion": f"Model '{most_expensive_model[0]}' accounts for >50% of costs. "
                        f"Consider using alternatives for simpler tasks.",
                        "estimated_savings": most_expensive_model[1] * 0.4,
                    }
                )

        # Check cache usage
        cached_ops = sum(1 for r in self.tracker.records if r.cached)
        total_ops = len(self.tracker.records)
        if total_ops > 100:
            cache_rate = cached_ops / total_ops
            if cache_rate < 0.3:
                avg_cost = summary["avg_cost_per_operation"]
                potential_savings = (total_ops * 0.3 - cached_ops) * avg_cost
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "caching",
                        "suggestion": f"Cache hit rate is only {cache_rate:.1%}. "
                        f"Improve caching to reduce costs.",
                        "estimated_savings": potential_savings,
                    }
                )

        return recommendations


# Global singletons
_cost_tracker: CostTracker | None = None
_cost_optimizer: CostOptimizer | None = None


def get_cost_tracker(
    daily_budget_usd: float | None = None,
    monthly_budget_usd: float | None = None,
) -> CostTracker:
    """
    Get global cost tracker instance.

    Args:
        daily_budget_usd: Daily budget (only on first call)
        monthly_budget_usd: Monthly budget (only on first call)

    Returns:
        CostTracker instance
    """
    global _cost_tracker

    if _cost_tracker is None:
        _cost_tracker = CostTracker(
            daily_budget_usd=daily_budget_usd,
            monthly_budget_usd=monthly_budget_usd,
        )

    return _cost_tracker


def get_cost_optimizer() -> CostOptimizer:
    """
    Get global cost optimizer instance.

    Returns:
        CostOptimizer instance
    """
    global _cost_optimizer

    if _cost_optimizer is None:
        tracker = get_cost_tracker()
        _cost_optimizer = CostOptimizer(tracker)

    return _cost_optimizer
