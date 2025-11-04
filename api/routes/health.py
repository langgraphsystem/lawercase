from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_agent

router = APIRouter()


@router.get("/health")
async def health(agent=Depends(get_agent)):
    return await agent.health_check()


@router.get("/ready")
async def ready(agent=Depends(get_agent)):
    # Reuse health for now; can be extended with dependency checks
    return await agent.health_check()
