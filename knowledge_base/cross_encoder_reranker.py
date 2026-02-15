"""Cross-Encoder Reranker for RAG.

Advanced reranking using cross-encoder models:
- Query-document pair scoring
- Multiple model support
- Batch processing
- Score normalization
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RerankerModel(str, Enum):
    """Available reranker models."""

    MS_MARCO_MINI = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MS_MARCO_BASE = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    BGE_RERANKER = "BAAI/bge-reranker-base"
    COHERE = "cohere-rerank"
    LLM_BASED = "llm-reranker"


@dataclass(slots=True)
class RerankResult:
    """Single reranked item."""

    content: str
    original_score: float
    rerank_score: float
    rank: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankResponse:
    """Response from reranking."""

    results: list[RerankResult]
    model_used: str
    execution_time_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankerConfig:
    """Configuration for reranker."""

    model: RerankerModel = RerankerModel.MS_MARCO_MINI
    batch_size: int = 32
    max_length: int = 512
    normalize_scores: bool = True
    return_scores: bool = True


class CrossEncoderReranker:
    """Cross-encoder based reranker.

    Features:
    - Multiple model support
    - Batch processing for efficiency
    - Score normalization
    - Fallback to simpler methods

    Usage:
        reranker = CrossEncoderReranker()

        results = await reranker.rerank(
            query="What are EB-1A requirements?",
            documents=["doc1", "doc2", "doc3"],
            top_k=5,
        )

        for result in results.results:
            print(f"Rank {result.rank}: {result.rerank_score:.3f}")
    """

    def __init__(
        self,
        config: RerankerConfig | None = None,
        model_name: str | None = None,
    ) -> None:
        self.config = config or RerankerConfig()
        if model_name:
            self.config.model = (
                RerankerModel(model_name)
                if model_name in [m.value for m in RerankerModel]
                else RerankerModel.MS_MARCO_MINI
            )

        self._model = None
        self._tokenizer = None

    def _load_model(self) -> bool:
        """Lazy load the cross-encoder model."""
        if self._model is not None:
            return True

        model_type = self.config.model

        if model_type == RerankerModel.LLM_BASED:
            # LLM-based reranking doesn't need local model
            return True

        if model_type == RerankerModel.COHERE:
            try:
                import cohere

                self._model = cohere.Client()
                return True
            except ImportError:
                logger.warning("cohere.import_failed")
                return False

        # Load sentence-transformers cross-encoder
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(model_type.value, max_length=self.config.max_length)
            return True
        except ImportError:
            logger.warning(
                "cross_encoder.import_failed",
                hint="Install sentence-transformers: pip install sentence-transformers",
            )
            return False
        except Exception as e:
            logger.warning("cross_encoder.load_failed", error=str(e))
            return False

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
        original_scores: list[float] | None = None,
    ) -> RerankResponse:
        """Rerank documents for a query.

        Args:
            query: Search query
            documents: List of document texts
            top_k: Number of results to return
            original_scores: Original retrieval scores

        Returns:
            RerankResponse with reranked results
        """
        import time

        start_time = time.perf_counter()

        if not documents:
            return RerankResponse(
                results=[],
                model_used="none",
                execution_time_ms=0,
            )

        top_k = top_k or len(documents)
        original_scores = original_scores or [0.5] * len(documents)

        # Try to load model
        model_loaded = self._load_model()

        if not model_loaded:
            # Fallback to keyword-based reranking
            results = self._fallback_rerank(query, documents, original_scores, top_k)
            elapsed = (time.perf_counter() - start_time) * 1000
            return RerankResponse(
                results=results,
                model_used="keyword_fallback",
                execution_time_ms=elapsed,
            )

        # Rerank based on model type
        if self.config.model == RerankerModel.COHERE:
            results = await self._rerank_cohere(query, documents, original_scores, top_k)
        elif self.config.model == RerankerModel.LLM_BASED:
            results = await self._rerank_llm(query, documents, original_scores, top_k)
        else:
            results = self._rerank_cross_encoder(query, documents, original_scores, top_k)

        elapsed = (time.perf_counter() - start_time) * 1000

        logger.info(
            "reranking.complete",
            model=self.config.model.value,
            documents=len(documents),
            top_k=top_k,
            time_ms=elapsed,
        )

        return RerankResponse(
            results=results,
            model_used=self.config.model.value,
            execution_time_ms=elapsed,
        )

    def _rerank_cross_encoder(
        self,
        query: str,
        documents: list[str],
        original_scores: list[float],
        top_k: int,
    ) -> list[RerankResult]:
        """Rerank using cross-encoder model."""
        # Truncate documents for model
        truncated_docs = [doc[: self.config.max_length * 4] for doc in documents]

        # Create pairs
        pairs = [(query, doc) for doc in truncated_docs]

        # Score in batches
        all_scores = []
        for i in range(0, len(pairs), self.config.batch_size):
            batch = pairs[i : i + self.config.batch_size]
            scores = self._model.predict(batch)
            all_scores.extend(scores)

        # Normalize scores if configured
        if self.config.normalize_scores:
            all_scores = self._normalize_scores(all_scores)

        # Create results
        results = []
        for i, (doc, score, orig_score) in enumerate(
            zip(documents, all_scores, original_scores, strict=False)
        ):
            results.append(
                RerankResult(
                    content=doc,
                    original_score=orig_score,
                    rerank_score=float(score),
                    rank=0,  # Will be set after sorting
                    metadata={"index": i},
                )
            )

        # Sort by rerank score
        results.sort(key=lambda r: r.rerank_score, reverse=True)

        # Assign ranks and limit
        for rank, result in enumerate(results[:top_k]):
            result.rank = rank + 1

        return results[:top_k]

    async def _rerank_cohere(
        self,
        query: str,
        documents: list[str],
        original_scores: list[float],
        top_k: int,
    ) -> list[RerankResult]:
        """Rerank using Cohere Rerank API."""
        try:
            response = self._model.rerank(
                query=query,
                documents=documents,
                top_n=top_k,
                model="rerank-english-v2.0",
            )

            results = []
            for i, item in enumerate(response.results):
                results.append(
                    RerankResult(
                        content=documents[item.index],
                        original_score=original_scores[item.index],
                        rerank_score=item.relevance_score,
                        rank=i + 1,
                        metadata={"cohere_index": item.index},
                    )
                )

            return results

        except Exception as e:
            logger.warning("cohere_rerank.failed", error=str(e))
            return self._fallback_rerank(query, documents, original_scores, top_k)

    async def _rerank_llm(
        self,
        query: str,
        documents: list[str],
        original_scores: list[float],
        top_k: int,
    ) -> list[RerankResult]:
        """Rerank using LLM-based scoring."""
        try:
            from core.llm_interface import TaskRequest, TaskRouter, TaskType

            router = TaskRouter()

            # Score each document
            scores = []
            for doc in documents[:20]:  # Limit for cost
                prompt = f"""Rate the relevance of this document to the query on a scale of 0-10.
