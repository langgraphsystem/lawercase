"""Context Compressor for reducing context size.

Provides multiple strategies for intelligent context compression:
- Truncation: Simple cut at limit
- Summarization: LLM-based summary
- Extraction: Key sentence extraction
- Chunking: Split and select best chunks
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class CompressionStrategy(str, Enum):
    """Available compression strategies."""

    TRUNCATE = "truncate"  # Simple truncation
    SUMMARIZE = "summarize"  # LLM summarization
    EXTRACT = "extract"  # Key sentence extraction
    CHUNK_SELECT = "chunk_select"  # Chunk and select best
    HYBRID = "hybrid"  # Combined approach


@dataclass(slots=True)
class CompressionResult:
    """Result of context compression."""

    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy_used: CompressionStrategy
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.compressed_tokens


class BaseCompressor(ABC):
    """Abstract base for compression strategies."""

    @abstractmethod
    def compress(
        self,
        text: str,
        target_tokens: int,
        **kwargs: Any,
    ) -> str:
        """Compress text to target token count."""


class TruncateCompressor(BaseCompressor):
    """Simple truncation compressor."""

    def __init__(self, preserve_end: bool = False) -> None:
        """
        Args:
            preserve_end: If True, keep end instead of beginning
        """
        self.preserve_end = preserve_end

    def compress(
        self,
        text: str,
        target_tokens: int,
        **kwargs: Any,
    ) -> str:
        """Truncate text to target tokens."""
        # Estimate: ~4 chars per token
        target_chars = target_tokens * 4

        if len(text) <= target_chars:
            return text

        if self.preserve_end:
            return "..." + text[-target_chars:]
        return text[:target_chars] + "..."


class ExtractCompressor(BaseCompressor):
    """Extract key sentences based on scoring."""

    def __init__(
        self,
        sentence_scorer: Callable[[str, str], float] | None = None,
    ) -> None:
        """
        Args:
            sentence_scorer: Custom function to score sentences
        """
        self.sentence_scorer = sentence_scorer or self._default_scorer

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _default_scorer(self, sentence: str, context: str) -> float:
        """Default sentence scoring based on length and position."""
        # Prefer medium-length sentences
        words = len(sentence.split())
        length_score = min(words / 20, 1.0) if words < 20 else max(0.5, 1.0 - (words - 20) / 50)

        # Bonus for sentences with important markers
        markers = ["important", "key", "note", "significant", "must", "required"]
        marker_score = 0.2 if any(m in sentence.lower() for m in markers) else 0

        return length_score + marker_score

    def compress(
        self,
        text: str,
        target_tokens: int,
        query: str = "",
        **kwargs: Any,
    ) -> str:
        """Extract key sentences to fit target."""
        sentences = self._split_sentences(text)

        if not sentences:
            return text[: target_tokens * 4]

        # Score sentences
        scored = []
        for i, sent in enumerate(sentences):
            _score = self.sentence_scorer(sent, query or text)
            # Slight position bias (earlier = better)
            position_bonus = 0.1 * (1 - i / len(sentences))
            scored.append((sent, _score + position_bonus, len(sent) // 4))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select sentences within budget
        selected = []
        total_tokens = 0

        for sent, _score, tokens in scored:
            if total_tokens + tokens <= target_tokens:
                selected.append((sent, sentences.index(sent)))
                total_tokens += tokens

        # Restore original order
        selected.sort(key=lambda x: x[1])

        return " ".join(sent for sent, _ in selected)


class ChunkSelectCompressor(BaseCompressor):
    """Split into chunks and select most relevant."""

    def __init__(
        self,
        chunk_size: int = 500,  # tokens per chunk
        overlap: int = 50,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        # Convert to approximate characters
        chunk_chars = self.chunk_size * 4
        overlap_chars = self.overlap * 4

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_chars
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(". ")
                if last_period > chunk_chars // 2:
                    chunk = chunk[: last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - overlap_chars

        return chunks

    def _score_chunk(self, chunk: str, query: str) -> float:
        """Score chunk relevance to query."""
        if not query:
            return 0.5

        query_words = set(query.lower().split())
        chunk_words = set(chunk.lower().split())

        overlap = len(query_words & chunk_words)
        return overlap / max(len(query_words), 1)

    def compress(
        self,
        text: str,
        target_tokens: int,
        query: str = "",
        **kwargs: Any,
    ) -> str:
        """Chunk and select best chunks."""
        chunks = self._chunk_text(text)

        if not chunks:
            return text[: target_tokens * 4]

        # Score chunks
        scored = [(chunk, self._score_chunk(chunk, query)) for chunk in chunks]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select chunks within budget
        selected = []
        total_tokens = 0

        for chunk, _ in scored:
            chunk_tokens = len(chunk) // 4
            if total_tokens + chunk_tokens <= target_tokens:
                selected.append(chunk)
                total_tokens += chunk_tokens

        return "\n\n".join(selected)


class ContextCompressor:
    """Main context compressor with multiple strategies.

    Usage:
        compressor = ContextCompressor()

        result = await compressor.compress(
            text=long_document,
            target_tokens=2000,
            strategy=CompressionStrategy.EXTRACT,
            query="EB-1A criteria"
        )

        print(f"Compressed from {result.original_tokens} to {result.compressed_tokens}")
        print(f"Ratio: {result.compression_ratio:.2%}")
    """

    def __init__(
        self,
        llm_summarizer: Callable[[str, int], str] | None = None,
    ) -> None:
        """Initialize compressor.

        Args:
            llm_summarizer: Optional LLM function for summarization
                           signature: (text, target_tokens) -> summary
        """
        self.llm_summarizer = llm_summarizer

        # Initialize strategy compressors
        self._truncate = TruncateCompressor()
        self._extract = ExtractCompressor()
        self._chunk = ChunkSelectCompressor()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~4 chars per token)."""
        return len(text) // 4

    async def compress(
        self,
        text: str,
        target_tokens: int,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        query: str = "",
        **kwargs: Any,
    ) -> CompressionResult:
        """Compress text to target token count.

        Args:
            text: Text to compress
            target_tokens: Target token budget
            strategy: Compression strategy to use
            query: Optional query for relevance-based compression
            **kwargs: Additional strategy-specific options

        Returns:
            CompressionResult with compressed text and metrics
        """
        original_tokens = self._estimate_tokens(text)

        # No compression needed
        if original_tokens <= target_tokens:
            return CompressionResult(
                original_text=text,
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                strategy_used=strategy,
            )

        # Apply compression strategy
        if strategy == CompressionStrategy.TRUNCATE:
            compressed = self._truncate.compress(text, target_tokens)

        elif strategy == CompressionStrategy.EXTRACT:
            compressed = self._extract.compress(text, target_tokens, query=query)

        elif strategy == CompressionStrategy.CHUNK_SELECT:
            compressed = self._chunk.compress(text, target_tokens, query=query)

        elif strategy == CompressionStrategy.SUMMARIZE:
            if self.llm_summarizer:
                compressed = await self._async_summarize(text, target_tokens)
            else:
                # Fallback to extraction
                compressed = self._extract.compress(text, target_tokens, query=query)

        else:  # HYBRID
            compressed = await self._hybrid_compress(text, target_tokens, query)

        compressed_tokens = self._estimate_tokens(compressed)

        return CompressionResult(
            original_text=text,
            compressed_text=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens,
            strategy_used=strategy,
            metadata={"query": query},
        )

    async def _async_summarize(self, text: str, target_tokens: int) -> str:
        """Summarize using LLM (if available)."""
        import asyncio

        if self.llm_summarizer:
            # Check if it's async
            result = self.llm_summarizer(text, target_tokens)
            if asyncio.iscoroutine(result):
                return await result
            return result

        # Fallback
        return self._extract.compress(text, target_tokens)

    async def _hybrid_compress(
        self,
        text: str,
        target_tokens: int,
        query: str,
    ) -> str:
        """Hybrid compression: extract + chunk select."""
        original_tokens = self._estimate_tokens(text)

        if original_tokens < target_tokens * 2:
            # Close to target, use extraction
            return self._extract.compress(text, target_tokens, query=query)
        # Far from target, use chunking first
        interim_target = target_tokens * 2
        chunked = self._chunk.compress(text, interim_target, query=query)
        return self._extract.compress(chunked, target_tokens, query=query)

    def compress_sync(
        self,
        text: str,
        target_tokens: int,
        strategy: CompressionStrategy = CompressionStrategy.EXTRACT,
        query: str = "",
    ) -> CompressionResult:
        """Synchronous compression (no LLM summarization)."""
        original_tokens = self._estimate_tokens(text)

        if original_tokens <= target_tokens:
            return CompressionResult(
                original_text=text,
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                strategy_used=strategy,
            )

        if strategy == CompressionStrategy.TRUNCATE:
            compressed = self._truncate.compress(text, target_tokens)
        elif strategy == CompressionStrategy.CHUNK_SELECT:
            compressed = self._chunk.compress(text, target_tokens, query=query)
        else:
            compressed = self._extract.compress(text, target_tokens, query=query)

        compressed_tokens = self._estimate_tokens(compressed)

        return CompressionResult(
            original_text=text,
            compressed_text=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens,
            strategy_used=strategy,
        )
