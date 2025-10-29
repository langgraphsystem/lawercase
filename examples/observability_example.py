"""Observability System Examples.

This module demonstrates how to use the complete monitoring and observability
system including:
- Prometheus metrics
- Grafana dashboards
- Distributed tracing
- Structured logging
"""

from __future__ import annotations

import asyncio
import time

from core.observability import (
    TracingConfig,
    get_metrics_collector,
    init_logging,
    init_tracing,
    structured_logger,
    trace_async,
    trace_function,
)
from core.observability.distributed_tracing import (
    TracingContext,
    add_span_event,
    set_span_attribute,
)
from core.observability.grafana_dashboards import create_dashboards
from core.observability.metrics_collector import DatabaseQueryTimer, WorkflowTimer


# Example 1: Basic Metrics Collection
def example_basic_metrics():
    """Demonstrate basic metrics collection."""
    print("\n=== Example 1: Basic Metrics Collection ===\n")

    # Get metrics collector
    collector = get_metrics_collector()

    # Record workflow execution
    collector.record_workflow_execution(
        workflow_name="research_workflow",
        status="success",
        duration_seconds=15.5,
    )

    # Record workflow nodes
    collector.record_workflow_node("research_workflow", "analyze_query", "success")
    collector.record_workflow_node("research_workflow", "search_documents", "success")
    collector.record_workflow_node("research_workflow", "generate_answer", "success")

    # Record error recovery
    collector.record_error_recovery_attempt("exponential_backoff")
    collector.record_error_recovery_success("exponential_backoff")

    # Record human review
    collector.record_human_review_requested("research_workflow", "quality_check")
    # ... later ...
    collector.record_human_review_completed("research_workflow", "approved", 120.0)

    # Record routing decision
    collector.record_routing_decision("research_workflow", "expert_route", 0.92)

    # Record database operations
    collector.update_db_connections(active=8, idle=2)
    collector.record_db_query("select", duration_seconds=0.015)

    # Record vector store operations
    collector.record_vector_operation("upsert", "success", 0.25)
    collector.set_vector_dimensions(2048)

    # Record LLM requests
    collector.record_llm_request(
        model="claude-3-opus",
        status="success",
        duration_seconds=2.5,
        prompt_tokens=150,
        completion_tokens=300,
        cached=False,
    )

    print("✅ Metrics recorded successfully")
    print("📊 View metrics at: http://localhost:9090 (Prometheus)")
    print("📈 View dashboards at: http://localhost:3000 (Grafana)")


# Example 2: Workflow Timer Context Manager
def example_workflow_timer():
    """Demonstrate workflow timer context manager."""
    print("\n=== Example 2: Workflow Timer Context Manager ===\n")

    collector = get_metrics_collector()

    # Automatically time workflow execution
    with WorkflowTimer(collector, "data_processing_workflow") as timer:
        print("Starting workflow...")
        time.sleep(0.5)

        # Simulate successful processing
        print("Processing data...")
        time.sleep(1.0)

        print("Workflow completed")
        timer.set_status("success")

    print("✅ Workflow metrics recorded automatically")


# Example 3: Database Query Timer
def example_database_timer():
    """Demonstrate database query timer."""
    print("\n=== Example 3: Database Query Timer ===\n")

    collector = get_metrics_collector()

    # Automatically time database queries
    with DatabaseQueryTimer(collector, "select_users"):
        print("Executing database query...")
        time.sleep(0.05)
        print("Query completed")

    # Timer with error
    try:
        with DatabaseQueryTimer(collector, "insert_user"):
            print("Executing failing query...")
            raise ValueError("Database connection error")
    except ValueError:
        print("Query failed (error recorded in metrics)")

    print("✅ Database metrics recorded automatically")


# Example 4: Distributed Tracing
@trace_function(name="calculate_result")
def sync_calculation(x: int, y: int) -> int:
    """Example traced synchronous function."""
    set_span_attribute("calculation.inputs", f"{x}, {y}")
    result = x + y
    set_span_attribute("calculation.result", result)
    add_span_event("calculation_completed", {"result": result})
    return result


@trace_async(name="fetch_data")
async def async_fetch_data(query: str) -> dict:
    """Example traced async function."""
    set_span_attribute("query", query)
    add_span_event("fetch_started")

    # Simulate async work
    await asyncio.sleep(0.1)

    result = {"data": f"Results for {query}"}
    add_span_event("fetch_completed", {"result_count": 1})
    return result


def example_distributed_tracing():
    """Demonstrate distributed tracing."""
    print("\n=== Example 4: Distributed Tracing ===\n")

    # Initialize tracing (console exporter for demo)
    config = TracingConfig(exporter_type="console", enabled=True)
    init_tracing(config)

    # Traced function call
    print("Calling traced function...")
    result = sync_calculation(10, 20)
    print(f"Result: {result}")

    # Traced async function call
    print("\nCalling traced async function...")
    asyncio.run(async_fetch_data("test query"))

    # Manual span creation
    print("\nManual span creation...")
    with TracingContext("manual_operation", {"operation_type": "test"}) as span:
        span.set_attribute("step", 1)
        time.sleep(0.1)
        span.add_event("step_1_completed")

        span.set_attribute("step", 2)
        time.sleep(0.1)
        span.add_event("step_2_completed")

    print("✅ Traces recorded successfully")
    print("🔍 View traces at:")
    print("   - Jaeger: http://localhost:16686")
    print("   - Zipkin: http://localhost:9411")


