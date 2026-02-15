"""Context Synthesizer for merging isolated context results.

Combines results from multiple isolated contexts:
- Result aggregation
- Deduplication
- Ranking by relevance
- Summary generation
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from .context_compressor import CompressionStrategy, ContextCompressor
from .isolated_context import ContextState, IsolatedContext, IsolatedContextPool

logger = structlog.get_logger(__name__)


class SynthesisStrategy(str, Enum):
    """Strategies for synthesizing multiple results."""

    CONCATENATE = "concatenate"  # Simple concatenation
    DEDUPLICATE = "deduplicate"  # Remove duplicates
    SUMMARIZE = "summarize"  # LLM summarization
    RANK_SELECT = "rank_select"  # Rank and select top
    HIERARCHICAL = "hierarchical"  # Tree-based synthesis


@dataclass(slots=True)
class SynthesisResult:
    """Result of context synthesis."""

    content: str
    source_count: int
    total_input_tokens: int
    output_tokens: int
    compression_ratio: float
    strategy_used: SynthesisStrategy
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisConfig:
    """Configuration for synthesis."""

    strategy: SynthesisStrategy = SynthesisStrategy.DEDUPLICATE
    max_output_tokens: int = 10000
    include_source_labels: bool = True
    preserve_order: bool = False
    min_content_length: int = 50
    dedup_threshold: float = 0.85  # Similarity threshold for dedup


class ContextSynthesizer:
    """Synthesize results from multiple isolated contexts.

    Features:
    - Multiple synthesis strategies
    - Deduplication of similar content
    - Compression when needed
    - Source tracking

    Usage:
        synthesizer = ContextSynthesizer()

        # From pool
        result = await synthesizer.synthesize_pool(pool, query="main question")

        # From contexts list
        result = await synthesizer.synthesize(
            contexts=[ctx1, ctx2, ctx3],
            strategy=SynthesisStrategy.SUMMARIZE,
        )
    """

    def __init__(
        self,
        config: SynthesisConfig | None = None,
        llm_summarizer: Callable[[str, int], str] | None = None,
    ) -> None:
        """Initialize synthesizer.

        Args:
            config: Synthesis configuration
            llm_summarizer: Optional LLM function for summarization
        """
        self.config = config or SynthesisConfig()
        self.llm_summarizer = llm_summarizer
        self.compressor = ContextCompressor()

    async def synthesize(
        self,
        contexts: list[IsolatedContext],
        query: str = "",
        strategy: SynthesisStrategy | None = None,
        max_tokens: int | None = None,
    ) -> SynthesisResult:
        """Synthesize results from multiple contexts.

        Args:
            contexts: List of isolated contexts with results
            query: Original query for relevance scoring
            strategy: Override default strategy
            max_tokens: Override max output tokens

        Returns:
            SynthesisResult with combined content
        """
        strategy = strategy or self.config.strategy
        max_tokens = max_tokens or self.config.max_output_tokens

        # Filter to completed contexts with results
        valid_contexts = [
            ctx for ctx in contexts if ctx.state == ContextState.COMPLETED and ctx.result
        ]

        if not valid_contexts:
            return SynthesisResult(
                content="",
                source_count=0,
                total_input_tokens=0,
                output_tokens=0,
                compression_ratio=1.0,
                strategy_used=strategy,
            )

        # Get results
        results = [(ctx.name or ctx.id, ctx.result) for ctx in valid_contexts]
        total_input_tokens = sum(len(r[1]) // 4 for r in results)

        # Apply synthesis strategy
        if strategy == SynthesisStrategy.CONCATENATE:
            content = self._concatenate(results)
        elif strategy == SynthesisStrategy.DEDUPLICATE:
            content = self._deduplicate(results)
        elif strategy == SynthesisStrategy.RANK_SELECT:
            content = self._rank_select(results, query, max_tokens)
        elif strategy == SynthesisStrategy.SUMMARIZE:
            content = await self._summarize(results, query, max_tokens)
        elif strategy == SynthesisStrategy.HIERARCHICAL:
            content = await self._hierarchical(results, query, max_tokens)
        else:
            content = self._concatenate(results)

        # Compress if still over budget
        output_tokens = len(content) // 4
        compression_ratio = 1.0

        if output_tokens > max_tokens:
            compressed = await self.compressor.compress(
                text=content,
                target_tokens=max_tokens,
                strategy=CompressionStrategy.EXTRACT,
                query=query,
            )
            content = compressed.compressed_text
            output_tokens = compressed.compressed_tokens
            compression_ratio = compressed.compression_ratio

        return SynthesisResult(
            content=content,
            source_count=len(valid_contexts),
            total_input_tokens=total_input_tokens,
            output_tokens=output_tokens,
            compression_ratio=output_tokens / max(1, total_input_tokens),
            strategy_used=strategy,
            sources=[ctx.name or ctx.id for ctx in valid_contexts],
        )

    async def synthesize_pool(
        self,
        pool: IsolatedContextPool,
        query: str = "",
        strategy: SynthesisStrategy | None = None,
        include_failed: bool = False,
    ) -> SynthesisResult:
        """Synthesize all results from a context pool.

        Args:
            pool: Context pool with completed tasks
            query: Original query
            strategy: Synthesis strategy
            include_failed: Include failed contexts

        Returns:
            SynthesisResult
        """
        contexts = pool.get_completed()

        if include_failed:
            failed = [
                ctx
                for ctx in pool._contexts.values()
                if ctx.state == ContextState.FAILED and ctx.result
            ]
            contexts.extend(failed)

        return await self.synthesize(contexts, query, strategy)

    def _concatenate(self, results: list[tuple[str, str]]) -> str:
        """Simple concatenation with source labels."""
        parts = []

        for source, content in results:
            if self.config.include_source_labels:
                parts.append(f"## Source: {source}\n{content}")
            else:
                parts.append(content)

        return "\n\n---\n\n".join(parts)

    def _deduplicate(self, results: list[tuple[str, str]]) -> str:
        """Deduplicate similar content."""
        unique_results = []
        seen_hashes: set[int] = set()

        for source, content in results:
            # Simple hash-based dedup (could use embeddings for better results)
            content_hash = hash(content.lower().strip()[:500])

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append((source, content))

        return self._concatenate(unique_results)

    def _rank_select(
        self,
        results: list[tuple[str, str]],
        query: str,
        max_tokens: int,
    ) -> str:
        """Rank by relevance and select top results."""
        from .priority_scorer import PriorityScorer

        scorer = PriorityScorer()

        # Score each result
        scored = []
        for source, content in results:
            score = scorer.score_item(content, query)
            scored.append((source, content, score.score))

        # Sort by score
        scored.sort(key=lambda x: x[2], reverse=True)

        # Select within budget
        selected = []
        total_tokens = 0

        for source, content, _ in scored:
            tokens = len(content) // 4
            if total_tokens + tokens <= max_tokens:
                selected.append((source, content))
                total_tokens += tokens

        return self._concatenate(selected)

    async def _summarize(
        self,
        results: list[tuple[str, str]],
        query: str,
        max_tokens: int,
    ) -> str:
        """Summarize using LLM (if available)."""
        combined = self._concatenate(results)

        if self.llm_summarizer:
            try:
                prompt = f"""Synthesize the following research results into a coherent summary.
