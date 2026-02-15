"""Caching Performance Benchmarks for MegaAgent Pro.

Provides comprehensive benchmarking for caching strategies:
- SemanticCacheBenchmark: LLM response caching performance
- EmbeddingCacheBenchmark: Vector embedding caching metrics
- MemoryCacheBenchmark: Memory store caching efficiency
- HybridCacheBenchmark: Multi-tier cache performance
- CacheAnalyzer: Comprehensive cache analysis and reporting
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import random
import statistics
import time
from typing import Any, TypeVar

T = TypeVar("T")


class CacheStrategy(Enum):
    """Cache eviction strategies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    SEMANTIC = "semantic"  # Semantic similarity based
    HYBRID = "hybrid"  # Combined strategies


class CacheTier(Enum):
    """Cache tier levels."""

    L1_MEMORY = "l1_memory"  # In-process memory
    L2_REDIS = "l2_redis"  # Redis/distributed
    L3_DATABASE = "l3_database"  # Persistent store


@dataclass
class CacheOperation:
    """Single cache operation record."""

    operation: str  # get, set, delete, invalidate
    key: str
    hit: bool
    latency_ms: float
    tier: CacheTier
    timestamp: datetime = field(default_factory=datetime.now)
    value_size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheBenchmarkResult:
    """Results from a cache benchmark run."""

    benchmark_name: str
    strategy: CacheStrategy
    duration_seconds: float
    total_operations: int
    hits: int
    misses: int
    hit_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_per_sec: float
    memory_used_mb: float
    cost_savings_pct: float
    operations: list[CacheOperation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "strategy": self.strategy.value,
            "duration_seconds": self.duration_seconds,
            "total_operations": self.total_operations,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "throughput_ops_per_sec": self.throughput_ops_per_sec,
            "memory_used_mb": self.memory_used_mb,
            "cost_savings_pct": self.cost_savings_pct,
            "metadata": self.metadata,
        }


@dataclass
class CacheConfig:
    """Cache configuration for benchmarks."""

    max_size: int = 10000
    ttl_seconds: int = 3600
    strategy: CacheStrategy = CacheStrategy.LRU
    similarity_threshold: float = 0.95
    enable_compression: bool = True
    tier: CacheTier = CacheTier.L1_MEMORY


class BaseCacheBenchmark(ABC):
    """Base class for cache benchmarks."""

    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()
        self.operations: list[CacheOperation] = []
        self._cache: dict[
            str, tuple[Any, datetime, int]
        ] = {}  # key -> (value, timestamp, access_count)
        self._access_order: list[str] = []

    @abstractmethod
    async def run(self, num_operations: int = 10000) -> CacheBenchmarkResult:
        """Run the benchmark."""

    def _generate_key(self, data: str) -> str:
        """Generate cache key from data."""
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _record_operation(
        self,
        operation: str,
        key: str,
        hit: bool,
        latency_ms: float,
        value_size: int = 0,
    ) -> None:
        """Record a cache operation."""
        self.operations.append(
            CacheOperation(
                operation=operation,
                key=key,
                hit=hit,
                latency_ms=latency_ms,
                tier=self.config.tier,
                value_size_bytes=value_size,
            )
        )

    def _calculate_percentile(self, latencies: list[float], percentile: float) -> float:
        """Calculate latency percentile."""
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    def _build_result(
        self,
        benchmark_name: str,
        duration: float,
    ) -> CacheBenchmarkResult:
        """Build benchmark result from recorded operations."""
        hits = sum(1 for op in self.operations if op.hit)
        misses = len(self.operations) - hits
        latencies = [op.latency_ms for op in self.operations]

        return CacheBenchmarkResult(
            benchmark_name=benchmark_name,
            strategy=self.config.strategy,
            duration_seconds=duration,
            total_operations=len(self.operations),
            hits=hits,
            misses=misses,
            hit_rate=hits / len(self.operations) if self.operations else 0.0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p50_latency_ms=self._calculate_percentile(latencies, 50),
            p95_latency_ms=self._calculate_percentile(latencies, 95),
            p99_latency_ms=self._calculate_percentile(latencies, 99),
            throughput_ops_per_sec=len(self.operations) / duration if duration > 0 else 0.0,
            memory_used_mb=self._estimate_memory_usage(),
            cost_savings_pct=self._estimate_cost_savings(hits, misses),
            operations=self.operations,
        )

    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        total_bytes = sum(len(str(k)) + len(str(v[0])) for k, v in self._cache.items())
        return total_bytes / (1024 * 1024)

    def _estimate_cost_savings(self, hits: int, misses: int) -> float:
        """Estimate cost savings percentage from cache hits."""
        if hits + misses == 0:
            return 0.0
        # Assume each miss costs ~$0.01 (LLM call) vs cache hit ~$0.0001
        miss_cost = misses * 0.01
        hit_cost = hits * 0.0001
        no_cache_cost = (hits + misses) * 0.01
        actual_cost = miss_cost + hit_cost
        return ((no_cache_cost - actual_cost) / no_cache_cost) * 100 if no_cache_cost > 0 else 0.0


