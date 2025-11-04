from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


@router.get("/health")
def workflow_health() -> dict[str, str]:
    """Minimal workflow health endpoint."""
    return {"status": "ok"}
