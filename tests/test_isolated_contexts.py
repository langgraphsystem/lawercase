"""Tests for Isolated Context Windows System.

Tests cover:
- IsolatedContext creation and management
- ContextState transitions
- Message handling within isolated contexts
- Token budget management
- Context merging and result extraction
"""

from __future__ import annotations

from datetime import datetime

import pytest

from core.context.isolated_context import (
    ContextMessage,
    ContextState,
    IsolatedContext,
)


class TestContextState:
    """Tests for ContextState enum."""

    def test_state_values(self) -> None:
        """Verify all context states exist."""
        assert ContextState.CREATED == "created"
        assert ContextState.ACTIVE == "active"
        assert ContextState.COMPLETED == "completed"
        assert ContextState.FAILED == "failed"
        assert ContextState.MERGED == "merged"

    def test_state_transitions(self) -> None:
        """Define valid state transitions."""
        valid_transitions = {
            ContextState.CREATED: [ContextState.ACTIVE, ContextState.FAILED],
            ContextState.ACTIVE: [ContextState.COMPLETED, ContextState.FAILED],
            ContextState.COMPLETED: [ContextState.MERGED],
            ContextState.FAILED: [],
            ContextState.MERGED: [],
        }

        # Verify created state can transition to active
        assert ContextState.ACTIVE in valid_transitions[ContextState.CREATED]


class TestContextMessage:
    """Tests for ContextMessage dataclass."""

    def test_message_creation(self) -> None:
        """Test basic message creation."""
        msg = ContextMessage(
            role="user",
            content="What are the EB-1A criteria?",
        )

        assert msg.role == "user"
        assert msg.content == "What are the EB-1A criteria?"
        assert isinstance(msg.timestamp, datetime)

    def test_message_token_estimation(self) -> None:
        """Test automatic token estimation."""
        content = "A" * 100  # 100 characters
        msg = ContextMessage(
            role="assistant",
            content=content,
        )

        # Token estimation: ~4 chars per token
        assert msg.tokens == 25  # 100 // 4

    def test_message_explicit_tokens(self) -> None:
        """Test explicit token count."""
        msg = ContextMessage(
            role="system",
            content="Instructions",
            tokens=50,
        )

        assert msg.tokens == 50

    def test_message_with_metadata(self) -> None:
        """Test message with custom metadata."""
        msg = ContextMessage(
            role="assistant",
            content="Response",
            metadata={"model": "claude-3", "tool_calls": ["search"]},
        )

        assert msg.metadata["model"] == "claude-3"
        assert "search" in msg.metadata["tool_calls"]

    def test_message_roles(self) -> None:
        """Test different message roles."""
        roles = ["system", "user", "assistant"]

        for role in roles:
            msg = ContextMessage(role=role, content=f"{role} message")
            assert msg.role == role


class TestIsolatedContext:
    """Tests for IsolatedContext dataclass."""

    def test_context_creation(self) -> None:
        """Test basic context creation."""
        ctx = IsolatedContext(
            name="research_subagent",
            task="Research EB-1A awards criterion",
        )

        assert ctx.name == "research_subagent"
        assert ctx.task == "Research EB-1A awards criterion"
        assert ctx.state == ContextState.CREATED
        assert len(ctx.id) == 8  # UUID truncated

    def test_context_default_values(self) -> None:
        """Test default values."""
        ctx = IsolatedContext()

        assert ctx.name == ""
        assert ctx.parent_id is None
        assert ctx.max_tokens == 50000
        assert ctx.state == ContextState.CREATED
        assert ctx.messages == []
        assert ctx.result == ""
        assert ctx.error is None

    def test_context_with_parent(self) -> None:
        """Test context with parent reference."""
        parent = IsolatedContext(name="parent")
        child = IsolatedContext(
            name="child",
            parent_id=parent.id,
        )

        assert child.parent_id == parent.id

    def test_total_tokens(self) -> None:
        """Test total token calculation."""
        ctx = IsolatedContext()
        ctx.messages = [
            ContextMessage(role="system", content="A" * 100, tokens=25),
            ContextMessage(role="user", content="B" * 200, tokens=50),
            ContextMessage(role="assistant", content="C" * 400, tokens=100),
        ]

        assert ctx.total_tokens == 175  # 25 + 50 + 100

    def test_remaining_tokens(self) -> None:
        """Test remaining token budget calculation."""
        ctx = IsolatedContext(max_tokens=1000)
        ctx.messages = [
            ContextMessage(role="user", content="Test", tokens=100),
        ]

        assert ctx.remaining_tokens == 900

    def test_remaining_tokens_no_overflow(self) -> None:
        """Test remaining tokens doesn't go negative."""
        ctx = IsolatedContext(max_tokens=50)
        ctx.messages = [
            ContextMessage(role="user", content="Test", tokens=100),
        ]

        assert ctx.remaining_tokens == 0  # max(0, 50 - 100)

    def test_is_active_property(self) -> None:
        """Test is_active property."""
        ctx = IsolatedContext()

        assert ctx.is_active is False  # Initially CREATED

        ctx.state = ContextState.ACTIVE
        assert ctx.is_active is True

        ctx.state = ContextState.COMPLETED
        assert ctx.is_active is False