Focus on answering: {query}

Results:
{combined}

Provide a comprehensive summary that:
1. Highlights key findings
2. Notes any conflicting information
3. Draws conclusions where possible
"""
                summary = self.llm_summarizer(prompt, max_tokens)
                if asyncio.iscoroutine(summary):
                    summary = await summary
                return summary
            except Exception as e:
                logger.warning("synthesis.summarize_failed", error=str(e))

        # Fallback to extraction
        return self._rank_select(results, query, max_tokens)

    async def _hierarchical(
        self,
        results: list[tuple[str, str]],
        query: str,
        max_tokens: int,
    ) -> str:
        """Hierarchical synthesis (merge pairs, then merge results)."""
        if len(results) <= 2:
            return await self._summarize(results, query, max_tokens)

        # Split into pairs and summarize each
        mid = len(results) // 2
        left_results = results[:mid]
        right_results = results[mid:]

        # Recursive synthesis
        left_synthesis = await self._summarize(left_results, query, max_tokens // 2)
        right_synthesis = await self._summarize(right_results, query, max_tokens // 2)

        # Final merge
        final_results = [
            ("left_group", left_synthesis),
            ("right_group", right_synthesis),
        ]

        return await self._summarize(final_results, query, max_tokens)

    def mark_contexts_merged(self, contexts: list[IsolatedContext]) -> None:
        """Mark contexts as merged after synthesis."""
        for ctx in contexts:
            ctx.state = ContextState.MERGED
