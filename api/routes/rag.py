from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.dto.context_chunk import ContextChunk
from core.dto.query_spec import QuerySpec
from core.rag.retrieve import retrieve as rag_retrieve


router = APIRouter(prefix="/rag")


class RetrieveRequest(BaseModel):
    text: str = Field(..., description="Query text")
    top_k: int = 5
    rerank_top_k: int = 5


class ChunkOut(BaseModel):
    chunk_id: str
    document_id: Optional[str]
    text: str
    score: Optional[float] = None


@router.post("/retrieve", response_model=List[ChunkOut])
async def rag_retrieve_endpoint(req: RetrieveRequest):
    spec = QuerySpec(text=req.text, top_k=req.top_k, rerank_top_k=req.rerank_top_k)
    chunks = await rag_retrieve(spec)
    # Normalize to API model
    out = [
        ChunkOut(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            text=c.text,
            score=c.score,
        )
        for c in chunks
    ]
    return out

