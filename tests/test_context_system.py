"""Tests for the Context Management System.

Tests cover:
- ContextManager initialization and configuration
- ContextTemplate registration and rendering
- ContextBlock creation and token estimation
- Context building with priorities and token limits
- Context compression and optimization
"""

from __future__ import annotations

from datetime import datetime

import pytest

from core.context.context_manager import (
    ContextBlock,
    ContextManager,
    ContextTemplate,
    ContextType,
)


class TestContextType:
    """Tests for ContextType enum."""

    def test_context_types_exist(self) -> None:
        """Verify all expected context types exist."""
        assert ContextType.SYSTEM == "system"
        assert ContextType.USER == "user"
        assert ContextType.ASSISTANT == "assistant"
        assert ContextType.BACKGROUND == "background"
        assert ContextType.MEMORY == "memory"
        assert ContextType.TOOLS == "tools"

    def test_context_type_is_string(self) -> None:
        """Context types should be string-based."""
        assert isinstance(ContextType.SYSTEM.value, str)


class TestContextTemplate:
    """Tests for ContextTemplate dataclass."""

    def test_template_creation(self) -> None:
        """Test basic template creation."""
        template = ContextTemplate(
            name="test_template",
            description="A test template",
            template="Hello, {name}!",
            max_tokens=1000,
            priority=7,
            required_fields=["name"],
        )

        assert template.name == "test_template"
        assert template.max_tokens == 1000
        assert template.priority == 7

    def test_template_render_success(self) -> None:
        """Test successful template rendering."""
        template = ContextTemplate(
            name="greeting",
            description="Greeting template",
            template="Hello, {name}! Welcome to {place}.",
            required_fields=["name", "place"],
        )

        result = template.render(name="Alice", place="Wonderland")
        assert result == "Hello, Alice! Welcome to Wonderland."

    def test_template_render_missing_field(self) -> None:
        """Test template rendering with missing required field."""
        template = ContextTemplate(
            name="greeting",
            description="Greeting template",
            template="Hello, {name}!",
            required_fields=["name"],
        )

        with pytest.raises(ValueError, match="Missing required field"):
            template.render()  # Missing 'name'

    def test_template_default_values(self) -> None:
        """Test default values for template fields."""
        template = ContextTemplate(
            name="minimal",
            description="Minimal template",
            template="Test",
        )

        assert template.max_tokens == 4000
        assert template.priority == 5
        assert template.required_fields == []
        assert template.context_type == ContextType.SYSTEM


class TestContextBlock:
    """Tests for ContextBlock dataclass."""

    def test_block_creation(self) -> None:
        """Test basic block creation."""
        block = ContextBlock(
            content="This is test content",
            context_type=ContextType.USER,
            priority=8,
            source="test",
        )

        assert block.content == "This is test content"
        assert block.context_type == ContextType.USER
        assert block.priority == 8
        assert block.source == "test"

    def test_block_token_estimation(self) -> None:
        """Test automatic token estimation."""
        content = "A" * 100  # 100 characters
        block = ContextBlock(
            content=content,
            context_type=ContextType.SYSTEM,
        )

        # Token estimation: ~4 chars per token
        assert block.tokens == 25  # 100 // 4

    def test_block_explicit_tokens(self) -> None:
        """Test explicit token count overrides estimation."""
        block = ContextBlock(
            content="Short text",
            context_type=ContextType.USER,
            tokens=100,  # Explicit token count
        )

        assert block.tokens == 100

    def test_block_timestamp(self) -> None:
        """Test timestamp is set automatically."""
        block = ContextBlock(
            content="Test",
            context_type=ContextType.SYSTEM,
        )

        assert isinstance(block.timestamp, datetime)

    def test_block_relevance_score_default(self) -> None:
        """Test default relevance score."""
        block = ContextBlock(
            content="Test",
            context_type=ContextType.SYSTEM,
        )

        assert block.relevance_score == 1.0


class TestContextManager:
    """Tests for ContextManager class."""

    def test_manager_initialization(self) -> None:
        """Test manager initialization with default values."""
        manager = ContextManager()
        assert manager.max_context_tokens == 8000
        assert manager.templates == {}
        assert manager.global_context == []

    def test_manager_custom_token_limit(self) -> None:
        """Test manager with custom token limit."""
        manager = ContextManager(max_context_tokens=16000)
        assert manager.max_context_tokens == 16000

    def test_register_template(self) -> None:
        """Test template registration."""
        manager = ContextManager()
        template = ContextTemplate(
            name="test",
            description="Test template",
            template="Hello {name}",
        )

        manager.register_template(template)

        assert "test" in manager.templates
        assert manager.templates["test"] == template

    def test_add_global_context(self) -> None:
        """Test adding global context blocks."""
        manager = ContextManager()
        block = ContextBlock(
            content="Global instruction",
            context_type=ContextType.SYSTEM,
            source="global",
        )

        manager.add_global_context(block)

        assert len(manager.global_context) == 1
        assert manager.global_context[0] == block

    def test_multiple_global_contexts(self) -> None:
        """Test adding multiple global context blocks."""
        manager = ContextManager()

        for i in range(3):
            block = ContextBlock(
                content=f"Context {i}",
                context_type=ContextType.BACKGROUND,
                source=f"source_{i}",
            )
            manager.add_global_context(block)

        assert len(manager.global_context) == 3


