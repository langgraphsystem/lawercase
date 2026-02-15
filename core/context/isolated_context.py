"""Isolated Context Windows for Subagents.

Provides isolated context management for parallel agent execution:
- Each subagent gets independent context window
- No context leakage between agents
- Efficient memory usage
- Context synthesis after completion
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

import structlog

logger = structlog.get_logger(__name__)


class ContextState(str, Enum):
    """State of isolated context."""

    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    MERGED = "merged"


@dataclass(slots=True)
class ContextMessage:
    """Single message in isolated context."""

    role: str  # system, user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tokens == 0:
            self.tokens = len(self.content) // 4


@dataclass
class IsolatedContext:
    """Isolated context window for a subagent.

    Features:
    - Independent message history
    - Token budget management
    - State tracking
    - Result storage
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    parent_id: str | None = None
    max_tokens: int = 50000
    state: ContextState = ContextState.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Message history
    messages: list[ContextMessage] = field(default_factory=list)

    # Task info
    task: str = ""
    task_type: str = "general"

    # Results
    result: str = ""
    result_tokens: int = 0
    error: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens used in this context."""
        return sum(m.tokens for m in self.messages)

    @property
    def remaining_tokens(self) -> int:
        """Remaining token budget."""
        return max(0, self.max_tokens - self.total_tokens)

    @property
    def is_active(self) -> bool:
        """Check if context is active."""
        return self.state == ContextState.ACTIVE

    def add_message(
        self,
        role: str,
        content: str,
        **metadata: Any,
    ) -> bool:
        """Add message to context.

        Args:
            role: Message role (system/user/assistant)
            content: Message content
            **metadata: Additional metadata

        Returns:
            True if added, False if would exceed budget
        """
        msg = ContextMessage(role=role, content=content, metadata=metadata)

        if self.total_tokens + msg.tokens > self.max_tokens:
            logger.warning(
                "isolated_context.budget_exceeded",
                context_id=self.id,
                current=self.total_tokens,
                new=msg.tokens,
                max=self.max_tokens,
            )
            return False

        self.messages.append(msg)
        return True

    def add_system(self, content: str) -> bool:
        """Add system message."""
        return self.add_message("system", content)

    def add_user(self, content: str) -> bool:
        """Add user message."""
        return self.add_message("user", content)

    def add_assistant(self, content: str) -> bool:
        """Add assistant message."""
        return self.add_message("assistant", content)

    def set_result(self, result: str, error: str | None = None) -> None:
        """Set the result of this context's task."""
        self.result = result
        self.result_tokens = len(result) // 4
        self.error = error
        self.state = ContextState.FAILED if error else ContextState.COMPLETED

    def activate(self) -> None:
        """Activate the context."""
        self.state = ContextState.ACTIVE

    def get_messages_for_llm(self) -> list[dict[str, str]]:
        """Get messages in LLM format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def get_summary(self) -> dict[str, Any]:
        """Get context summary."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "task": self.task[:100] + "..." if len(self.task) > 100 else self.task,
            "messages": len(self.messages),
            "total_tokens": self.total_tokens,
            "remaining_tokens": self.remaining_tokens,
            "has_result": bool(self.result),
            "has_error": bool(self.error),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "state": self.state.value,
            "task": self.task,
            "task_type": self.task_type,
            "messages": [
                {"role": m.role, "content": m.content, "tokens": m.tokens} for m in self.messages
            ],
            "result": self.result,
            "error": self.error,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
        }


