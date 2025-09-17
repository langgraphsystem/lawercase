from __future__ import annotations

import os
from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from core.db.engine import db
from core.llm.router import LLMRouter
from core.vector.service import get_vector_service


router = APIRouter()


async def healthz_payload() -> Dict[str, object]:
    base = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }
    db_ok = await db.ping()
    base["db"] = "ok" if db_ok else "down"

    # Vector store health - actual Pinecone connectivity check
    try:
        vector_service = await get_vector_service()
        vector_ok = await vector_service.health_check()
        base["vector"] = "ok" if vector_ok else "down"
    except Exception:
        base["vector"] = "down"

    # LLM health: ok if at least one provider is registered/available, else degraded
    llm_router = LLMRouter()
    base["llm"] = "ok" if llm_router.providers else "degraded"
    return base


@router.get("/healthz")
async def healthz():
    return await healthz_payload()
