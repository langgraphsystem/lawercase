"""RAG Pipeline Agent - Retrieval-Augmented Generation for knowledge base search.

This agent provides:
- Semantic search over knowledge base
- Similar case finding
- Context enrichment for LLM queries
- Source attribution and ranking

Implementation phases:
- Phase 1: Keyword-based search (current)
- Phase 2: Embedding-based semantic search (future)
- Phase 3: Hybrid retrieval (future)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
import structlog

from ..memory.memory_manager import MemoryManager
from ..memory.models import MemoryRecord
from ..rag import Document, RAGPipeline, RAGResult

logger = structlog.get_logger(__name__)


# ========== MODELS ==========


class RagSource(BaseModel):
    """Source attribution for RAG result."""

    source_id: str = Field(..., description="Unique ID of source")
    source_type: str = Field(..., description="Type: memory, case, document")
    content: str = Field(..., description="Source content snippet")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class RagAnswer(BaseModel):
    """Answer from RAG pipeline."""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: list[RagSource] = Field(default_factory=list, description="Source attributions")
    context_used: str = Field(..., description="Context provided to LLM")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in answer")
    retrieval_time_ms: float = Field(ge=0.0, description="Time for retrieval in ms")
    generation_time_ms: float = Field(ge=0.0, description="Time for generation in ms")
    total_time_ms: float = Field(ge=0.0, description="Total time in ms")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class SimilarCase(BaseModel):
    """Similar case found through search."""

    case_id: str = Field(..., description="Case ID")
    case_title: str = Field(..., description="Case title")
    case_type: str = Field(..., description="Case type")
    similarity_score: float = Field(ge=0.0, le=1.0, description="Similarity score")
    matching_criteria: list[str] = Field(default_factory=list, description="Matching criteria")
    outcome: str | None = Field(None, description="Case outcome if known")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Case metadata")


class ContextEnrichment(BaseModel):
    """Enriched context for LLM."""

    original_query: str = Field(..., description="Original query")
    enriched_context: str = Field(..., description="Enriched context text")
    related_info: list[str] = Field(default_factory=list, description="Related information")
    legal_precedents: list[str] = Field(default_factory=list, description="Legal precedents")
    success_patterns: list[str] = Field(default_factory=list, description="Success patterns")
    sources_count: int = Field(ge=0, description="Number of sources used")


# ========== RAG PIPELINE AGENT ==========


class RagPipelineAgent:
    """
    RAG Pipeline Agent for knowledge base search and retrieval.

    Provides three main capabilities:
    1. arag() - Full RAG query with answer generation
    2. asearch_similar_cases() - Find similar cases
    3. aenrich_context() - Enrich context for LLM

    Phase 1 implementation uses keyword-based search.
    Future phases will add embeddings and hybrid retrieval.

    Example:
        >>> agent = RagPipelineAgent(memory_manager=memory)
        >>> answer = await agent.arag("What are EB-1A requirements?")
        >>> print(answer.answer)
        >>> print(f"Sources: {len(answer.sources)}")
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        rag_pipeline: RAGPipeline | None = None,
        cache_ttl_seconds: int = 3600,
    ):
        """
        Initialize RAG Pipeline Agent.

        Args:
            memory_manager: Memory manager for retrieval
            cache_ttl_seconds: TTL for query cache (default 1 hour)
        """
        self.memory = memory_manager or MemoryManager()
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.cache_ttl = cache_ttl_seconds
        self.logger = logger.bind(agent="rag_pipeline")

        # Simple query cache: query -> (answer, timestamp)
        self._query_cache: dict[str, tuple[RagAnswer, datetime]] = {}

        # Stats
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_retrieval_time_ms": 0.0,
        }

    async def aload_documents(self, documents: list[Document]) -> list[str]:
        """Ingest external documents into the RAG pipeline store."""
        chunks = await self.rag_pipeline.ingest(documents)
        return [chunk.chunk_id for chunk in chunks]

    async def arag(
        self,
        question: str,
        context: str | None = None,
        topk: int = 5,
        user_id: str | None = None,
        use_cache: bool = True,
    ) -> RagAnswer:
        """
        Main RAG query with retrieval and answer generation.

        Phase 1: Keyword-based retrieval from semantic memory.

        Args:
            question: User question
            context: Optional additional context
            topk: Number of results to retrieve
            user_id: User ID for filtering
            use_cache: Whether to use query cache

        Returns:
            RagAnswer with generated answer and sources

        Example:
            >>> answer = await agent.arag(
            ...     "What documents are required for EB-1A?",
            ...     topk=5
            ... )
            >>> print(answer.answer)
            >>> for source in answer.sources:
            ...     print(f"  - {source.content[:50]}...")
        """
        self.logger.info("rag_query_start", question=question[:100], topk=topk)

        start_time = datetime.utcnow()
        self._stats["total_queries"] += 1

        # Check cache
        if use_cache:
            cached = self._check_cache(question)
            if cached:
                self._stats["cache_hits"] += 1
                self.logger.info("rag_cache_hit", question=question[:50])
                return cached

        self._stats["cache_misses"] += 1

        retrieval_start = datetime.utcnow()

        pipeline_results: list[RAGResult] = []
        pipeline_context: dict[str, Any] | None = None
        store_chunks = self.rag_pipeline.store.iter_chunks()
        if store_chunks:
            pipeline_payload = await self.rag_pipeline.query(question, top_k=topk)
            pipeline_results = pipeline_payload.get("results", [])
            pipeline_context = pipeline_payload.get("context")

        retrieved_records = await self.memory.aretrieve(query=question, user_id=user_id, topk=topk)
        retrieval_time = (datetime.utcnow() - retrieval_start).total_seconds() * 1000

        pipeline_sources = self._convert_pipeline_results(pipeline_results)
        memory_sources = self._convert_to_sources(retrieved_records, question)

        sources = pipeline_sources + memory_sources

        # Build context for LLM
        context_parts = []
        if context:
            context_parts.append(f"Additional Context:\n{context}\n")

        if pipeline_context and pipeline_context.get("text"):
            context_parts.append("RAG Pipeline Context:")
            context_parts.append(pipeline_context["text"])

        if sources:
            context_parts.append("Retrieved Information:")
            for i, source in enumerate(sources, 1):
                context_parts.append(f"{i}. {source.content}")

        context_used = "\n\n".join(context_parts) if context_parts else "No context available."

        # Phase 1: Simple answer generation (placeholder - no LLM yet)
        generation_start = datetime.utcnow()
        answer_text = self._generate_answer_simple(question, context_used, sources)
        generation_time = (datetime.utcnow() - generation_start).total_seconds() * 1000

        # Calculate confidence
        confidence = self._calculate_confidence(sources, context_used)

        total_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Create answer
        answer = RagAnswer(
            query=question,
            answer=answer_text,
            sources=sources,
            context_used=context_used,
            confidence=confidence,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time,
        )

        # Cache result
        if use_cache:
            self._cache_result(question, answer)

        # Update stats
        self._update_stats(retrieval_time)

        self.logger.info(
            "rag_query_complete",
            sources_count=len(sources),
            confidence=confidence,
            total_time_ms=total_time,
        )

        return answer

    async def asearch_similar_cases(
        self,
        query: str,
        case_type: str | None = None,
        field: str | None = None,
        topk: int = 10,
        min_similarity: float = 0.3,
        user_id: str | None = None,
    ) -> list[SimilarCase]:
        """
        Search for similar cases in the knowledge base.

        Phase 1: Keyword matching with filtering.

        Args:
            query: Search query (description of case)
            case_type: Filter by case type (e.g., "immigration")
            field: Filter by field (e.g., "EB-1A")
            topk: Maximum number of results
            min_similarity: Minimum similarity threshold
            user_id: User ID for filtering

        Returns:
            List of similar cases ranked by similarity

        Example:
            >>> cases = await agent.asearch_similar_cases(
            ...     "AI researcher EB-1A petition",
            ...     case_type="immigration",
            ...     topk=5
            ... )
            >>> for case in cases:
            ...     print(f"{case.case_title}: {case.similarity_score:.2f}")
        """
        self.logger.info(
            "search_similar_cases",
            query=query[:100],
            case_type=case_type,
            topk=topk,
        )

        # Retrieve relevant memories
        retrieved = await self.memory.aretrieve(
            query=query,
            user_id=user_id,
            k=topk * 2,  # Retrieve more for filtering
        )

        # Convert to similar cases
        similar_cases: list[SimilarCase] = []

        for record in retrieved:
            # Try to extract case info from tags or metadata
            tags = record.tags or []

            # Filter by case_type if specified
            if case_type and case_type.lower() not in [t.lower() for t in tags]:
                continue

            # Filter by field if specified
            if field and field.lower() not in record.text.lower():
                continue

            # Calculate similarity (Phase 1: simple keyword matching)
            similarity = self._calculate_similarity_simple(query, record.text)

            if similarity < min_similarity:
                continue

            # Extract case info
            case_id = record.record_id
            case_title = self._extract_title(record.text, tags)
            case_type_extracted = self._extract_case_type(tags)
            matching_criteria = self._extract_matching_criteria(query, record.text)

            similar_case = SimilarCase(
                case_id=case_id,
                case_title=case_title,
                case_type=case_type_extracted,
                similarity_score=similarity,
                matching_criteria=matching_criteria,
                outcome=None,  # Would extract from record if available
                metadata={
                    "tags": tags,
                    "source": record.source,
                    "created_at": record.created_at.isoformat(),
                },
            )

            similar_cases.append(similar_case)

        # Sort by similarity
        similar_cases.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit to topk
        similar_cases = similar_cases[:topk]

        self.logger.info("search_complete", results_count=len(similar_cases))

        return similar_cases

    async def aenrich_context(
        self,
        query: str,
        base_context: str | None = None,
        include_legal_precedents: bool = True,
        include_success_patterns: bool = True,
        user_id: str | None = None,
    ) -> ContextEnrichment:
        """
        Enrich context with related information, legal precedents, and success patterns.

        Args:
            query: Query to enrich context for
            base_context: Base context to start with
            include_legal_precedents: Include legal precedents
            include_success_patterns: Include success patterns
            user_id: User ID for filtering

        Returns:
            ContextEnrichment with enriched context

        Example:
            >>> enrichment = await agent.aenrich_context(
            ...     "EB-1A petition for AI researcher",
            ...     include_legal_precedents=True
            ... )
            >>> print(enrichment.enriched_context)
            >>> print(f"Legal precedents: {len(enrichment.legal_precedents)}")
        """
        self.logger.info("enrich_context", query=query[:100])

        # Retrieve related information
        related_records = await self.memory.aretrieve(
            query=query,
            user_id=user_id,
            k=10,
        )

        related_info = [record.text for record in related_records[:5]]

        legal_precedents: list[str] = []
        success_patterns: list[str] = []

        # Search for legal precedents
        if include_legal_precedents:
            legal_query = f"legal precedent case law {query}"
            legal_records = await self.memory.aretrieve(
                query=legal_query,
                user_id=user_id,
                k=5,
            )

            for record in legal_records:
                if any(
                    keyword in record.text.lower()
                    for keyword in ["case", "precedent", "decision", "ruling"]
                ):
                    legal_precedents.append(record.text)

        # Search for success patterns
        if include_success_patterns:
            success_query = f"successful approved {query}"
            success_records = await self.memory.aretrieve(
                query=success_query,
                user_id=user_id,
                k=5,
            )

            for record in success_records:
                if any(
                    keyword in record.text.lower()
                    for keyword in ["success", "approved", "granted", "won"]
                ):
                    success_patterns.append(record.text)

        # Build enriched context
        context_parts = []

        if base_context:
            context_parts.append("Base Context:")
            context_parts.append(base_context)
            context_parts.append("")

        if related_info:
            context_parts.append("Related Information:")
            for i, info in enumerate(related_info, 1):
                context_parts.append(f"{i}. {info}")
            context_parts.append("")

        if legal_precedents:
            context_parts.append("Legal Precedents:")
            for i, precedent in enumerate(legal_precedents, 1):
                context_parts.append(f"{i}. {precedent}")
            context_parts.append("")

        if success_patterns:
            context_parts.append("Success Patterns:")
            for i, pattern in enumerate(success_patterns, 1):
                context_parts.append(f"{i}. {pattern}")

        enriched_context = "\n".join(context_parts)

        enrichment = ContextEnrichment(
            original_query=query,
            enriched_context=enriched_context,
            related_info=related_info,
            legal_precedents=legal_precedents,
            success_patterns=success_patterns,
            sources_count=len(related_records),
        )

        self.logger.info(
            "enrich_complete",
            related_info=len(related_info),
            legal_precedents=len(legal_precedents),
            success_patterns=len(success_patterns),
        )

        return enrichment

    # ========== HELPER METHODS ==========

    def _check_cache(self, question: str) -> RagAnswer | None:
        """Check if query is in cache and not expired."""
        if question not in self._query_cache:
            return None

        answer, timestamp = self._query_cache[question]

        # Check if expired
        if datetime.utcnow() - timestamp > timedelta(seconds=self.cache_ttl):
            del self._query_cache[question]
            return None

        return answer

    def _cache_result(self, question: str, answer: RagAnswer) -> None:
        """Cache query result."""
        self._query_cache[question] = (answer, datetime.utcnow())

        # Simple cache size limit
        if len(self._query_cache) > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(
                self._query_cache.items(),
                key=lambda x: x[1][1],  # Sort by timestamp
            )
            for key, _ in sorted_items[:100]:
                del self._query_cache[key]

    def _convert_pipeline_results(self, results: list[RAGResult]) -> list[RagSource]:
        sources: list[RagSource] = []
        for result in results:
            sources.append(
                RagSource(
                    source_id=result.chunk_id,
                    source_type=result.metadata.get("source_type", "rag"),
                    content=result.text,
                    relevance_score=result.score,
                    metadata=result.metadata,
                )
            )
        return sources

    def _convert_to_sources(
        self,
        records: list[MemoryRecord],
        query: str,
    ) -> list[RagSource]:
        """Convert memory records to RAG sources."""
        sources = []

        for record in records:
            # Calculate relevance (Phase 1: simple keyword matching)
            relevance = self._calculate_similarity_simple(query, record.text)

            source = RagSource(
                source_id=record.record_id,
                source_type="memory",
                content=record.text,
                relevance_score=relevance,
                metadata={
                    "source": record.source,
                    "tags": record.tags or [],
                    "user_id": record.user_id,
                    "created_at": record.created_at.isoformat(),
                },
            )

            sources.append(source)

        # Sort by relevance
        sources.sort(key=lambda x: x.relevance_score, reverse=True)

        return sources

    def _calculate_similarity_simple(self, query: str, text: str) -> float:
        """
        Calculate simple keyword-based similarity.

        Phase 1 implementation: keyword overlap.
        Future: Use embeddings for semantic similarity.
        """
        query_lower = query.lower()
        text_lower = text.lower()

        # Extract keywords (simple: words longer than 3 chars)
        query_keywords = {w for w in query_lower.split() if len(w) > 3}
        text_keywords = {w for w in text_lower.split() if len(w) > 3}

        if not query_keywords:
            return 0.0

        # Jaccard similarity
        intersection = len(query_keywords & text_keywords)
        union = len(query_keywords | text_keywords)

        if union == 0:
            return 0.0

        similarity = intersection / union

        # Boost if query appears as substring
        if query_lower in text_lower:
            similarity = min(1.0, similarity + 0.3)

        return similarity

    def _generate_answer_simple(
        self,
        question: str,
        context: str,
        sources: list[RagSource],
    ) -> str:
        """
        Generate answer from context (Phase 1: simple extraction).

        Future: Use LLM for generation.
        """
        if not sources:
            return f"I don't have enough information to answer: {question}"

        # Simple answer: return most relevant source content
        top_source = sources[0]

        answer_parts = [
            "Based on the available information:",
            "",
            top_source.content,
        ]

        if len(sources) > 1:
            answer_parts.append("")
            answer_parts.append("Additional relevant information:")
            for source in sources[1:3]:  # Add 2 more sources
                answer_parts.append(f"- {source.content[:200]}...")

        return "\n".join(answer_parts)

    def _calculate_confidence(self, sources: list[RagSource], context: str) -> float:
        """Calculate confidence in answer."""
        if not sources:
            return 0.0

        # Base confidence from average relevance
        avg_relevance = sum(s.relevance_score for s in sources) / len(sources)

        # Boost if multiple high-relevance sources
        high_relevance_count = len([s for s in sources if s.relevance_score > 0.7])
        quantity_boost = min(0.2, high_relevance_count * 0.05)

        confidence = min(1.0, avg_relevance + quantity_boost)

        return confidence

    def _extract_title(self, text: str, tags: list[str]) -> str:
        """Extract case title from text or tags."""
        # Try to extract from first line
        first_line = text.split("\n")[0]
        if len(first_line) < 100:
            return first_line

        # Try to extract from tags
        for tag in tags:
            if "title" in tag.lower():
                return tag

        # Default: truncate text
        return text[:80] + "..." if len(text) > 80 else text

    def _extract_case_type(self, tags: list[str]) -> str:
        """Extract case type from tags."""
        case_types = ["immigration", "corporate", "family", "criminal", "civil"]

        for tag in tags:
            tag_lower = tag.lower()
            for case_type in case_types:
                if case_type in tag_lower:
                    return case_type

        return "unknown"

    def _extract_matching_criteria(self, query: str, text: str) -> list[str]:
        """Extract matching criteria between query and text."""
        query_keywords = {w.lower() for w in query.split() if len(w) > 3}
        text_lower = text.lower()

        matching = []
        for keyword in query_keywords:
            if keyword in text_lower:
                matching.append(keyword)

        return matching[:5]  # Top 5

    def _update_stats(self, retrieval_time: float) -> None:
        """Update running statistics."""
        # Update average retrieval time (exponential moving average)
        alpha = 0.1  # Smoothing factor
        self._stats["avg_retrieval_time_ms"] = (
            alpha * retrieval_time + (1 - alpha) * self._stats["avg_retrieval_time_ms"]
        )

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        cache_hit_rate = (
            self._stats["cache_hits"] / self._stats["total_queries"]
            if self._stats["total_queries"] > 0
            else 0.0
        )

        return {
            **self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._query_cache),
        }

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._query_cache.clear()
        self.logger.info("cache_cleared")
