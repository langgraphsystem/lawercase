"""Performance benchmarks for RAG pipeline.

Benchmarks for:
- BM25 retrieval latency
- RRF fusion performance
- Document chunking speed
- RAG pipeline operations
"""

from __future__ import annotations

import gc
import statistics
import time
from dataclasses import dataclass
from typing import Any

import pytest

# ============================================================================
# Benchmark Configuration
# ============================================================================


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarks."""

    warmup_iterations: int = 2
    benchmark_iterations: int = 5


@dataclass
class BenchmarkResult:
    """Result of a benchmark."""

    name: str
    iterations: int
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    throughput: float  # operations per second

    def __str__(self) -> str:
        return (
            f"{self.name}: mean={self.mean_ms:.2f}ms, "
            f"median={self.median_ms:.2f}ms, "
            f"std={self.std_dev_ms:.2f}ms, "
            f"throughput={self.throughput:.2f} ops/s"
        )


# ============================================================================
# Benchmark Utilities
# ============================================================================


def generate_documents(count: int, avg_length: int = 500) -> list[dict[str, Any]]:
    """Generate sample documents for benchmarking."""
    import random
    import string

    documents = []
    for i in range(count):
        words = [
            "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
            for _ in range(avg_length // 5)
        ]
        text = " ".join(words)
        documents.append(
            {
                "text": text,
                "doc_id": f"doc_{i}",
                "metadata": {"index": i, "type": "benchmark"},
            }
        )
    return documents


def generate_queries(count: int) -> list[str]:
    """Generate sample queries for benchmarking."""
    import random
    import string

    queries = []
    for _ in range(count):
        words = [
            "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
            for _ in range(random.randint(2, 5))
        ]
        queries.append(" ".join(words))
    return queries


async def run_benchmark(
    func,
    config: BenchmarkConfig,
) -> BenchmarkResult:
    """Run a benchmark and collect statistics."""
    # Warmup
    for _ in range(config.warmup_iterations):
        await func()

    # Benchmark
    times = []
    for _ in range(config.benchmark_iterations):
        start = time.perf_counter()
        await func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return BenchmarkResult(
        name=func.__name__,
        iterations=config.benchmark_iterations,
        mean_ms=statistics.mean(times),
        median_ms=statistics.median(times),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
        throughput=1000 / statistics.mean(times) if statistics.mean(times) > 0 else 0,
    )


# ============================================================================
# BM25 Benchmarks
# ============================================================================


class TestBM25Benchmarks:
    """Benchmarks for BM25 retrieval."""

    @pytest.fixture
    def config(self) -> BenchmarkConfig:
        return BenchmarkConfig(warmup_iterations=2, benchmark_iterations=5)

    @pytest.mark.asyncio
    async def test_bm25_creation_speed(self, config: BenchmarkConfig) -> None:
        """Benchmark BM25 retriever creation."""
        from core.rag import create_bm25_retriever

        documents = generate_documents(500)
        texts = [d["text"] for d in documents]

        async def create_retriever():
            await create_bm25_retriever(texts)

        result = await run_benchmark(create_retriever, config)
        print(f"\nBM25 Creation (500 docs): {result}")

        # Assert reasonable performance - 5 seconds max for 500 docs
        assert result.mean_ms < 5000

    @pytest.mark.asyncio
    async def test_bm25_search_latency(self, config: BenchmarkConfig) -> None:
        """Benchmark BM25 search latency."""
        from core.rag import create_bm25_retriever

        documents = generate_documents(500)
        texts = [d["text"] for d in documents]

        retriever = await create_bm25_retriever(texts)
        queries = generate_queries(5)

        async def search_queries():
            for query in queries:
                await retriever.asearch(query, top_k=10)

        result = await run_benchmark(search_queries, config)
        print(f"\nBM25 Search (500 docs, 5 queries): {result}")

        # Assert reasonable performance - 1 second max for 5 queries
        assert result.mean_ms < 1000


# ============================================================================
# RRF Fusion Benchmarks
# ============================================================================


class TestFusionBenchmarks:
    """Benchmarks for hybrid fusion."""

    @pytest.fixture
    def config(self) -> BenchmarkConfig:
        return BenchmarkConfig(warmup_iterations=2, benchmark_iterations=5)

    @pytest.mark.asyncio
    async def test_rrf_fusion_speed(self, config: BenchmarkConfig) -> None:
        """Benchmark RRF fusion speed."""
        import random

        from core.rag import ReciprocalRankFusion

        # Generate mock rankings
        doc_ids = [f"doc_{i}" for i in range(100)]

        def create_ranking(count: int) -> list[tuple[str, float]]:
            selected = random.sample(doc_ids, count)
            return [(doc_id, random.random()) for doc_id in selected]

        rrf = ReciprocalRankFusion()
        rankings = [create_ranking(50) for _ in range(3)]

        async def fuse_rankings():
            await rrf.fuse(rankings, top_k=20)

        result = await run_benchmark(fuse_rankings, config)
        print(f"\nRRF Fusion (3 rankings x 50 results): {result}")

        # Assert reasonable performance - 50ms max for fusion
        assert result.mean_ms < 50


# ============================================================================
# Chunking Benchmarks
# ============================================================================


class TestChunkingBenchmarks:
    """Benchmarks for document chunking."""

    @pytest.fixture
    def config(self) -> BenchmarkConfig:
        return BenchmarkConfig(warmup_iterations=2, benchmark_iterations=5)

    @pytest.mark.asyncio
    async def test_fixed_chunking_speed(self, config: BenchmarkConfig) -> None:
        """Benchmark fixed-size chunking."""
        from core.rag import ChunkingStrategy, create_chunker

        # Generate a large document
        text = " ".join(["word"] * 10000)

        chunker = create_chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=500,
            chunk_overlap=50,
        )

        async def chunk_document():
            return chunker.chunk_text(text, "doc_1")

        result = await run_benchmark(chunk_document, config)
        print(f"\nFixed Chunking (10K words): {result}")

        # Assert reasonable performance - 500ms max
        assert result.mean_ms < 500

    @pytest.mark.asyncio
    async def test_semantic_chunking_speed(self, config: BenchmarkConfig) -> None:
        """Benchmark semantic chunking."""
        from core.rag import ChunkingStrategy, create_chunker

        # Generate text with sentence structure
        sentences = [f"This is sentence number {i}." for i in range(200)]
        text = " ".join(sentences)

        chunker = create_chunker(
            strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=500,
        )

        async def chunk_document():
            return chunker.chunk_text(text, "doc_1")

        result = await run_benchmark(chunk_document, config)
        print(f"\nSemantic Chunking (200 sentences): {result}")

        # Assert reasonable performance - 500ms max
        assert result.mean_ms < 500


# ============================================================================
# RAG Pipeline Benchmarks
# ============================================================================


class TestPipelineBenchmarks:
    """Benchmarks for RAG pipeline."""

    @pytest.fixture
    def config(self) -> BenchmarkConfig:
        return BenchmarkConfig(warmup_iterations=1, benchmark_iterations=3)

    @pytest.mark.asyncio
    async def test_pipeline_creation(self, config: BenchmarkConfig) -> None:
        """Benchmark pipeline creation speed."""
        from core.rag import create_rag_pipeline

        async def create_pipeline():
            await create_rag_pipeline(use_hybrid=False)

        result = await run_benchmark(create_pipeline, config)
        print(f"\nPipeline Creation: {result}")

        # Assert reasonable performance - 1 second max
        assert result.mean_ms < 1000


# ============================================================================
# Memory Usage Tests
# ============================================================================


class TestMemoryUsage:
    """Tests for memory usage."""

    @pytest.mark.asyncio
    async def test_document_memory_footprint(self) -> None:
        """Test memory footprint of documents."""
        import sys

        gc.collect()

        # Generate documents
        documents = generate_documents(1000)

        gc.collect()

        # Calculate approximate memory
        doc_size = sys.getsizeof(documents)
        print(f"\n1000 documents size: {doc_size / 1024:.2f} KB")

        # Reasonable size check - less than 10MB for 1000 docs
        assert doc_size < 10 * 1024 * 1024


# ============================================================================
# Benchmark Summary
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_summary() -> None:
    """Run core benchmarks and print summary."""
    from core.rag import ReciprocalRankFusion, create_bm25_retriever

    config = BenchmarkConfig(warmup_iterations=1, benchmark_iterations=3)
    results = []

    # BM25 Creation
    documents = generate_documents(200)
    texts = [d["text"] for d in documents]

    async def bm25_create():
        await create_bm25_retriever(texts)

    result = await run_benchmark(bm25_create, config)
    result.name = "bm25_create"
    results.append(result)

    # BM25 Search
    retriever = await create_bm25_retriever(texts)

    async def bm25_search():
        await retriever.asearch("test query", top_k=10)

    result = await run_benchmark(bm25_search, config)
    result.name = "bm25_search"
    results.append(result)

    # RRF Fusion
    import random

    doc_ids = [f"doc_{i}" for i in range(50)]
    rankings = [
        [(doc_id, random.random()) for doc_id in random.sample(doc_ids, 30)] for _ in range(2)
    ]
    rrf = ReciprocalRankFusion()

    async def rrf_fuse():
        await rrf.fuse(rankings, top_k=10)

    result = await run_benchmark(rrf_fuse, config)
    result.name = "rrf_fuse"
    results.append(result)

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r}")
    print("=" * 60)
