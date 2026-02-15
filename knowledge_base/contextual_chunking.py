"""Contextual Chunking for RAG.

Intelligent document chunking that preserves semantic context:
- Semantic boundary detection
- Context window overlapping
- Metadata preservation
- Hierarchical chunking
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    FIXED = "fixed"  # Fixed size chunks
    SEMANTIC = "semantic"  # Semantic boundary detection
    HIERARCHICAL = "hierarchical"  # Multi-level chunks
    SLIDING = "sliding"  # Sliding window
    SENTENCE = "sentence"  # Sentence-based


@dataclass(slots=True)
class Chunk:
    """Single chunk of text."""

    id: str
    content: str
    start_idx: int
    end_idx: int
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Context fields
    context_before: str = ""
    context_after: str = ""
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)

    @property
    def with_context(self) -> str:
        """Get content with surrounding context."""
        parts = []
        if self.context_before:
            parts.append(f"[Context: {self.context_before}]")
        parts.append(self.content)
        if self.context_after:
            parts.append(f"[Context: {self.context_after}]")
        return "\n".join(parts)


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""

    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    chunk_size: int = 512  # Target tokens per chunk
    chunk_overlap: int = 50  # Overlap tokens
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 1000  # Maximum chunk size
    context_window: int = 100  # Context to preserve
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True


@dataclass
class ChunkingResult:
    """Result of chunking operation."""

    chunks: list[Chunk]
    total_tokens: int
    avg_chunk_size: int
    strategy: ChunkingStrategy
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextualChunker:
    """Intelligent document chunker with context preservation.

    Features:
    - Multiple chunking strategies
    - Semantic boundary detection
    - Context window preservation
    - Hierarchical structure support

    Usage:
        chunker = ContextualChunker()

        result = chunker.chunk(
            text="Your document text...",
            strategy=ChunkingStrategy.SEMANTIC,
        )

        for chunk in result.chunks:
            print(f"Chunk {chunk.id}: {chunk.content[:50]}...")
            print(f"  Context: {chunk.context_before[:30]}...")
    """

    def __init__(
        self,
        config: ChunkingConfig | None = None,
        tokenizer: Callable[[str], int] | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.tokenizer = tokenizer or self._default_tokenizer

    def _default_tokenizer(self, text: str) -> int:
        """Default token counter (approximation)."""
        return len(text) // 4

    def chunk(
        self,
        text: str,
        strategy: ChunkingStrategy | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChunkingResult:
        """Chunk text using specified strategy.

        Args:
            text: Text to chunk
            strategy: Chunking strategy (uses config default if None)
            metadata: Metadata to attach to chunks

        Returns:
            ChunkingResult with list of chunks
        """
        strategy = strategy or self.config.strategy
        metadata = metadata or {}

        if strategy == ChunkingStrategy.FIXED:
            chunks = self._chunk_fixed(text)
        elif strategy == ChunkingStrategy.SEMANTIC:
            chunks = self._chunk_semantic(text)
        elif strategy == ChunkingStrategy.HIERARCHICAL:
            chunks = self._chunk_hierarchical(text)
        elif strategy == ChunkingStrategy.SLIDING:
            chunks = self._chunk_sliding(text)
        elif strategy == ChunkingStrategy.SENTENCE:
            chunks = self._chunk_sentence(text)
        else:
            chunks = self._chunk_fixed(text)

        # Add context to chunks
        chunks = self._add_context(chunks, text)

        # Add metadata
        for chunk in chunks:
            chunk.metadata.update(metadata)

        total_tokens = sum(c.tokens for c in chunks)
        avg_size = total_tokens // max(1, len(chunks))

        logger.info(
            "chunking.complete",
            strategy=strategy.value,
            chunks=len(chunks),
            total_tokens=total_tokens,
            avg_size=avg_size,
        )

        return ChunkingResult(
            chunks=chunks,
            total_tokens=total_tokens,
            avg_chunk_size=avg_size,
            strategy=strategy,
            metadata={"source_length": len(text)},
        )

    def _chunk_fixed(self, text: str) -> list[Chunk]:
        """Fixed-size chunking."""
        chunks = []
        char_size = self.config.chunk_size * 4  # Approximate chars
        overlap_chars = self.config.chunk_overlap * 4

        start = 0
        chunk_id = 0

        while start < len(text):
            end = min(start + char_size, len(text))

            # Try to break at word boundary
            if end < len(text):
                space_idx = text.rfind(" ", start, end)
                if space_idx > start + char_size // 2:
                    end = space_idx

            content = text[start:end].strip()
            if content:
                chunks.append(
                    Chunk(
                        id=f"chunk_{chunk_id}",
                        content=content,
                        start_idx=start,
                        end_idx=end,
                        tokens=self.tokenizer(content),
                    )
                )
                chunk_id += 1

            start = end - overlap_chars

        return chunks

    def _chunk_semantic(self, text: str) -> list[Chunk]:
        """Semantic boundary-based chunking."""
        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_content = ""
        current_start = 0
        chunk_id = 0
        char_pos = 0

        for para in paragraphs:
            para_tokens = self.tokenizer(para)
            current_tokens = self.tokenizer(current_content)

            # Check if adding paragraph exceeds limit
            if current_tokens + para_tokens > self.config.chunk_size:
                # Save current chunk if not empty
                if current_content.strip():
                    chunks.append(
                        Chunk(
                            id=f"chunk_{chunk_id}",
                            content=current_content.strip(),
                            start_idx=current_start,
                            end_idx=char_pos,
                            tokens=current_tokens,
                        )
                    )
                    chunk_id += 1

                # Start new chunk
                current_content = para
                current_start = char_pos
            else:
                current_content += "\n\n" + para if current_content else para

            char_pos += len(para) + 2  # +2 for paragraph separator

        # Add final chunk
        if current_content.strip():
            chunks.append(
                Chunk(
                    id=f"chunk_{chunk_id}",
                    content=current_content.strip(),
                    start_idx=current_start,
                    end_idx=char_pos,
                    tokens=self.tokenizer(current_content),
                )
            )

        return chunks

    def _chunk_hierarchical(self, text: str) -> list[Chunk]:
        """Hierarchical chunking with parent-child relationships."""
        # Level 1: Large chunks (sections)
        sections = self._split_sections(text)
        chunks = []
        for section_id, section in enumerate(sections):
            # Create parent chunk
            parent = Chunk(
                id=f"section_{section_id}",
                content=section["content"],
                start_idx=section["start"],
                end_idx=section["end"],
                tokens=self.tokenizer(section["content"]),
                metadata={"level": 0, "heading": section.get("heading", "")},
            )

            para_chunks = self._chunk_semantic(section["content"])
            child_ids = []

            for para_chunk in para_chunks:
                para_chunk.id = f"section_{section_id}_para_{para_chunk.id}"
                para_chunk.parent_id = parent.id
                para_chunk.metadata["level"] = 1
                para_chunk.start_idx += section["start"]
                para_chunk.end_idx += section["start"]
                child_ids.append(para_chunk.id)
                chunks.append(para_chunk)

            parent.child_ids = child_ids
            chunks.insert(0, parent)

        return chunks

    def _chunk_sliding(self, text: str) -> list[Chunk]:
        """Sliding window chunking with overlap."""
        chunks = []
        sentences = self._split_sentences(text)

        window_size = self.config.chunk_size
        step_size = window_size - self.config.chunk_overlap

        current_sentences: list[str] = []
        current_tokens = 0
        chunk_id = 0
        char_pos = 0
        start_pos = 0

        for sentence in sentences:
            sent_tokens = self.tokenizer(sentence)

            current_sentences.append(sentence)
            current_tokens += sent_tokens

            if current_tokens >= window_size:
                # Create chunk
                content = " ".join(current_sentences)
                chunks.append(
                    Chunk(
                        id=f"chunk_{chunk_id}",
                        content=content,
                        start_idx=start_pos,
                        end_idx=char_pos + len(sentence),
                        tokens=current_tokens,
                    )
                )
                chunk_id += 1

                # Slide window
                while current_tokens > step_size and current_sentences:
                    removed = current_sentences.pop(0)
                    current_tokens -= self.tokenizer(removed)
                    start_pos += len(removed) + 1

            char_pos += len(sentence) + 1

        # Add final chunk
        if current_sentences:
            content = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    id=f"chunk_{chunk_id}",
                    content=content,
                    start_idx=start_pos,
                    end_idx=char_pos,
                    tokens=current_tokens,
                )
            )

        return chunks

    def _chunk_sentence(self, text: str) -> list[Chunk]:
        """Sentence-based chunking."""
        sentences = self._split_sentences(text)
        chunks = []
        current_content = ""
        current_start = 0
        chunk_id = 0
        char_pos = 0

        for sent_item in sentences:
            sent_tokens = self.tokenizer(sent_item)
            current_tokens = self.tokenizer(current_content)

            if current_tokens + sent_tokens > self.config.chunk_size:
                if current_content.strip():
                    chunks.append(
                        Chunk(
                            id=f"chunk_{chunk_id}",
                            content=current_content.strip(),
                            start_idx=current_start,
                            end_idx=char_pos,
                            tokens=current_tokens,
                        )
                    )
                    chunk_id += 1

                current_content = sent_item
                current_start = char_pos
            else:
                current_content += " " + sent_item if current_content else sent_item

            char_pos += len(sent_item) + 1

        if current_content.strip():
            chunks.append(
                Chunk(
                    id=f"chunk_{chunk_id}",
                    content=current_content.strip(),
                    start_idx=current_start,
                    end_idx=char_pos,
                    tokens=self.tokenizer(current_content),
                )
            )

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentence_endings = re.compile(r"(?<=[.!?])\s+")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_sections(self, text: str) -> list[dict[str, Any]]:
        """Split text into sections based on headings."""
        # Match markdown-style headings
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections = []
        last_end = 0
        last_heading = ""

        for match in heading_pattern.finditer(text):
            if last_end > 0 or match.start() > 0:
                # Save previous section
                content = text[last_end : match.start()].strip()
                if content:
                    sections.append(
                        {
                            "heading": last_heading,
                            "content": content,
                            "start": last_end,
                            "end": match.start(),
                        }
                    )

            last_end = match.end()
            last_heading = match.group(2)

        # Add final section
        if last_end < len(text):
            sections.append(
                {
                    "heading": last_heading,
                    "content": text[last_end:].strip(),
                    "start": last_end,
                    "end": len(text),
                }
            )

        # If no sections found, return whole text as one section
        if not sections:
            sections.append(
                {
                    "heading": "",
                    "content": text,
                    "start": 0,
                    "end": len(text),
                }
            )

        return sections

    def _add_context(self, chunks: list[Chunk], full_text: str) -> list[Chunk]:
        """Add context before/after each chunk."""
        context_chars = self.config.context_window * 4

        for chunk in chunks:
            # Context before
            start = max(0, chunk.start_idx - context_chars)
            if start < chunk.start_idx:
                context = full_text[start : chunk.start_idx].strip()
                # Take last sentence or phrase
                if ". " in context:
                    context = context.split(". ")[-1]
                chunk.context_before = context[:200]

            # Context after
            end = min(len(full_text), chunk.end_idx + context_chars)
            if end > chunk.end_idx:
                context = full_text[chunk.end_idx : end].strip()
                # Take first sentence or phrase
                if ". " in context:
                    context = context.split(". ")[0]
                chunk.context_after = context[:200]

        return chunks


# Convenience functions
def chunk_document(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    chunk_size: int = 512,
    **kwargs: Any,
) -> ChunkingResult:
    """Convenience function to chunk a document."""
    config = ChunkingConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        **kwargs,
    )
    chunker = ContextualChunker(config=config)
    return chunker.chunk(text, strategy=strategy)


def chunk_for_embedding(
    text: str,
    max_tokens: int = 512,
) -> list[str]:
    """Chunk text optimized for embedding."""
    result = chunk_document(
        text,
        strategy=ChunkingStrategy.SEMANTIC,
        chunk_size=max_tokens,
    )
    return [chunk.content for chunk in result.chunks]
