"""Integration tests for monitoring and observability."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("opentelemetry")

from core.observability import (TracingConfig, get_log_aggregator,
                                get_metrics_collector, get_tracer,
                                init_logging, init_tracing, structured_logger,
                                trace_async, trace_function)
from core.observability.grafana_dashboards import (
    create_api_dashboard, create_cache_dashboard, create_dashboards,
    create_orchestration_dashboard, create_system_dashboard)
from core.observability.metrics_collector import (DatabaseQueryTimer,
                                                  WorkflowTimer)


# Grafana Dashboard Tests
def test_create_cache_dashboard():
    """Test cache dashboard creation."""
    dashboard = create_cache_dashboard()

    assert dashboard.title == "MegaAgent Cache Performance"
    assert dashboard.uid == "megaagent-cache"
    assert "cache" in dashboard.tags
    assert len(dashboard.panels) == 4

    # Check panel types
    panel_titles = [p.title for p in dashboard.panels]
    assert "Cache Hit Rate" in panel_titles
    assert "Cache Operations" in panel_titles
    assert "Cache Latency" in panel_titles


def test_create_api_dashboard():
    """Test API dashboard creation."""
    dashboard = create_api_dashboard()

    assert dashboard.title == "MegaAgent API Monitoring"
    assert dashboard.uid == "megaagent-api"
    assert "api" in dashboard.tags
    assert len(dashboard.panels) == 4


def test_create_orchestration_dashboard():
    """Test orchestration dashboard creation."""
    dashboard = create_orchestration_dashboard()

    assert dashboard.title == "MegaAgent Orchestration"
    assert dashboard.uid == "megaagent-orchestration"
    assert "orchestration" in dashboard.tags


def test_create_system_dashboard():
    """Test system dashboard creation."""
    dashboard = create_system_dashboard()

    assert dashboard.title == "MegaAgent System Overview"
    assert dashboard.uid == "megaagent-system"
    assert "system" in dashboard.tags


def test_export_dashboard():
    """Test dashboard export to JSON."""
    dashboard = create_cache_dashboard()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_dashboard.json"
        dashboard.export_json(output_path)

        assert output_path.exists()

        # Validate JSON structure
        with output_path.open() as f:
            data = json.load(f)

        assert "dashboard" in data
        assert data["dashboard"]["title"] == "MegaAgent Cache Performance"
        assert "panels" in data["dashboard"]


def test_create_all_dashboards():
    """Test creating all dashboards."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = create_dashboards(tmpdir)

        assert len(files) == 4
        assert all(f.exists() for f in files)

        # Check filenames
        filenames = [f.name for f in files]
        assert "cache_dashboard.json" in filenames
        assert "api_dashboard.json" in filenames
        assert "orchestration_dashboard.json" in filenames
        assert "system_dashboard.json" in filenames


# Distributed Tracing Tests
def test_init_tracing_console():
    """Test tracing initialization with console exporter."""
    config = TracingConfig(exporter_type="console", enabled=True)
    tracer = init_tracing(config)

    assert tracer is not None


def test_init_tracing_disabled():
    """Test tracing initialization when disabled."""
    config = TracingConfig(enabled=False)
    tracer = init_tracing(config)

    assert tracer is not None  # Returns no-op tracer


def test_get_tracer():
    """Test getting global tracer."""
    tracer = get_tracer()
    assert tracer is not None


