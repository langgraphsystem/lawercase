"""RAG Performance Comparison Benchmarks for MegaAgent Pro.

Provides comprehensive benchmarking for RAG (Retrieval Augmented Generation) strategies:
- RetrievalBenchmark: Compare retrieval methods (dense, sparse, hybrid)
- GenerationBenchmark: Compare generation quality with different retrievers
- EndToEndRAGBenchmark: Full pipeline benchmarking
- RAGComparator: Multi-system comparison and analysis
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import random
import statistics
import time
from typing import Any


class RetrievalMethod(Enum):
    """Retrieval methods for comparison."""

    DENSE = "dense"  # Vector similarity
    SPARSE = "sparse"  # BM25/TF-IDF
    HYBRID = "hybrid"  # Combined dense + sparse
    GRAPH = "graph"  # Knowledge graph
    RERANKED = "reranked"  # With cross-encoder reranking


class ChunkingStrategy(Enum):
    """Document chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    HIERARCHICAL = "hierarchical"


class EmbeddingModel(Enum):
    """Embedding models for comparison."""

    ADA_002 = "text-embedding-ada-002"
    E5_LARGE = "e5-large-v2"
    BGE_LARGE = "bge-large-en-v1.5"
    COHERE_EMBED = "embed-english-v3.0"
    VOYAGE_2 = "voyage-2"


