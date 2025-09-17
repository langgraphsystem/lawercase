import pytest

from core.dto.context_chunk import ContextChunk
from core.dto.query_spec import QuerySpec
from core.rag.retrieve import HybridRetriever


@pytest.mark.asyncio
async def test_hybrid_retriever_ranks_documents():
    retriever = HybridRetriever(namespace="unit")
    chunks = [
        ContextChunk(chunk_id="1", document_id="A", text="Immigration law case involving visa"),
        ContextChunk(chunk_id="2", document_id="B", text="Corporate merger compliance checklist"),
        ContextChunk(chunk_id="3", document_id="C", text="Family custody dispute precedent"),
    ]
    retriever.index(chunks)

    results = await retriever.retrieve(QuerySpec(text="visa compliance", top_k=2, rerank_top_k=2))
    assert results
    assert results[0].document_id == "A"
    assert len(results) == 2