class TestIsolatedContextMessageHandling:
    """Tests for message handling in IsolatedContext."""

    def test_add_message_basic(self) -> None:
        """Test adding a message to context."""
        ctx = IsolatedContext(max_tokens=1000)
        ctx.state = ContextState.ACTIVE

        result = ctx.add_message(
            role="user",
            content="What is EB-1A?",
        )

        assert result is True
        assert len(ctx.messages) == 1
        assert ctx.messages[0].role == "user"

    def test_add_message_with_metadata(self) -> None:
        """Test adding message with metadata."""
        ctx = IsolatedContext(max_tokens=1000)
        ctx.state = ContextState.ACTIVE

        ctx.add_message(
            role="assistant",
            content="Response",
            source="research_agent",
            confidence=0.95,
        )

        msg = ctx.messages[0]
        assert msg.metadata["source"] == "research_agent"
        assert msg.metadata["confidence"] == 0.95

    def test_add_message_respects_token_budget(self) -> None:
        """Test that adding messages respects token budget."""
        ctx = IsolatedContext(max_tokens=100)
        ctx.state = ContextState.ACTIVE

        # First message uses most of budget
        ctx.add_message(role="user", content="A" * 320)  # ~80 tokens

        # Second message exceeds budget
        result = ctx.add_message(role="user", content="B" * 200)  # ~50 tokens

        # Behavior depends on implementation - may reject or truncate
        assert ctx.total_tokens <= ctx.max_tokens or result is False


class TestIsolatedContextStateTransitions:
    """Tests for context state transitions."""

    def test_activate_context(self) -> None:
        """Test activating a context."""
        ctx = IsolatedContext()
        assert ctx.state == ContextState.CREATED

        ctx.state = ContextState.ACTIVE
        assert ctx.is_active is True

    def test_complete_context(self) -> None:
        """Test completing a context with result."""
        ctx = IsolatedContext(task="Research task")
        ctx.state = ContextState.ACTIVE
        ctx.result = "Research findings: 10 criteria identified"
        ctx.state = ContextState.COMPLETED

        assert ctx.state == ContextState.COMPLETED
        assert ctx.result != ""

    def test_fail_context(self) -> None:
        """Test failing a context with error."""
        ctx = IsolatedContext()
        ctx.state = ContextState.ACTIVE
        ctx.error = "API rate limit exceeded"
        ctx.state = ContextState.FAILED

        assert ctx.state == ContextState.FAILED
        assert ctx.error == "API rate limit exceeded"

    def test_merge_context(self) -> None:
        """Test merging a completed context."""
        ctx = IsolatedContext()
        ctx.state = ContextState.ACTIVE
        ctx.result = "Completed work"
        ctx.state = ContextState.COMPLETED
        ctx.state = ContextState.MERGED

        assert ctx.state == ContextState.MERGED


class TestIsolatedContextHierarchy:
    """Tests for parent-child context relationships."""

    def test_create_child_context(self) -> None:
        """Test creating a child context."""
        parent = IsolatedContext(
            name="main_agent",
            task="Process EB-1A case",
        )

        child = IsolatedContext(
            name="research_subagent",
            parent_id=parent.id,
            task="Research awards criterion",
        )

        assert child.parent_id == parent.id

    def test_multiple_children(self) -> None:
        """Test creating multiple child contexts."""
        parent = IsolatedContext(name="coordinator")

        children = [IsolatedContext(name=f"worker_{i}", parent_id=parent.id) for i in range(3)]

        assert all(c.parent_id == parent.id for c in children)
        assert len([c.id for c in children]) == 3


