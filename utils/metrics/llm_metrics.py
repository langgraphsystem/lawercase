"""LLM Metrics Collection System.

Provides comprehensive metrics for LLM operations:
- Token usage tracking (input/output/total)
- Latency metrics (TTFT, TPS, total latency)
- Cost tracking per model/provider
- Error rate tracking
- Cache hit/miss rates
- Request/response logging
- Prometheus-compatible metric export
- Grafana dashboard JSON generation
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
import time
from typing import Any, TypeVar
import uuid

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class MetricType(str, Enum):
    """Types of metrics for Prometheus."""

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

    def to_prometheus(self) -> str:
        """Convert to Prometheus exposition format."""
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(self.labels.items()))
        if label_str:
            return f"{self.name}{{{label_str}}} {self.value}"
        return f"{self.name} {self.value}"


@dataclass
class LLMRequestLog:
    """Detailed log of an LLM request."""

    request_id: str
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_seconds: float
    ttft_seconds: float | None  # Time to first token
    tps: float | None  # Tokens per second
    cost_usd: float
    success: bool
    error_type: str | None = None
    error_message: str | None = None
    cache_hit: bool = False
    prompt_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": self.latency_seconds,
            "ttft_seconds": self.ttft_seconds,
            "tps": self.tps,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "cache_hit": self.cache_hit,
            "prompt_hash": self.prompt_hash,
            "metadata": self.metadata,
        }


class Counter:
    """Monotonically increasing counter metric."""

    def __init__(self, name: str, description: str = "", labels: list[str] | None = None) -> None:
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment counter asynchronously."""
        async with self._lock:
            key = tuple(sorted((labels or {}).items()))
            self._values[key] += value

    def inc_sync(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment counter synchronously."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] += value

    def get(self, labels: dict[str, str] | None = None) -> float:
        """Get current value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0.0)

    def collect(self) -> list[MetricValue]:
        """Collect all metric values."""
        return [
            MetricValue(
                name=self.name,
                value=value,
                labels=dict(key),
                metric_type=MetricType.COUNTER,
            )
            for key, value in self._values.items()
        ]

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        for metric in self.collect():
            lines.append(metric.to_prometheus())
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all values."""
        self._values.clear()


class Gauge:
    """Metric that can go up and down."""

    def __init__(self, name: str, description: str = "", labels: list[str] | None = None) -> None:
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge value asynchronously."""
        async with self._lock:
            key = tuple(sorted((labels or {}).items()))
            self._values[key] = value

    def set_sync(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge value synchronously."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] = value

    async def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment gauge asynchronously."""
        async with self._lock:
            key = tuple(sorted((labels or {}).items()))
            self._values[key] += value

    def inc_sync(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment gauge synchronously."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] += value

    async def dec(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Decrement gauge asynchronously."""
        async with self._lock:
            key = tuple(sorted((labels or {}).items()))
            self._values[key] -= value

    def dec_sync(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Decrement gauge synchronously."""
        key = tuple(sorted((labels or {}).items()))
        self._values[key] -= value

    def get(self, labels: dict[str, str] | None = None) -> float:
        """Get current value."""
        key = tuple(sorted((labels or {}).items()))
        return self._values.get(key, 0.0)

    def collect(self) -> list[MetricValue]:
        """Collect all metric values."""
        return [
            MetricValue(
                name=self.name,
                value=value,
                labels=dict(key),
                metric_type=MetricType.GAUGE,
            )
            for key, value in self._values.items()
        ]

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        for metric in self.collect():
            lines.append(metric.to_prometheus())
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all values."""
        self._values.clear()


class Histogram:
    """Histogram for measuring distributions."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: tuple[float, ...] | None = None,
        labels: list[str] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self.label_names = labels or []

        self._counts: dict[tuple[tuple[str, str], ...], dict[float, int]] = defaultdict(
            lambda: dict.fromkeys(self.buckets, 0)
        )
        self._sums: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._totals: dict[tuple[tuple[str, str], ...], int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Record an observation asynchronously."""
        async with self._lock:
            self._observe_internal(value, labels)

    def observe_sync(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Record an observation synchronously."""
        self._observe_internal(value, labels)

    def _observe_internal(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Internal observation logic."""
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

        for bucket in sorted(b for b in self.buckets if b != float("inf")):
            count = self._counts[key].get(bucket, 0)
            if count >= target:
                if count == prev_count:
                    return bucket
                ratio = (target - prev_count) / (count - prev_count)
                return prev_bucket + ratio * (bucket - prev_bucket)
            prev_bucket = bucket
            prev_count = count

        finite_buckets = [b for b in self.buckets if b != float("inf")]
        return finite_buckets[-1] if finite_buckets else 0.0

    def get_count(self, labels: dict[str, str] | None = None) -> int:
        """Get total observation count."""
        key = tuple(sorted((labels or {}).items()))
        return self._totals.get(key, 0)

    def get_sum(self, labels: dict[str, str] | None = None) -> float:
        """Get sum of all observations."""
        key = tuple(sorted((labels or {}).items()))
        return self._sums.get(key, 0.0)

    def collect(self) -> list[MetricValue]:
        """Collect all metric values."""
        results = []
        for key, counts in self._counts.items():
            labels = dict(key)
            for bucket, count in sorted(counts.items()):
                bucket_label = "+Inf" if bucket == float("inf") else str(bucket)
                results.append(
                    MetricValue(
                        name=f"{self.name}_bucket",
                        value=count,
                        labels={**labels, "le": bucket_label},
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

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        for metric in self.collect():
            lines.append(metric.to_prometheus())
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all values."""
        self._counts.clear()
        self._sums.clear()
        self._totals.clear()


@dataclass
class RequestContext:
    """Context for tracking an in-flight LLM request."""

    request_id: str
    start_time: float
    provider: str
    model: str
    first_token_time: float | None = None
    prompt_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMMetricsCollector:
    """Collector for LLM-specific metrics.

    Tracks:
    - Request counts by model/provider (llm_requests_total)
    - Token usage (llm_tokens_used)
    - Latency distribution (llm_request_duration_seconds)
    - Cost tracking (llm_cost_dollars)
    - Error rates (llm_errors_total)
    - Cache hit/miss (llm_cache_hits_total)

    Features:
    - TTFT (Time to First Token) tracking
    - TPS (Tokens Per Second) calculation
    - Request/response logging
    - Prometheus-compatible export
    - Grafana dashboard generation

    Usage:
        collector = LLMMetricsCollector()

        # Track a request
        async with collector.track_request("anthropic", "claude-opus-4-5") as ctx:
            ctx.record_first_token()
            # ... make LLM call ...

        # Record completion
        await collector.record_completion(
            ctx,
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
        )

        # Export metrics
        prometheus_text = collector.export_prometheus()
        grafana_json = collector.generate_grafana_dashboard()
    """

    # Cost per 1K tokens for different models (USD)
    MODEL_COSTS: dict[str, dict[str, float]] = {
        "anthropic": {
            "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
            "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        },
        "openai": {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        },
        "google": {
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
            "gemini-pro": {"input": 0.0005, "output": 0.0015},
        },
    }

    def __init__(
        self,
        max_log_entries: int = 10000,
        enable_logging: bool = True,
    ) -> None:
        self.max_log_entries = max_log_entries
        self.enable_logging = enable_logging

        # Core metrics (Prometheus-compatible)
        self.requests_total = Counter(
            "llm_requests_total",
            "Total number of LLM requests",
            labels=["provider", "model", "status"],
        )
        self.tokens_used = Counter(
            "llm_tokens_used",
            "Total tokens used",
            labels=["provider", "model", "type"],  # type: input/output
        )
        self.request_duration = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration in seconds",
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")),
            labels=["provider", "model"],
        )
        self.cost_dollars = Counter(
            "llm_cost_dollars",
            "Total cost in USD",
            labels=["provider", "model"],
        )
        self.errors_total = Counter(
            "llm_errors_total",
            "Total LLM errors",
            labels=["provider", "model", "error_type"],
        )
        self.cache_hits_total = Counter(
            "llm_cache_hits_total",
            "Total cache hits",
            labels=["provider", "model"],
        )
        self.cache_misses_total = Counter(
            "llm_cache_misses_total",
            "Total cache misses",
            labels=["provider", "model"],
        )

        # Additional latency metrics
        self.ttft_seconds = Histogram(
            "llm_ttft_seconds",
            "Time to first token in seconds",
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
            labels=["provider", "model"],
        )
        self.tps = Histogram(
            "llm_tokens_per_second",
            "Output tokens per second",
            buckets=(1, 5, 10, 25, 50, 100, 200, 500, float("inf")),
            labels=["provider", "model"],
        )

        # Gauges for current state
        self.active_requests = Gauge(
            "llm_active_requests",
            "Currently active LLM requests",
            labels=["provider", "model"],
        )

        # Request logging
        self._request_logs: list[LLMRequestLog] = []
        self._log_lock = asyncio.Lock()

        # Active request tracking
        self._active_contexts: dict[str, RequestContext] = {}
        self._context_lock = asyncio.Lock()

        # Aggregated statistics
        self._hourly_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._daily_stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    @asynccontextmanager
    async def track_request(
        self,
        provider: str,
        model: str,
        prompt_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Context manager for tracking an LLM request.

        Usage:
            async with collector.track_request("anthropic", "claude-opus-4-5") as ctx:
                # Call record_first_token() when first token arrives
                ctx.first_token_time = time.perf_counter()
                # ... make LLM call ...
            # Context auto-records end time
        """
        request_id = str(uuid.uuid4())
        ctx = RequestContext(
            request_id=request_id,
            start_time=time.perf_counter(),
            provider=provider,
            model=model,
            prompt_hash=prompt_hash,
            metadata=metadata or {},
        )

        async with self._context_lock:
            self._active_contexts[request_id] = ctx

        await self.active_requests.inc(labels={"provider": provider, "model": model})

        try:
            yield ctx
        finally:
            await self.active_requests.dec(labels={"provider": provider, "model": model})
            async with self._context_lock:
                self._active_contexts.pop(request_id, None)

    async def record_completion(
        self,
        ctx: RequestContext,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | None = None,
        success: bool = True,
        error_type: str | None = None,
        error_message: str | None = None,
        cache_hit: bool = False,
    ) -> LLMRequestLog:
        """Record completion of an LLM request."""
        end_time = time.perf_counter()
        latency = end_time - ctx.start_time
        total_tokens = input_tokens + output_tokens

        # Calculate TTFT and TPS
        ttft = None
        tps = None
        if ctx.first_token_time is not None:
            ttft = ctx.first_token_time - ctx.start_time
            generation_time = end_time - ctx.first_token_time
            if generation_time > 0 and output_tokens > 0:
                tps = output_tokens / generation_time

        # Calculate cost if not provided
        if cost_usd is None:
            cost_usd = self._calculate_cost(ctx.provider, ctx.model, input_tokens, output_tokens)

        labels = {"provider": ctx.provider, "model": ctx.model}
        status = "success" if success else "error"

        # Update counters
        await self.requests_total.inc(labels={**labels, "status": status})
        await self.tokens_used.inc(input_tokens, labels={**labels, "type": "input"})
        await self.tokens_used.inc(output_tokens, labels={**labels, "type": "output"})
        await self.cost_dollars.inc(cost_usd, labels=labels)

        # Update histograms
        await self.request_duration.observe(latency, labels=labels)
        if ttft is not None:
            await self.ttft_seconds.observe(ttft, labels=labels)
        if tps is not None:
            await self.tps.observe(tps, labels=labels)

        # Update cache metrics
        if cache_hit:
            await self.cache_hits_total.inc(labels=labels)
        else:
            await self.cache_misses_total.inc(labels=labels)

        # Update error metrics
        if not success and error_type:
            await self.errors_total.inc(labels={**labels, "error_type": error_type})

        # Update time-based aggregates
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%d-%H")
        day_key = now.strftime("%Y-%m-%d")

        self._hourly_stats[hour_key]["requests"] += 1
        self._hourly_stats[hour_key]["tokens"] += total_tokens
        self._hourly_stats[hour_key]["cost"] += cost_usd
        self._hourly_stats[hour_key]["errors"] += 0 if success else 1

        self._daily_stats[day_key]["requests"] += 1
        self._daily_stats[day_key]["tokens"] += total_tokens
        self._daily_stats[day_key]["cost"] += cost_usd
        self._daily_stats[day_key]["errors"] += 0 if success else 1

        # Create log entry
        log_entry = LLMRequestLog(
            request_id=ctx.request_id,
            timestamp=now,
            provider=ctx.provider,
            model=ctx.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
            ttft_seconds=ttft,
            tps=tps,
            cost_usd=cost_usd,
            success=success,
            error_type=error_type,
            error_message=error_message,
            cache_hit=cache_hit,
            prompt_hash=ctx.prompt_hash,
            metadata=ctx.metadata,
        )

        if self.enable_logging:
            await self._add_log_entry(log_entry)

        logger.debug(
            "llm_metrics.request_completed",
            request_id=ctx.request_id,
            provider=ctx.provider,
            model=ctx.model,
            tokens=total_tokens,
            latency=latency,
            ttft=ttft,
            tps=tps,
            cost=cost_usd,
            success=success,
        )

        return log_entry

    async def record_error(
        self,
        provider: str,
        model: str,
        error_type: str,
        error_message: str | None = None,
    ) -> None:
        """Record an LLM error without a request context."""
        labels = {"provider": provider, "model": model, "error_type": error_type}
        await self.errors_total.inc(labels=labels)
        await self.requests_total.inc(
            labels={"provider": provider, "model": model, "status": "error"}
        )

        logger.warning(
            "llm_metrics.error_recorded",
            provider=provider,
            model=model,
            error_type=error_type,
            error_message=error_message,
        )

    async def record_cache_hit(self, provider: str, model: str) -> None:
        """Record a cache hit."""
        await self.cache_hits_total.inc(labels={"provider": provider, "model": model})

    async def record_cache_miss(self, provider: str, model: str) -> None:
        """Record a cache miss."""
        await self.cache_misses_total.inc(labels={"provider": provider, "model": model})

    def _calculate_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost based on model pricing."""
        provider_costs = self.MODEL_COSTS.get(provider, {})

        # Try exact match first, then partial match
        model_costs = provider_costs.get(model)
        if model_costs is None:
            for key, costs in provider_costs.items():
                if key in model or model in key:
                    model_costs = costs
                    break

        if model_costs is None:
            # Default pricing
            model_costs = {"input": 0.001, "output": 0.002}

        input_cost = (input_tokens / 1000) * model_costs.get("input", 0.001)
        output_cost = (output_tokens / 1000) * model_costs.get("output", 0.002)
        return input_cost + output_cost

    async def _add_log_entry(self, entry: LLMRequestLog) -> None:
        """Add a log entry, maintaining max size."""
        async with self._log_lock:
            self._request_logs.append(entry)
            if len(self._request_logs) > self.max_log_entries:
                # Remove oldest entries
                self._request_logs = self._request_logs[-self.max_log_entries :]

    def get_request_logs(
        self,
        limit: int = 100,
        provider: str | None = None,
        model: str | None = None,
        since: datetime | None = None,
    ) -> list[LLMRequestLog]:
        """Get request logs with optional filtering."""
        logs = self._request_logs

        if provider:
            logs = [log_entry for log_entry in logs if log_entry.provider == provider]
        if model:
            logs = [log_entry for log_entry in logs if log_entry.model == model]
        if since:
            logs = [log_entry for log_entry in logs if log_entry.timestamp >= since]

        return logs[-limit:]

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        summary = {
            "requests": {},
            "tokens": {"input": {}, "output": {}},
            "costs": {},
            "errors": {},
            "latency": {
                "p50": {},
                "p95": {},
                "p99": {},
            },
            "ttft": {
                "p50": {},
                "p95": {},
            },
            "tps": {
                "p50": {},
                "p95": {},
            },
            "cache": {
                "hits": {},
                "misses": {},
                "hit_rate": {},
            },
            "hourly_stats": dict(self._hourly_stats),
            "daily_stats": dict(self._daily_stats),
        }

        # Aggregate by provider
        for metric in self.requests_total.collect():
            provider = metric.labels.get("provider", "unknown")
            if provider not in summary["requests"]:
                summary["requests"][provider] = 0
            summary["requests"][provider] += metric.value

        for metric in self.tokens_used.collect():
            provider = metric.labels.get("provider", "unknown")
            token_type = metric.labels.get("type", "input")
            if provider not in summary["tokens"][token_type]:
                summary["tokens"][token_type][provider] = 0
            summary["tokens"][token_type][provider] += metric.value

        for metric in self.cost_dollars.collect():
            provider = metric.labels.get("provider", "unknown")
            if provider not in summary["costs"]:
                summary["costs"][provider] = 0
            summary["costs"][provider] += metric.value

        for metric in self.errors_total.collect():
            provider = metric.labels.get("provider", "unknown")
            error_type = metric.labels.get("error_type", "unknown")
            key = f"{provider}:{error_type}"
            summary["errors"][key] = summary["errors"].get(key, 0) + metric.value

        # Calculate cache hit rates
        for metric in self.cache_hits_total.collect():
            provider = metric.labels.get("provider", "unknown")
            summary["cache"]["hits"][provider] = metric.value

        for metric in self.cache_misses_total.collect():
            provider = metric.labels.get("provider", "unknown")
            summary["cache"]["misses"][provider] = metric.value

        # Calculate hit rates
        for provider in set(summary["cache"]["hits"].keys()) | set(
            summary["cache"]["misses"].keys()
        ):
            hits = summary["cache"]["hits"].get(provider, 0)
            misses = summary["cache"]["misses"].get(provider, 0)
            total = hits + misses
            summary["cache"]["hit_rate"][provider] = hits / total if total > 0 else 0.0

        # Latency percentiles by provider
        providers = set()
        for metric in self.request_duration.collect():
            provider = metric.labels.get("provider")
            if provider:
                providers.add(provider)

        for provider in providers:
            labels = {"provider": provider}
            summary["latency"]["p50"][provider] = self.request_duration.get_percentile(50, labels)
            summary["latency"]["p95"][provider] = self.request_duration.get_percentile(95, labels)
            summary["latency"]["p99"][provider] = self.request_duration.get_percentile(99, labels)

            summary["ttft"]["p50"][provider] = self.ttft_seconds.get_percentile(50, labels)
            summary["ttft"]["p95"][provider] = self.ttft_seconds.get_percentile(95, labels)

            summary["tps"]["p50"][provider] = self.tps.get_percentile(50, labels)
            summary["tps"]["p95"][provider] = self.tps.get_percentile(95, labels)

        return summary

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus exposition format."""
        sections = [
            self.requests_total.to_prometheus(),
            self.tokens_used.to_prometheus(),
            self.request_duration.to_prometheus(),
            self.cost_dollars.to_prometheus(),
            self.errors_total.to_prometheus(),
            self.cache_hits_total.to_prometheus(),
            self.cache_misses_total.to_prometheus(),
            self.ttft_seconds.to_prometheus(),
            self.tps.to_prometheus(),
            self.active_requests.to_prometheus(),
        ]
        return "\n\n".join(sections)

    def generate_grafana_dashboard(
        self,
        title: str = "LLM Metrics Dashboard",
        uid: str | None = None,
    ) -> dict[str, Any]:
        """Generate a Grafana dashboard JSON.

        Returns a complete Grafana dashboard configuration that can be
        imported directly into Grafana.
        """
        uid = uid or f"llm-metrics-{uuid.uuid4().hex[:8]}"

        def panel(
            title: str,
            panel_type: str,
            expr: str | list[str],
            grid_pos: dict[str, int],
            unit: str = "",
            legend: str = "{{provider}} - {{model}}",
        ) -> dict[str, Any]:
            """Helper to create a panel configuration."""
            if isinstance(expr, str):
                targets = [{"expr": expr, "legendFormat": legend, "refId": "A"}]
            else:
                targets = [
                    {"expr": e, "legendFormat": legend, "refId": chr(65 + i)}
                    for i, e in enumerate(expr)
                ]

            panel_config = {
                "title": title,
                "type": panel_type,
                "gridPos": grid_pos,
                "targets": targets,
                "fieldConfig": {
                    "defaults": {
                        "unit": unit,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 80},
                                {"color": "red", "value": 90},
                            ],
                        },
                    },
                },
            }

            if panel_type == "timeseries":
                panel_config["options"] = {
                    "legend": {"displayMode": "table", "placement": "bottom"},
                    "tooltip": {"mode": "multi"},
                }
            elif panel_type == "stat":
                panel_config["options"] = {
                    "colorMode": "value",
                    "graphMode": "area",
                    "justifyMode": "auto",
                    "textMode": "auto",
                }

            return panel_config

        dashboard = {
            "uid": uid,
            "title": title,
            "tags": ["llm", "metrics", "ai"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "30s",
            "time": {"from": "now-6h", "to": "now"},
            "templating": {
                "list": [
                    {
                        "name": "provider",
                        "type": "query",
                        "query": "label_values(llm_requests_total, provider)",
                        "multi": True,
                        "includeAll": True,
                        "current": {"text": "All", "value": "$__all"},
                    },
                    {
                        "name": "model",
                        "type": "query",
                        "query": 'label_values(llm_requests_total{provider=~"$provider"}, model)',
                        "multi": True,
                        "includeAll": True,
                        "current": {"text": "All", "value": "$__all"},
                    },
                ],
            },
            "panels": [
                # Row 1: Overview stats
                panel(
                    "Total Requests",
                    "stat",
                    'sum(llm_requests_total{provider=~"$provider", model=~"$model"})',
                    {"x": 0, "y": 0, "w": 4, "h": 4},
                    legend="Total",
                ),
                panel(
                    "Total Tokens",
                    "stat",
                    'sum(llm_tokens_used{provider=~"$provider", model=~"$model"})',
                    {"x": 4, "y": 0, "w": 4, "h": 4},
                    legend="Total",
                ),
                panel(
                    "Total Cost",
                    "stat",
                    'sum(llm_cost_dollars{provider=~"$provider", model=~"$model"})',
                    {"x": 8, "y": 0, "w": 4, "h": 4},
                    unit="currencyUSD",
                    legend="Total",
                ),
                panel(
                    "Error Rate",
                    "stat",
                    'sum(rate(llm_errors_total{provider=~"$provider", model=~"$model"}[5m])) / sum(rate(llm_requests_total{provider=~"$provider", model=~"$model"}[5m])) * 100',
                    {"x": 12, "y": 0, "w": 4, "h": 4},
                    unit="percent",
                    legend="Error %",
                ),
                panel(
                    "Cache Hit Rate",
                    "stat",
                    'sum(llm_cache_hits_total{provider=~"$provider", model=~"$model"}) / (sum(llm_cache_hits_total{provider=~"$provider", model=~"$model"}) + sum(llm_cache_misses_total{provider=~"$provider", model=~"$model"})) * 100',
                    {"x": 16, "y": 0, "w": 4, "h": 4},
                    unit="percent",
                    legend="Hit %",
                ),
                panel(
                    "Active Requests",
                    "stat",
                    'sum(llm_active_requests{provider=~"$provider", model=~"$model"})',
                    {"x": 20, "y": 0, "w": 4, "h": 4},
                    legend="Active",
                ),
                # Row 2: Request rate and latency
                panel(
                    "Request Rate",
                    "timeseries",
                    'sum(rate(llm_requests_total{provider=~"$provider", model=~"$model"}[5m])) by (provider, model)',
                    {"x": 0, "y": 4, "w": 12, "h": 8},
                    unit="reqps",
                ),
                panel(
                    "Request Latency (p95)",
                    "timeseries",
                    'histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket{provider=~"$provider", model=~"$model"}[5m])) by (le, provider, model))',
                    {"x": 12, "y": 4, "w": 12, "h": 8},
                    unit="s",
                ),
                # Row 3: Token usage
                panel(
                    "Token Usage Rate",
                    "timeseries",
                    [
                        'sum(rate(llm_tokens_used{provider=~"$provider", model=~"$model", type="input"}[5m])) by (provider, model)',
                        'sum(rate(llm_tokens_used{provider=~"$provider", model=~"$model", type="output"}[5m])) by (provider, model)',
                    ],
                    {"x": 0, "y": 12, "w": 12, "h": 8},
                    unit="short",
                ),
                panel(
                    "Cost Rate",
                    "timeseries",
                    'sum(rate(llm_cost_dollars{provider=~"$provider", model=~"$model"}[5m])) by (provider, model) * 3600',
                    {"x": 12, "y": 12, "w": 12, "h": 8},
                    unit="currencyUSD",
                    legend="$/hour",
                ),
                # Row 4: TTFT and TPS
                panel(
                    "Time to First Token (p95)",
                    "timeseries",
                    'histogram_quantile(0.95, sum(rate(llm_ttft_seconds_bucket{provider=~"$provider", model=~"$model"}[5m])) by (le, provider, model))',
                    {"x": 0, "y": 20, "w": 12, "h": 8},
                    unit="s",
                ),
                panel(
                    "Tokens Per Second (p50)",
                    "timeseries",
                    'histogram_quantile(0.50, sum(rate(llm_tokens_per_second_bucket{provider=~"$provider", model=~"$model"}[5m])) by (le, provider, model))',
                    {"x": 12, "y": 20, "w": 12, "h": 8},
                    unit="short",
                ),
                # Row 5: Errors
                panel(
                    "Error Rate by Type",
                    "timeseries",
                    'sum(rate(llm_errors_total{provider=~"$provider", model=~"$model"}[5m])) by (provider, model, error_type)',
                    {"x": 0, "y": 28, "w": 12, "h": 8},
                    unit="short",
                    legend="{{provider}}/{{model}} - {{error_type}}",
                ),
                panel(
                    "Latency Distribution",
                    "heatmap",
                    'sum(rate(llm_request_duration_seconds_bucket{provider=~"$provider", model=~"$model"}[5m])) by (le)',
                    {"x": 12, "y": 28, "w": 12, "h": 8},
                ),
            ],
        }

        return dashboard

    def export_grafana_dashboard_json(
        self,
        title: str = "LLM Metrics Dashboard",
        uid: str | None = None,
        indent: int = 2,
    ) -> str:
        """Export Grafana dashboard as JSON string."""
        dashboard = self.generate_grafana_dashboard(title, uid)
        return json.dumps(dashboard, indent=indent)

    async def reset(self) -> None:
        """Reset all metrics."""
        self.requests_total.reset()
        self.tokens_used.reset()
        self.request_duration.reset()
        self.cost_dollars.reset()
        self.errors_total.reset()
        self.cache_hits_total.reset()
        self.cache_misses_total.reset()
        self.ttft_seconds.reset()
        self.tps.reset()
        self.active_requests.reset()
        self._hourly_stats.clear()
        self._daily_stats.clear()
        async with self._log_lock:
            self._request_logs.clear()


# Global instance
_collector: LLMMetricsCollector | None = None


def get_llm_metrics_collector() -> LLMMetricsCollector:
    """Get the global LLM metrics collector instance."""
    global _collector
    if _collector is None:
        _collector = LLMMetricsCollector()
    return _collector


def set_llm_metrics_collector(collector: LLMMetricsCollector) -> None:
    """Set the global LLM metrics collector instance."""
    global _collector
    _collector = collector


# Convenience decorator for tracking LLM calls
def track_llm_call(
    provider: str,
    model: str,
    extract_tokens: Callable[[Any], tuple[int, int]] | None = None,
):
    """Decorator for tracking LLM function calls.

    Usage:
        @track_llm_call("anthropic", "claude-opus-4-5")
        async def call_claude(prompt: str) -> str:
            # ... implementation
            return response

        # Or with custom token extraction:
        @track_llm_call(
            "openai",
            "gpt-4",
            extract_tokens=lambda r: (r.usage.prompt_tokens, r.usage.completion_tokens)
        )
        async def call_gpt4(prompt: str):
            return await openai.chat.completions.create(...)
    """

    def decorator(func: F) -> F:
        import functools

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = get_llm_metrics_collector()

            async with collector.track_request(provider, model) as ctx:
                try:
                    result = await func(*args, **kwargs)

                    # Extract tokens if possible
                    input_tokens = 0
                    output_tokens = 0

                    if extract_tokens:
                        try:
                            input_tokens, output_tokens = extract_tokens(result)
                        except Exception:
                            pass

                    await collector.record_completion(
                        ctx,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        success=True,
                    )

                    return result

                except Exception as e:
                    await collector.record_completion(
                        ctx,
                        input_tokens=0,
                        output_tokens=0,
                        success=False,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                    raise

        return wrapper  # type: ignore

    return decorator
