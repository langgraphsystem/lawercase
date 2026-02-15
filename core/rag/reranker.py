"""Cross-encoder reranking for precision-focused result ordering.

Uses cross-encoder models to score query-document pairs directly,
providing more accurate relevance scores than bi-encoders.
Typically applied after hybrid fusion as final reranking step.

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

import asyncio
from typing import Any

from core.rag.fusion import DocumentID, RankedResults, Score

# Type alias for document content
DocumentContent = str


class CrossEncoderReranker:
    """Cross-encoder reranker for precision-focused relevance scoring.

    Cross-encoders process query and document together, enabling deeper
    interaction modeling compared to bi-encoders. More accurate but slower,
    ideal for final reranking of top-k candidates.

    Attributes:
        model_name: Hugging Face model ID (e.g., "BAAI/bge-reranker-base")
        device: Computation device ("cpu" or "cuda")
        batch_size: Batch size for inference

    Example:
        >>> reranker = CrossEncoderReranker()
        >>> candidates = [
        ...     ("doc1", 0.7, "Immigration law governs visa applications"),
        ...     ("doc2", 0.6, "Contract law covers agreements")
        ... ]
        >>> reranked = await reranker.rerank(
        ...     query="visa requirements",
        ...     candidates=candidates,
        ...     top_k=1
        ... )
        >>> print(reranked[0][0])  # doc1
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: str = "cpu",
        batch_size: int = 32,
    ) -> None:
        """Initialize cross-encoder reranker.

        Args:
            model_name: Hugging Face model identifier.
                        Recommended: "BAAI/bge-reranker-base" (560M params)
                        or "BAAI/bge-reranker-large" (1.1B params, higher quality)
            device: Computation device ("cpu" or "cuda")
            batch_size: Batch size for inference (higher = faster but more memory)

        Example:
            >>> # CPU inference
            >>> reranker = CrossEncoderReranker(device="cpu")
            >>>
            >>> # GPU inference with larger model
            >>> reranker = CrossEncoderReranker(
            ...     model_name="BAAI/bge-reranker-large",
            ...     device="cuda",
            ...     batch_size=64
            ... )
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None  # Lazy loading
        self._tokenizer = None

    def _load_model(self) -> None:
        """Lazy load model and tokenizer.

        Model is loaded on first use to avoid initialization overhead
        if reranker is created but never used.
        """
        if self._model is not None:
            return  # Already loaded

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            raise ImportError(
                "transformers library required for cross-encoder reranking. "
                "Install with: pip install transformers torch"
            )

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self._model.to(self.device)
        self._model.eval()  # Set to evaluation mode

    async def rerank(
        self,
        query: str,
        candidates: list[tuple[DocumentID, Score, DocumentContent]],
        top_k: int | None = None,
    ) -> list[tuple[DocumentID, Score, DocumentContent]]:
        """Rerank candidates using cross-encoder model.

        Args:
            query: Search query string
            candidates: List of (doc_id, initial_score, content) tuples
                        from hybrid retrieval
            top_k: Number of top results to return after reranking.
                   If None, returns all reranked candidates.

        Returns:
            Reranked list of (doc_id, reranker_score, content) tuples,
            sorted by reranker_score descending.

        Example:
            >>> candidates = [
            ...     ("doc1", 0.7, "EB-1A visa for extraordinary ability"),
            ...     ("doc2", 0.65, "Contract law fundamentals"),
            ...     ("doc3", 0.6, "EB-1A application requirements")
            ... ]
            >>> reranked = await reranker.rerank(
            ...     query="EB-1A extraordinary ability criteria",
            ...     candidates=candidates,
            ...     top_k=2
            ... )
            >>> # doc1 and doc3 should rank higher (relevant to query)
        """
        # Lazy load model
        self._load_model()

        if not candidates:
            return []

        # Extract content for scoring
        doc_ids = [doc_id for doc_id, _score, _content in candidates]
        contents = [content for _doc_id, _score, content in candidates]

        # Compute cross-encoder scores
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            self._compute_scores,
            query,
            contents,
        )

        # Combine with document IDs and content
        reranked = [
            (doc_id, float(score), content)
            for doc_id, score, content in zip(doc_ids, scores, contents, strict=False)
        ]

        # Sort by reranker score (descending)
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Apply top_k limit
        if top_k is not None:
            reranked = reranked[:top_k]

        return reranked

    def _compute_scores(
        self,
        query: str,
        documents: list[str],
    ) -> list[float]:
        """Compute relevance scores for query-document pairs.

        Args:
            query: Search query
            documents: List of document texts

        Returns:
            List of relevance scores (higher = more relevant)
        """
        import torch

        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Batch processing
        all_scores = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i : i + self.batch_size]

            # Tokenize
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.device)

            # Forward pass
            with torch.no_grad():
                outputs = self._model(**inputs)
                # Most reranker models output single logit per pair
                scores = outputs.logits.squeeze(-1)

            all_scores.extend(scores.cpu().tolist())

        return all_scores

    async def rerank_batch(
        self,
        queries: list[str],
        candidate_lists: list[list[tuple[DocumentID, Score, DocumentContent]]],
        top_k: int | None = None,
    ) -> list[list[tuple[DocumentID, Score, DocumentContent]]]:
        """Rerank multiple candidate lists in batch.

        Args:
            queries: List of search queries
            candidate_lists: List of candidate lists (one per query)
            top_k: Number of results to return per query

        Returns:
            List of reranked candidate lists (one per query)

        Example:
            >>> queries = ["EB-1A criteria", "visa requirements"]
            >>> candidates = [candidates_q1, candidates_q2]
            >>> reranked = await reranker.rerank_batch(
            ...     queries, candidates, top_k=5
            ... )
            >>> len(reranked)
            2
        """
        tasks = [
            self.rerank(query, candidates, top_k)
            for query, candidates in zip(queries, candidate_lists, strict=False)
        ]
        return await asyncio.gather(*tasks)

    def get_model_info(self) -> dict[str, Any]:
        """Get reranker model information.

        Returns:
            Dictionary with model configuration

        Example:
            >>> info = reranker.get_model_info()
            >>> print(f"Model: {info['model_name']}")
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "loaded": self._model is not None,
        }