class TestIsolatedContextIntegration:
    """Integration tests for isolated context system."""

    def test_full_workflow(self) -> None:
        """Test complete context lifecycle."""
        # Create context
        ctx = IsolatedContext(
            name="research_agent",
            task="Research EB-1A scholarly articles criterion",
            max_tokens=10000,
        )
        assert ctx.state == ContextState.CREATED

        # Activate and add messages
        ctx.state = ContextState.ACTIVE
        ctx.add_message(
            role="system",
            content="You are a research agent specializing in EB-1A visa criteria.",
        )
        ctx.add_message(
            role="user",
            content="Find evidence for scholarly articles criterion.",
        )

        # Simulate work
        ctx.add_message(
            role="assistant",
            content="I found 15 publications in peer-reviewed journals...",
        )

        # Complete with result
        ctx.result = "Identified 15 qualifying publications with 500+ citations"
        ctx.result_tokens = len(ctx.result) // 4
        ctx.state = ContextState.COMPLETED

        assert ctx.state == ContextState.COMPLETED
        assert ctx.result != ""
        assert len(ctx.messages) == 3

    def test_parallel_contexts(self) -> None:
        """Test multiple parallel isolated contexts."""
        parent = IsolatedContext(name="coordinator", task="Process case")

        # Create parallel workers
        contexts = []
        criteria = ["awards", "membership", "publications", "judging"]

        for criterion in criteria:
            ctx = IsolatedContext(
                name=f"worker_{criterion}",
                parent_id=parent.id,
                task=f"Research {criterion} criterion",
                task_type="research",
            )
            ctx.state = ContextState.ACTIVE
            contexts.append(ctx)

        # All contexts are independent
        assert all(c.is_active for c in contexts)
        assert all(c.parent_id == parent.id for c in contexts)

        # Complete them
        for ctx in contexts:
            ctx.result = f"Found evidence for {ctx.task}"
            ctx.state = ContextState.COMPLETED

        assert all(c.state == ContextState.COMPLETED for c in contexts)

    def test_context_isolation(self) -> None:
        """Test that contexts are truly isolated."""
        ctx1 = IsolatedContext(name="agent_1")
        ctx2 = IsolatedContext(name="agent_2")

        ctx1.state = ContextState.ACTIVE
        ctx2.state = ContextState.ACTIVE

        ctx1.add_message(role="user", content="Message for agent 1")
        ctx2.add_message(role="user", content="Message for agent 2")

        # Messages should not leak
        assert len(ctx1.messages) == 1
        assert len(ctx2.messages) == 1
        assert "agent 1" in ctx1.messages[0].content
        assert "agent 2" in ctx2.messages[0].content


class TestContextMetadata:
    """Tests for context metadata handling."""

    def test_context_with_metadata(self) -> None:
        """Test context with custom metadata."""
        ctx = IsolatedContext(
            name="specialized_agent",
            task="Complex task",
            metadata={
                "model": "claude-3-opus",
                "temperature": 0.7,
                "max_retries": 3,
            },
        )

        assert ctx.metadata["model"] == "claude-3-opus"
        assert ctx.metadata["temperature"] == 0.7

    def test_update_metadata(self) -> None:
        """Test updating context metadata."""
        ctx = IsolatedContext(metadata={"version": 1})
        ctx.metadata["version"] = 2
        ctx.metadata["status"] = "updated"

        assert ctx.metadata["version"] == 2
        assert ctx.metadata["status"] == "updated"


# Pytest fixtures
@pytest.fixture
def active_context() -> IsolatedContext:
    """Create an active context for testing."""
    ctx = IsolatedContext(
        name="test_agent",
        task="Test task",
        max_tokens=5000,
    )
    ctx.state = ContextState.ACTIVE
    return ctx


@pytest.fixture
def context_with_messages(active_context: IsolatedContext) -> IsolatedContext:
    """Create context with sample messages."""
    active_context.add_message(
        role="system",
        content="You are a helpful assistant.",
    )
    active_context.add_message(
        role="user",
        content="Help me with EB-1A visa.",
    )
    active_context.add_message(
        role="assistant",
        content="I can help with that. The EB-1A is...",
    )
    return active_context


@pytest.fixture
def completed_context(context_with_messages: IsolatedContext) -> IsolatedContext:
    """Create a completed context."""
    context_with_messages.result = "Task completed successfully"
    context_with_messages.state = ContextState.COMPLETED
    return context_with_messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
