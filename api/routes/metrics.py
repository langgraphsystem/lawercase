from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import REGISTRY, generate_latest
from starlette.responses import Response

from core.observability import get_metrics_collector

router = APIRouter(tags=["metrics"])

# Initialize metrics collector on module import
# This ensures all Prometheus metrics are registered
_collector = get_metrics_collector()


@router.get("/metrics")
def get_metrics() -> Response:
    """
    Expose Prometheus-compatible metrics.

    Returns real-time metrics for:
    - Workflow executions and duration
    - LLM requests (total, errors, duration, token usage)
    - Cache operations (hits, misses, hit rate)
    - Database queries (duration, errors, connections)
    - Vector store operations
    - System resources

    Format: Prometheus text-based exposition format
    Compatible with: Prometheus, Grafana, Datadog, etc.
    """
    metrics_output = generate_latest(REGISTRY)
    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={
            "Content-Type": "text/plain; version=0.0.4; charset=utf-8",
        },
    )