class IsolatedContextPool:
    """Pool manager for isolated contexts.

    Manages multiple isolated contexts for parallel execution:
    - Create and track contexts
    - Enforce total memory limits
    - Context lifecycle management

    Usage:
        pool = IsolatedContextPool(max_total_tokens=500000)

        # Create isolated contexts for subtasks
        ctx1 = pool.create("research_task_1", max_tokens=50000)
        ctx2 = pool.create("research_task_2", max_tokens=50000)

        # Run tasks in parallel
        await asyncio.gather(
            run_agent(ctx1),
            run_agent(ctx2),
        )

        # Get all results
        results = pool.get_all_results()
    """

    def __init__(
        self,
        max_total_tokens: int = 500000,
        max_contexts: int = 10,
    ) -> None:
        """Initialize context pool.

        Args:
            max_total_tokens: Maximum total tokens across all contexts
            max_contexts: Maximum number of concurrent contexts
        """
        self.max_total_tokens = max_total_tokens
        self.max_contexts = max_contexts
        self._contexts: dict[str, IsolatedContext] = {}
        self._lock = asyncio.Lock()

    @property
    def total_tokens_used(self) -> int:
        """Total tokens used across all contexts."""
        return sum(ctx.total_tokens for ctx in self._contexts.values())

    @property
    def remaining_tokens(self) -> int:
        """Remaining token budget for pool."""
        return max(0, self.max_total_tokens - self.total_tokens_used)

    @property
    def active_count(self) -> int:
        """Number of active contexts."""
        return sum(1 for ctx in self._contexts.values() if ctx.is_active)

    def create(
        self,
        name: str,
        task: str = "",
        task_type: str = "general",
        max_tokens: int | None = None,
        parent_id: str | None = None,
        **metadata: Any,
    ) -> IsolatedContext | None:
        """Create a new isolated context.

        Args:
            name: Context name
            task: Task description
            task_type: Type of task
            max_tokens: Token budget (auto-calculated if None)
            parent_id: Parent context ID
            **metadata: Additional metadata

        Returns:
            Created context or None if limits exceeded
        """
        # Check context limit
        if len(self._contexts) >= self.max_contexts:
            logger.warning(
                "isolated_context_pool.max_contexts_reached",
                current=len(self._contexts),
                max=self.max_contexts,
            )
            return None

        # Auto-calculate max_tokens if not specified
        if max_tokens is None:
            # Distribute remaining budget evenly among potential new contexts
            remaining_slots = self.max_contexts - len(self._contexts)
            max_tokens = min(
                self.remaining_tokens // max(1, remaining_slots),
                100000,  # Cap at 100k per context
            )

        # Check token budget
        if max_tokens > self.remaining_tokens:
            logger.warning(
                "isolated_context_pool.insufficient_tokens",
                requested=max_tokens,
                remaining=self.remaining_tokens,
            )
            return None

        # Create context
        ctx = IsolatedContext(
            name=name,
            parent_id=parent_id,
            max_tokens=max_tokens,
            task=task,
            task_type=task_type,
            metadata=metadata,
        )

        self._contexts[ctx.id] = ctx

        logger.info(
            "isolated_context.created",
            context_id=ctx.id,
            name=name,
            max_tokens=max_tokens,
        )

        return ctx

    def get(self, context_id: str) -> IsolatedContext | None:
        """Get context by ID."""
        return self._contexts.get(context_id)

    def get_by_name(self, name: str) -> IsolatedContext | None:
        """Get context by name."""
        for ctx in self._contexts.values():
            if ctx.name == name:
                return ctx
        return None

    def get_active(self) -> list[IsolatedContext]:
        """Get all active contexts."""
        return [ctx for ctx in self._contexts.values() if ctx.is_active]

    def get_completed(self) -> list[IsolatedContext]:
        """Get all completed contexts."""
        return [ctx for ctx in self._contexts.values() if ctx.state == ContextState.COMPLETED]

    def get_all_results(self) -> dict[str, str]:
        """Get results from all completed contexts."""
        return {ctx.name or ctx.id: ctx.result for ctx in self._contexts.values() if ctx.result}

    def remove(self, context_id: str) -> bool:
        """Remove a context."""
        if context_id in self._contexts:
            del self._contexts[context_id]
            return True
        return False

    def clear_completed(self) -> int:
        """Clear all completed/merged contexts."""
        to_remove = [
            ctx_id
            for ctx_id, ctx in self._contexts.items()
            if ctx.state in (ContextState.COMPLETED, ContextState.MERGED, ContextState.FAILED)
        ]
        for ctx_id in to_remove:
            del self._contexts[ctx_id]
        return len(to_remove)

    def clear_all(self) -> None:
        """Clear all contexts."""
        self._contexts.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        by_state = {}
        for ctx in self._contexts.values():
            state = ctx.state.value
            by_state[state] = by_state.get(state, 0) + 1

        return {
            "total_contexts": len(self._contexts),
            "active_contexts": self.active_count,
            "total_tokens_used": self.total_tokens_used,
            "remaining_tokens": self.remaining_tokens,
            "max_total_tokens": self.max_total_tokens,
            "max_contexts": self.max_contexts,
            "by_state": by_state,
        }
