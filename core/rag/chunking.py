"""Contextual document chunking strategies for RAG pipeline.

Provides multiple chunking strategies to split large documents into
smaller, semantically meaningful chunks while preserving context.

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

# Type aliases
ChunkMetadata = dict[str, Any]


class ChunkingStrategy(Enum):
    """Chunking strategy options."""

    FIXED_SIZE = "fixed_size"  # Fixed character/token count
    SEMANTIC = "semantic"  # Sentence/paragraph boundaries
    RECURSIVE = "recursive"  # Recursive splitting by separators
    CONTEXTUAL = "contextual"  # Preserve context around chunks


@dataclass
class DocumentChunk:
    """Document chunk with metadata.

    Attributes:
        content: Chunk text content
        chunk_id: Unique identifier for this chunk
        start_pos: Start position in original document
        end_pos: End position in original document
        metadata: Additional metadata (source, page_num, etc.)

    Example:
        >>> chunk = DocumentChunk(
        ...     content="EB-1A visa requires extraordinary ability...",
        ...     chunk_id="doc1_chunk_0",
        ...     start_pos=0,
        ...     end_pos=100,
        ...     metadata={"source": "doc1.pdf", "page": 1}
        ... )
    """

    content: str
    chunk_id: str
    start_pos: int
    end_pos: int
    metadata: ChunkMetadata


class FixedSizeChunker:
    """Fixed-size chunking with optional overlap.

    Splits text into chunks of approximately equal size with configurable overlap.
    Simple and predictable, but may split sentences/paragraphs.

    Attributes:
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters

    Example:
        >>> chunker = FixedSizeChunker(chunk_size=500, overlap=50)
        >>> chunks = chunker.chunk_text("Long document text...")
        >>> len(chunks[0].content) <= 500
        True
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> None:
        """Initialize fixed-size chunker.

        Args:
            chunk_size: Target size for each chunk (characters)
            overlap: Number of overlapping characters between chunks
                     (helps preserve context across boundaries)

        Example:
            >>> # 1000 char chunks with 200 char overlap
            >>> chunker = FixedSizeChunker(chunk_size=1000, overlap=200)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        text: str,
        doc_id: str = "unknown",
        base_metadata: ChunkMetadata | None = None,
    ) -> list[DocumentChunk]:
        """Split text into fixed-size chunks.

        Args:
            text: Input text to chunk
            doc_id: Document identifier for chunk IDs
            base_metadata: Base metadata to include in all chunks

        Returns:
            List of DocumentChunk objects

        Example:
            >>> text = "A" * 2500  # 2500 characters
            >>> chunks = chunker.chunk_text(text, doc_id="doc1")
            >>> len(chunks)
            3  # Approximately 3 chunks
        """
        chunks = []
        base_metadata = base_metadata or {}

        start = 0
        chunk_idx = 0

        while start < len(text):
            # Extract chunk
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            # Create chunk
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                start_pos=start,
                end_pos=end,
                metadata={**base_metadata, "chunk_index": chunk_idx},
            )
            chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - self.overlap if end < len(text) else end
            chunk_idx += 1

        return chunks


class SemanticChunker:
    """Semantic chunking respecting sentence and paragraph boundaries.

    Splits text at natural boundaries (sentences, paragraphs) while
    maintaining target chunk size. More context-aware than fixed-size.

    Attributes:
        chunk_size: Target chunk size in characters
        min_chunk_size: Minimum chunk size (prevents tiny chunks)

    Example:
        >>> chunker = SemanticChunker(chunk_size=800)
        >>> chunks = chunker.chunk_text("First sentence. Second sentence...")
        >>> # Chunks split at sentence boundaries
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        min_chunk_size: int = 100,
    ) -> None:
        """Initialize semantic chunker.

        Args:
            chunk_size: Target size for chunks
            min_chunk_size: Minimum chunk size to avoid tiny fragments

        Example:
            >>> chunker = SemanticChunker(
            ...     chunk_size=1000,
            ...     min_chunk_size=200
            ... )
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        doc_id: str = "unknown",
        base_metadata: ChunkMetadata | None = None,
    ) -> list[DocumentChunk]:
        """Split text at semantic boundaries.

        Args:
            text: Input text to chunk
            doc_id: Document identifier
            base_metadata: Base metadata for chunks

        Returns:
            List of DocumentChunk objects

        Example:
            >>> text = "First paragraph.\\n\\nSecond paragraph."
            >>> chunks = chunker.chunk_text(text)
            >>> # Respects paragraph boundaries
        """
        chunks = []
        base_metadata = base_metadata or {}

        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        current_chunk = ""
        current_start = 0
        chunk_idx = 0

        for para_start, para_text in paragraphs:
            # If adding paragraph exceeds chunk_size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk) + len(para_text) > self.chunk_size
                and len(current_chunk) >= self.min_chunk_size
            ):
                # Create chunk
                chunk = DocumentChunk(
                    content=current_chunk.strip(),
                    chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                    start_pos=current_start,
                    end_pos=current_start + len(current_chunk),
                    metadata={**base_metadata, "chunk_index": chunk_idx},
                )
                chunks.append(chunk)

                # Reset for next chunk
                current_chunk = para_text
                current_start = para_start
                chunk_idx += 1
            else:
                # Add paragraph to current chunk
                if not current_chunk:
                    current_start = para_start
                current_chunk += para_text

        # Add final chunk
        if current_chunk.strip():
            chunk = DocumentChunk(
                content=current_chunk.strip(),
                chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                start_pos=current_start,
                end_pos=current_start + len(current_chunk),
                metadata={**base_metadata, "chunk_index": chunk_idx},
            )
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> list[tuple[int, str]]:
        """Split text into paragraphs.

        Args:
            text: Input text

        Returns:
            List of (start_position, paragraph_text) tuples
        """
        # Split on double newlines (paragraph separator)
        paragraphs = []
        current_pos = 0

        for para in re.split(r"\n\s*\n", text):
            if para.strip():
                # Find actual position in original text
                start = text.find(para, current_pos)
                paragraphs.append((start, para + "\n\n"))
                current_pos = start + len(para)

        return paragraphs


class RecursiveChunker:
    """Recursive chunking with multiple separator levels.

    Tries to split text using hierarchy of separators (paragraphs, then
    sentences, then words) to maintain maximum context while respecting
    size constraints.

    Attributes:
        chunk_size: Target chunk size
        separators: Ordered list of separators to try (highest to lowest priority)

    Example:
        >>> chunker = RecursiveChunker(chunk_size=1000)
        >>> chunks = chunker.chunk_text("Document with multiple paragraphs...")
        >>> # Splits at best available separator
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        separators: list[str] | None = None,
    ) -> None:
        """Initialize recursive chunker.

        Args:
            chunk_size: Target chunk size
            overlap: Overlap between chunks
            separators: Ordered list of separators (default: paragraph, sentence, word)

        Example:
            >>> # Default separators: paragraphs, sentences, words
            >>> chunker = RecursiveChunker(chunk_size=1000)
            >>>
            >>> # Custom separators
            >>> chunker = RecursiveChunker(
            ...     chunk_size=1000,
            ...     separators=["\\n\\n", "\\n", ". ", " "]
            ... )
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or [
            "\n\n",  # Paragraphs
            "\n",  # Lines
            ". ",  # Sentences
            " ",  # Words
        ]

    def chunk_text(
        self,
        text: str,
        doc_id: str = "unknown",
        base_metadata: ChunkMetadata | None = None,
    ) -> list[DocumentChunk]:
        """Split text recursively using separator hierarchy.

        Args:
            text: Input text to chunk
            doc_id: Document identifier
            base_metadata: Base metadata for chunks

        Returns:
            List of DocumentChunk objects

        Example:
            >>> text = "Paragraph 1\\n\\nParagraph 2\\n\\nParagraph 3"
            >>> chunks = chunker.chunk_text(text)
            >>> # Splits at paragraph boundaries if possible
        """
        base_metadata = base_metadata or {}
        splits = self._recursive_split(text, self.separators)

        # Combine splits into chunks
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_idx = 0
        text_pos = 0

        for split in splits:
            # If adding split exceeds chunk_size, finalize current chunk
            if current_chunk and len(current_chunk) + len(split) > self.chunk_size:
                chunk = DocumentChunk(
                    content=current_chunk.strip(),
                    chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                    start_pos=current_start,
                    end_pos=current_start + len(current_chunk),
                    metadata={**base_metadata, "chunk_index": chunk_idx},
                )
                chunks.append(chunk)

                # Handle overlap
                overlap_text = current_chunk[-self.overlap :] if self.overlap > 0 else ""
                current_chunk = overlap_text + split
                current_start = text_pos - len(overlap_text)
                chunk_idx += 1
            else:
                if not current_chunk:
                    current_start = text_pos
                current_chunk += split

            text_pos += len(split)

        # Add final chunk
        if current_chunk.strip():
            chunk = DocumentChunk(
                content=current_chunk.strip(),
                chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                start_pos=current_start,
                end_pos=current_start + len(current_chunk),
                metadata={**base_metadata, "chunk_index": chunk_idx},
            )
            chunks.append(chunk)

        return chunks

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
    ) -> list[str]:
        """Recursively split text using separator hierarchy.

        Args:
            text: Text to split
            separators: Remaining separators to try

        Returns:
            List of text splits
        """
        if not separators:
            # Base case: no more separators, return as-is
            return [text] if text else []

        separator = separators[0]
        remaining_separators = separators[1:]

        # Split on current separator
        splits = text.split(separator)

        # Recursively split large chunks
        result = []
        for split in splits:
            if len(split) > self.chunk_size and remaining_separators:
                # Too large, try next separator level
                result.extend(self._recursive_split(split, remaining_separators))
            elif split:
                result.append(split + separator)

        return result


class ContextualChunker:
    """Contextual chunking with surrounding context preservation.

    Creates chunks that include surrounding context (previous/next chunks)
    to improve semantic understanding during retrieval.

    Attributes:
        base_chunker: Underlying chunker (e.g., SemanticChunker)
        context_sentences: Number of sentences to include as context

    Example:
        >>> base = SemanticChunker(chunk_size=800)
        >>> chunker = ContextualChunker(base, context_sentences=2)
        >>> chunks = chunker.chunk_text("Document text...")
        >>> # Each chunk includes 2 sentences of surrounding context
    """

    def __init__(
        self,
        base_chunker: FixedSizeChunker | SemanticChunker | RecursiveChunker,
        context_sentences: int = 3,
    ) -> None:
        """Initialize contextual chunker.

        Args:
            base_chunker: Base chunker to use for initial splitting
            context_sentences: Number of surrounding sentences to include

        Example:
            >>> base = SemanticChunker(chunk_size=1000)
            >>> chunker = ContextualChunker(base, context_sentences=3)
        """
        self.base_chunker = base_chunker
        self.context_sentences = context_sentences

    def chunk_text(
        self,
        text: str,
        doc_id: str = "unknown",
        base_metadata: ChunkMetadata | None = None,
    ) -> list[DocumentChunk]:
        """Create chunks with surrounding context.

        Args:
            text: Input text to chunk
            doc_id: Document identifier
            base_metadata: Base metadata for chunks

        Returns:
            List of DocumentChunk objects with context

        Example:
            >>> chunks = chunker.chunk_text("Document with multiple paragraphs...")
            >>> # Each chunk has context from neighboring chunks
        """
        # Get base chunks
        base_chunks = self.base_chunker.chunk_text(text, doc_id, base_metadata)

        # Extract sentences from text
        sentences = self._extract_sentences(text)

        # Add context to each chunk
        contextual_chunks = []
        for _, chunk in enumerate(base_chunks):
            # Find sentences in this chunk
            chunk_start_sent = self._find_sentence_index(sentences, chunk.start_pos)
            chunk_end_sent = self._find_sentence_index(sentences, chunk.end_pos)

            # Add context sentences
            context_start = max(0, chunk_start_sent - self.context_sentences)
            context_end = min(len(sentences), chunk_end_sent + self.context_sentences + 1)

            # Build contextual content
            context_content = " ".join(sent for idx, sent in sentences[context_start:context_end])

            # Create contextual chunk
            contextual_chunk = DocumentChunk(
                content=context_content,
                chunk_id=chunk.chunk_id,
                start_pos=sentences[context_start][0] if sentences else chunk.start_pos,
                end_pos=(
                    sentences[context_end - 1][0] + len(sentences[context_end - 1][1])
                    if context_end > 0 and sentences
                    else chunk.end_pos
                ),
                metadata={
                    **chunk.metadata,
                    "has_context": True,
                    "context_sentences_before": chunk_start_sent - context_start,
                    "context_sentences_after": context_end - chunk_end_sent - 1,
                },
            )
            contextual_chunks.append(contextual_chunk)

        return contextual_chunks

    def _extract_sentences(self, text: str) -> list[tuple[int, str]]:
        """Extract sentences with positions.

        Args:
            text: Input text

        Returns:
            List of (position, sentence) tuples
        """
        # Simple sentence splitting (can be improved with spaCy/NLTK)
        sentence_pattern = r"[.!?]+\s+"
        sentences = []
        current_pos = 0

        for match in re.finditer(sentence_pattern, text):
            sent_start = current_pos
            sent_end = match.end()
            sentence = text[sent_start:sent_end].strip()
            if sentence:
                sentences.append((sent_start, sentence))
            current_pos = sent_end

        # Add final sentence
        if current_pos < len(text):
            final_sent = text[current_pos:].strip()
            if final_sent:
                sentences.append((current_pos, final_sent))

        return sentences

    def _find_sentence_index(
        self,
        sentences: list[tuple[int, str]],
        position: int,
    ) -> int:
        """Find sentence index containing position.

        Args:
            sentences: List of (position, sentence) tuples
            position: Character position

        Returns:
            Sentence index
        """
        for idx, (sent_pos, sent_text) in enumerate(sentences):
            if sent_pos <= position < sent_pos + len(sent_text):
                return idx
        return len(sentences) - 1 if sentences else 0


def create_chunker(
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    chunk_size: int = 1000,
    **kwargs: Any,
) -> FixedSizeChunker | SemanticChunker | RecursiveChunker | ContextualChunker:
    """Factory function to create chunker.

    Args:
        strategy: Chunking strategy to use
        chunk_size: Target chunk size
        **kwargs: Additional strategy-specific arguments

    Returns:
        Initialized chunker instance

    Example:
        >>> # Semantic chunker
        >>> chunker = create_chunker(
        ...     strategy=ChunkingStrategy.SEMANTIC,
        ...     chunk_size=1000
        ... )
        >>>
        >>> # Contextual chunker with semantic base
        >>> chunker = create_chunker(
        ...     strategy=ChunkingStrategy.CONTEXTUAL,
        ...     chunk_size=1000,
        ...     context_sentences=3
        ... )
    """
    if strategy == ChunkingStrategy.FIXED_SIZE:
        return FixedSizeChunker(
            chunk_size=chunk_size,
            overlap=kwargs.get("overlap", 200),
        )
    if strategy == ChunkingStrategy.SEMANTIC:
        return SemanticChunker(
            chunk_size=chunk_size,
            min_chunk_size=kwargs.get("min_chunk_size", 100),
        )
    if strategy == ChunkingStrategy.RECURSIVE:
        return RecursiveChunker(
            chunk_size=chunk_size,
            overlap=kwargs.get("overlap", 200),
            separators=kwargs.get("separators"),
        )
    if strategy == ChunkingStrategy.CONTEXTUAL:
        base_strategy = kwargs.get("base_strategy", ChunkingStrategy.SEMANTIC)
        base_chunker = create_chunker(base_strategy, chunk_size, **kwargs)
        return ContextualChunker(
            base_chunker=base_chunker,
            context_sentences=kwargs.get("context_sentences", 3),
        )
    raise ValueError(f"Unknown chunking strategy: {strategy}")


__all__ = [
    "ChunkingStrategy",
    "ContextualChunker",
    "DocumentChunk",
    "FixedSizeChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "create_chunker",
]
