from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import PlainTextResponse

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def get_metrics() -> str:
    """Expose basic Prometheus-compatible metrics placeholder."""
    return (
        "# HELP megaagent_requests_total Total requests handled\n"
        "# TYPE megaagent_requests_total counter\n"
        "megaagent_requests_total 0\n"
    )
