"""LLM-Specific Metrics Collection.

Provides comprehensive metrics for LLM operations:
- Request/response metrics
- Token usage tracking
- Cost monitoring
- Latency histograms
- Error rates
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Single metric measurement."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class HistogramBucket:
    """Histogram bucket for latency distribution."""

    le: float  # Less than or equal
    count: int = 0


class Counter:
    """Monotonically increasing counter."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._values: dict[tuple, float] = defaultdict(float)

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment counter."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] += value

    def get(self, labels: dict[str, str] | None = None) -> float:
        """Get current value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0.0)

    def collect(self) -> list[MetricValue]:
        """Collect all values."""
        return [
            MetricValue(
                name=self.name,
                value=value,
                labels=dict(key),
                metric_type=MetricType.COUNTER,
            )
            for key, value in self._values.items()
        ]


class Gauge:
    """Metric that can go up and down."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._values: dict[tuple, float] = defaultdict(float)

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge value."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] = value

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment gauge."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] += value

    def dec(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Decrement gauge."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] -= value

    def get(self, labels: dict[str, str] | None = None) -> float:
        """Get current value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0.0)

    def collect(self) -> list[MetricValue]:
        """Collect all values."""
        return [
            MetricValue(
                name=self.name,
                value=value,
                labels=dict(key),
                metric_type=MetricType.GAUGE,
            )
            for key, value in self._values.items()
        ]


class Histogram:
    """Histogram for measuring distributions."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.buckets = buckets or self.DEFAULT_BUCKETS

        self._counts: dict[tuple, dict[float, int]] = defaultdict(
            lambda: dict.fromkeys(self.buckets, 0)
        )
        self._sums: dict[tuple, float] = defaultdict(float)
        self._totals: dict[tuple, int] = defaultdict(int)

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Record an observation."""
        key = tuple(sorted((labels or {}).items()))
        self._sums[key] += value
        self._totals[key] += 1

        for bucket in self.buckets:
            if value <= bucket:
                self._counts[key][bucket] += 1

    def get_percentile(self, percentile: float, labels: dict[str, str] | None = None) -> float:
        """Estimate percentile from histogram."""
        key = tuple(sorted((labels or {}).items()))
        total = self._totals.get(key, 0)
        if total == 0:
            return 0.0

        target = total * percentile / 100

        prev_bucket = 0.0
        prev_count = 0

        for bucket in sorted(self.buckets):
            count = self._counts[key].get(bucket, 0)
            if count >= target:
                # Linear interpolation
                if count == prev_count:
                    return bucket
                ratio = (target - prev_count) / (count - prev_count)
                return prev_bucket + ratio * (bucket - prev_bucket)
            prev_bucket = bucket
            prev_count = count

        return self.buckets[-1]

    def collect(self) -> list[MetricValue]:
        """Collect all values."""
        results = []
        for key, counts in self._counts.items():
            labels = dict(key)
            for bucket, count in counts.items():
                results.append(
                    MetricValue(
                        name=f"{self.name}_bucket",
                        value=count,
                        labels={**labels, "le": str(bucket)},
                        metric_type=MetricType.HISTOGRAM,
                    )
                )
            results.append(
                MetricValue(
                    name=f"{self.name}_sum",
                    value=self._sums.get(key, 0),
                    labels=labels,
                    metric_type=MetricType.HISTOGRAM,
                )
            )
            results.append(
                MetricValue(
                    name=f"{self.name}_count",
                    value=self._totals.get(key, 0),
                    labels=labels,
                    metric_type=MetricType.HISTOGRAM,
                )
            )
        return results


class LLMMetricsCollector:
    """Collector for LLM-specific metrics.

    Tracks:
    - Request counts by model/provider
    - Token usage
    - Latency distribution
    - Costs
    - Error rates

    Usage:
        collector = LLMMetricsCollector()

        # Record request
        collector.record_request(
            provider="anthropic",
            model="claude-opus-4-5",
            input_tokens=1000,
            output_tokens=500,
            latency_seconds=2.5,
            cost_usd=0.05,
        )

        # Get metrics
        metrics = collector.get_metrics()
    """

    def __init__(self) -> None:
        # Counters
        self.requests_total = Counter(
            "llm_requests_total",
            "Total number of LLM requests",
        )
        self.tokens_input_total = Counter(
            "llm_tokens_input_total",
            "Total input tokens",
        )
        self.tokens_output_total = Counter(
            "llm_tokens_output_total",
            "Total output tokens",
        )
        self.errors_total = Counter(
            "llm_errors_total",
            "Total LLM errors",
        )
        self.cost_usd_total = Counter(
            "llm_cost_usd_total",
            "Total cost in USD",
        )

        # Gauges
        self.active_requests = Gauge(
            "llm_active_requests",
            "Currently active requests",
        )

        # Histograms
        self.request_latency = Histogram(
            "llm_request_latency_seconds",
            "Request latency in seconds",
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
        )
        self.tokens_per_request = Histogram(
            "llm_tokens_per_request",
            "Tokens per request",
            buckets=(100, 500, 1000, 2000, 5000, 10000, 50000),
        )

        # Time-based aggregates
        self._hourly_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._last_reset = datetime.now(UTC)

    def record_request(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float,
        cost_usd: float = 0.0,
        task_type: str = "general",
        success: bool = True,
    ) -> None:
        """Record a completed LLM request."""
        labels = {
            "provider": provider,
            "model": model,
            "task_type": task_type,
        }

        # Update counters
        self.requests_total.inc(labels=labels)
        self.tokens_input_total.inc(input_tokens, labels=labels)
        self.tokens_output_total.inc(output_tokens, labels=labels)
        self.cost_usd_total.inc(cost_usd, labels=labels)

        if not success:
            self.errors_total.inc(labels=labels)

        # Update histograms
        self.request_latency.observe(latency_seconds, labels=labels)
        self.tokens_per_request.observe(
            input_tokens + output_tokens,
            labels=labels,
        )

        # Update hourly stats
        hour_key = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key]["requests"] += 1
        self._hourly_stats[hour_key]["tokens"] += input_tokens + output_tokens
        self._hourly_stats[hour_key]["cost"] += cost_usd

        logger.debug(
            "llm_metrics.request_recorded",
            provider=provider,
            model=model,
            tokens=input_tokens + output_tokens,
            latency=latency_seconds,
        )

    def record_error(
        self,
        provider: str,
        model: str,
        error_type: str,
        task_type: str = "general",
    ) -> None:
        """Record an LLM error."""
        labels = {
            "provider": provider,
            "model": model,
            "task_type": task_type,
            "error_type": error_type,
        }
        self.errors_total.inc(labels=labels)

    def start_request(self, provider: str, model: str) -> None:
        """Mark request start."""
        self.active_requests.inc(labels={"provider": provider, "model": model})

    def end_request(self, provider: str, model: str) -> None:
        """Mark request end."""
        self.active_requests.dec(labels={"provider": provider, "model": model})

    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics as dictionary."""
        metrics = {
            "requests_total": {},
            "tokens_total": {},
            "errors_total": {},
            "cost_total": {},
            "latency_p50": {},
            "latency_p95": {},
            "latency_p99": {},
            "hourly_stats": dict(self._hourly_stats),
        }

        # Aggregate by provider
        for metric in self.requests_total.collect():
            key = metric.labels.get("provider", "unknown")
            metrics["requests_total"][key] = metrics["requests_total"].get(key, 0) + metric.value

        for metric in self.tokens_input_total.collect():
            key = metric.labels.get("provider", "unknown")
            metrics["tokens_total"][key] = metrics["tokens_total"].get(key, 0) + metric.value

        for metric in self.cost_usd_total.collect():
            key = metric.labels.get("provider", "unknown")
            metrics["cost_total"][key] = metrics["cost_total"].get(key, 0) + metric.value

        # Latency percentiles
        for provider in ["anthropic", "openai", "google"]:
            labels = {"provider": provider}
            metrics["latency_p50"][provider] = self.request_latency.get_percentile(50, labels)
            metrics["latency_p95"][provider] = self.request_latency.get_percentile(95, labels)
            metrics["latency_p99"][provider] = self.request_latency.get_percentile(99, labels)

        return metrics

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        for collector in [
            self.requests_total,
            self.tokens_input_total,
            self.tokens_output_total,
            self.errors_total,
            self.cost_usd_total,
            self.active_requests,
            self.request_latency,
            self.tokens_per_request,
        ]:
            for metric in collector.collect():
                label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                if label_str:
                    lines.append(f"{metric.name}{{{label_str}}} {metric.value}")
                else:
                    lines.append(f"{metric.name} {metric.value}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        self.requests_total = Counter("llm_requests_total", "")
        self.tokens_input_total = Counter("llm_tokens_input_total", "")
        self.tokens_output_total = Counter("llm_tokens_output_total", "")
        self.errors_total = Counter("llm_errors_total", "")
        self.cost_usd_total = Counter("llm_cost_usd_total", "")
        self.active_requests = Gauge("llm_active_requests", "")
        self.request_latency = Histogram("llm_request_latency_seconds", "")
        self.tokens_per_request = Histogram("llm_tokens_per_request", "")
        self._hourly_stats.clear()


class AgentMetricsCollector:
    """Collector for agent-specific metrics."""

    def __init__(self) -> None:
        self.tasks_total = Counter("agent_tasks_total", "Total agent tasks")
        self.task_duration = Histogram(
            "agent_task_duration_seconds",
            "Task duration",
            buckets=(1, 5, 10, 30, 60, 120, 300, 600),
        )
        self.active_agents = Gauge("agent_active_count", "Active agents")
        self.errors_total = Counter("agent_errors_total", "Agent errors")

    def record_task(
        self,
        agent_name: str,
        task_type: str,
        duration_seconds: float,
        success: bool = True,
    ) -> None:
        """Record completed agent task."""
        labels = {"agent": agent_name, "task_type": task_type}
        self.tasks_total.inc(labels=labels)
        self.task_duration.observe(duration_seconds, labels=labels)

        if not success:
            self.errors_total.inc(labels=labels)


# Global collectors
_llm_collector: LLMMetricsCollector | None = None
_agent_collector: AgentMetricsCollector | None = None


def get_llm_metrics() -> LLMMetricsCollector:
    """Get global LLM metrics collector."""
    global _llm_collector
    if _llm_collector is None:
        _llm_collector = LLMMetricsCollector()
    return _llm_collector


def get_agent_metrics() -> AgentMetricsCollector:
    """Get global agent metrics collector."""
    global _agent_collector
    if _agent_collector is None:
        _agent_collector = AgentMetricsCollector()
    return _agent_collector