@dataclass
class RetrievalResult:
    """Single retrieval operation result."""

    query: str
    retrieved_docs: list[dict[str, Any]]
    latency_ms: float
    method: RetrievalMethod
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    mrr: float  # Mean Reciprocal Rank
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Single generation result with retrieved context."""

    query: str
    generated_response: str
    retrieval_result: RetrievalResult
    generation_latency_ms: float
    total_latency_ms: float
    faithfulness_score: float  # How well response matches retrieved context
    relevance_score: float  # How relevant response is to query
    completeness_score: float  # How complete the answer is
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGBenchmarkResult:
    """Complete RAG benchmark results."""

    benchmark_name: str
    method: RetrievalMethod
    embedding_model: EmbeddingModel | None
    chunking_strategy: ChunkingStrategy
    duration_seconds: float
    num_queries: int

    # Retrieval metrics
    avg_retrieval_latency_ms: float
    p95_retrieval_latency_ms: float
    avg_precision_at_k: float
    avg_recall_at_k: float
    avg_ndcg_at_k: float
    avg_mrr: float

    # Generation metrics (if applicable)
    avg_generation_latency_ms: float = 0.0
    avg_total_latency_ms: float = 0.0
    avg_faithfulness: float = 0.0
    avg_relevance: float = 0.0
    avg_completeness: float = 0.0

    # Cost metrics
    estimated_cost_per_query_usd: float = 0.0

    retrieval_results: list[RetrievalResult] = field(default_factory=list)
    generation_results: list[GenerationResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "method": self.method.value,
            "embedding_model": self.embedding_model.value if self.embedding_model else None,
            "chunking_strategy": self.chunking_strategy.value,
            "duration_seconds": self.duration_seconds,
            "num_queries": self.num_queries,
            "avg_retrieval_latency_ms": self.avg_retrieval_latency_ms,
            "p95_retrieval_latency_ms": self.p95_retrieval_latency_ms,
            "avg_precision_at_k": self.avg_precision_at_k,
            "avg_recall_at_k": self.avg_recall_at_k,
            "avg_ndcg_at_k": self.avg_ndcg_at_k,
            "avg_mrr": self.avg_mrr,
            "avg_generation_latency_ms": self.avg_generation_latency_ms,
            "avg_total_latency_ms": self.avg_total_latency_ms,
            "avg_faithfulness": self.avg_faithfulness,
            "avg_relevance": self.avg_relevance,
            "avg_completeness": self.avg_completeness,
            "estimated_cost_per_query_usd": self.estimated_cost_per_query_usd,
            "metadata": self.metadata,
        }


@dataclass
class RAGConfig:
    """Configuration for RAG benchmark."""

    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    embedding_model: EmbeddingModel = EmbeddingModel.ADA_002
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50
    rerank_top_n: int = 3
    similarity_threshold: float = 0.7


class BaseRAGBenchmark(ABC):
    """Base class for RAG benchmarks."""

    def __init__(self, config: RAGConfig | None = None):
        self.config = config or RAGConfig()
        self.retrieval_results: list[RetrievalResult] = []
        self.generation_results: list[GenerationResult] = []

    @abstractmethod
    async def run(
        self, queries: list[str], ground_truth: dict[str, list[str]] | None = None
    ) -> RAGBenchmarkResult:
        """Run the benchmark."""

    def _calculate_percentile(self, values: list[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _calculate_precision_at_k(self, retrieved: list[str], relevant: list[str], k: int) -> float:
        """Calculate precision@k."""
        if not retrieved or not relevant:
            return 0.0
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        return len([d for d in retrieved_k if d in relevant_set]) / k

    def _calculate_recall_at_k(self, retrieved: list[str], relevant: list[str], k: int) -> float:
        """Calculate recall@k."""
        if not retrieved or not relevant:
            return 0.0
        retrieved_k = set(retrieved[:k])
        relevant_set = set(relevant)
        return len(retrieved_k & relevant_set) / len(relevant_set)

    def _calculate_ndcg_at_k(self, retrieved: list[str], relevant: list[str], k: int) -> float:
        """Calculate NDCG@k."""
        if not retrieved or not relevant:
            return 0.0

        import math

        relevant_set = set(relevant)
        dcg = 0.0
        for i, doc in enumerate(retrieved[:k]):
            if doc in relevant_set:
                dcg += 1.0 / math.log2(i + 2)

        # Ideal DCG
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))

        return dcg / idcg if idcg > 0 else 0.0

    def _calculate_mrr(self, retrieved: list[str], relevant: list[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        if not retrieved or not relevant:
            return 0.0

        relevant_set = set(relevant)
        for i, doc in enumerate(retrieved):
            if doc in relevant_set:
                return 1.0 / (i + 1)
        return 0.0


class RetrievalBenchmark(BaseRAGBenchmark):
    """Benchmark for retrieval methods."""

    def __init__(
        self,
        config: RAGConfig | None = None,
        retriever: Callable[[str, int], list[dict[str, Any]]] | None = None,
    ):
        super().__init__(config)
        self._retriever = retriever or self._mock_retriever

    def _mock_retriever(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Mock retriever for testing."""
        return [
            {
                "id": f"doc_{i}_{hash(query) % 1000}",
                "content": f"Document {i} content for query: {query[:50]}...",
                "score": 0.9 - (i * 0.1),
                "metadata": {"source": f"source_{i}"},
            }
            for i in range(top_k)
        ]

    async def run(
        self,
        queries: list[str],
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGBenchmarkResult:
        """Run retrieval benchmark."""
        self.retrieval_results = []
        ground_truth = ground_truth or {}

        start_time = time.perf_counter()

        for query in queries:
            op_start = time.perf_counter()

            # Retrieve documents
            docs = self._retriever(query, self.config.top_k)

            latency = (time.perf_counter() - op_start) * 1000

            # Get retrieved doc IDs
            retrieved_ids = [d["id"] for d in docs]
            relevant_ids = ground_truth.get(
                query, retrieved_ids[:2]
            )  # Mock relevance if not provided

            result = RetrievalResult(
                query=query,
                retrieved_docs=docs,
                latency_ms=latency,
                method=self.config.retrieval_method,
                precision_at_k=self._calculate_precision_at_k(
                    retrieved_ids, relevant_ids, self.config.top_k
                ),
                recall_at_k=self._calculate_recall_at_k(
                    retrieved_ids, relevant_ids, self.config.top_k
                ),
                ndcg_at_k=self._calculate_ndcg_at_k(retrieved_ids, relevant_ids, self.config.top_k),
                mrr=self._calculate_mrr(retrieved_ids, relevant_ids),
            )
            self.retrieval_results.append(result)

        duration = time.perf_counter() - start_time
        return self._build_result("RetrievalBenchmark", duration, len(queries))

    def _build_result(self, name: str, duration: float, num_queries: int) -> RAGBenchmarkResult:
        """Build benchmark result."""
        latencies = [r.latency_ms for r in self.retrieval_results]

        return RAGBenchmarkResult(
            benchmark_name=name,
            method=self.config.retrieval_method,
            embedding_model=self.config.embedding_model,
            chunking_strategy=self.config.chunking_strategy,
            duration_seconds=duration,
            num_queries=num_queries,
            avg_retrieval_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p95_retrieval_latency_ms=self._calculate_percentile(latencies, 95),
            avg_precision_at_k=statistics.mean(r.precision_at_k for r in self.retrieval_results),
            avg_recall_at_k=statistics.mean(r.recall_at_k for r in self.retrieval_results),
            avg_ndcg_at_k=statistics.mean(r.ndcg_at_k for r in self.retrieval_results),
            avg_mrr=statistics.mean(r.mrr for r in self.retrieval_results),
            retrieval_results=self.retrieval_results,
        )


class EndToEndRAGBenchmark(BaseRAGBenchmark):
    """End-to-end RAG benchmark including generation."""

    def __init__(
        self,
        config: RAGConfig | None = None,
        retriever: Callable[[str, int], list[dict[str, Any]]] | None = None,
        generator: Callable[[str, list[dict[str, Any]]], str] | None = None,
        evaluator: Callable[[str, str, list[dict[str, Any]]], dict[str, float]] | None = None,
    ):
        super().__init__(config)
        self._retriever = retriever or self._mock_retriever
        self._generator = generator or self._mock_generator
        self._evaluator = evaluator or self._mock_evaluator

    def _mock_retriever(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Mock retriever."""
        return [
            {
                "id": f"doc_{i}",
                "content": f"Relevant content {i} for: {query[:30]}",
                "score": 0.95 - (i * 0.05),
            }
            for i in range(top_k)
        ]

    def _mock_generator(self, query: str, context: list[dict[str, Any]]) -> str:
        """Mock generator."""
        context_text = " ".join(d["content"] for d in context[:3])
        return f"Based on the context: {context_text[:100]}... The answer to '{query}' is synthesized from the retrieved documents."

    def _mock_evaluator(
        self, query: str, response: str, context: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Mock evaluator."""
        # Simulate quality scores
        return {
            "faithfulness": 0.85 + random.uniform(-0.1, 0.1),
            "relevance": 0.80 + random.uniform(-0.1, 0.1),
            "completeness": 0.75 + random.uniform(-0.1, 0.1),
        }

    async def run(
        self,
        queries: list[str],
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGBenchmarkResult:
        """Run end-to-end RAG benchmark."""
        self.retrieval_results = []
        self.generation_results = []
        ground_truth = ground_truth or {}

        start_time = time.perf_counter()

        for query in queries:
            # Retrieval phase
            retrieval_start = time.perf_counter()
            docs = self._retriever(query, self.config.top_k)
            retrieval_latency = (time.perf_counter() - retrieval_start) * 1000

            retrieved_ids = [d["id"] for d in docs]
            relevant_ids = ground_truth.get(query, retrieved_ids[:2])

            retrieval_result = RetrievalResult(
                query=query,
                retrieved_docs=docs,
                latency_ms=retrieval_latency,
                method=self.config.retrieval_method,
                precision_at_k=self._calculate_precision_at_k(
                    retrieved_ids, relevant_ids, self.config.top_k
                ),
                recall_at_k=self._calculate_recall_at_k(
                    retrieved_ids, relevant_ids, self.config.top_k
                ),
                ndcg_at_k=self._calculate_ndcg_at_k(retrieved_ids, relevant_ids, self.config.top_k),
                mrr=self._calculate_mrr(retrieved_ids, relevant_ids),
            )
            self.retrieval_results.append(retrieval_result)

            # Generation phase
            generation_start = time.perf_counter()
            response = self._generator(query, docs)
            generation_latency = (time.perf_counter() - generation_start) * 1000

            total_latency = retrieval_latency + generation_latency

            # Evaluation
            scores = self._evaluator(query, response, docs)

            generation_result = GenerationResult(
                query=query,
                generated_response=response,
                retrieval_result=retrieval_result,
                generation_latency_ms=generation_latency,
                total_latency_ms=total_latency,
                faithfulness_score=scores["faithfulness"],
                relevance_score=scores["relevance"],
                completeness_score=scores["completeness"],
            )
            self.generation_results.append(generation_result)

        duration = time.perf_counter() - start_time
        return self._build_result("EndToEndRAGBenchmark", duration, len(queries))

    def _build_result(self, name: str, duration: float, num_queries: int) -> RAGBenchmarkResult:
        """Build benchmark result."""
        retrieval_latencies = [r.latency_ms for r in self.retrieval_results]
        generation_latencies = [g.generation_latency_ms for g in self.generation_results]
        total_latencies = [g.total_latency_ms for g in self.generation_results]

        return RAGBenchmarkResult(
            benchmark_name=name,
            method=self.config.retrieval_method,
            embedding_model=self.config.embedding_model,
            chunking_strategy=self.config.chunking_strategy,
            duration_seconds=duration,
            num_queries=num_queries,
            avg_retrieval_latency_ms=(
                statistics.mean(retrieval_latencies) if retrieval_latencies else 0.0
            ),
            p95_retrieval_latency_ms=self._calculate_percentile(retrieval_latencies, 95),
            avg_precision_at_k=statistics.mean(r.precision_at_k for r in self.retrieval_results),
            avg_recall_at_k=statistics.mean(r.recall_at_k for r in self.retrieval_results),
            avg_ndcg_at_k=statistics.mean(r.ndcg_at_k for r in self.retrieval_results),
            avg_mrr=statistics.mean(r.mrr for r in self.retrieval_results),
            avg_generation_latency_ms=(
                statistics.mean(generation_latencies) if generation_latencies else 0.0
            ),
            avg_total_latency_ms=statistics.mean(total_latencies) if total_latencies else 0.0,
            avg_faithfulness=statistics.mean(g.faithfulness_score for g in self.generation_results),
            avg_relevance=statistics.mean(g.relevance_score for g in self.generation_results),
            avg_completeness=statistics.mean(g.completeness_score for g in self.generation_results),
            retrieval_results=self.retrieval_results,
            generation_results=self.generation_results,
        )


@dataclass
class RAGComparisonReport:
    """Comprehensive RAG comparison report."""

    timestamp: datetime
    benchmark_results: list[RAGBenchmarkResult]
    best_retrieval_method: RetrievalMethod
    best_overall_config: RAGConfig
    comparison_matrix: dict[str, dict[str, float]]
    recommendations: list[str]
    summary_stats: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "benchmark_results": [r.to_dict() for r in self.benchmark_results],
            "best_retrieval_method": self.best_retrieval_method.value,
            "best_overall_config": {
                "retrieval_method": self.best_overall_config.retrieval_method.value,
                "embedding_model": self.best_overall_config.embedding_model.value,
                "chunking_strategy": self.best_overall_config.chunking_strategy.value,
            },
            "comparison_matrix": self.comparison_matrix,
            "recommendations": self.recommendations,
            "summary_stats": self.summary_stats,
        }

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=2)


class RAGComparator:
    """Compare different RAG configurations."""

    def __init__(self):
        self.results: list[RAGBenchmarkResult] = []

    async def compare_retrieval_methods(
        self,
        queries: list[str],
        methods: list[RetrievalMethod] | None = None,
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGComparisonReport:
        """Compare different retrieval methods."""
        methods = methods or list(RetrievalMethod)
        self.results = []

        for method in methods:
            config = RAGConfig(retrieval_method=method)
            benchmark = RetrievalBenchmark(config)
            result = await benchmark.run(queries, ground_truth)
            self.results.append(result)

        return self._generate_report()

    async def compare_embedding_models(
        self,
        queries: list[str],
        models: list[EmbeddingModel] | None = None,
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGComparisonReport:
        """Compare different embedding models."""
        models = models or list(EmbeddingModel)
        self.results = []

        for model in models:
            config = RAGConfig(embedding_model=model)
            benchmark = RetrievalBenchmark(config)
            result = await benchmark.run(queries, ground_truth)
            self.results.append(result)

        return self._generate_report()

    async def compare_chunking_strategies(
        self,
        queries: list[str],
        strategies: list[ChunkingStrategy] | None = None,
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGComparisonReport:
        """Compare different chunking strategies."""
        strategies = strategies or list(ChunkingStrategy)
        self.results = []

        for strategy in strategies:
            config = RAGConfig(chunking_strategy=strategy)
            benchmark = RetrievalBenchmark(config)
            result = await benchmark.run(queries, ground_truth)
            self.results.append(result)

        return self._generate_report()

    async def run_full_comparison(
        self,
        queries: list[str],
        ground_truth: dict[str, list[str]] | None = None,
    ) -> RAGComparisonReport:
        """Run comprehensive comparison across all dimensions."""
        self.results = []

        # Test key combinations
        configs = [
            RAGConfig(
                retrieval_method=RetrievalMethod.DENSE, embedding_model=EmbeddingModel.ADA_002
            ),
            RAGConfig(retrieval_method=RetrievalMethod.SPARSE),
            RAGConfig(
                retrieval_method=RetrievalMethod.HYBRID, embedding_model=EmbeddingModel.ADA_002
            ),
            RAGConfig(
                retrieval_method=RetrievalMethod.RERANKED, embedding_model=EmbeddingModel.BGE_LARGE
            ),
            RAGConfig(retrieval_method=RetrievalMethod.GRAPH),
        ]

        for config in configs:
            benchmark = EndToEndRAGBenchmark(config)
            result = await benchmark.run(queries, ground_truth)
            self.results.append(result)

        return self._generate_report()

    def _generate_report(self) -> RAGComparisonReport:
        """Generate comparison report."""
        # Find best configurations
        best_by_ndcg = max(self.results, key=lambda r: r.avg_ndcg_at_k)
        best_method = best_by_ndcg.method

        best_config = RAGConfig(
            retrieval_method=best_by_ndcg.method,
            embedding_model=best_by_ndcg.embedding_model or EmbeddingModel.ADA_002,
            chunking_strategy=best_by_ndcg.chunking_strategy,
        )

        # Build comparison matrix
        comparison_matrix = self._build_comparison_matrix()

        # Generate recommendations
        recommendations = self._generate_recommendations()

        # Summary statistics
        summary_stats = {
            "avg_ndcg": statistics.mean(r.avg_ndcg_at_k for r in self.results),
            "max_ndcg": max(r.avg_ndcg_at_k for r in self.results),
            "avg_mrr": statistics.mean(r.avg_mrr for r in self.results),
            "avg_latency_ms": statistics.mean(r.avg_retrieval_latency_ms for r in self.results),
            "min_latency_ms": min(r.avg_retrieval_latency_ms for r in self.results),
        }

        return RAGComparisonReport(
            timestamp=datetime.now(),
            benchmark_results=self.results,
            best_retrieval_method=best_method,
            best_overall_config=best_config,
            comparison_matrix=comparison_matrix,
            recommendations=recommendations,
            summary_stats=summary_stats,
        )

    def _build_comparison_matrix(self) -> dict[str, dict[str, float]]:
        """Build comparison matrix."""
        matrix: dict[str, dict[str, float]] = {}

        for result in self.results:
            key = f"{result.method.value}"
            if result.embedding_model:
                key += f"_{result.embedding_model.value}"

            matrix[key] = {
                "ndcg": result.avg_ndcg_at_k,
                "mrr": result.avg_mrr,
                "precision": result.avg_precision_at_k,
                "recall": result.avg_recall_at_k,
                "latency_ms": result.avg_retrieval_latency_ms,
            }

        return matrix

    def _generate_recommendations(self) -> list[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Analyze results
        hybrid_results = [r for r in self.results if r.method == RetrievalMethod.HYBRID]
        dense_results = [r for r in self.results if r.method == RetrievalMethod.DENSE]

        if hybrid_results and dense_results:
            hybrid_ndcg = statistics.mean(r.avg_ndcg_at_k for r in hybrid_results)
            dense_ndcg = statistics.mean(r.avg_ndcg_at_k for r in dense_results)

            if hybrid_ndcg > dense_ndcg:
                recommendations.append(
                    f"Hybrid retrieval outperforms dense by {(hybrid_ndcg - dense_ndcg) * 100:.1f}% NDCG. "
                    "Recommend using hybrid approach."
                )

        # Check latency
        fast_results = [r for r in self.results if r.avg_retrieval_latency_ms < 50]
        if fast_results:
            fastest = min(fast_results, key=lambda r: r.avg_retrieval_latency_ms)
            recommendations.append(
                f"For latency-sensitive applications, consider {fastest.method.value} "
                f"with {fastest.avg_retrieval_latency_ms:.1f}ms average latency."
            )

        # Check quality
        high_quality = [r for r in self.results if r.avg_ndcg_at_k > 0.8]
        if high_quality:
            best = max(high_quality, key=lambda r: r.avg_ndcg_at_k)
            recommendations.append(
                f"For highest quality, use {best.method.value} achieving {best.avg_ndcg_at_k:.2f} NDCG@k."
            )

        if not recommendations:
            recommendations.append("All configurations show comparable performance.")

        return recommendations


async def run_quick_rag_benchmark(queries: list[str] | None = None) -> RAGComparisonReport:
    """Run quick RAG benchmark."""
    queries = queries or [
        "What is machine learning?",
        "How does neural network work?",
        "Explain deep learning",
        "What are transformers in NLP?",
        "How to train a model?",
    ]

    comparator = RAGComparator()
    return await comparator.compare_retrieval_methods(queries)


async def run_full_rag_benchmark(queries: list[str]) -> RAGComparisonReport:
    """Run comprehensive RAG benchmark."""
    comparator = RAGComparator()
    return await comparator.run_full_comparison(queries)


__all__ = [
    # Benchmarks
    "BaseRAGBenchmark",
    "ChunkingStrategy",
    "EmbeddingModel",
    "EndToEndRAGBenchmark",
    "GenerationResult",
    "RAGBenchmarkResult",
    # Comparator
    "RAGComparator",
    "RAGComparisonReport",
    "RAGConfig",
    "RetrievalBenchmark",
    # Enums
    "RetrievalMethod",
    # Data classes
    "RetrievalResult",
    "run_full_rag_benchmark",
    # Functions
    "run_quick_rag_benchmark",
]
