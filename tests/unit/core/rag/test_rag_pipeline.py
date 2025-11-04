from __future__ import annotations

import pytest

from core.rag import Document, RAGPipeline


@pytest.mark.asyncio
async def test_rag_pipeline_ingest_and_query() -> None:
    pipeline = RAGPipeline()
    documents = [
        Document(
            text="The EB-1A visa requires evidence of extraordinary ability in the sciences.",
            metadata={"source_type": "knowledge_base", "topic": "immigration"},
        ),
        Document(
            text="Applicants should prepare detailed recommendation letters and proof of awards.",
            metadata={"source_type": "knowledge_base", "topic": "immigration"},
        ),
    ]

    chunks = await pipeline.ingest(documents)
    assert chunks, "Ingestion should create document chunks"

    result = await pipeline.query("What evidence does an EB-1A petition need?", top_k=2)
    results = result["results"]
    context = result["context"]

    assert results, "Query should return scored results"
    assert context["text"], "Context builder should provide aggregated text"
    assert results[0].metadata["topic"] == "immigration"


@pytest.mark.asyncio
async def test_rag_pipeline_returns_deterministic_scores() -> None:
    pipeline = RAGPipeline()
    document = Document(text="MegaAgent maintains an immutable audit log for security.")
    await pipeline.ingest([document])

    first = await pipeline.query("How does MegaAgent log security events?", top_k=1)
    second = await pipeline.query("How does MegaAgent log security events?", top_k=1)

    assert first["results"][0].score == pytest.approx(second["results"][0].score)
