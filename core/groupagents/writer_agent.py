from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.dto.route_policy import RoutePolicy
from core.dto.task_request import TaskRequest
from core.dto.context_chunk import ContextChunk
from core.llm.router import LLMRouter
from core.rag.retrieve import HybridRetriever, _default_retriever


class DraftDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    body: str
    author_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)


class WriterAgent:
    """Document generation agent leveraging the LLM router and hybrid RAG."""

    def __init__(
        self,
        *,
        router: Optional[LLMRouter] = None,
        retriever: Optional[HybridRetriever] = None,
    ) -> None:
        self._router = router or LLMRouter()
        self._retriever = retriever or _default_retriever
        self._drafts: Dict[str, DraftDocument] = {}

    async def agenerate_letter(
        self,
        *,
        author_id: str,
        recipient: str,
        subject: str,
        outline: str,
        case_reference: Optional[str] = None,
    ) -> DraftDocument:
        context_chunks: List[ContextChunk] = []
        if case_reference:
            context_chunks = await self._retriever.retrieve(case_reference)
        context_text = "\n".join(chunk.text for chunk in context_chunks[:5])
        prompt = (
            f"You are drafting a professional letter to {recipient}.\n"
            f"Subject: {subject}. Outline: {outline}."
        )
        if context_text:
            prompt = f"Context:\n{context_text}\n\n" + prompt
        response = await self._router.invoke(
            TaskRequest(
                prompt=prompt,
                policy=RoutePolicy(label="writer_letter", provider_priority=["openai", "anthropic"]),
            )
        )
        draft = DraftDocument(title=subject, body=response.text, author_id=author_id)
        self._drafts[draft.document_id] = draft
        return draft

    async def aget_document(self, document_id: str) -> DraftDocument:
        draft = self._drafts.get(document_id)
        if not draft:
            raise KeyError(f"Document {document_id} not found")
        return draft
