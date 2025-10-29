"""Document ingestion pipeline for the RAG subsystem."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
import uuid

from .utils import tokenize


class SupportsEmbed(Protocol):
    """Async embedding protocol used by the ingestion pipeline."""

    async def aembed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(slots=True)
class Document:
    """Raw document that should be chunked and indexed."""

    text: str
    doc_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    chunk_size: int = 400
    chunk_overlap: int = 60

    def ensure_id(self) -> str:
        if self.doc_id is None:
            self.doc_id = str(uuid.uuid4())
        return self.doc_id


@dataclass(slots=True)
class DocumentChunk:
    """Chunk generated for the vector store."""

    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, str]
    embedding: list[float]


class DocumentStore:
    """In-memory store used for hybrid retrieval."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}

    def add_document(self, document: Document) -> None:
        self._documents[document.doc_id or document.ensure_id()] = document

    def add_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        return self._chunks.get(chunk_id)

    def iter_chunks(self) -> list[DocumentChunk]:
        return list(self._chunks.values())


class DocumentIngestion:
    """Chunk text and populate the document store with embeddings."""

    def __init__(self, *, store: DocumentStore, embedder: SupportsEmbed) -> None:
        self.store = store
        self.embedder = embedder

    async def ingest(self, documents: Sequence[Document]) -> list[DocumentChunk]:
        if not documents:
            return []

        all_chunks: list[DocumentChunk] = []
        texts: list[str] = []

        for document in documents:
            doc_id = document.ensure_id()
            self.store.add_document(document)
            chunk_texts = self._chunk_text(
                document.text, document.chunk_size, document.chunk_overlap
            )
            document.metadata.setdefault("token_count", str(len(tokenize(document.text))))

            for index, text in enumerate(chunk_texts):
                chunk_id = f"{doc_id}:{index}"
                metadata = dict(document.metadata)
                metadata["chunk_index"] = str(index)
                metadata["chunk_count"] = str(len(chunk_texts))
                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        text=text,
                        metadata=metadata,
                        embedding=[],
                    )
                )
                texts.append(text)

        embeddings = await self.embedder.aembed(texts)
        if len(embeddings) != len(all_chunks):
            raise RuntimeError("Embedder returned unexpected number of vectors")

        for chunk, embedding in zip(all_chunks, embeddings, strict=False):
            chunk.embedding = embedding

        self.store.add_chunks(all_chunks)
        return all_chunks

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        tokens = tokenize(text)
        if not tokens:
            return []

        chunk_size = max(1, chunk_size)
        chunk_overlap = min(max(0, chunk_overlap), chunk_size - 1)
        step = chunk_size - chunk_overlap

        chunks: list[str] = []
        for start in range(0, len(tokens), step):
            end = min(len(tokens), start + chunk_size)
            chunk_tokens = tokens[start:end]
            if not chunk_tokens:
                continue
            chunks.append(" ".join(chunk_tokens))
            if end == len(tokens):
                break

        if not chunks:
            chunks.append(" ".join(tokens[:chunk_size]))
        return chunks


async def ingest_concurrently(
    ingestion: DocumentIngestion,
    documents: Sequence[Document],
    *,
    batch_size: int = 8,
) -> list[DocumentChunk]:
    """Ingest documents concurrently in batches to improve throughput."""

    chunks: list[DocumentChunk] = []
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        # Process batches sequentially but allow internal async embedder work.
        chunks.extend(await ingestion.ingest(batch))
    return chunks


__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentIngestion",
    "DocumentStore",
    "ingest_concurrently",
]