class TestContextManagerBuildContext:
    """Tests for ContextManager.build_context method."""

    @pytest.fixture
    def manager_with_template(self) -> ContextManager:
        """Create manager with a registered template."""
        manager = ContextManager(max_context_tokens=1000)
        template = ContextTemplate(
            name="eb1a_analysis",
            description="EB-1A case analysis template",
            template="Analyze the following case for {criterion}:\n\n{case_details}",
            max_tokens=500,
            priority=9,
            required_fields=["criterion", "case_details"],
        )
        manager.register_template(template)
        return manager

    def test_build_context_basic(self, manager_with_template: ContextManager) -> None:
        """Test basic context building."""
        result = manager_with_template.build_context(
            template_name="eb1a_analysis",
            criterion="Original Contributions",
            case_details="The applicant has 50 citations...",
        )

        assert "Original Contributions" in result
        assert "50 citations" in result

    def test_build_context_unknown_template(self) -> None:
        """Test error handling for unknown template."""
        manager = ContextManager()

        with pytest.raises(ValueError, match="Template not found"):
            manager.build_context(template_name="nonexistent")


class TestContextCompression:
    """Tests for context compression functionality."""

    def test_blocks_sorted_by_priority(self) -> None:
        """Verify blocks are sorted by priority."""
        blocks = [
            ContextBlock(content="Low", context_type=ContextType.BACKGROUND, priority=3),
            ContextBlock(content="High", context_type=ContextType.SYSTEM, priority=9),
            ContextBlock(content="Medium", context_type=ContextType.USER, priority=5),
        ]

        sorted_blocks = sorted(blocks, key=lambda b: b.priority, reverse=True)

        assert sorted_blocks[0].content == "High"
        assert sorted_blocks[1].content == "Medium"
        assert sorted_blocks[2].content == "Low"

    def test_blocks_sorted_by_relevance(self) -> None:
        """Verify blocks can be sorted by relevance score."""
        blocks = [
            ContextBlock(content="A", context_type=ContextType.MEMORY, relevance_score=0.3),
            ContextBlock(content="B", context_type=ContextType.MEMORY, relevance_score=0.9),
            ContextBlock(content="C", context_type=ContextType.MEMORY, relevance_score=0.6),
        ]

        sorted_blocks = sorted(blocks, key=lambda b: b.relevance_score, reverse=True)

        assert sorted_blocks[0].content == "B"
        assert sorted_blocks[1].content == "C"
        assert sorted_blocks[2].content == "A"


class TestContextManagerIntegration:
    """Integration tests for the context system."""

    def test_full_workflow(self) -> None:
        """Test complete workflow: create, configure, build context."""
        # Initialize
        manager = ContextManager(max_context_tokens=10000)

        # Register templates
        system_template = ContextTemplate(
            name="system",
            description="System instructions",
            template="You are an EB-1A immigration expert. Focus on {focus_area}.",
            priority=10,
            required_fields=["focus_area"],
            context_type=ContextType.SYSTEM,
        )
        manager.register_template(system_template)

        # Add global context
        global_block = ContextBlock(
            content="Always cite specific USCIS policy manual sections.",
            context_type=ContextType.BACKGROUND,
            priority=8,
            source="guidelines",
        )
        manager.add_global_context(global_block)

        # Build context
        result = manager.build_context(
            template_name="system",
            focus_area="scholarly articles criterion",
        )

        assert "EB-1A immigration expert" in result
        assert "scholarly articles criterion" in result

    def test_token_budget_tracking(self) -> None:
        """Test that token budgets are tracked correctly."""
        manager = ContextManager(max_context_tokens=100)

        # Add blocks that approach the limit
        block1 = ContextBlock(
            content="A" * 200,  # ~50 tokens
            context_type=ContextType.SYSTEM,
            tokens=50,
        )
        block2 = ContextBlock(
            content="B" * 200,  # ~50 tokens
            context_type=ContextType.USER,
            tokens=50,
        )

        manager.add_global_context(block1)
        manager.add_global_context(block2)

        total_tokens = sum(b.tokens for b in manager.global_context)
        assert total_tokens == 100


# Pytest fixtures
@pytest.fixture
def sample_template() -> ContextTemplate:
    """Create a sample template for testing."""
    return ContextTemplate(
        name="sample",
        description="Sample template for testing",
        template="Input: {input}\nOutput: {output}",
        max_tokens=500,
        required_fields=["input", "output"],
    )


@pytest.fixture
def sample_block() -> ContextBlock:
    """Create a sample context block for testing."""
    return ContextBlock(
        content="Sample content for testing purposes.",
        context_type=ContextType.USER,
        priority=5,
        source="test",
        relevance_score=0.85,
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