# Example 5: Structured Logging
def example_structured_logging():
    """Demonstrate structured logging."""
    print("\n=== Example 5: Structured Logging ===\n")

    # Initialize logging
    aggregator = init_logging(
        service_name="megaagent-demo",
        log_level="INFO",
        console_output=True,
        file_output=True,
        json_format=True,
        log_dir="logs",
    )

    # Get logger
    logger = structured_logger(__name__)

    # Basic logging
    logger.info("Application started")

    # Log with context
    aggregator.log_with_context(
        logger,
        "info",
        "User action",
        user_id="user_123",
        action="query",
        ip_address="192.168.1.100",
    )

    # Log workflow event
    aggregator.log_workflow_event(
        logger,
        "research_workflow",
        "started",
        query="What is machine learning?",
        user_id="user_123",
    )

    # Log LLM request
    aggregator.log_llm_request(
        logger,
        model="claude-3-opus",
        prompt_tokens=150,
        completion_tokens=300,
        latency_ms=2500.0,
        temperature=0.7,
        cached=False,
    )

    # Log cache operation
    aggregator.log_cache_operation(
        logger,
        operation="get",
        hit=True,
        latency_ms=2.5,
        key="user:123:profile",
        semantic=False,
    )

    # Log with trace context
    config = TracingConfig(exporter_type="console", enabled=True)
    init_tracing(config)

    with TracingContext("traced_operation"):
        logger.info("This log includes trace context")

    print("✅ Logs written to logs/megaagent-demo.log")
    print("📝 View logs with: tail -f logs/megaagent-demo.log")


# Example 6: Grafana Dashboards
def example_grafana_dashboards():
    """Demonstrate Grafana dashboard creation."""
    print("\n=== Example 6: Grafana Dashboards ===\n")

    # Create all dashboards
    print("Creating Grafana dashboards...")
    dashboard_files = create_dashboards("grafana_dashboards")

    print(f"✅ Created {len(dashboard_files)} dashboards:")
    for file_path in dashboard_files:
        print(f"   📊 {file_path}")

    print("\n📈 To use these dashboards:")
    print("   1. Start Grafana: docker run -d -p 3000:3000 grafana/grafana")
    print("   2. Access Grafana: http://localhost:3000")
    print("   3. Login with admin/admin")
    print("   4. Add Prometheus data source: http://localhost:9090")
    print("   5. Import dashboards from JSON files")


# Example 7: Complete Integration
@trace_async(name="complete_workflow")
async def complete_workflow_example():
    """Demonstrate complete observability integration."""
    print("\n=== Example 7: Complete Integration ===\n")

    # Initialize all observability systems
    init_tracing(TracingConfig(exporter_type="console"))
    aggregator = init_logging(log_level="INFO", json_format=True)
    collector = get_metrics_collector()
    logger = structured_logger(__name__)

    # Start workflow with full observability
    with WorkflowTimer(collector, "complete_workflow") as timer:
        # Log workflow start
        aggregator.log_workflow_event(logger, "complete_workflow", "started", user_id="user_123")

        # Simulate workflow steps with tracing
        with TracingContext("step_1_query_analysis") as span:
            span.set_attribute("query", "What is AI?")
            add_span_event("analysis_started")

            # Log step
            logger.info("Analyzing query")

            # Simulate work
            await asyncio.sleep(0.5)

            # Record node execution
            collector.record_workflow_node("complete_workflow", "query_analysis", "success")

            add_span_event("analysis_completed")

        # Simulate LLM call
        with TracingContext("step_2_llm_call") as span:
            span.set_attribute("model", "claude-3-opus")

            logger.info("Calling LLM")

            start_time = time.time()
            await asyncio.sleep(1.0)
            duration = time.time() - start_time

            # Record LLM metrics
            collector.record_llm_request(
                model="claude-3-opus",
                status="success",
                duration_seconds=duration,
                prompt_tokens=150,
                completion_tokens=300,
                cached=False,
            )

            # Log LLM request
            aggregator.log_llm_request(
                logger,
                model="claude-3-opus",
                prompt_tokens=150,
                completion_tokens=300,
                latency_ms=duration * 1000,
            )

            collector.record_workflow_node("complete_workflow", "llm_call", "success")

        # Simulate cache operation
        with TracingContext("step_3_cache_store"):
            logger.info("Storing in cache")
            await asyncio.sleep(0.1)

            aggregator.log_cache_operation(logger, "set", True, 5.0, key="result:123")

        # Workflow completed
        timer.set_status("success")
        aggregator.log_workflow_event(
            logger, "complete_workflow", "completed", duration_seconds=1.6
        )

    print("✅ Complete workflow executed with full observability")
    print("   - Metrics: Recorded in Prometheus")
    print("   - Traces: Exported to tracing backend")
    print("   - Logs: Written to logs/megaagent-pro.log")


# Main execution
def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  MegaAgent Pro - Observability System Examples")
    print("=" * 60)

    # Run examples
    example_basic_metrics()
    example_workflow_timer()
    example_database_timer()
    example_distributed_tracing()
    example_structured_logging()
    example_grafana_dashboards()

    # Run async example
    asyncio.run(complete_workflow_example())

    print("\n" + "=" * 60)
    print("  All Examples Completed Successfully! ✅")
    print("=" * 60)
    print("\n📚 Next Steps:")
    print("   1. Start Prometheus: docker run -p 9090:9090 prom/prometheus")
    print("   2. Start Grafana: docker run -p 3000:3000 grafana/grafana")
    print("   3. Start Jaeger: docker run -p 16686:16686 jaegertracing/all-in-one")
    print("   4. Import Grafana dashboards from grafana_dashboards/")
    print("   5. View metrics, traces, and logs in respective UIs")
    print()


if __name__ == "__main__":
    main()
