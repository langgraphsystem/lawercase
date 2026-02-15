"""Extended Metrics Package.

Provides comprehensive metrics collection:
- LLMMetricsCollector: LLM-specific metrics
- AgentMetricsCollector: Agent task metrics
- Counter, Gauge, Histogram: Metric types

Usage:
    from utils.metrics_ext import get_llm_metrics, get_agent_metrics

    llm_metrics = get_llm_metrics()
    llm_metrics.record_request(
        provider="anthropic",
        model="claude-opus-4-5",
        input_tokens=1000,
        output_tokens=500,
        latency_seconds=2.5,
    )
"""

from __future__ import annotations

from .llm_metrics import (
    AgentMetricsCollector,
    Counter,
    Gauge,
    Histogram,
    LLMMetricsCollector,
    MetricType,
    MetricValue,
    get_agent_metrics,
    get_llm_metrics,
)

__all__ = [
    "AgentMetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "LLMMetricsCollector",
    "MetricType",
    "MetricValue",
    "get_agent_metrics",
    "get_llm_metrics",
]
