from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_agent, get_current_user
from api.schemas import MemoryRetrieveRequest, MemoryWriteRequest
from core.memory.models import AuditEvent, MemoryRecord

router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("/snapshot")
async def snapshot(thread_id: str, agent=Depends(get_agent), user=Depends(get_current_user)):
    snap = await agent.memory.asnapshot_thread(thread_id)
    return {"thread_id": thread_id, "snapshot": snap}


@router.post("/write")
async def write(body: MemoryWriteRequest, agent=Depends(get_agent), user=Depends(get_current_user)):
    # If payload provided, treat as audit event reflection; else direct memory record
    if body.payload:
        ae = AuditEvent(
            event_id="api_write",
            user_id=body.user_id or user.get("sub") or "user",
            thread_id="api",
            source="api",
            action="write",
            payload=body.payload,
        )
        recs = await agent.memory.awrite(ae)
    elif body.text:
        recs = await agent.memory.awrite(
            [
                MemoryRecord(
                    user_id=body.user_id or user.get("sub") or "user",
                    text=body.text,
                    type=body.type or "semantic",
                    source="api",
                )
            ]
        )
    else:
        raise HTTPException(status_code=400, detail="payload or text required")
    return {"count": len(recs)}


@router.post("/retrieve")
async def retrieve(
    body: MemoryRetrieveRequest, agent=Depends(get_agent), user=Depends(get_current_user)
):
    results = await agent.memory.aretrieve(
        body.query,
        user_id=body.user_id or user.get("sub") or None,
        topk=body.topk,
        filters=body.filters or None,
    )
    return {"count": len(results), "results": [r.model_dump() for r in results]}
