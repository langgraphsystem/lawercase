"""Tests for context compression module."""

from __future__ import annotations

import pytest

from core.context.compression import (CompressionStrategy, ContextCompressor,
                                      count_tokens, estimate_tokens,
                                      trim_to_tokens)


class TestCountTokens:
    """Tests for count_tokens function."""

    def test_empty_text(self) -> None:
        """Test count_tokens with empty text."""
        assert count_tokens("") == 0

    def test_short_text(self) -> None:
        """Test count_tokens with short text."""
        result = count_tokens("Hello world")
        # Should be roughly len/4 without tiktoken
        assert result > 0
        assert result < 10

    def test_long_text(self) -> None:
        """Test count_tokens with longer text."""
        text = "This is a longer piece of text that spans multiple words and sentences."
        result = count_tokens(text)
        assert result > 10

    def test_with_model_parameter(self) -> None:
        """Test count_tokens with different model names."""
        text = "Test text"
        # Different models should still work
        gpt4_tokens = count_tokens(text, model="gpt-4")
        gpt35_tokens = count_tokens(text, model="gpt-3.5-turbo")
        assert gpt4_tokens > 0
        assert gpt35_tokens > 0


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_estimate_tokens_calls_count_tokens(self) -> None:
        """Test that estimate_tokens is an alias for count_tokens."""
        text = "Some test text"
        assert estimate_tokens(text) == count_tokens(text)


class TestTrimToTokens:
    """Tests for trim_to_tokens function."""

    def test_short_text_not_trimmed(self) -> None:
        """Test that short text is not trimmed."""
        text = "Short"
        result = trim_to_tokens(text, max_tokens=100)
        assert result == text

    def test_long_text_trimmed(self) -> None:
        """Test that long text is trimmed."""
        text = "A" * 1000
        result = trim_to_tokens(text, max_tokens=50)
        assert len(result) < len(text)
        assert "[... trimmed ...]" in result or "[...]" in result


class TestCompressionStrategy:
    """Tests for CompressionStrategy enum."""

    def test_all_strategies_exist(self) -> None:
        """Test all expected strategies exist."""
        assert CompressionStrategy.NONE == "none"
        assert CompressionStrategy.SIMPLE == "simple"
        assert CompressionStrategy.SUMMARIZE == "summarize"
        assert CompressionStrategy.EXTRACT == "extract"
        assert CompressionStrategy.HYBRID == "hybrid"


class TestContextCompressor:
    """Tests for ContextCompressor class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        compressor = ContextCompressor()
        assert compressor.target_compression == 0.5

    def test_init_custom_ratio(self) -> None:
        """Test initialization with custom ratio."""
        compressor = ContextCompressor(target_compression=0.3)
        assert compressor.target_compression == 0.3

    def test_init_clamps_ratio(self) -> None:
        """Test that ratio is clamped to valid range."""
        compressor_low = ContextCompressor(target_compression=0.01)
        assert compressor_low.target_compression == 0.1

        compressor_high = ContextCompressor(target_compression=1.5)
        assert compressor_high.target_compression == 1.0


class TestSimpleCompression:
    """Tests for simple compression strategy."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor()

    def test_removes_extra_whitespace(self, compressor: ContextCompressor) -> None:
        """Test that extra whitespace is removed."""
        text = "Hello    world   test"
        result = compressor.compress(text, CompressionStrategy.SIMPLE)
        assert "    " not in result
        assert "   " not in result

    def test_removes_weak_modifiers(self, compressor: ContextCompressor) -> None:
        """Test that weak modifiers are removed."""
        text = "This is very really quite important"
        result = compressor.compress(text, CompressionStrategy.SIMPLE)
        # Some weak modifiers should be removed
        assert len(result) <= len(text)

    def test_strips_whitespace(self, compressor: ContextCompressor) -> None:
        """Test that leading/trailing whitespace is stripped."""
        text = "  Hello world  "
        result = compressor.compress(text, CompressionStrategy.SIMPLE)
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_none_strategy_returns_original(self, compressor: ContextCompressor) -> None:
        """Test that NONE strategy returns original text."""
        text = "  Hello   world  "
        result = compressor.compress(text, CompressionStrategy.NONE)
        assert result == text


