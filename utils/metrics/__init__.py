"""LLM Metrics Package.

Provides comprehensive metrics collection for LLM operations:
- LLMMetricsCollector: Main metrics collector with Prometheus/Grafana support
- Counter, Gauge, Histogram: Prometheus-compatible metric types
- Request/response logging
- TTFT, TPS, and latency tracking
- Cost tracking per model/provider
- Self-correction analytics

Metrics exported:
- llm_requests_total (counter)
- llm_tokens_used (counter, labels: type=input/output)
- llm_request_duration_seconds (histogram)
- llm_cost_dollars (counter, labels: provider, model)
- llm_errors_total (counter, labels: error_type)
- llm_cache_hits_total (counter)
- llm_ttft_seconds (histogram)
- llm_tokens_per_second (histogram)
- correction_events_total (counter)
- correction_success_rate (gauge)

Usage:
    from utils.metrics import get_llm_metrics_collector, track_llm_call

    # Get collector
    collector = get_llm_metrics_collector()

    # Track a request manually
    async with collector.track_request("anthropic", "claude-opus-4-5") as ctx:
        ctx.first_token_time = time.perf_counter()  # Record TTFT
        response = await make_llm_call()

    await collector.record_completion(
        ctx,
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.05,
    )

    # Or use decorator
    @track_llm_call("anthropic", "claude-opus-4-5")
    async def my_llm_function():
        pass

    # Export metrics
    prometheus_text = collector.export_prometheus()
    grafana_json = collector.generate_grafana_dashboard()

    # Self-correction analytics
    from utils.metrics import get_self_correction_analytics
    analytics = get_self_correction_analytics()
"""

from __future__ import annotations

from .llm_metrics import (
    # Metric types
    Counter,
    Gauge,
    Histogram,
    # Main collector
    LLMMetricsCollector,
    # Data classes
    LLMRequestLog,
    MetricType,
    MetricValue,
    RequestContext,
    get_llm_metrics_collector,
    set_llm_metrics_collector,
    track_llm_call,
)
from .self_correction_analytics import (
    AnalyticsSummary,
    CorrectionEvent,
    CorrectionOutcome,
    CorrectionPattern,
    CorrectionTrigger,
    CorrectionType,
    LearningCurve,
    SelfCorrectionAnalytics,
    get_self_correction_analytics,
    set_self_correction_analytics,
)

__all__ = [
    "AnalyticsSummary",
    "CorrectionEvent",
    "CorrectionOutcome",
    "CorrectionPattern",
    "CorrectionTrigger",
    "CorrectionType",
    # Metric types
    "Counter",
    "Gauge",
    "Histogram",
    # Main collector
    "LLMMetricsCollector",
    # Data classes
    "LLMRequestLog",
    "LearningCurve",
    "MetricType",
    "MetricValue",
    "RequestContext",
    # Self-correction analytics
    "SelfCorrectionAnalytics",
    "get_llm_metrics_collector",
    "get_self_correction_analytics",
    "set_llm_metrics_collector",
    "set_self_correction_analytics",
    "track_llm_call",
]