Query: {query}
Document: {doc[:500]}

Return ONLY a number between 0 and 10."""

                response = await router.route(
                    TaskRequest(
                        prompt=prompt,
                        task_type=TaskType.GENERAL,
                        temperature=0.0,
                        max_tokens=10,
                    )
                )

                try:
                    score = float(response.content.strip()) / 10.0
                except ValueError:
                    score = 0.5

                scores.append(score)

            # Pad remaining with original scores
            scores.extend(original_scores[len(scores) :])

            # Create results
            results = []
            for i, (doc, score, orig_score) in enumerate(
                zip(documents, scores, original_scores, strict=False)
            ):
                results.append(
                    RerankResult(
                        content=doc,
                        original_score=orig_score,
                        rerank_score=score,
                        rank=0,
                        metadata={"index": i},
                    )
                )

            results.sort(key=lambda r: r.rerank_score, reverse=True)
            for rank, result in enumerate(results[:top_k]):
                result.rank = rank + 1

            return results[:top_k]

        except Exception as e:
            logger.warning("llm_rerank.failed", error=str(e))
            return self._fallback_rerank(query, documents, original_scores, top_k)

    def _fallback_rerank(
        self,
        query: str,
        documents: list[str],
        original_scores: list[float],
        top_k: int,
    ) -> list[RerankResult]:
        """Fallback reranking using keyword matching."""
        query_terms = set(query.lower().split())

        results = []
        for i, (doc, orig_score) in enumerate(zip(documents, original_scores, strict=False)):
            doc_terms = set(doc.lower().split())
            overlap = len(query_terms & doc_terms)
            keyword_score = overlap / max(1, len(query_terms))

            # Combine with original score
            combined_score = 0.7 * orig_score + 0.3 * keyword_score

            results.append(
                RerankResult(
                    content=doc,
                    original_score=orig_score,
                    rerank_score=combined_score,
                    rank=0,
                    metadata={"index": i, "keyword_overlap": overlap},
                )
            )

        results.sort(key=lambda r: r.rerank_score, reverse=True)
        for rank, result in enumerate(results[:top_k]):
            result.rank = rank + 1

        return results[:top_k]

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """Normalize scores to 0-1 range."""
        if not scores:
            return scores

        min_score = min(scores)
        max_score = max(scores)
        range_score = max_score - min_score

        if range_score == 0:
            return [0.5] * len(scores)

        return [(s - min_score) / range_score for s in scores]


class MultiStageReranker:
    """Multi-stage reranking pipeline.

    Applies multiple reranking stages for improved accuracy.
    """

    def __init__(self, stages: list[CrossEncoderReranker] | None = None) -> None:
        self.stages = stages or [
            CrossEncoderReranker(RerankerConfig(model=RerankerModel.MS_MARCO_MINI)),
        ]

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> RerankResponse:
        """Apply multi-stage reranking."""
        import time

        start_time = time.perf_counter()

        current_docs = documents
        current_scores = [0.5] * len(documents)
        models_used = []

        for stage in self.stages:
            # Get more results from intermediate stages
            stage_top_k = min(len(current_docs), (top_k or 10) * 2)

            response = await stage.rerank(
                query=query,
                documents=current_docs,
                top_k=stage_top_k,
                original_scores=current_scores,
            )

            current_docs = [r.content for r in response.results]
            current_scores = [r.rerank_score for r in response.results]
            models_used.append(response.model_used)

        # Final result
        final_results = []
        for i, (doc, score) in enumerate(
            zip(current_docs[:top_k], current_scores[:top_k], strict=False)
        ):
            final_results.append(
                RerankResult(
                    content=doc,
                    original_score=0.5,
                    rerank_score=score,
                    rank=i + 1,
                )
            )

        elapsed = (time.perf_counter() - start_time) * 1000

        return RerankResponse(
            results=final_results,
            model_used=" -> ".join(models_used),
            execution_time_ms=elapsed,
            metadata={"stages": len(self.stages)},
        )


# Convenience functions
def create_reranker(
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> CrossEncoderReranker:
    """Create configured reranker."""
    config = RerankerConfig()
    return CrossEncoderReranker(config=config, model_name=model)


async def rerank_documents(
    query: str,
    documents: list[str],
    top_k: int = 10,
) -> list[RerankResult]:
    """Convenience function for reranking."""
    reranker = create_reranker()
    response = await reranker.rerank(query, documents, top_k)
    return response.results
