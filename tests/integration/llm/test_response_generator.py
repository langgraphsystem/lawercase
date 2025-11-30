"""Integration tests for LLM Response Generator.

Tests the ResponseGenerator module structure and basic functionality.
Uses mocks to avoid actual API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# ============================================================================
# Module Import Tests
# ============================================================================


class TestModuleImports:
    """Tests for module imports and structure."""

    def test_import_core_classes(self) -> None:
        """Test importing core LLM classes."""
        from core.llm import (GenerationResult, LLMConfig, LLMProvider,
                              Message, ResponseGenerator, StreamChunk,
                              create_response_generator)

        assert LLMProvider is not None
        assert Message is not None
        assert GenerationResult is not None
        assert StreamChunk is not None
        assert LLMConfig is not None
        assert ResponseGenerator is not None
        assert create_response_generator is not None

    def test_llm_provider_enum_values(self) -> None:
        """Test LLMProvider enum values."""
        from core.llm import LLMProvider

        assert hasattr(LLMProvider, "OPENAI")
        assert hasattr(LLMProvider, "ANTHROPIC")
        assert hasattr(LLMProvider, "GOOGLE")

    def test_message_dataclass(self) -> None:
        """Test Message dataclass structure."""
        from core.llm import Message

        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_generation_result_dataclass(self) -> None:
        """Test GenerationResult dataclass structure."""
        from core.llm import GenerationResult, LLMProvider

        result = GenerationResult(
            content="Test response",
            model="gpt-4o-mini",
            provider=LLMProvider.OPENAI,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            latency_ms=100.0,
            cached=False,
            finish_reason="stop",
        )

        assert result.content == "Test response"
        assert result.total_tokens == 30

    def test_stream_chunk_dataclass(self) -> None:
        """Test StreamChunk dataclass structure."""
        from core.llm import StreamChunk

        chunk = StreamChunk(
            content="Hello",
            index=0,
            is_final=False,
            finish_reason=None,
        )

        assert chunk.content == "Hello"
        assert chunk.is_final is False


# ============================================================================
# Response Generator Tests
# ============================================================================


class TestResponseGenerator:
    """Tests for ResponseGenerator class."""

    def test_create_generator_openai(self) -> None:
        """Test creating generator for OpenAI."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        assert generator is not None

    def test_create_generator_anthropic(self) -> None:
        """Test creating generator for Anthropic."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
        )
        assert generator is not None

    def test_create_generator_google(self) -> None:
        """Test creating generator for Google."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.GOOGLE,
            model="gemini-1.5-flash",
        )
        assert generator is not None

    def test_create_generator_with_options(self) -> None:
        """Test creating generator with custom options."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2000,
        )
        assert generator is not None

    def test_generator_has_generate_method(self) -> None:
        """Test generator has generate method."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        assert hasattr(generator, "generate")
        assert callable(generator.generate)

    def test_generator_has_stream_method(self) -> None:
        """Test generator has generate_stream method."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        assert hasattr(generator, "generate_stream")
        assert callable(generator.generate_stream)

    def test_generator_has_stats_method(self) -> None:
        """Test generator has get_stats method."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        assert hasattr(generator, "get_stats")
        stats = generator.get_stats()
        assert isinstance(stats, dict)


# ============================================================================
# LLM Config Tests
# ============================================================================


class TestLLMConfig:
    """Tests for LLMConfig class."""

    def test_config_creation(self) -> None:
        """Test LLMConfig creation."""
        from core.llm import LLMConfig, LLMProvider

        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4o-mini"

    def test_config_defaults(self) -> None:
        """Test LLMConfig default values."""
        from core.llm import LLMConfig, LLMProvider

        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
        # Check defaults are set
        assert hasattr(config, "temperature")
        assert hasattr(config, "max_tokens")


# ============================================================================
# Mocked Generation Tests
# ============================================================================


class TestMockedGeneration:
    """Tests with mocked LLM calls."""

    @pytest.mark.asyncio
    async def test_generate_returns_result(self) -> None:
        """Test that generate returns a GenerationResult."""
        from core.llm import (GenerationResult, LLMProvider, Message,
                              create_response_generator)

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

        # Mock the internal generate method
        mock_result = GenerationResult(
            content="Mocked response",
            model="gpt-4o-mini",
            provider=LLMProvider.OPENAI,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            latency_ms=50.0,
            cached=False,
            finish_reason="stop",
        )

        with patch.object(generator, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_result
            messages = [Message(role="user", content="Hello")]
            result = await generator.generate(messages)

            assert result.content == "Mocked response"
            assert result.total_tokens == 30

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self) -> None:
        """Test that generate_stream yields StreamChunks."""
        from core.llm import (LLMProvider, Message, StreamChunk,
                              create_response_generator)

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

        async def mock_stream(*args: Any, **kwargs: Any):
            yield StreamChunk(content="Hello", index=0, is_final=False, finish_reason=None)
            yield StreamChunk(content=" World", index=1, is_final=True, finish_reason="stop")

        with patch.object(generator, "generate_stream", side_effect=mock_stream):
            messages = [Message(role="user", content="Hi")]
            chunks = []
            async for chunk in generator.generate_stream(messages):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0].content == "Hello"
            assert chunks[1].is_final


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Tests for statistics tracking."""

    def test_initial_stats(self) -> None:
        """Test initial statistics values."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

        stats = generator.get_stats()
        assert "total_requests" in stats
        assert "total_tokens" in stats

    def test_stats_structure(self) -> None:
        """Test statistics structure."""
        from core.llm import LLMProvider, create_response_generator

        generator = create_response_generator(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

        stats = generator.get_stats()
        # Check for common stat keys that should be present
        expected_keys = ["total_requests", "total_tokens"]
        for key in expected_keys:
            assert key in stats, f"Missing stat: {key}"
        # Stats should be a dict
        assert isinstance(stats, dict)
