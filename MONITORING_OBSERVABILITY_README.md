## Monitoring & Observability

Comprehensive monitoring and observability system for MegaAgent Pro with Prometheus metrics, Grafana dashboards, distributed tracing (OpenTelemetry), and structured logging.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Prometheus Metrics](#prometheus-metrics)
6. [Grafana Dashboards](#grafana-dashboards)
7. [Distributed Tracing](#distributed-tracing)
8. [Log Aggregation](#log-aggregation)
9. [Integration Guide](#integration-guide)
10. [Configuration](#configuration)
11. [Docker Setup](#docker-setup)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The monitoring and observability system provides complete visibility into the MegaAgent Pro application with:

- **Prometheus Metrics**: Real-time metrics collection and querying
- **Grafana Dashboards**: Pre-configured dashboards for visualization
- **Distributed Tracing**: Request tracing with OpenTelemetry (Jaeger/Zipkin)
- **Structured Logging**: JSON-formatted logs with trace context

**Status**: ✅ Complete (Phase 3)

---

## Features

### ✅ Prometheus Metrics
- Workflow execution metrics (duration, success/failure rates)
- Error recovery metrics (attempts, success rates by strategy)
- Human review metrics (pending, completed, duration)
- Routing metrics (confidence scores, route distribution)
- Cache metrics (hit rates, latency, semantic vs exact hits)
- API metrics (request rates, latency percentiles, error rates)
- Database metrics (connections, query duration, errors)
- Vector store metrics (operations, dimensions)
- LLM metrics (requests, tokens, cache hits)
- System metrics (memory, connections)

### ✅ Grafana Dashboards
- **Cache Dashboard**: Hit rates, operations, latency, errors
- **API Dashboard**: Request rates, latency, errors, rate limiting
- **Orchestration Dashboard**: Workflow executions, error recovery, human reviews, routing
- **System Dashboard**: Database, memory, vector store, LLM operations

### ✅ Distributed Tracing
- OpenTelemetry integration
- Multiple exporters: Console, Jaeger, Zipkin, OTLP
- Function decorators for automatic tracing
- LangGraph workflow node tracing
- Span events and attributes
- Trace context propagation

### ✅ Structured Logging
- JSON-formatted logs
- Trace context integration (trace_id, span_id in logs)
- Multiple outputs: console, file, syslog
- Log rotation (10MB per file, 5 backups)
- Separate error logs
- Workflow, LLM, and cache operation helpers

---

## Quick Start

### 1. Install Dependencies

```bash
pip install prometheus-client opentelemetry-api opentelemetry-sdk \
    opentelemetry-exporter-jaeger opentelemetry-exporter-zipkin-json \
    opentelemetry-exporter-otlp
```

### 2. Initialize Observability

```python
from core.observability import (
    init_tracing,
    init_logging,
    get_metrics_collector,
    TracingConfig,
)

# Initialize tracing
tracing_config = TracingConfig(
    service_name="megaagent-pro",
    exporter_type="jaeger",  # or "zipkin", "otlp", "console"
    jaeger_host="localhost",
)
init_tracing(tracing_config)

# Initialize logging
init_logging(
    service_name="megaagent-pro",
    log_level="INFO",
    json_format=True,
    log_dir="logs",
)

# Get metrics collector
collector = get_metrics_collector()
```

### 3. Use in Your Code

```python
from core.observability import trace_async, structured_logger
from core.observability.metrics_collector import WorkflowTimer

logger = structured_logger(__name__)
collector = get_metrics_collector()

@trace_async(name="process_query")
async def process_query(query: str):
    with WorkflowTimer(collector, "query_workflow") as timer:
        logger.info("Processing query", extra={"query": query})

        # Your logic here
        result = await do_work(query)

        timer.set_status("success")
        return result
```

### 4. Run the Example

```bash
python examples/observability_example.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Code                      │
│  (Workflows, Agents, API, Cache, Database, etc.)        │
└────────────┬───────────────┬──────────────┬─────────────┘
             │               │              │
             ▼               ▼              ▼
    ┌────────────┐  ┌──────────────┐  ┌──────────┐
    │  Metrics   │  │   Tracing    │  │ Logging  │
    │ Collector  │  │  (OpenTel)   │  │ (JSON)   │
    └─────┬──────┘  └──────┬───────┘  └────┬─────┘
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Prometheus│    │  Jaeger  │    │   File   │
    │  :9090   │    │  Zipkin  │    │  Logs    │
    └─────┬────┘    │  OTLP    │    └────┬─────┘
          │         └──────────┘         │
          ▼                              ▼
    ┌──────────┐                  ┌───────────┐
    │ Grafana  │                  │    ELK    │
    │  :3000   │                  │   Loki    │
    └──────────┘                  └───────────┘
```

---

## Prometheus Metrics

### Workflow Metrics

```python
from core.observability import get_metrics_collector

collector = get_metrics_collector()

# Record workflow execution
collector.record_workflow_execution(
    workflow_name="research_workflow",
    status="success",  # success, error, timeout
    duration_seconds=15.5,
)

# Record workflow node
collector.record_workflow_node(
    workflow_name="research_workflow",
    node_name="analyze_query",
    status="success",
)
```

**Available Metrics:**
- `workflow_executions_total{workflow_name, status}` - Counter
- `workflow_duration_seconds{workflow_name}` - Histogram
- `workflow_nodes_executed_total{workflow_name, node_name, status}` - Counter

### Error Recovery Metrics

```python
# Record error recovery attempt
collector.record_error_recovery_attempt("exponential_backoff")

# Record successful recovery
collector.record_error_recovery_success("exponential_backoff")
```

**Available Metrics:**
- `workflow_error_recovery_attempts_total{strategy}` - Counter
- `workflow_error_recovery_success_total{strategy}` - Counter

### Human Review Metrics

```python
# Request human review
collector.record_human_review_requested(
    workflow_name="research_workflow",
    reason="quality_check",
)

# Complete review
collector.record_human_review_completed(
    workflow_name="research_workflow",
    decision="approved",
    duration_seconds=120.0,
)
```

**Available Metrics:**
- `workflow_human_reviews_requested_total{workflow_name, reason}` - Counter
- `workflow_human_reviews_pending` - Gauge
- `workflow_human_reviews_completed_total{workflow_name, decision}` - Counter
- `workflow_human_review_duration_seconds{workflow_name}` - Histogram

### Cache Metrics

Cache metrics are automatically collected by the existing cache monitoring system.

**Available Metrics:**
- `cache_hits_total` - Counter
- `cache_misses_total` - Counter
- `cache_hit_rate` - Gauge
- `cache_avg_hit_latency_ms` - Gauge

### API Metrics

API metrics are automatically collected by middleware.

**Available Metrics:**
- `mega_agent_http_requests_total{method, path, status}` - Counter
- `mega_agent_http_request_duration_seconds{method, path}` - Histogram
- `mega_agent_rate_limit_rejections_total{key}` - Counter

### Querying Metrics

Example Prometheus queries:

```promql
# Workflow success rate
rate(workflow_executions_total{status="success"}[5m]) /
rate(workflow_executions_total[5m])

# Average workflow duration
histogram_quantile(0.95, workflow_duration_seconds_bucket)

# Cache hit rate
cache_hit_rate

# API latency (p95)
histogram_quantile(0.95, rate(mega_agent_http_request_duration_seconds_bucket[5m]))

# Error recovery success rate
rate(workflow_error_recovery_success_total[5m]) /
rate(workflow_error_recovery_attempts_total[5m])
```

---

## Grafana Dashboards

### Creating Dashboards

```python
from core.observability.grafana_dashboards import create_dashboards

# Create all dashboards
dashboard_files = create_dashboards("grafana_dashboards")

# Creates:
# - grafana_dashboards/cache_dashboard.json
# - grafana_dashboards/api_dashboard.json
# - grafana_dashboards/orchestration_dashboard.json
# - grafana_dashboards/system_dashboard.json
```

### Importing into Grafana

1. Access Grafana: `http://localhost:3000`
2. Login (default: admin/admin)
3. Click **+** → **Import Dashboard**
4. Upload JSON file or paste JSON content
5. Select Prometheus data source
6. Click **Import**

### Available Dashboards

#### 1. Cache Dashboard
- Cache hit rate (stat with color thresholds)
- Cache operations over time (hits, misses, sets)
- Average latency (hit vs miss)
- Error rate graph

#### 2. API Dashboard
- Request rate by method
- Request latency percentiles (p95, p99)
- Error rate by status code
- Rate limit rejections

#### 3. Orchestration Dashboard
- Workflow executions by status
- Error recovery attempts by strategy
- Human reviews pending (gauge)
- Routing confidence (gauge)

#### 4. System Dashboard
- Database connections (active, idle)
- Memory usage
- Vector store operations
- LLM request rate by model

---

## Distributed Tracing

### Configuration

```python
from core.observability import init_tracing, TracingConfig

# Console exporter (development)
config = TracingConfig(exporter_type="console")

# Jaeger exporter (production)
config = TracingConfig(
    exporter_type="jaeger",
    jaeger_host="localhost",
    jaeger_port=6831,
)

# Zipkin exporter
config = TracingConfig(
    exporter_type="zipkin",
    zipkin_endpoint="http://localhost:9411/api/v2/spans",
)

# OTLP exporter
config = TracingConfig(
    exporter_type="otlp",
    otlp_endpoint="localhost:4317",
)

init_tracing(config)
```

### Tracing Functions

```python
from core.observability import trace_function, trace_async

# Trace synchronous function
@trace_function(name="calculate_score")
def calculate_score(data):
    return sum(data) / len(data)

# Trace async function
@trace_async(name="fetch_data")
async def fetch_data(query):
    return await database.query(query)
```

### Manual Spans

```python
from core.observability.distributed_tracing import (
    TracingContext,
    add_span_event,
    set_span_attribute,
)

with TracingContext("complex_operation") as span:
    span.set_attribute("user_id", "123")
    span.add_event("operation_started")

    # Do work
    result = process_data()

    span.set_attribute("result_count", len(result))
    span.add_event("operation_completed")
```

### LangGraph Node Tracing

```python
from core.observability.distributed_tracing import trace_workflow_node

@trace_workflow_node("analyze_query")
async def analyze_query(state: WorkflowState):
    # Automatically traced with workflow context
    return {"analysis": "..."}
```

### Viewing Traces

**Jaeger UI**: `http://localhost:16686`
**Zipkin UI**: `http://localhost:9411`

---

## Log Aggregation

### Configuration

```python
from core.observability import init_logging

aggregator = init_logging(
    service_name="megaagent-pro",
    log_level="INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_output=True,
    file_output=True,
    json_format=True,  # JSON or plain text
    log_dir="logs",
)
```

### Basic Logging

```python
from core.observability import structured_logger

logger = structured_logger(__name__)

logger.info("User logged in", extra={"user_id": "123"})
logger.warning("High cache miss rate", extra={"rate": 0.8})
logger.error("Database connection failed", extra={"host": "db1"})
```

### Structured Logging Helpers

```python
from core.observability import get_log_aggregator

aggregator = get_log_aggregator()
logger = structured_logger(__name__)

# Log workflow event
aggregator.log_workflow_event(
    logger,
    workflow_name="research_workflow",
    event_type="started",
    query="What is AI?",
    user_id="123",
)

# Log LLM request
aggregator.log_llm_request(
    logger,
    model="claude-3-opus",
    prompt_tokens=150,
    completion_tokens=300,
    latency_ms=2500.0,
    temperature=0.7,
)

# Log cache operation
aggregator.log_cache_operation(
    logger,
    operation="get",
    hit=True,
    latency_ms=2.5,
    key="user:123",
)
```

### Log Format

JSON logs include:
```json
{
  "timestamp": "2025-10-10T12:34:56.789Z",
  "level": "INFO",
  "logger": "core.workflows.research",
  "message": "Workflow started",
  "module": "research",
  "function": "execute_workflow",
  "line": 42,
  "trace_id": "abc123...",
  "span_id": "def456...",
  "workflow_name": "research_workflow",
  "user_id": "123"
}
```

### Log Files

- `logs/megaagent-pro.log` - All logs
- `logs/megaagent-pro.error.log` - Errors only
- Rotation: 10MB per file, 5 backups

---

## Integration Guide

### Complete Workflow Integration

```python
from core.observability import (
    init_tracing,
    init_logging,
    trace_async,
    structured_logger,
    get_metrics_collector,
    TracingConfig,
)
from core.observability.metrics_collector import WorkflowTimer
from core.observability.distributed_tracing import TracingContext, add_span_event

# Initialize once at startup
init_tracing(TracingConfig(exporter_type="jaeger"))
aggregator = init_logging()
collector = get_metrics_collector()
logger = structured_logger(__name__)

@trace_async(name="research_workflow")
async def research_workflow(query: str, user_id: str):
    """Complete workflow with full observability."""

    # Start workflow timer
    with WorkflowTimer(collector, "research_workflow") as timer:
        # Log workflow start
        aggregator.log_workflow_event(
            logger, "research_workflow", "started",
            query=query, user_id=user_id
        )

        try:
            # Step 1: Analyze query
            with TracingContext("analyze_query") as span:
                span.set_attribute("query", query)
                add_span_event("analysis_started")

                analysis = await analyze_query(query)

                collector.record_workflow_node(
                    "research_workflow", "analyze_query", "success"
                )
                add_span_event("analysis_completed")

            # Step 2: LLM call
            with TracingContext("llm_call") as span:
                span.set_attribute("model", "claude-3-opus")

                start_time = time.time()
                result = await llm_call(query)
                duration = time.time() - start_time

                # Record LLM metrics
                collector.record_llm_request(
                    model="claude-3-opus",
                    status="success",
                    duration_seconds=duration,
                    prompt_tokens=150,
                    completion_tokens=300,
                )

                # Log LLM request
                aggregator.log_llm_request(
                    logger, "claude-3-opus", 150, 300, duration * 1000
                )

            # Workflow completed successfully
            timer.set_status("success")
            aggregator.log_workflow_event(
                logger, "research_workflow", "completed"
            )

            return result

        except Exception as e:
            # Workflow failed
            timer.set_status("error")
            logger.error("Workflow failed", extra={"error": str(e)})
            raise
```

---

## Configuration

### Environment Variables

```bash
# Tracing
export TRACING_ENABLED=true
export TRACING_SERVICE_NAME=megaagent-pro
export TRACING_EXPORTER=jaeger  # console, jaeger, zipkin, otlp
export TRACING_SAMPLE_RATE=1.0  # 0.0 to 1.0

# Jaeger
export JAEGER_HOST=localhost
export JAEGER_PORT=6831

# Zipkin
export ZIPKIN_ENDPOINT=http://localhost:9411/api/v2/spans

# OTLP
export OTLP_ENDPOINT=localhost:4317

# API Rate Limiting
export API_RATE_LIMIT=60
export API_RATE_WINDOW=60
```

### Loading from Environment

```python
from core.observability import TracingConfig

config = TracingConfig.from_env()
init_tracing(config)
```

---

## Docker Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  # Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./grafana_dashboards:/var/lib/grafana/dashboards

  # Jaeger
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"
      - "14268:14268"
      - "14250:14250"
      - "9411:9411"
    environment:
      - COLLECTOR_ZIPKIN_HTTP_PORT=9411

volumes:
  grafana-storage:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'megaagent-pro'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

### Start Services

```bash
docker-compose up -d
```

### Access UIs

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger**: http://localhost:16686

---

## Best Practices

### 1. Metrics

- ✅ Use counters for cumulative values (requests, errors)
- ✅ Use gauges for point-in-time values (connections, queue depth)
- ✅ Use histograms for distributions (latency, size)
- ✅ Add meaningful labels but avoid high cardinality
- ❌ Don't use timestamps in labels
- ❌ Don't record PII in metric labels

### 2. Tracing

- ✅ Trace at workflow/request boundaries
- ✅ Add relevant attributes (user_id, query, model)
- ✅ Use span events for important milestones
- ✅ Sample traces in high-traffic scenarios
- ❌ Don't trace every function (overhead)
- ❌ Don't include sensitive data in spans

### 3. Logging

- ✅ Use structured logging (JSON)
- ✅ Include trace context for correlation
- ✅ Log at appropriate levels (DEBUG, INFO, ERROR)
- ✅ Use log aggregation helpers for consistency
- ❌ Don't log secrets or PII
- ❌ Don't log excessively (performance impact)

### 4. Dashboards

- ✅ Focus on key metrics (SLIs, SLOs)
- ✅ Use appropriate visualizations
- ✅ Set meaningful thresholds and alerts
- ✅ Group related metrics together
- ❌ Don't overcrowd dashboards
- ❌ Don't use defaults without customization

---

## Troubleshooting

### Metrics Not Appearing in Prometheus

1. Check metrics endpoint: `curl http://localhost:8000/metrics`
2. Verify Prometheus can reach the endpoint
3. Check Prometheus logs: `docker logs prometheus`
4. Verify scrape configuration in prometheus.yml

### Traces Not Appearing in Jaeger

1. Check tracing is enabled: `TRACING_ENABLED=true`
2. Verify Jaeger endpoint: `JAEGER_HOST` and `JAEGER_PORT`
3. Check Jaeger logs: `docker logs jaeger`
4. Test with console exporter first

### Logs Not Being Written

1. Check log directory exists and is writable
2. Verify log level allows your log statements
3. Check file permissions on log directory
4. Verify logging initialization was called

### High Memory Usage

1. Reduce tracing sample rate: `TRACING_SAMPLE_RATE=0.1`
2. Increase log rotation limits
3. Limit metric label cardinality
4. Use time-windowed queries in Prometheus

### Dashboard Not Loading

1. Verify Prometheus data source is configured
2. Check metric names match your application
3. Test queries in Prometheus UI first
4. Review Grafana logs for errors

---

## Performance Considerations

### Metrics Collection Overhead

- **Counter increment**: ~100ns
- **Histogram observation**: ~500ns
- **Gauge set**: ~100ns

**Impact**: Negligible (<0.1% overhead)

### Tracing Overhead

- **No sampling**: ~1-5ms per trace
- **With sampling (0.1)**: ~0.1-0.5ms per request

**Recommendation**: Use sampling in production

### Logging Overhead

- **JSON formatting**: ~100-500μs per log
- **File I/O**: Async, minimal blocking

**Recommendation**: Use INFO level in production

---

## Next Steps

1. ✅ Start observability stack: `docker-compose up -d`
2. ✅ Initialize observability in your app
3. ✅ Import Grafana dashboards
4. ✅ Run example: `python examples/observability_example.py`
5. ✅ Customize dashboards for your needs
6. ✅ Set up alerts in Grafana
7. ✅ Configure log aggregation (ELK, Loki)

---

## API Reference

See inline documentation in:
- `core/observability/metrics_collector.py`
- `core/observability/distributed_tracing.py`
- `core/observability/log_aggregation.py`
- `core/observability/grafana_dashboards.py`

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review examples in `examples/observability_example.py`
- Test with console exporters first
- Check Docker container logs

---

**Status**: ✅ Phase 3 Complete
**Coverage**: Prometheus ✅ | Grafana ✅ | Tracing ✅ | Logging ✅
