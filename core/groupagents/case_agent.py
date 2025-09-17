from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.dto.context_chunk import ContextChunk
from core.dto.route_policy import RoutePolicy
from core.dto.task_request import TaskRequest
from core.llm.router import LLMRouter
from core.rag.retrieve import HybridRetriever, _default_retriever


class CaseRecord(BaseModel):
    case_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    description: str
    client_id: str
    case_type: str = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class CaseAgent:
    """Case management agent backed by the LLM router and hybrid RAG."""

    def __init__(
        self,
        *,
        router: Optional[LLMRouter] = None,
        retriever: Optional[HybridRetriever] = None,
    ) -> None:
        self._router = router or LLMRouter()
        self._retriever = retriever or _default_retriever
        self._cases: Dict[str, CaseRecord] = {}

    async def acreate_case(
        self,
        *,
        title: str,
        description: str,
        client_id: str,
        case_type: str = "general",
        metadata: Optional[Dict[str, str]] = None,
    ) -> CaseRecord:
        record = CaseRecord(title=title, description=description, client_id=client_id, case_type=case_type, metadata=metadata or {})
        summary_prompt = (
            "Summarize the following legal case for rapid orientation."
            f"\nTitle: {title}\nClient: {client_id}\nCase Type: {case_type}\nDescription: {description}\n"
        )
        response = await self._router.invoke(TaskRequest(prompt=summary_prompt, policy=RoutePolicy(label="case_summary")))
        record.summary = response.text
        self._cases[record.case_id] = record

        chunk = ContextChunk(
            chunk_id=record.case_id,
            document_id=record.case_id,
            text=record.description,
            metadata={"case_id": record.case_id, "title": record.title},
        )
        self._retriever.index([chunk])
        return record

    async def aget_case(self, case_id: str) -> CaseRecord:
        record = self._cases.get(case_id)
        if not record:
            raise KeyError(f"Case {case_id} not found")
        return record

    async def aupdate_summary(self, case_id: str) -> CaseRecord:
        record = await self.aget_case(case_id)
        prompt = f"Refresh the summary for the following case based on description.\n{record.description}"
        response = await self._router.invoke(TaskRequest(prompt=prompt, policy=RoutePolicy(label="case_refresh")))
        record.summary = response.text
        record.updated_at = datetime.utcnow()
        return record

    async def asearch_cases(self, query: str, *, limit: int = 5) -> List[CaseRecord]:
        results = await self._retriever.retrieve(query)
        case_ids = [chunk.metadata.get("case_id") for chunk in results if chunk.metadata.get("case_id") in self._cases]
        unique: List[str] = []
        for cid in case_ids:
            if cid not in unique:
                unique.append(cid)
        return [self._cases[cid] for cid in unique[:limit]]

    async def agenerate_brief(self, case_id: str) -> str:
        record = await self.aget_case(case_id)
        context = await self._retriever.retrieve(record.title)
        context_text = "\n".join(chunk.text for chunk in context[:5])
        prompt = (
            "Draft a concise legal brief.\n"
            f"Case Title: {record.title}\n"
            f"Summary: {record.summary or 'N/A'}\n"
            f"Description: {record.description}\n"
        )
        if context_text:
            prompt = f"Context:\n{context_text}\n\n{prompt}"
        response = await self._router.invoke(TaskRequest(prompt=prompt, policy=RoutePolicy(label="case_brief")))
        return response.text