class SemanticCacheBenchmark(BaseCacheBenchmark):
    """Benchmark for semantic LLM response caching."""

    def __init__(
        self,
        config: CacheConfig | None = None,
        embedding_fn: Callable[[str], list[float]] | None = None,
    ):
        super().__init__(config)
        self._embedding_fn = embedding_fn or self._mock_embedding
        self._embeddings: dict[str, list[float]] = {}

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate mock embedding for testing."""
        random.seed(hash(text) % 2**32)
        return [random.gauss(0, 1) for _ in range(1536)]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def _find_similar(self, query_embedding: list[float]) -> tuple[str, float] | None:
        """Find similar cached item by embedding."""
        best_match = None
        best_similarity = 0.0

        for key, embedding in self._embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity > best_similarity and similarity >= self.config.similarity_threshold:
                best_similarity = similarity
                best_match = key

        return (best_match, best_similarity) if best_match else None

    async def run(self, num_operations: int = 10000) -> CacheBenchmarkResult:
        """Run semantic cache benchmark."""
        self.operations = []
        self._cache = {}
        self._embeddings = {}

        # Generate test queries with some semantic similarity
        base_queries = [
            "What is machine learning?",
            "Explain neural networks",
            "How does NLP work?",
            "Describe deep learning",
            "What are transformers?",
        ]

        # Create variations
        queries = []
        for _ in range(num_operations):
            base = random.choice(base_queries)
            variation = random.choice(["", " in simple terms", " briefly", " in detail"])
            queries.append(base + variation)

        start_time = time.perf_counter()

        for query in queries:
            op_start = time.perf_counter()
            embedding = self._embedding_fn(query)

            # Try semantic match
            match = self._find_similar(embedding)

            if match:
                key, _similarity = match
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("get", key, True, latency)
            else:
                # Cache miss - store new entry
                key = self._generate_key(query)
                response = f"Response for: {query}"  # Mock response
                self._cache[key] = (response, datetime.now(), 1)
                self._embeddings[key] = embedding
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("set", key, False, latency, len(response))

                # Evict if over capacity
                if len(self._cache) > self.config.max_size:
                    self._evict_one()

        duration = time.perf_counter() - start_time
        return self._build_result("SemanticCacheBenchmark", duration)

    def _evict_one(self) -> None:
        """Evict one entry based on strategy."""
        if not self._cache:
            return

        if self.config.strategy == CacheStrategy.LRU:
            # Find oldest accessed
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
        elif self.config.strategy == CacheStrategy.LFU:
            # Find least frequently used
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        else:
            # FIFO - first key
            oldest_key = next(iter(self._cache))

        del self._cache[oldest_key]
        del self._embeddings[oldest_key]


class EmbeddingCacheBenchmark(BaseCacheBenchmark):
    """Benchmark for embedding vector caching."""

    def __init__(
        self,
        config: CacheConfig | None = None,
        embedding_dim: int = 1536,
    ):
        super().__init__(config)
        self.embedding_dim = embedding_dim

    async def run(self, num_operations: int = 10000) -> CacheBenchmarkResult:
        """Run embedding cache benchmark."""
        self.operations = []
        self._cache = {}

        # Generate test texts with repetition
        unique_texts = [f"Text sample {i}" for i in range(num_operations // 10)]
        texts = [random.choice(unique_texts) for _ in range(num_operations)]

        start_time = time.perf_counter()

        for text in texts:
            key = self._generate_key(text)
            op_start = time.perf_counter()

            if key in self._cache:
                # Cache hit
                _ = self._cache[key][0]
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("get", key, True, latency)
            else:
                # Cache miss - generate embedding
                embedding = [random.gauss(0, 1) for _ in range(self.embedding_dim)]
                self._cache[key] = (embedding, datetime.now(), 1)
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("set", key, False, latency, self.embedding_dim * 4)

                if len(self._cache) > self.config.max_size:
                    self._evict_lru()

        duration = time.perf_counter() - start_time
        return self._build_result("EmbeddingCacheBenchmark", duration)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]


class MemoryCacheBenchmark(BaseCacheBenchmark):
    """Benchmark for memory store caching."""

    async def run(self, num_operations: int = 10000) -> CacheBenchmarkResult:
        """Run memory cache benchmark."""
        self.operations = []
        self._cache = {}

        # Simulate memory operations
        memory_types = ["episodic", "semantic", "persona", "working"]
        user_ids = [f"user_{i}" for i in range(100)]

        start_time = time.perf_counter()

        for i in range(num_operations):
            mem_type = random.choice(memory_types)
            user_id = random.choice(user_ids)
            key = f"{user_id}:{mem_type}:{i % 500}"
            op_start = time.perf_counter()

            if random.random() < 0.7:  # 70% reads
                if key in self._cache:
                    _ = self._cache[key]
                    latency = (time.perf_counter() - op_start) * 1000
                    self._record_operation("get", key, True, latency)
                else:
                    latency = (time.perf_counter() - op_start) * 1000
                    self._record_operation("get", key, False, latency)
            else:  # 30% writes
                value = {"type": mem_type, "content": f"Memory content {i}"}
                self._cache[key] = (value, datetime.now(), 1)
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("set", key, False, latency, len(str(value)))

        duration = time.perf_counter() - start_time
        return self._build_result("MemoryCacheBenchmark", duration)


class HybridCacheBenchmark(BaseCacheBenchmark):
    """Benchmark for multi-tier hybrid caching."""

    def __init__(self, config: CacheConfig | None = None):
        super().__init__(config)
        self._l1_cache: dict[str, Any] = {}  # In-memory
        self._l2_cache: dict[str, Any] = {}  # Simulated Redis
        self._l3_cache: dict[str, Any] = {}  # Simulated database
        self._l1_max = 1000
        self._l2_max = 10000

    async def run(self, num_operations: int = 10000) -> CacheBenchmarkResult:
        """Run hybrid cache benchmark."""
        self.operations = []
        self._l1_cache = {}
        self._l2_cache = {}
        self._l3_cache = {}

        keys = [f"key_{i % 2000}" for i in range(num_operations)]

        start_time = time.perf_counter()

        for key in keys:
            op_start = time.perf_counter()

            # Check L1
            if key in self._l1_cache:
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("get_l1", key, True, latency)
                continue

            # Check L2
            if key in self._l2_cache:
                # Promote to L1
                self._l1_cache[key] = self._l2_cache[key]
                if len(self._l1_cache) > self._l1_max:
                    self._evict_from_l1()
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("get_l2", key, True, latency)
                continue

            # Check L3
            if key in self._l3_cache:
                # Promote to L2 and L1
                self._l2_cache[key] = self._l3_cache[key]
                self._l1_cache[key] = self._l3_cache[key]
                if len(self._l2_cache) > self._l2_max:
                    self._evict_from_l2()
                if len(self._l1_cache) > self._l1_max:
                    self._evict_from_l1()
                latency = (time.perf_counter() - op_start) * 1000
                self._record_operation("get_l3", key, True, latency)
                continue

            # Cache miss - store in all tiers
            value = f"value_for_{key}"
            self._l1_cache[key] = value
            self._l2_cache[key] = value
            self._l3_cache[key] = value
            latency = (time.perf_counter() - op_start) * 1000
            self._record_operation("set_all", key, False, latency, len(value))

        duration = time.perf_counter() - start_time
        return self._build_result("HybridCacheBenchmark", duration)

    def _evict_from_l1(self) -> None:
        """Evict from L1 cache."""
        if self._l1_cache:
            key = next(iter(self._l1_cache))
            del self._l1_cache[key]

    def _evict_from_l2(self) -> None:
        """Evict from L2 cache."""
        if self._l2_cache:
            key = next(iter(self._l2_cache))
            del self._l2_cache[key]


@dataclass
class CacheAnalysisReport:
    """Comprehensive cache analysis report."""

    timestamp: datetime
    benchmarks: list[CacheBenchmarkResult]
    best_strategy: CacheStrategy
    recommendations: list[str]
    comparison_matrix: dict[str, dict[str, float]]
    summary_stats: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "best_strategy": self.best_strategy.value,
            "recommendations": self.recommendations,
            "comparison_matrix": self.comparison_matrix,
            "summary_stats": self.summary_stats,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class CacheAnalyzer:
    """Comprehensive cache performance analyzer."""

    def __init__(self):
        self.results: list[CacheBenchmarkResult] = []

    async def run_all_benchmarks(
        self,
        num_operations: int = 10000,
        strategies: list[CacheStrategy] | None = None,
    ) -> CacheAnalysisReport:
        """Run all cache benchmarks and generate analysis report."""
        strategies = strategies or [CacheStrategy.LRU, CacheStrategy.LFU, CacheStrategy.SEMANTIC]
        self.results = []

        benchmarks = [
            SemanticCacheBenchmark,
            EmbeddingCacheBenchmark,
            MemoryCacheBenchmark,
            HybridCacheBenchmark,
        ]

        for strategy in strategies:
            config = CacheConfig(strategy=strategy)
            for benchmark_class in benchmarks:
                benchmark = benchmark_class(config)
                result = await benchmark.run(num_operations)
                self.results.append(result)

        return self._generate_report()

    def _generate_report(self) -> CacheAnalysisReport:
        """Generate comprehensive analysis report."""
        # Find best strategy by hit rate
        best_result = max(self.results, key=lambda r: r.hit_rate)
        best_strategy = best_result.strategy

        # Build comparison matrix
        comparison_matrix = self._build_comparison_matrix()

        # Generate recommendations
        recommendations = self._generate_recommendations()

        # Summary stats
        summary_stats = {
            "avg_hit_rate": statistics.mean(r.hit_rate for r in self.results),
            "avg_latency_ms": statistics.mean(r.avg_latency_ms for r in self.results),
            "max_throughput": max(r.throughput_ops_per_sec for r in self.results),
            "avg_cost_savings_pct": statistics.mean(r.cost_savings_pct for r in self.results),
        }

        return CacheAnalysisReport(
            timestamp=datetime.now(),
            benchmarks=self.results,
            best_strategy=best_strategy,
            recommendations=recommendations,
            comparison_matrix=comparison_matrix,
            summary_stats=summary_stats,
        )

    def _build_comparison_matrix(self) -> dict[str, dict[str, float]]:
        """Build strategy comparison matrix."""
        matrix: dict[str, dict[str, float]] = defaultdict(dict)

        for result in self.results:
            strategy = result.strategy.value
            benchmark = result.benchmark_name
            key = f"{strategy}_{benchmark}"
            matrix[key] = {
                "hit_rate": result.hit_rate,
                "avg_latency_ms": result.avg_latency_ms,
                "throughput": result.throughput_ops_per_sec,
                "cost_savings": result.cost_savings_pct,
            }

        return dict(matrix)

    def _generate_recommendations(self) -> list[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Analyze hit rates
        avg_hit_rate = statistics.mean(r.hit_rate for r in self.results)
        if avg_hit_rate < 0.5:
            recommendations.append(
                "Low hit rate detected. Consider increasing cache size or adjusting TTL."
            )

        # Analyze latencies
        high_latency_results = [r for r in self.results if r.p99_latency_ms > 100]
        if high_latency_results:
            recommendations.append(
                "High P99 latency in some benchmarks. Consider async cache writes."
            )

        # Strategy-specific recommendations
        semantic_results = [r for r in self.results if r.strategy == CacheStrategy.SEMANTIC]
        if semantic_results:
            semantic_hit_rate = statistics.mean(r.hit_rate for r in semantic_results)
            if semantic_hit_rate > avg_hit_rate:
                recommendations.append(
                    "Semantic caching shows higher hit rates. Recommend for LLM responses."
                )

        # Memory recommendations
        max_memory = max(r.memory_used_mb for r in self.results)
        if max_memory > 100:
            recommendations.append(
                f"High memory usage ({max_memory:.1f}MB). Consider compression or tiered caching."
            )

        if not recommendations:
            recommendations.append("Cache performance is within acceptable parameters.")

        return recommendations


async def run_quick_benchmark() -> CacheAnalysisReport:
    """Run a quick benchmark with default settings."""
    analyzer = CacheAnalyzer()
    return await analyzer.run_all_benchmarks(num_operations=1000)


async def run_full_benchmark() -> CacheAnalysisReport:
    """Run comprehensive benchmark with all strategies."""
    analyzer = CacheAnalyzer()
    return await analyzer.run_all_benchmarks(
        num_operations=10000,
        strategies=list(CacheStrategy),
    )


# Export convenience function
def create_benchmark_suite(
    config: CacheConfig | None = None,
) -> dict[str, BaseCacheBenchmark]:
    """Create a suite of cache benchmarks."""
    return {
        "semantic": SemanticCacheBenchmark(config),
        "embedding": EmbeddingCacheBenchmark(config),
        "memory": MemoryCacheBenchmark(config),
        "hybrid": HybridCacheBenchmark(config),
    }


__all__ = [
    # Benchmarks
    "BaseCacheBenchmark",
    "CacheAnalysisReport",
    # Analyzer
    "CacheAnalyzer",
    "CacheBenchmarkResult",
    "CacheConfig",
    # Data classes
    "CacheOperation",
    # Enums
    "CacheStrategy",
    "CacheTier",
    "EmbeddingCacheBenchmark",
    "HybridCacheBenchmark",
    "MemoryCacheBenchmark",
    "SemanticCacheBenchmark",
    "create_benchmark_suite",
    "run_full_benchmark",
    # Functions
    "run_quick_benchmark",
]
