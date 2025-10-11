"""Comprehensive performance benchmarking suite."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    description: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_time: float
    min_time: float
    max_time: float
    p50_time: float
    p95_time: float
    p99_time: float
    std_dev: float
    throughput: float  # ops/sec
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "avg_time_ms": self.avg_time * 1000,
            "min_time_ms": self.min_time * 1000,
            "max_time_ms": self.max_time * 1000,
            "p50_time_ms": self.p50_time * 1000,
            "p95_time_ms": self.p95_time * 1000,
            "p99_time_ms": self.p99_time * 1000,
            "std_dev_ms": self.std_dev * 1000,
            "throughput_ops_sec": self.throughput,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class BenchmarkSuite:
    """Performance benchmarking suite."""

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize benchmark suite.

        Args:
            output_dir: Directory to save results
        """
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[BenchmarkResult] = []
        logger.info(f"BenchmarkSuite initialized (output: {self.output_dir})")

    async def run_async_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        description: str = "",
        **kwargs: Any,
    ) -> BenchmarkResult:
        """Run async function benchmark.

        Args:
            name: Benchmark name
            func: Async function to benchmark
            iterations: Number of iterations
            warmup: Warmup iterations
            description: Benchmark description
            **kwargs: Arguments for the function

        Returns:
            BenchmarkResult
        """
        logger.info(f"Starting benchmark: {name} ({iterations} iterations)")

        # Warmup
        for _ in range(warmup):
            try:
                await func(**kwargs)
            except Exception as e:
                logger.warning(f"Warmup error: {e}")

        # Actual benchmark
        times: list[float] = []
        successful = 0
        failed = 0

        start_time = time.time()

        for i in range(iterations):
            iter_start = time.time()
            try:
                await func(**kwargs)
                iter_time = time.time() - iter_start
                times.append(iter_time)
                successful += 1
            except Exception as e:
                logger.error(f"Iteration {i} failed: {e}")
                failed += 1

        total_time = time.time() - start_time

        # Calculate statistics
        if times:
            times_array = np.array(times)
            result = BenchmarkResult(
                name=name,
                description=description,
                total_runs=iterations,
                successful_runs=successful,
                failed_runs=failed,
                avg_time=float(np.mean(times_array)),
                min_time=float(np.min(times_array)),
                max_time=float(np.max(times_array)),
                p50_time=float(np.percentile(times_array, 50)),
                p95_time=float(np.percentile(times_array, 95)),
                p99_time=float(np.percentile(times_array, 99)),
                std_dev=float(np.std(times_array)),
                throughput=successful / total_time if total_time > 0 else 0,
                metadata={"warmup": warmup, "kwargs": str(kwargs)},
            )
        else:
            result = BenchmarkResult(
                name=name,
                description=description,
                total_runs=iterations,
                successful_runs=0,
                failed_runs=failed,
                avg_time=0.0,
                min_time=0.0,
                max_time=0.0,
                p50_time=0.0,
                p95_time=0.0,
                p99_time=0.0,
                std_dev=0.0,
                throughput=0.0,
            )

        self.results.append(result)
        self._log_result(result)

        return result

    def run_sync_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        description: str = "",
        **kwargs: Any,
    ) -> BenchmarkResult:
        """Run synchronous function benchmark.

        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Warmup iterations
            description: Benchmark description
            **kwargs: Arguments for the function

        Returns:
            BenchmarkResult
        """
        logger.info(f"Starting benchmark: {name} ({iterations} iterations)")

        # Warmup
        for _ in range(warmup):
            try:
                func(**kwargs)
            except Exception as e:
                logger.warning(f"Warmup error: {e}")

        # Actual benchmark
        times: list[float] = []
        successful = 0
        failed = 0

        start_time = time.time()

        for i in range(iterations):
            iter_start = time.time()
            try:
                func(**kwargs)
                iter_time = time.time() - iter_start
                times.append(iter_time)
                successful += 1
            except Exception as e:
                logger.error(f"Iteration {i} failed: {e}")
                failed += 1

        total_time = time.time() - start_time

        # Calculate statistics
        if times:
            times_array = np.array(times)
            result = BenchmarkResult(
                name=name,
                description=description,
                total_runs=iterations,
                successful_runs=successful,
                failed_runs=failed,
                avg_time=float(np.mean(times_array)),
                min_time=float(np.min(times_array)),
                max_time=float(np.max(times_array)),
                p50_time=float(np.percentile(times_array, 50)),
                p95_time=float(np.percentile(times_array, 95)),
                p99_time=float(np.percentile(times_array, 99)),
                std_dev=float(np.std(times_array)),
                throughput=successful / total_time if total_time > 0 else 0,
                metadata={"warmup": warmup, "kwargs": str(kwargs)},
            )
        else:
            result = BenchmarkResult(
                name=name,
                description=description,
                total_runs=iterations,
                successful_runs=0,
                failed_runs=failed,
                avg_time=0.0,
                min_time=0.0,
                max_time=0.0,
                p50_time=0.0,
                p95_time=0.0,
                p99_time=0.0,
                std_dev=0.0,
                throughput=0.0,
            )

        self.results.append(result)
        self._log_result(result)

        return result

    def _log_result(self, result: BenchmarkResult) -> None:
        """Log benchmark result."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Benchmark: {result.name}")
        logger.info(f"Description: {result.description}")
        logger.info(f"Total runs: {result.total_runs}")
        logger.info(f"Success: {result.successful_runs}, Failed: {result.failed_runs}")
        logger.info(f"Avg time: {result.avg_time * 1000:.2f} ms")
        logger.info(f"Min time: {result.min_time * 1000:.2f} ms")
        logger.info(f"Max time: {result.max_time * 1000:.2f} ms")
        logger.info(f"P50: {result.p50_time * 1000:.2f} ms")
        logger.info(f"P95: {result.p95_time * 1000:.2f} ms")
        logger.info(f"P99: {result.p99_time * 1000:.2f} ms")
        logger.info(f"Throughput: {result.throughput:.2f} ops/sec")
        logger.info(f"{'=' * 60}\n")

    def save_results(self, filename: str = "benchmark_results.json") -> Path:
        """Save results to JSON file.

        Args:
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename

        results_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_benchmarks": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"Results saved to: {output_path}")
        return output_path

    def generate_report(self) -> str:
        """Generate human-readable benchmark report.

        Returns:
            Report string
        """
        lines = [
            "=" * 80,
            "PERFORMANCE BENCHMARK REPORT",
            "=" * 80,
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Total Benchmarks: {len(self.results)}",
            "",
        ]

        for result in self.results:
            lines.extend(
                [
                    f"\n{result.name}",
                    "-" * 80,
                    f"Description: {result.description}",
                    f"Runs: {result.successful_runs}/{result.total_runs} successful",
                    f"Average: {result.avg_time * 1000:.2f} ms",
                    f"P50: {result.p50_time * 1000:.2f} ms",
                    f"P95: {result.p95_time * 1000:.2f} ms",
                    f"P99: {result.p99_time * 1000:.2f} ms",
                    f"Throughput: {result.throughput:.2f} ops/sec",
                ]
            )

        lines.append("\n" + "=" * 80)

        report = "\n".join(lines)

        # Save report
        report_path = self.output_dir / "benchmark_report.txt"
        report_path.write_text(report, encoding="utf-8")

        logger.info(f"Report saved to: {report_path}")

        return report

    def compare_with_baseline(self, baseline_file: Path, threshold: float = 1.2) -> dict[str, Any]:
        """Compare results with baseline.

        Args:
            baseline_file: Path to baseline results
            threshold: Performance degradation threshold (1.2 = 20% slower)

        Returns:
            Comparison results
        """
        with baseline_file.open("r", encoding="utf-8") as f:
            baseline_data = json.load(f)

        baseline_results = {r["name"]: r for r in baseline_data["results"]}

        comparison = {"regressions": [], "improvements": [], "unchanged": []}

        for result in self.results:
            if result.name not in baseline_results:
                continue

            baseline = baseline_results[result.name]
            current_avg = result.avg_time * 1000
            baseline_avg = baseline["avg_time_ms"]

            ratio = current_avg / baseline_avg if baseline_avg > 0 else 0

            if ratio > threshold:
                comparison["regressions"].append(
                    {
                        "name": result.name,
                        "baseline_ms": baseline_avg,
                        "current_ms": current_avg,
                        "ratio": ratio,
                        "degradation_pct": (ratio - 1) * 100,
                    }
                )
            elif ratio < (1 / threshold):
                comparison["improvements"].append(
                    {
                        "name": result.name,
                        "baseline_ms": baseline_avg,
                        "current_ms": current_avg,
                        "ratio": ratio,
                        "improvement_pct": (1 - ratio) * 100,
                    }
                )
            else:
                comparison["unchanged"].append({"name": result.name, "ratio": ratio})

        return comparison