class HybridRetrieverWithReranking:
    """Hybrid retriever with integrated cross-encoder reranking.

    Combines sparse + dense retrieval via RRF fusion, then applies
    cross-encoder reranking for final precision-focused ordering.

    This is the complete pipeline:
    1. Parallel sparse (BM25) + dense (vector) retrieval
    2. Reciprocal Rank Fusion (RRF)
    3. Cross-encoder reranking

    Attributes:
        hybrid_retriever: Base hybrid retriever (sparse + dense + RRF)
        reranker: Cross-encoder reranker
        rerank_top_k: Number of candidates to rerank (for efficiency)

    Example:
        >>> from core.rag.fusion import HybridRetriever
        >>>
        >>> hybrid = HybridRetriever(sparse, dense)
        >>> reranker = CrossEncoderReranker()
        >>> retriever = HybridRetrieverWithReranking(hybrid, reranker)
        >>>
        >>> results = await retriever.search("EB-1A criteria", top_k=5)
    """

    def __init__(
        self,
        hybrid_retriever: Any,  # HybridRetriever
        reranker: CrossEncoderReranker,
        rerank_top_k: int = 100,
    ) -> None:
        """Initialize retriever with reranking.

        Args:
            hybrid_retriever: Base hybrid retriever
            reranker: Cross-encoder reranker
            rerank_top_k: Number of top fusion candidates to rerank.
                          Higher = more accurate but slower.
                          Typically 50-100 is good balance.

        Example:
            >>> # Rerank top 50 fusion candidates for efficiency
            >>> retriever = HybridRetrieverWithReranking(
            ...     hybrid, reranker, rerank_top_k=50
            ... )
        """
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker
        self.rerank_top_k = rerank_top_k

    async def search(
        self,
        query: str,
        document_store: dict[DocumentID, DocumentContent],
        top_k: int = 10,
    ) -> RankedResults:
        """Hybrid search with reranking.

        Args:
            query: Search query string
            document_store: Mapping from doc_id to full document content
                            (needed for reranking)
            top_k: Number of final results to return

        Returns:
            Reranked results as list of (doc_id, score) tuples

        Example:
            >>> doc_store = {
            ...     "doc1": "EB-1A visa for extraordinary ability...",
            ...     "doc2": "Contract law fundamentals...",
            ...     "doc3": "EB-1A application requirements..."
            ... }
            >>> results = await retriever.search(
            ...     query="EB-1A criteria",
            ...     document_store=doc_store,
            ...     top_k=5
            ... )
        """
        # Step 1: Hybrid retrieval (sparse + dense + RRF)
        fusion_results = await self.hybrid_retriever.search(
            query,
            top_k=self.rerank_top_k,  # Over-retrieve for reranking
        )

        # Step 2: Prepare candidates with content
        candidates = [
            (doc_id, score, document_store.get(doc_id, ""))
            for doc_id, score in fusion_results
            if doc_id in document_store  # Skip missing documents
        ]

        # Step 3: Rerank with cross-encoder
        reranked = await self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )

        # Step 4: Convert back to (doc_id, score) format
        final_results = [(doc_id, score) for doc_id, score, _content in reranked]

        return final_results

    async def search_batch(
        self,
        queries: list[str],
        document_store: dict[DocumentID, DocumentContent],
        top_k: int = 10,
    ) -> list[RankedResults]:
        """Batch hybrid search with reranking.

        Args:
            queries: List of search queries
            document_store: Document content mapping
            top_k: Number of results per query

        Returns:
            List of reranked result lists (one per query)

        Example:
            >>> queries = ["EB-1A criteria", "visa requirements"]
            >>> results = await retriever.search_batch(
            ...     queries, doc_store, top_k=5
            ... )
        """
        tasks = [self.search(query, document_store, top_k) for query in queries]
        return await asyncio.gather(*tasks)


async def create_reranker(
    model_name: str = "BAAI/bge-reranker-base",
    device: str = "cpu",
) -> CrossEncoderReranker:
    """Factory function to create cross-encoder reranker.

    Args:
        model_name: Hugging Face model identifier
        device: Computation device

    Returns:
        Initialized CrossEncoderReranker instance

    Example:
        >>> reranker = await create_reranker()
        >>> # Or with custom model
        >>> reranker = await create_reranker(
        ...     model_name="BAAI/bge-reranker-large",
        ...     device="cuda"
        ... )
    """
    return CrossEncoderReranker(model_name=model_name, device=device)


__all__ = [
    "CrossEncoderReranker",
    "HybridRetrieverWithReranking",
    "create_reranker",
]
