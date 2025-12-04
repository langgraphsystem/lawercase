"""Context compression utilities.

This module provides:
- Multiple compression strategies (simple, extract, summarize, hybrid)
- LLM-based summarization for intelligent compression
- Accurate token counting with tiktoken
- Async support for LLM operations
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token counting
try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using character-based estimation")


class CompressionStrategy(str, Enum):
    """Context compression strategies."""

    NONE = "none"
    SIMPLE = "simple"  # Remove extra whitespace, redundancy
    SUMMARIZE = "summarize"  # Summarize long sections
    EXTRACT = "extract"  # Extract key information
    HYBRID = "hybrid"  # Combine multiple strategies


class ContextCompressor:
    """Compresses context to fit within token limits.

    Supports multiple compression strategies:
    - NONE: No compression
    - SIMPLE: Remove redundant whitespace and weak modifiers
    - EXTRACT: Extract key sentences based on importance scoring
    - SUMMARIZE: Use LLM to intelligently summarize (async only)
    - HYBRID: Combine simple + extract, or simple + summarize
    """

    def __init__(
        self,
        target_compression: float = 0.5,
        llm_client: Any | None = None,
        model: str = "gpt-4",
    ) -> None:
        """Initialize compressor.

        Args:
            target_compression: Target compression ratio (0.0-1.0)
            llm_client: Optional LLM client for summarization
            model: Model name for token counting
        """
        self.target_compression = max(0.1, min(1.0, target_compression))
        self.llm_client = llm_client
        self.model = model
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

    async def _llm_summarize(self, text: str, max_tokens: int | None = None) -> str:
        """Summarize text using LLM.

        Args:
            text: Text to summarize
            max_tokens: Maximum tokens for summary

        Returns:
            Summarized text
        """
        if not self.llm_client:
            logger.warning("No LLM client configured, falling back to extraction")
            return self._extract_key_info(text)

        target_tokens = max_tokens or int(count_tokens(text, self.model) * self.target_compression)

        prompt = f"""Summarize the following text concisely, preserving all key facts,
entities, dates, and important details. Target approximately {target_tokens} tokens.

TEXT:
{text}

SUMMARY:"""

        try:
            result = await self.llm_client.acomplete(prompt=prompt)
            summary = result.get("output", "")
            if summary:
                logger.debug(
                    f"LLM summarization: {count_tokens(text)} -> {count_tokens(summary)} tokens"
                )
                return summary.strip()
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}, falling back to extraction")

        return self._extract_key_info(text)

    async def acompress(
        self,
        text: str,
        strategy: CompressionStrategy = CompressionStrategy.SIMPLE,
    ) -> str:
        """Async compress text using specified strategy.

        Supports SUMMARIZE strategy with LLM.

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
        if strategy == CompressionStrategy.SUMMARIZE:
            return await self._llm_summarize(text)
        if strategy == CompressionStrategy.HYBRID:
            # Try LLM first if available, fallback to extraction
            compressed = self._simple_compression(text)
            target_length = int(len(text) * self.target_compression)
            if len(compressed) > target_length:
                if self.llm_client:
                    compressed = await self._llm_summarize(compressed)
                else:
                    compressed = self._extract_key_info(compressed)
            return compressed

        return self._simple_compression(text)

    async def acompress_to_tokens(
        self,
        text: str,
        max_tokens: int,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
    ) -> str:
        """Async compress text to fit within token limit.

        Args:
            text: Text to compress
            max_tokens: Maximum tokens allowed
            strategy: Compression strategy

        Returns:
            Compressed text fitting within token limit
        """
        current_tokens = count_tokens(text, self.model)

        if current_tokens <= max_tokens:
            return text

        # Calculate required compression ratio
        required_ratio = max_tokens / current_tokens
        self.target_compression = required_ratio

        # Use LLM summarization for better quality if available
        if self.llm_client and strategy in (
            CompressionStrategy.SUMMARIZE,
            CompressionStrategy.HYBRID,
        ):
            compressed = await self._llm_summarize(text, max_tokens)
        else:
            compressed = await self.acompress(text, strategy)

        # Verify token count and truncate if needed
        compressed_tokens = count_tokens(compressed, self.model)
        if compressed_tokens > max_tokens:
            # Binary search for optimal truncation point
            compressed = self._truncate_to_tokens(compressed, max_tokens)

        logger.info(
            f"Compressed from {current_tokens} to {count_tokens(compressed, self.model)} tokens"
        )
        return compressed

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to exact token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated text
        """
        if _TIKTOKEN_AVAILABLE:
            try:
                if "gpt-4" in self.model or "gpt-3.5" in self.model or "gpt-5" in self.model:
                    encoding = tiktoken.encoding_for_model("gpt-4")
                else:
                    encoding = tiktoken.get_encoding("cl100k_base")

                tokens = encoding.encode(text)
                if len(tokens) <= max_tokens:
                    return text

                # Leave room for truncation indicator
                truncated_tokens = tokens[: max_tokens - 5]
                return encoding.decode(truncated_tokens) + "\n[...]"
            except Exception:  # nosec B110 - fallback to char-based truncation
                pass  # Fall through to character-based truncation below

        # Fallback to character-based truncation
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 20] + "\n[... truncated ...]"

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
        current_tokens = count_tokens(text, self.model)

        if current_tokens <= max_tokens:
            return text

        # Calculate required compression ratio
        required_ratio = max_tokens / current_tokens
        self.target_compression = required_ratio

        compressed = self.compress(text, strategy)

        # Verify and truncate if needed
        compressed_tokens = count_tokens(compressed, self.model)
        if compressed_tokens > max_tokens:
            compressed = self._truncate_to_tokens(compressed, max_tokens)

        final_tokens = count_tokens(compressed, self.model)
        logger.info(f"Compressed from {current_tokens} to {final_tokens} tokens")

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


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens accurately using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer selection

    Returns:
        Exact token count (or estimate if tiktoken unavailable)
    """
    if not text:
        return 0

    if _TIKTOKEN_AVAILABLE:
        try:
            # Map model names to tiktoken encodings
            if "gpt-4" in model or "gpt-3.5" in model or "gpt-5" in model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken encoding failed: {e}, using estimation")

    # Fallback to character-based estimation
    return len(text) // 4


def estimate_tokens(text: str) -> int:
    """Estimate token count for text (legacy function).

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return count_tokens(text)


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