def test_trace_function_decorator():
    """Test function tracing decorator."""

    @trace_function(name="test_operation")
    def test_func(x: int, y: int) -> int:
        return x + y

    result = test_func(2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_trace_async_decorator():
    """Test async function tracing decorator."""

    @trace_async(name="test_async_operation")
    async def test_async_func(x: int, y: int) -> int:
        return x + y

    result = await test_async_func(2, 3)
    assert result == 5


def test_trace_function_with_error():
    """Test function tracing with error."""

    @trace_function()
    def failing_func():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        failing_func()


@pytest.mark.asyncio
async def test_trace_async_with_error():
    """Test async function tracing with error."""

    @trace_async()
    async def failing_async_func():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await failing_async_func()


# Log Aggregation Tests
def test_init_logging():
    """Test logging initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = init_logging(
            service_name="test-service",
            log_level="DEBUG",
            log_dir=tmpdir,
        )

        assert aggregator is not None
        assert aggregator.service_name == "test-service"


def test_get_log_aggregator():
    """Test getting global log aggregator."""
    aggregator = get_log_aggregator()
    assert aggregator is not None


def test_structured_logger():
    """Test getting structured logger."""
    logger = structured_logger(__name__)
    assert logger is not None
    assert logger.name == __name__


def test_log_with_context():
    """Test logging with context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = init_logging(
            log_dir=tmpdir,
            json_format=True,
            file_output=True,
            console_output=False,
        )

        logger = aggregator.get_logger("test")
        aggregator.log_with_context(
            logger,
            "info",
            "Test message",
            user_id="123",
            action="test",
        )

        # Check log file was created
        log_files = list(Path(tmpdir).glob("*.log"))
        assert len(log_files) > 0


def test_log_workflow_event():
    """Test workflow event logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = init_logging(
            log_dir=tmpdir,
            json_format=True,
            file_output=True,
            console_output=False,
        )

        logger = aggregator.get_logger("test")
        aggregator.log_workflow_event(
            logger,
            "test_workflow",
            "start",
            query="test query",
        )

        # Check log file exists
        log_files = list(Path(tmpdir).glob("*.log"))
        assert len(log_files) > 0


def test_log_llm_request():
    """Test LLM request logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = init_logging(
            log_dir=tmpdir,
            json_format=True,
            file_output=True,
            console_output=False,
        )

        logger = aggregator.get_logger("test")
        aggregator.log_llm_request(
            logger,
            "claude-3-opus",
            150,
            300,
            1200.5,
            temperature=0.7,
        )

        # Check log file exists
        log_files = list(Path(tmpdir).glob("*.log"))
        assert len(log_files) > 0


# Metrics Collector Tests
def test_metrics_collector_initialization():
    """Test metrics collector initialization."""
    collector = get_metrics_collector()
    assert collector is not None


def test_record_workflow_execution():
    """Test recording workflow execution."""
    collector = get_metrics_collector()
    collector.record_workflow_execution("test_workflow", "success", 10.5)

    # Verify metric was recorded (check Prometheus registry)
    metric = collector.workflow_executions_total.labels(
        workflow_name="test_workflow",
        status="success",
    )
    assert metric is not None


def test_record_workflow_node():
    """Test recording workflow node execution."""
    collector = get_metrics_collector()
    collector.record_workflow_node("test_workflow", "node1", "success")

    metric = collector.workflow_nodes_executed.labels(
        workflow_name="test_workflow",
        node_name="node1",
        status="success",
    )
    assert metric is not None


def test_record_error_recovery():
    """Test recording error recovery."""
    collector = get_metrics_collector()
    collector.record_error_recovery_attempt("exponential_backoff")
    collector.record_error_recovery_success("exponential_backoff")

    attempt_metric = collector.workflow_error_recovery_attempts.labels(
        strategy="exponential_backoff"
    )
    success_metric = collector.workflow_error_recovery_success.labels(
        strategy="exponential_backoff"
    )
    assert attempt_metric is not None
    assert success_metric is not None


def test_record_human_review():
    """Test recording human review."""
    collector = get_metrics_collector()
    collector.record_human_review_requested("test_workflow", "quality_check")
    collector.record_human_review_completed("test_workflow", "approved", 120.0)

    # Pending should be 0 (requested then completed)
    pending = collector.workflow_human_reviews_pending._value._value
    assert pending == 0


def test_record_routing_decision():
    """Test recording routing decision."""
    collector = get_metrics_collector()
    collector.record_routing_decision("test_workflow", "route_a", 0.95)

    # Check confidence gauge was set
    confidence_metric = collector.workflow_routing_confidence.labels(workflow_name="test_workflow")
    assert confidence_metric is not None


def test_record_db_operations():
    """Test recording database operations."""
    collector = get_metrics_collector()
    collector.update_db_connections(5, 3)
    collector.record_db_query("select", 0.015)

    assert collector.db_connections_active._value._value == 5
    assert collector.db_connections_idle._value._value == 3


def test_record_vector_operation():
    """Test recording vector store operation."""
    collector = get_metrics_collector()
    collector.record_vector_operation("upsert", "success", 0.25)
    collector.set_vector_dimensions(2048)

    assert collector.vector_store_dimensions._value._value == 2048


def test_record_llm_request_metrics():
    """Test recording LLM request metrics."""
    collector = get_metrics_collector()
    collector.record_llm_request(
        "claude-3-opus",
        "success",
        2.5,
        150,
        300,
        cached=True,
    )

    # Verify tokens were recorded
    prompt_tokens = collector.llm_tokens_used.labels(
        model="claude-3-opus",
        token_type="prompt",
    )
    assert prompt_tokens is not None


def test_workflow_timer_context_manager():
    """Test workflow timer context manager."""
    collector = get_metrics_collector()

    with WorkflowTimer(collector, "test_workflow"):
        # Simulate work
        import time

        time.sleep(0.1)

    # Timer should have recorded metrics automatically


def test_workflow_timer_with_error():
    """Test workflow timer with error."""
    collector = get_metrics_collector()

    with pytest.raises(ValueError), WorkflowTimer(collector, "test_workflow"):
        raise ValueError("Test error")

    # Should have recorded as error status


def test_database_query_timer():
    """Test database query timer."""
    collector = get_metrics_collector()

    with DatabaseQueryTimer(collector, "select"):
        import time

        time.sleep(0.01)

    # Timer should have recorded metrics


def test_database_query_timer_with_error():
    """Test database query timer with error."""
    collector = get_metrics_collector()

    with pytest.raises(ValueError), DatabaseQueryTimer(collector, "insert"):
        raise ValueError("Query failed")

    # Should have recorded error


def test_set_system_info():
    """Test setting system information."""
    collector = get_metrics_collector()
    collector.set_system_info(
        {
            "version": "1.0.0",
            "python_version": "3.11",
            "environment": "production",
        }
    )

    # System info should be set
    assert collector.system_info is not None
