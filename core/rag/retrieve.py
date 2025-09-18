from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple

from core.dto.context_chunk import ContextChunk
from core.dto.query_spec import QuerySpec
from core.embed.embeddings import SimpleEmbedder
from core.telemetry import metrics
from core.vector.service import get_vector_service, VectorRecord, VectorMetadata, initialize_vector_service


class HybridRetriever:
    """A simple hybrid BM25 + vector similarity retriever."""

    def __init__(self, *, namespace: str = "default", embedder: SimpleEmbedder | None = None) -> None:
        self._namespace = namespace
        self._embedder = embedder or SimpleEmbedder()
        self._documents: Dict[str, ContextChunk] = {}
        self._inv_index: Dict[str, List[str]] = defaultdict(list)
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_len: float = 1.0
        self._vectors: Dict[str, List[float]] = {}
        self._vector_service = None
        self._vector_initialized = False

    def index(self, chunks: Iterable[ContextChunk]) -> None:
        """Synchronous indexing for BM25 (backward compatibility)."""
        for chunk in chunks:
            self._documents[chunk.chunk_id] = chunk
            tokens = chunk.text.lower().split()
            self._doc_lengths[chunk.chunk_id] = len(tokens)
            for token in set(tokens):
                self._inv_index[token].append(chunk.chunk_id)
        if self._doc_lengths:
            self._avg_doc_len = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    async def aindex(self, chunks: Iterable[ContextChunk]) -> bool:
        """Asynchronous indexing with Pinecone vector store."""
        chunks_list = list(chunks)

        # Index for BM25 first
        self.index(chunks_list)

        # Try to index in Pinecone
        try:
            if not self._vector_service:
                self._vector_service = await get_vector_service()

            if not self._vector_initialized:
                # Initialize with embedder dimension
                dimension = getattr(self._embedder, 'dimension', 1536)
                self._vector_initialized = await initialize_vector_service(dimension)

            if self._vector_initialized:
                # Convert chunks to vector records
                vector_records = []
                for chunk in chunks_list:
                    # Generate embedding
                    vectors = await self._embedder.aembed([chunk.text])
                    if vectors and len(vectors) > 0:
                        vector_record = VectorRecord(
                            id=chunk.chunk_id,
                            vector=vectors[0],
                            metadata=VectorMetadata(
                                document_id=chunk.document_id or chunk.chunk_id,
                                chunk_id=chunk.chunk_id,
                                source=chunk.metadata.get("source"),
                                tags=chunk.metadata.get("tags", []),
                                text=chunk.text
                            )
                        )
                        vector_records.append(vector_record)

                # Upsert to Pinecone
                if vector_records:
                    success = await self._vector_service.upsert_batch(vector_records)
                    return success

            return True  # BM25 indexing successful even if vector failed

        except Exception:
            # Fallback to local-only indexing
            return True

    async def _ensure_vectors(self, chunk_ids: Sequence[str]) -> None:
        missing = [cid for cid in chunk_ids if cid not in self._vectors]
        if not missing:
            return
        vectors = await self._embedder.aembed(self._documents[cid].text for cid in missing)
        for cid, vec in zip(missing, vectors):
            self._vectors[cid] = vec

    def _bm25_scores(self, query_tokens: Sequence[str]) -> Dict[str, float]:
        scores: Dict[str, float] = defaultdict(float)
        doc_count = len(self._documents) or 1
        for token in query_tokens:
            postings = self._inv_index.get(token)
            if not postings:
                continue
            idf = math.log(1 + (doc_count - len(postings) + 0.5) / (len(postings) + 0.5))
            for chunk_id in postings:
                freq = self._documents[chunk_id].text.lower().split().count(token)
                denom = freq + 1.2 * (1 - 0.75 + 0.75 * self._doc_lengths[chunk_id] / self._avg_doc_len)
                scores[chunk_id] += idf * (freq * (1.2 + 1) / denom)
        return scores

    def _cosine(self, a: Sequence[float], b: Sequence[float]) -> float:
        num = sum(x * y for x, y in zip(a, b))
        denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
        if not denom:
            return 0.0
        return num / denom

    async def retrieve(self, query: str | QuerySpec) -> List[ContextChunk]:
        spec = query if isinstance(query, QuerySpec) else QuerySpec(text=query)
        start = time.perf_counter()

        # Try Pinecone vector search first
        vector_results = await self._vector_search_pinecone(spec)
        if vector_results:
            # Use Pinecone results and combine with BM25
            return await self._hybrid_search_with_pinecone(spec, vector_results)

        # Fallback to local hybrid search
        return await self._local_hybrid_search(spec, start)

    async def _vector_search_pinecone(self, spec: QuerySpec) -> List[ContextChunk]:
        """Search using Pinecone vector store."""
        try:
            if not self._vector_service:
                self._vector_service = await get_vector_service()

            if not self._vector_initialized:
                return []

            # Generate query embedding
            query_vec = (await self._embedder.aembed([spec.text]))[0]

            # Query Pinecone
            query_results = await self._vector_service.query(
                vector=query_vec,
                top_k=max(50, spec.top_k * 2)  # Get more for reranking
            )

            # Convert to ContextChunk
            chunks = []
            for result in query_results:
                chunk = ContextChunk(
                    chunk_id=result.metadata.chunk_id,
                    document_id=result.metadata.document_id,
                    text=result.metadata.text or "",
                    score=result.score,
                    metadata={
                        "source": result.metadata.source,
                        "tags": result.metadata.tags,
                        "vector_score": result.score
                    }
                )
                chunks.append(chunk)

            return chunks

        except Exception:
            return []

    async def _hybrid_search_with_pinecone(self, spec: QuerySpec, vector_chunks: List[ContextChunk]) -> List[ContextChunk]:
        """Combine Pinecone vector results with BM25 scores."""
        start = time.perf_counter()

        # Calculate BM25 scores for vector results
        query_tokens = spec.text.lower().split()
        bm25_scores = {}

        for chunk in vector_chunks:
            # If chunk exists locally, get BM25 score
            if chunk.chunk_id in self._documents:
                chunk_tokens = self._documents[chunk.chunk_id].text.lower().split()
                score = 0.0
                for token in query_tokens:
                    if token in chunk_tokens:
                        score += 1.0  # Simple term frequency
                bm25_scores[chunk.chunk_id] = score

        # Combine scores (0.7 vector, 0.3 BM25)
        combined_chunks = []
        for chunk in vector_chunks:
            vector_score = chunk.score or 0.0
            bm25_score = bm25_scores.get(chunk.chunk_id, 0.0)
            combined_score = 0.7 * vector_score + 0.3 * bm25_score

            chunk_copy = chunk.model_copy(update={'score': combined_score})
            chunk_copy.metadata["combined_score"] = combined_score
            chunk_copy.metadata["bm25_score"] = bm25_score
            combined_chunks.append(chunk_copy)

        # Sort by combined score and limit
        combined_chunks.sort(key=lambda x: x.score, reverse=True)
        results = combined_chunks[:spec.rerank_top_k]

        duration = time.perf_counter() - start
        metrics.record_rag_latency(namespace=self._namespace, duration_seconds=duration)

        return results

    async def _local_hybrid_search(self, spec: QuerySpec, start: float) -> List[ContextChunk]:
        """Fallback to local BM25 + vector search."""
        query_tokens = spec.text.lower().split()
        bm25_scores = self._bm25_scores(query_tokens)

        candidate_ids = list({cid for cid in bm25_scores.keys()})
        if not candidate_ids:
            candidate_ids = list(self._documents.keys())
        await self._ensure_vectors(candidate_ids)

        query_vec = (await self._embedder.aembed([spec.text]))[0]
        vector_scores = {cid: self._cosine(query_vec, self._vectors[cid]) for cid in candidate_ids}

        combined: List[Tuple[str, float]] = []
        for cid in candidate_ids:
            score = 0.6 * vector_scores.get(cid, 0.0) + 0.4 * bm25_scores.get(cid, 0.0)
            combined.append((cid, score))
        combined.sort(key=lambda item: item[1], reverse=True)

        rerank_pool = combined[: max(50, spec.top_k)]
        rerank_pool.sort(key=lambda item: vector_scores.get(item[0], 0.0), reverse=True)
        selected = rerank_pool[: spec.rerank_top_k]

        duration = time.perf_counter() - start
        metrics.record_rag_latency(namespace=self._namespace, duration_seconds=duration)

        results: List[ContextChunk] = []
        for cid, score in selected:
            chunk = self._documents[cid].model_copy(update={'score': score})
            results.append(chunk)
        return results


_default_retriever = HybridRetriever(namespace="global")


async def retrieve(query: str | QuerySpec) -> List[ContextChunk]:
    return await _default_retriever.retrieve(query)

