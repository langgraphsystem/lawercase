"""Tests for Context Manager."""

from __future__ import annotations

import pytest

from core.context import (
    ContextBlock,
    ContextManager,
    ContextTemplate,
    ContextType,
)


class TestContextManager:
    """Test ContextManager functionality."""

    @pytest.fixture
    def context_manager(self) -> ContextManager:
        """Create context manager for testing."""
        return ContextManager(max_context_tokens=1000)

    @pytest.fixture
    def simple_template(self) -> ContextTemplate:
        """Create simple test template."""
        return ContextTemplate(
            name="test_template",
            description="Test template",
            template="Task: {task}\nContext: {context}",
            max_tokens=500,
            priority=5,
            required_fields=["task", "context"],
        )

    def test_initialization(self, context_manager: ContextManager) -> None:
        """Test context manager initialization."""
        assert context_manager.max_context_tokens == 1000
        assert len(context_manager.templates) == 0
        assert len(context_manager.global_context) == 0

    def test_register_template(
        self, context_manager: ContextManager, simple_template: ContextTemplate
    ) -> None:
        """Test template registration."""
        context_manager.register_template(simple_template)
        assert "test_template" in context_manager.templates
        assert context_manager.templates["test_template"] == simple_template

    def test_template_rendering(self, simple_template: ContextTemplate) -> None:
        """Test template rendering with variables."""
        rendered = simple_template.render(task="Test task", context="Test context")
        assert "Test task" in rendered
        assert "Test context" in rendered

    def test_template_missing_field(self, simple_template: ContextTemplate) -> None:
        """Test template rendering with missing field."""
        with pytest.raises(ValueError, match="Missing required field"):
            simple_template.render(task="Test task")  # Missing 'context'

    def test_add_global_context(self, context_manager: ContextManager) -> None:
        """Test adding global context."""
        block = ContextBlock(
            content="Global context information",
            context_type=ContextType.BACKGROUND,
            priority=5,
            source="test",
        )
        context_manager.add_global_context(block)
        assert len(context_manager.global_context) == 1
        assert context_manager.global_context[0] == block

    def test_build_context(
        self,
        context_manager: ContextManager,
        simple_template: ContextTemplate,
    ) -> None:
        """Test building context from template."""
        context_manager.register_template(simple_template)

        context = context_manager.build_context(
            template_name="test_template",
            task="Write a document",
            context="Legal case analysis",
        )

        assert "Write a document" in context
        assert "Legal case analysis" in context

    def test_build_context_with_additional_blocks(
        self,
        context_manager: ContextManager,
        simple_template: ContextTemplate,
    ) -> None:
        """Test building context with additional blocks."""
        context_manager.register_template(simple_template)

        additional_block = ContextBlock(
            content="Additional information",
            context_type=ContextType.MEMORY,
            priority=8,
            source="memory",
        )

        context = context_manager.build_context(
            template_name="test_template",
            additional_context=[additional_block],
            task="Analyze case",
            context="Background",
        )

        assert "Analyze case" in context
        assert "Additional information" in context

    def test_context_optimization_token_limit(
        self, context_manager: ContextManager
    ) -> None:
        """Test context optimization respects token limits."""
        # Create template with lots of content
        long_template = ContextTemplate(
            name="long_template",
            description="Long template",
            template="Task: {task}\n" + "x" * 10000,  # Very long content
            max_tokens=500,
            priority=5,
            required_fields=["task"],
        )

        context_manager.register_template(long_template)
        context = context_manager.build_context(
            template_name="long_template",
            task="Test",
        )

        # Verify it was truncated
        estimated_tokens = len(context) // 4
        assert estimated_tokens <= context_manager.max_context_tokens

    def test_context_block_priority(self, context_manager: ContextManager) -> None:
        """Test that higher priority blocks are included first."""
        template = ContextTemplate(
            name="priority_test",
            description="Priority test",
            template="Main content",
            max_tokens=100,
            priority=10,
            required_fields=[],
        )
        context_manager.register_template(template)

        # Add blocks with different priorities
        low_priority = ContextBlock(
            content="Low priority" * 100,  # Large, low priority
            context_type=ContextType.BACKGROUND,
            priority=1,
            source="low",
        )

        high_priority = ContextBlock(
            content="High priority info",
            context_type=ContextType.MEMORY,
            priority=10,
            source="high",
        )

        context = context_manager.build_context(
            template_name="priority_test",
            additional_context=[low_priority, high_priority],
        )

        # High priority should be included
        assert "High priority info" in context

    def test_clear_global_context(self, context_manager: ContextManager) -> None:
        """Test clearing global context."""
        block = ContextBlock(
            content="Test",
            context_type=ContextType.BACKGROUND,
            priority=5,
            source="test",
        )
        context_manager.add_global_context(block)
        assert len(context_manager.global_context) == 1

        context_manager.clear_global_context()
        assert len(context_manager.global_context) == 0

    def test_create_agent_context(self, context_manager: ContextManager) -> None:
        """Test creating agent-specific context."""
        # Register default template
        default_template = ContextTemplate(
            name="default_agent",
            description="Default agent template",
            template="Agent: {agent_type}\nTask: {task}",
            max_tokens=500,
            priority=5,
            required_fields=["agent_type", "task"],
        )
        context_manager.register_template(default_template)

        context = context_manager.create_agent_context(
            agent_type="test",
            task_description="Perform analysis",
            memory_snippets=["Previous context"],
            available_tools=["tool1", "tool2"],
        )

        assert "Perform analysis" in context
        assert "Previous context" in context
        assert "tool1" in context
        assert "tool2" in context
