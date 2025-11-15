"""Context compression utilities."""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class CompressionStrategy(str, Enum):
    """Context compression strategies."""

    NONE = "none"
    SIMPLE = "simple"  # Remove extra whitespace, redundancy
    SUMMARIZE = "summarize"  # Summarize long sections
    EXTRACT = "extract"  # Extract key information
    HYBRID = "hybrid"  # Combine multiple strategies


class ContextCompressor:
    """Compresses context to fit within token limits."""

    def __init__(self, target_compression: float = 0.5) -> None:
        """Initialize compressor.

        Args:
            target_compression: Target compression ratio (0.0-1.0)
        """
        self.target_compression = max(0.1, min(1.0, target_compression))
        logger.info(f"ContextCompressor initialized with ratio={self.target_compression}")

    def compress(
        self, text: str, strategy: CompressionStrategy = CompressionStrategy.SIMPLE
    ) -> str:
        """Compress text using specified strategy.

        Args:
            text: Text to compress
            strategy: Compression strategy to use

        Returns:
            Compressed text
        """
        if strategy == CompressionStrategy.NONE:
            return text
        if strategy == CompressionStrategy.SIMPLE:
            return self._simple_compression(text)
        if strategy == CompressionStrategy.EXTRACT:
            return self._extract_key_info(text)
        if strategy == CompressionStrategy.HYBRID:
            return self._hybrid_compression(text)

        # Default to simple
        return self._simple_compression(text)

    def _simple_compression(self, text: str) -> str:
        """Apply simple compression techniques.

        Args:
            text: Text to compress

        Returns:
            Compressed text
        """
        # Remove extra whitespace
        compressed = re.sub(r"\s+", " ", text)

        # Remove redundant phrases
        redundant_patterns = [
            r"\b(very|really|quite|just|actually)\b",  # Weak modifiers
            r"\b(in order to|in order for)\b",  # Replace with "to"
            r"\b(due to the fact that|because of the fact that)\b",  # Replace with "because"
            r"\b(at this point in time|at the present time)\b",  # Replace with "now"
        ]

        for pattern in redundant_patterns:
            compressed = re.sub(pattern, "", compressed, flags=re.IGNORECASE)

        # Remove multiple spaces again
        compressed = re.sub(r"\s+", " ", compressed)

        # Remove leading/trailing whitespace
        compressed = compressed.strip()

        compression_ratio = len(compressed) / len(text) if text else 1.0
        logger.debug(f"Simple compression: {compression_ratio:.2%} of original size")

        return compressed

    def _extract_key_info(self, text: str) -> str:
        """Extract key information from text.

        Args:
            text: Text to process

        Returns:
            Key information
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)

        # Score sentences based on keywords
        keywords = [
            "must",
            "should",
            "required",
            "important",
            "critical",
            "key",
            "essential",
            "note",
            "warning",
            "error",
        ]

        scored_sentences: list[tuple[str, int]] = []
        for sent in sentences:
            sentence = sent.strip()
            if not sentence:
                continue

            score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())

            # Bonus for numbers, dates, names
            if re.search(r"\d+", sentence):
                score += 1
            if re.search(r"\b[A-Z][a-z]+\b", sentence):  # Proper nouns
                score += 1

            scored_sentences.append((sentence, score))

        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        target_count = max(1, int(len(scored_sentences) * self.target_compression))
        key_sentences = [s[0] for s in scored_sentences[:target_count]]

        # Reconstruct text
        extracted = ". ".join(key_sentences)
        if extracted and not extracted.endswith("."):
            extracted += "."

        logger.debug(f"Extracted {len(key_sentences)}/{len(sentences)} key sentences")

        return extracted

    def _hybrid_compression(self, text: str) -> str:
        """Apply hybrid compression strategy.

        Args:
            text: Text to compress

        Returns:
            Compressed text
        """
        # First apply simple compression
        compressed = self._simple_compression(text)

        # Then extract key information if still too long
        target_length = int(len(text) * self.target_compression)
        if len(compressed) > target_length:
            compressed = self._extract_key_info(compressed)

        return compressed

    def compress_to_tokens(
        self, text: str, max_tokens: int, strategy: CompressionStrategy = CompressionStrategy.HYBRID
    ) -> str:
        """Compress text to fit within token limit.

        Args:
            text: Text to compress
            max_tokens: Maximum tokens allowed
            strategy: Compression strategy

        Returns:
            Compressed text
        """
        # Rough estimation: 1 token ≈ 4 characters
        current_tokens = len(text) // 4

        if current_tokens <= max_tokens:
            return text

        # Calculate required compression ratio
        required_ratio = max_tokens / current_tokens
        self.target_compression = required_ratio

        compressed = self.compress(text, strategy)

        # If still too long, truncate
        max_chars = max_tokens * 4
        if len(compressed) > max_chars:
            compressed = compressed[: max_chars - 20] + "\n[... truncated ...]"

        logger.info(f"Compressed from {current_tokens} to ~{len(compressed) // 4} tokens")

        return compressed

    def batch_compress(
        self,
        texts: list[str],
        total_max_tokens: int,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
    ) -> list[str]:
        """Compress multiple texts to fit within total token limit.

        Args:
            texts: List of texts to compress
            total_max_tokens: Total token limit for all texts
            strategy: Compression strategy

        Returns:
            List of compressed texts
        """
        if not texts:
            return []

        # Calculate tokens per text
        tokens_per_text = total_max_tokens // len(texts)

        compressed_texts = []
        for text in texts:
            compressed = self.compress_to_tokens(text, tokens_per_text, strategy)
            compressed_texts.append(compressed)

        logger.info(f"Batch compressed {len(texts)} texts")

        return compressed_texts


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # Rough estimation: 1 token ≈ 4 characters
    # This is a simplification; real tokenization varies by model
    return len(text) // 4


def trim_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to fit within token limit.

    Args:
        text: Text to trim
        max_tokens: Maximum tokens

    Returns:
        Trimmed text
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text

    return text[: max_chars - 20] + "\n[... trimmed ...]"
