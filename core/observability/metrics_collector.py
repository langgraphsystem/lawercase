"""Enhanced Metrics Collector with Prometheus.

This module extends the existing Prometheus metrics with workflow-specific
metrics and provides a centralized metrics collection API.
"""

from __future__ import annotations

import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info


class MetricsCollector:
    """
    Centralized metrics collector for all system components.

    Provides Prometheus metrics for:
    - Workflow executions
    - Error recovery
    - Human reviews
    - Routing decisions
    - Database operations
    - Vector store operations
    - LLM requests
    - System resources
    """

    def __init__(self):
        """Initialize all Prometheus metrics."""
        # Workflow metrics
        self.workflow_executions_total = Counter(
            "workflow_executions_total",
            "Total workflow executions",
            ["workflow_name", "status"],
        )

        self.workflow_duration_seconds = Histogram(
            "workflow_duration_seconds",
            "Workflow execution duration",
            ["workflow_name"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
        )

        self.workflow_nodes_executed = Counter(
            "workflow_nodes_executed_total",
            "Total workflow nodes executed",
            ["workflow_name", "node_name", "status"],
        )

        # Error recovery metrics
        self.workflow_error_recovery_attempts = Counter(
            "workflow_error_recovery_attempts_total",
            "Total error recovery attempts",
            ["strategy"],
        )

        self.workflow_error_recovery_success = Counter(
            "workflow_error_recovery_success_total",
            "Successful error recoveries",
            ["strategy"],
        )

        # Human review metrics
        self.workflow_human_reviews_requested = Counter(
            "workflow_human_reviews_requested_total",
            "Total human reviews requested",
            ["workflow_name", "reason"],
        )

        self.workflow_human_reviews_pending = Gauge(
            "workflow_human_reviews_pending",
            "Number of pending human reviews",
        )

        self.workflow_human_reviews_completed = Counter(
            "workflow_human_reviews_completed_total",
            "Total human reviews completed",
            ["workflow_name", "decision"],
        )

        self.workflow_human_review_duration_seconds = Histogram(
            "workflow_human_review_duration_seconds",
            "Human review duration",
            ["workflow_name"],
            buckets=[60, 300, 900, 1800, 3600, 7200],  # 1min to 2hr
        )

        # Routing metrics
        self.workflow_routing_confidence = Gauge(
            "workflow_routing_confidence",
            "Current routing confidence score",
            ["workflow_name"],
        )

        self.workflow_routes_taken = Counter(
            "workflow_routes_taken_total",
            "Total routes taken",
            ["workflow_name", "route"],
        )

        # Database metrics
        self.db_connections_active = Gauge(
            "db_connections_active",
            "Number of active database connections",
        )

        self.db_connections_idle = Gauge(
            "db_connections_idle",
            "Number of idle database connections",
        )

        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query duration",
            ["operation"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5],
        )

        self.db_query_errors = Counter(
            "db_query_errors_total",
            "Database query errors",
            ["operation", "error_type"],
        )

        # Vector store metrics
        self.vector_store_operations = Counter(
            "vector_store_operations_total",
            "Vector store operations",
            ["operation", "status"],
        )

        self.vector_store_duration_seconds = Histogram(
            "vector_store_duration_seconds",
            "Vector store operation duration",
            ["operation"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
        )

        self.vector_store_dimensions = Gauge(
            "vector_store_dimensions",
            "Vector dimensions",
        )

        # LLM metrics
        self.llm_requests = Counter(
            "llm_requests_total",
            "Total LLM requests",
            ["model", "status"],
        )

        self.llm_request_duration_seconds = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration",
            ["model"],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )

        self.llm_tokens_used = Counter(
            "llm_tokens_used_total",
            "Total tokens used",
            ["model", "token_type"],
        )

        self.llm_cache_hits = Counter(
            "llm_cache_hits_total",
            "LLM cache hits",
            ["model"],
        )

        # System metrics
        self.system_info = Info(
            "megaagent_system_info",
            "System information",
        )

    # Workflow methods
    def record_workflow_execution(
        self,
        workflow_name: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """
        Record a workflow execution.

        Args:
            workflow_name: Name of the workflow
            status: Execution status (success, error, timeout)
            duration_seconds: Execution duration

        Example:
            >>> collector = get_metrics_collector()
            >>> collector.record_workflow_execution("research", "success", 12.5)
        """
        self.workflow_executions_total.labels(
            workflow_name=workflow_name,
            status=status,
        ).inc()

        self.workflow_duration_seconds.labels(
            workflow_name=workflow_name,
        ).observe(duration_seconds)

    def record_workflow_node(
        self,
        workflow_name: str,
        node_name: str,
        status: str,
    ) -> None:
        """Record workflow node execution."""
        self.workflow_nodes_executed.labels(
            workflow_name=workflow_name,
            node_name=node_name,
            status=status,
        ).inc()

    # Error recovery methods
    def record_error_recovery_attempt(self, strategy: str) -> None:
        """Record an error recovery attempt."""
        self.workflow_error_recovery_attempts.labels(strategy=strategy).inc()

    def record_error_recovery_success(self, strategy: str) -> None:
        """Record a successful error recovery."""
        self.workflow_error_recovery_success.labels(strategy=strategy).inc()

    # Human review methods
    def record_human_review_requested(
        self,
        workflow_name: str,
        reason: str,
    ) -> None:
        """Record a human review request."""
        self.workflow_human_reviews_requested.labels(
            workflow_name=workflow_name,
            reason=reason,
        ).inc()
        self.workflow_human_reviews_pending.inc()

    def record_human_review_completed(
        self,
        workflow_name: str,
        decision: str,
        duration_seconds: float,
    ) -> None:
        """Record a completed human review."""
        self.workflow_human_reviews_completed.labels(
            workflow_name=workflow_name,
            decision=decision,
        ).inc()

        self.workflow_human_review_duration_seconds.labels(
            workflow_name=workflow_name,
        ).observe(duration_seconds)

        self.workflow_human_reviews_pending.dec()

    # Routing methods
    def record_routing_decision(
        self,
        workflow_name: str,
        route: str,
        confidence: float,
    ) -> None:
        """Record a routing decision."""
        self.workflow_routing_confidence.labels(
            workflow_name=workflow_name,
        ).set(confidence)

        self.workflow_routes_taken.labels(
            workflow_name=workflow_name,
            route=route,
        ).inc()

    # Database methods
    def update_db_connections(self, active: int, idle: int) -> None:
        """Update database connection counts."""
        self.db_connections_active.set(active)
        self.db_connections_idle.set(idle)

    def record_db_query(
        self,
        operation: str,
        duration_seconds: float,
        error: Exception | None = None,
    ) -> None:
        """Record a database query."""
        self.db_query_duration_seconds.labels(operation=operation).observe(duration_seconds)

        if error:
            self.db_query_errors.labels(
                operation=operation,
                error_type=type(error).__name__,
            ).inc()

    # Vector store methods
    def record_vector_operation(
        self,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record a vector store operation."""
        self.vector_store_operations.labels(
            operation=operation,
            status=status,
        ).inc()

        self.vector_store_duration_seconds.labels(operation=operation).observe(duration_seconds)

    def set_vector_dimensions(self, dimensions: int) -> None:
        """Set vector dimensions."""
        self.vector_store_dimensions.set(dimensions)

    # LLM methods
    def record_llm_request(
        self,
        model: str,
        status: str,
        duration_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        cached: bool = False,
    ) -> None:
        """Record an LLM request."""
        self.llm_requests.labels(model=model, status=status).inc()

        self.llm_request_duration_seconds.labels(model=model).observe(duration_seconds)

        self.llm_tokens_used.labels(model=model, token_type="prompt").inc(  # nosec B106
            prompt_tokens
        )
        self.llm_tokens_used.labels(model=model, token_type="completion").inc(  # nosec B106
            completion_tokens
        )

        if cached:
            self.llm_cache_hits.labels(model=model).inc()

    # System methods
    def set_system_info(self, info: dict[str, Any]) -> None:
        """Set system information."""
        self.system_info.info(info)


# Context managers for automatic timing
class WorkflowTimer:
    """Context manager for timing workflows."""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        workflow_name: str,
    ):
        """Initialize workflow timer."""
        self.collector = metrics_collector
        self.workflow_name = workflow_name
        self.start_time = None
        self.status = "success"

    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timer and record metrics."""
        duration = time.time() - self.start_time

        if exc_type is not None:
            self.status = "error"

        self.collector.record_workflow_execution(
            self.workflow_name,
            self.status,
            duration,
        )

    def set_status(self, status: str) -> None:
        """Set workflow status."""
        self.status = status


class DatabaseQueryTimer:
    """Context manager for timing database queries."""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        operation: str,
    ):
        """Initialize query timer."""
        self.collector = metrics_collector
        self.operation = operation
        self.start_time = None
        self.error = None

    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timer and record metrics."""
        duration = time.time() - self.start_time

        if exc_type is not None:
            self.error = exc_val

        self.collector.record_db_query(
            self.operation,
            duration,
            self.error,
        )


# Global singleton
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get global metrics collector instance.

    Returns:
        MetricsCollector instance

    Example:
        >>> collector = get_metrics_collector()
        >>> collector.record_workflow_execution("research", "success", 10.5)
    """
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()

    return _metrics_collector