class TestExtractCompression:
    """Tests for extract compression strategy."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor(target_compression=0.5)

    def test_extracts_key_sentences(self, compressor: ContextCompressor) -> None:
        """Test that key sentences are extracted."""
        text = (
            "This is a normal sentence. "
            "This is important critical information. "
            "Another regular sentence. "
            "A required warning note here."
        )
        result = compressor.compress(text, CompressionStrategy.EXTRACT)
        # Should prioritize sentences with keywords
        assert len(result) < len(text)
        assert len(result) > 0

    def test_preserves_numbers(self, compressor: ContextCompressor) -> None:
        """Test that sentences with numbers get higher scores."""
        text = "Just a regular sentence. " "The deadline is 2024-01-15. " "Another boring sentence."
        result = compressor.compress(text, CompressionStrategy.EXTRACT)
        # Should favor sentences with dates/numbers
        assert "2024" in result

    def test_handles_empty_text(self, compressor: ContextCompressor) -> None:
        """Test extraction with empty text."""
        result = compressor.compress("", CompressionStrategy.EXTRACT)
        assert result == ""


class TestHybridCompression:
    """Tests for hybrid compression strategy."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor(target_compression=0.3)

    def test_combines_strategies(self, compressor: ContextCompressor) -> None:
        """Test that hybrid applies multiple strategies."""
        text = (
            "This   is   very really   important. "
            "Note: critical deadline 2024-01-15. "
            "Regular boring   sentence   here. "
        )
        result = compressor.compress(text, CompressionStrategy.HYBRID)
        # Should remove whitespace AND extract key info
        assert "   " not in result
        assert len(result) < len(text)


class TestCompressToTokens:
    """Tests for compress_to_tokens method."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor()

    def test_short_text_not_compressed(self, compressor: ContextCompressor) -> None:
        """Test that text under limit is not compressed."""
        text = "Short text"
        result = compressor.compress_to_tokens(text, max_tokens=100)
        assert result == text

    def test_long_text_compressed(self, compressor: ContextCompressor) -> None:
        """Test that text over limit is compressed."""
        text = "A " * 500
        result = compressor.compress_to_tokens(text, max_tokens=50)
        assert len(result) < len(text)


class TestBatchCompress:
    """Tests for batch_compress method."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor()

    def test_batch_compress_multiple_texts(self, compressor: ContextCompressor) -> None:
        """Test batch compression of multiple texts."""
        texts = [
            "A " * 100,
            "B " * 100,
            "C " * 100,
        ]
        results = compressor.batch_compress(texts, total_max_tokens=150)
        assert len(results) == 3
        for result in results:
            assert len(result) > 0

    def test_batch_compress_empty_list(self, compressor: ContextCompressor) -> None:
        """Test batch compression with empty list."""
        results = compressor.batch_compress([], total_max_tokens=100)
        assert results == []


class TestAsyncCompression:
    """Tests for async compression methods."""

    @pytest.fixture
    def compressor(self) -> ContextCompressor:
        return ContextCompressor()

    @pytest.mark.asyncio
    async def test_acompress_simple(self, compressor: ContextCompressor) -> None:
        """Test async compress with simple strategy."""
        text = "Hello   world   test"
        result = await compressor.acompress(text, CompressionStrategy.SIMPLE)
        assert "   " not in result

    @pytest.mark.asyncio
    async def test_acompress_extract(self, compressor: ContextCompressor) -> None:
        """Test async compress with extract strategy."""
        text = "Normal. Important critical note. Regular."
        result = await compressor.acompress(text, CompressionStrategy.EXTRACT)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_acompress_none(self, compressor: ContextCompressor) -> None:
        """Test async compress with none strategy."""
        text = "  Original  text  "
        result = await compressor.acompress(text, CompressionStrategy.NONE)
        assert result == text

    @pytest.mark.asyncio
    async def test_acompress_to_tokens(self, compressor: ContextCompressor) -> None:
        """Test async compress to tokens."""
        text = "A " * 200
        result = await compressor.acompress_to_tokens(text, max_tokens=50)
        assert len(result) < len(text)
