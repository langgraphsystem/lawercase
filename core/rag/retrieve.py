from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple

from core.dto.context_chunk import ContextChunk
from core.dto.query_spec import QuerySpec
from core.embed.embeddings import SimpleEmbedder
from core.telemetry import metrics


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

    def index(self, chunks: Iterable[ContextChunk]) -> None:
        for chunk in chunks:
            self._documents[chunk.chunk_id] = chunk
            tokens = chunk.text.lower().split()
            self._doc_lengths[chunk.chunk_id] = len(tokens)
            for token in set(tokens):
                self._inv_index[token].append(chunk.chunk_id)
        if self._doc_lengths:
            self._avg_doc_len = sum(self._doc_lengths.values()) / len(self._doc_lengths)

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

