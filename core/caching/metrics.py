"""Cache metrics and monitoring.

This module provides metrics collection and monitoring for cache performance.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .config import get_cache_config


@dataclass
class CacheMetrics:
    """Container for cache performance metrics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0

    # Latency tracking (milliseconds)
    hit_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    miss_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    set_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Size tracking
    total_bytes_cached: int = 0
    evictions: int = 0

    # Semantic cache specific
    semantic_hits: int = 0
    exact_hits: int = 0

    def hit_rate(self) -> float:
        """Calculate cache hit rate (0-1)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def semantic_hit_rate(self) -> float:
        """Calculate semantic hit rate among all hits."""
        return self.semantic_hits / self.hits if self.hits > 0 else 0.0

    def avg_hit_latency(self) -> float:
        """Average latency for cache hits (ms)."""
        if not self.hit_latencies:
            return 0.0
        return sum(self.hit_latencies) / len(self.hit_latencies)

    def avg_miss_latency(self) -> float:
        """Average latency for cache misses (ms)."""
        if not self.miss_latencies:
            return 0.0
        return sum(self.miss_latencies) / len(self.miss_latencies)

    def avg_set_latency(self) -> float:
        """Average latency for cache sets (ms)."""
        if not self.set_latencies:
            return 0.0
        return sum(self.set_latencies) / len(self.set_latencies)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": self.hit_rate(),
            "semantic_hits": self.semantic_hits,
            "exact_hits": self.exact_hits,
            "semantic_hit_rate": self.semantic_hit_rate(),
            "avg_hit_latency_ms": self.avg_hit_latency(),
            "avg_miss_latency_ms": self.avg_miss_latency(),
            "avg_set_latency_ms": self.avg_set_latency(),
            "total_bytes_cached": self.total_bytes_cached,
            "evictions": self.evictions,
        }


class CacheMonitor:
    """
    Monitor cache performance and health.

    Features:
    - Real-time metrics collection
    - Performance alerts
    - Health checks
    - Prometheus-compatible export

    Example:
        >>> monitor = CacheMonitor()
        >>> monitor.record_hit(latency_ms=5.2)
        >>> monitor.record_miss(latency_ms=150.0)
        >>> stats = monitor.get_stats()
        >>> print(stats["hit_rate"])
        0.5
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize cache monitor.

        Args:
            window_size: Number of recent operations to track for latency
        """
        self.metrics = CacheMetrics()
        self.config = get_cache_config()
        self.window_size = window_size

        # Time-windowed metrics
        self._start_time = time.time()
        self._last_reset = time.time()

    def record_hit(
        self,
        latency_ms: float,
        is_semantic: bool = False,
    ) -> None:
        """
        Record a cache hit.

        Args:
            latency_ms: Latency in milliseconds
            is_semantic: Whether hit was from semantic matching
        """
        self.metrics.hits += 1
        self.metrics.hit_latencies.append(latency_ms)

        if is_semantic:
            self.metrics.semantic_hits += 1
        else:
            self.metrics.exact_hits += 1

    def record_miss(self, latency_ms: float) -> None:
        """
        Record a cache miss.

        Args:
            latency_ms: Latency in milliseconds
        """
        self.metrics.misses += 1
        self.metrics.miss_latencies.append(latency_ms)

    def record_set(
        self,
        latency_ms: float,
        size_bytes: int | None = None,
    ) -> None:
        """
        Record a cache set operation.

        Args:
            latency_ms: Latency in milliseconds
            size_bytes: Size of cached value in bytes
        """
        self.metrics.sets += 1
        self.metrics.set_latencies.append(latency_ms)

        if size_bytes:
            self.metrics.total_bytes_cached += size_bytes

    def record_delete(self) -> None:
        """Record a cache delete operation."""
        self.metrics.deletes += 1

    def record_eviction(self, size_bytes: int | None = None) -> None:
        """
        Record a cache eviction.

        Args:
            size_bytes: Size of evicted value in bytes
        """
        self.metrics.evictions += 1

        if size_bytes:
            self.metrics.total_bytes_cached -= size_bytes

    def record_error(self) -> None:
        """Record a cache error."""
        self.metrics.errors += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Get current cache statistics.

        Returns:
            Dictionary with metrics and calculated stats
        """
        uptime = time.time() - self._start_time
        total_ops = (
            self.metrics.hits + self.metrics.misses + self.metrics.sets + self.metrics.deletes
        )

        stats = self.metrics.to_dict()
        stats.update(
            {
                "uptime_seconds": uptime,
                "total_operations": total_ops,
                "ops_per_second": total_ops / uptime if uptime > 0 else 0.0,
                "error_rate": (self.metrics.errors / total_ops if total_ops > 0 else 0.0),
            }
        )

        return stats

    def get_health(self) -> dict[str, Any]:
        """
        Get cache health status.

        Returns:
            Health status dict with:
                - healthy: Overall health boolean
                - issues: List of detected issues
                - recommendations: List of recommendations
        """
        issues = []
        recommendations = []

        # Check hit rate
        hit_rate = self.metrics.hit_rate()
        if hit_rate < 0.5 and self.metrics.hits + self.metrics.misses > 100:
            issues.append(f"Low hit rate: {hit_rate:.2%}")
            recommendations.append("Consider increasing cache TTL or size")

        # Check error rate
        total_ops = self.metrics.hits + self.metrics.misses + self.metrics.sets
        if total_ops > 0:
            error_rate = self.metrics.errors / total_ops
            if error_rate > 0.05:
                issues.append(f"High error rate: {error_rate:.2%}")
                recommendations.append("Check Redis connection and health")

        # Check latencies
        avg_hit_latency = self.metrics.avg_hit_latency()
        if avg_hit_latency > 50:
            issues.append(f"High hit latency: {avg_hit_latency:.1f}ms")
            recommendations.append("Check Redis performance and network")

        # Check semantic hit rate
        semantic_rate = self.metrics.semantic_hit_rate()
        if semantic_rate > 0.8 and self.metrics.hits > 100:
            recommendations.append(
                "High semantic hit rate - consider adjusting similarity threshold"
            )

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations,
            "metrics": self.get_stats(),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = CacheMetrics()
        self._last_reset = time.time()

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string

        Example:
            >>> monitor = CacheMonitor()
            >>> print(monitor.export_prometheus())
            # HELP cache_hits_total Total number of cache hits
            # TYPE cache_hits_total counter
            cache_hits_total 42
            ...
        """
        metrics = self.metrics
        lines = []

        # Counters
        lines.extend(
            [
                "# HELP cache_hits_total Total number of cache hits",
                "# TYPE cache_hits_total counter",
                f"cache_hits_total {metrics.hits}",
                "",
                "# HELP cache_misses_total Total number of cache misses",
                "# TYPE cache_misses_total counter",
                f"cache_misses_total {metrics.misses}",
                "",
                "# HELP cache_sets_total Total number of cache set operations",
                "# TYPE cache_sets_total counter",
                f"cache_sets_total {metrics.sets}",
                "",
                "# HELP cache_deletes_total Total number of cache delete operations",
                "# TYPE cache_deletes_total counter",
                f"cache_deletes_total {metrics.deletes}",
                "",
                "# HELP cache_errors_total Total number of cache errors",
                "# TYPE cache_errors_total counter",
                f"cache_errors_total {metrics.errors}",
                "",
            ]
        )

        # Gauges
        lines.extend(
            [
                "# HELP cache_hit_rate Current cache hit rate",
                "# TYPE cache_hit_rate gauge",
                f"cache_hit_rate {metrics.hit_rate()}",
                "",
                "# HELP cache_semantic_hit_rate Semantic hit rate",
                "# TYPE cache_semantic_hit_rate gauge",
                f"cache_semantic_hit_rate {metrics.semantic_hit_rate()}",
                "",
                "# HELP cache_avg_hit_latency_ms Average hit latency in milliseconds",
                "# TYPE cache_avg_hit_latency_ms gauge",
                f"cache_avg_hit_latency_ms {metrics.avg_hit_latency()}",
                "",
                "# HELP cache_avg_miss_latency_ms Average miss latency in milliseconds",
                "# TYPE cache_avg_miss_latency_ms gauge",
                f"cache_avg_miss_latency_ms {metrics.avg_miss_latency()}",
                "",
                "# HELP cache_total_bytes_cached Total bytes currently cached",
                "# TYPE cache_total_bytes_cached gauge",
                f"cache_total_bytes_cached {metrics.total_bytes_cached}",
                "",
            ]
        )

        return "\n".join(lines)


# Global singleton
_cache_monitor: CacheMonitor | None = None


def get_cache_monitor() -> CacheMonitor:
    """
    Get global cache monitor instance.

    Returns:
        Shared CacheMonitor instance
    """
    global _cache_monitor
    if _cache_monitor is None:
        _cache_monitor = CacheMonitor()
    return _cache_monitor
