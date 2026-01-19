"""LangGraph 1.0 Human-in-the-Loop and Interrupt Features.

This module implements modern LangGraph 1.0 patterns for:
- interrupt() function for workflow pauses
- Command type for routing control
- NodeInterrupt exception handling
- Durable execution with checkpointing
- Human approval workflows

Based on LangGraph 1.0 release (October 2025).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver

# Try importing LangGraph 1.0 features
try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.errors import NodeInterrupt
    from langgraph.types import Command, interrupt

    LANGGRAPH_1_0 = True
except ImportError:
    # Fallback implementations for older versions
    LANGGRAPH_1_0 = False

    class Command:
        """Fallback Command class for routing control."""

        def __init__(
            self,
            *,
            goto: str | list[str] | None = None,
            update: dict[str, Any] | None = None,
            resume: Any | None = None,
        ):
            self.goto = goto
            self.update = update
            self.resume = resume

    class NodeInterrupt(Exception):
        """Fallback NodeInterrupt exception."""

        def __init__(self, value: Any = None):
            self.value = value
            super().__init__(str(value))

    def interrupt(value: Any = None) -> Any:
        """Fallback interrupt function that raises NodeInterrupt."""
        raise NodeInterrupt(value)

    MemorySaver = None
    SqliteSaver = None


class InterruptType(str, Enum):
    """Types of workflow interrupts."""

    APPROVAL_REQUIRED = "approval_required"
    INPUT_REQUIRED = "input_required"
    VALIDATION_REQUIRED = "validation_required"
    REVIEW_REQUIRED = "review_required"
    DECISION_REQUIRED = "decision_required"
    ERROR_RECOVERY = "error_recovery"
    CHECKPOINT = "checkpoint"


class ApprovalStatus(str, Enum):
    """Status of human approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


@dataclass
class InterruptContext:
    """Context for a workflow interrupt.

    Contains all information needed to resume a workflow after human intervention.
    """

    interrupt_id: str = field(default_factory=lambda: str(uuid4()))
    interrupt_type: InterruptType = InterruptType.APPROVAL_REQUIRED
    workflow_id: str = ""
    thread_id: str = ""
    node_name: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Human-readable context
    title: str = ""
    description: str = ""
    instructions: str = ""

    # Data for the human to review
    data: dict[str, Any] = field(default_factory=dict)

    # Options for human response
    options: list[str] = field(default_factory=lambda: ["approve", "reject", "revise"])
    allow_custom_input: bool = False

    # Timeout settings
    timeout_seconds: int | None = None
    escalate_on_timeout: bool = False
    escalation_target: str | None = None

    # Response (filled after human action)
    response: str | None = None
    response_data: dict[str, Any] = field(default_factory=dict)
    responded_at: datetime | None = None
    responded_by: str | None = None


class InterruptRequest(BaseModel):
    """Pydantic model for interrupt request serialization."""

    interrupt_id: str = Field(default_factory=lambda: str(uuid4()))
    interrupt_type: InterruptType
    workflow_id: str
    thread_id: str
    node_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    title: str
    description: str = ""
    instructions: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    options: list[str] = Field(default_factory=lambda: ["approve", "reject"])
    allow_custom_input: bool = False

    timeout_seconds: int | None = None


class InterruptResponse(BaseModel):
    """Pydantic model for interrupt response."""

    interrupt_id: str
    response: str
    response_data: dict[str, Any] = Field(default_factory=dict)
    responded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    responded_by: str = "user"

    # Additional metadata
    notes: str = ""
    attachments: list[str] = Field(default_factory=list)


class HumanInLoopManager:
    """Manager for human-in-the-loop workflow interrupts.

    Handles:
    - Creating and tracking interrupts
    - Storing interrupt state for resume
    - Notifying humans of pending actions
    - Processing human responses
    - Timeout handling and escalation

    Example usage:
        manager = HumanInLoopManager()

        # In a workflow node
        async def approval_node(state):
            context = await manager.create_interrupt(
                interrupt_type=InterruptType.APPROVAL_REQUIRED,
                workflow_id=state.thread_id,
                title="Review EB-1A Petition",
                data={"petition": state.petition_content},
            )

            # This raises NodeInterrupt, pausing the workflow
            response = interrupt(context)

            # After resume, process response
            if response.response == "approved":
                return Command(goto="finalize")
            return Command(goto="revise")
    """

    def __init__(
        self,
        checkpoint_saver: BaseCheckpointSaver | None = None,
        notification_callback: Callable[[InterruptContext], None] | None = None,
    ):
        self._pending: dict[str, InterruptContext] = {}
        self._completed: dict[str, InterruptContext] = {}
        self._checkpoint_saver = checkpoint_saver
        self._notification_callback = notification_callback
        self._response_futures: dict[str, asyncio.Future] = {}

    async def create_interrupt(
        self,
        *,
        interrupt_type: InterruptType,
        workflow_id: str,
        thread_id: str = "",
        node_name: str = "",
        title: str,
        description: str = "",
        instructions: str = "",
        data: dict[str, Any] | None = None,
        options: list[str] | None = None,
        allow_custom_input: bool = False,
        timeout_seconds: int | None = None,
        escalate_on_timeout: bool = False,
        escalation_target: str | None = None,
    ) -> InterruptContext:
        """Create a new interrupt context.

        Args:
            interrupt_type: Type of interrupt
            workflow_id: ID of the workflow
            thread_id: Thread/conversation ID
            node_name: Name of the node creating interrupt
            title: Human-readable title
            description: Detailed description
            instructions: Instructions for the human
            data: Data to show for review
            options: Available response options
            allow_custom_input: Whether to allow custom input
            timeout_seconds: Timeout before escalation
            escalate_on_timeout: Whether to escalate on timeout
            escalation_target: Target for escalation

        Returns:
            InterruptContext ready for use with interrupt()
        """
        context = InterruptContext(
            interrupt_type=interrupt_type,
            workflow_id=workflow_id,
            thread_id=thread_id or workflow_id,
            node_name=node_name,
            title=title,
            description=description,
            instructions=instructions,
            data=data or {},
            options=options or ["approve", "reject"],
            allow_custom_input=allow_custom_input,
            timeout_seconds=timeout_seconds,
            escalate_on_timeout=escalate_on_timeout,
            escalation_target=escalation_target,
        )

        self._pending[context.interrupt_id] = context

        # Notify if callback is set
        if self._notification_callback:
            try:
                self._notification_callback(context)
            except Exception:  # nosec B110
                pass  # Don't fail on notification errors - callbacks are optional

        return context

    async def respond_to_interrupt(
        self,
        interrupt_id: str,
        response: str,
        response_data: dict[str, Any] | None = None,
        responded_by: str = "user",
        notes: str = "",
    ) -> InterruptContext | None:
        """Respond to a pending interrupt.

        Args:
            interrupt_id: ID of the interrupt
            response: Response string (from options or custom)
            response_data: Additional response data
            responded_by: Who responded
            notes: Additional notes

        Returns:
            Updated InterruptContext or None if not found
        """
        context = self._pending.get(interrupt_id)
        if not context:
            return None

        context.response = response
        context.response_data = response_data or {}
        context.responded_at = datetime.now(UTC)
        context.responded_by = responded_by

        # Move from pending to completed
        del self._pending[interrupt_id]
        self._completed[interrupt_id] = context

        # Resolve any waiting futures
        if interrupt_id in self._response_futures:
            future = self._response_futures.pop(interrupt_id)
            if not future.done():
                future.set_result(context)

        return context

    async def wait_for_response(
        self,
        interrupt_id: str,
        timeout: float | None = None,
    ) -> InterruptContext | None:
        """Wait for a response to an interrupt.

        Args:
            interrupt_id: ID of the interrupt
            timeout: Timeout in seconds

        Returns:
            InterruptContext with response or None if timeout
        """
        # Check if already completed
        if interrupt_id in self._completed:
            return self._completed[interrupt_id]

        # Check if not pending
        if interrupt_id not in self._pending:
            return None

        # Create a future and wait
        if interrupt_id not in self._response_futures:
            self._response_futures[interrupt_id] = asyncio.get_event_loop().create_future()

        try:
            if timeout:
                context = await asyncio.wait_for(
                    self._response_futures[interrupt_id], timeout=timeout
                )
            else:
                context = await self._response_futures[interrupt_id]
            return context
        except asyncio.TimeoutError:
            # Handle timeout
            context = self._pending.get(interrupt_id)
            if context and context.escalate_on_timeout:
                await self._escalate_interrupt(context)
            return None

    async def _escalate_interrupt(self, context: InterruptContext) -> None:
        """Escalate a timed-out interrupt."""
        context.response = ApprovalStatus.TIMED_OUT.value
        context.responded_at = datetime.now(UTC)
        context.responded_by = "system"
        context.response_data["escalated_to"] = context.escalation_target

        del self._pending[context.interrupt_id]
        self._completed[context.interrupt_id] = context

    def get_pending_interrupts(
        self,
        workflow_id: str | None = None,
        interrupt_type: InterruptType | None = None,
    ) -> list[InterruptContext]:
        """Get pending interrupts, optionally filtered."""
        results = list(self._pending.values())

        if workflow_id:
            results = [c for c in results if c.workflow_id == workflow_id]

        if interrupt_type:
            results = [c for c in results if c.interrupt_type == interrupt_type]

        return results

    def get_interrupt(self, interrupt_id: str) -> InterruptContext | None:
        """Get an interrupt by ID (pending or completed)."""
        return self._pending.get(interrupt_id) or self._completed.get(interrupt_id)


# Convenience functions for use in workflow nodes


def create_approval_interrupt(
    *,
    title: str,
    data: dict[str, Any],
    workflow_id: str,
    description: str = "",
    options: list[str] | None = None,
) -> InterruptContext:
    """Create an approval interrupt context.

    Example:
        context = create_approval_interrupt(
            title="Review EB-1A Petition",
            data={"petition": content, "score": 85},
            workflow_id=state.thread_id,
        )
        response = interrupt(context)
    """
    return InterruptContext(
        interrupt_type=InterruptType.APPROVAL_REQUIRED,
        workflow_id=workflow_id,
        title=title,
        description=description,
        data=data,
        options=options or ["approve", "reject", "request_revision"],
    )


def create_validation_interrupt(
    *,
    title: str,
    validation_results: dict[str, Any],
    workflow_id: str,
    issues: list[str] | None = None,
) -> InterruptContext:
    """Create a validation review interrupt context."""
    return InterruptContext(
        interrupt_type=InterruptType.VALIDATION_REQUIRED,
        workflow_id=workflow_id,
        title=title,
        data={
            "validation_results": validation_results,
            "issues": issues or [],
        },
        options=["accept", "override", "request_fix"],
        allow_custom_input=True,
    )


def create_input_interrupt(
    *,
    title: str,
    prompt: str,
    workflow_id: str,
    fields: list[dict[str, Any]] | None = None,
) -> InterruptContext:
    """Create an input request interrupt context."""
    return InterruptContext(
        interrupt_type=InterruptType.INPUT_REQUIRED,
        workflow_id=workflow_id,
        title=title,
        description=prompt,
        data={"fields": fields or []},
        options=[],
        allow_custom_input=True,
    )


def create_decision_interrupt(
    *,
    title: str,
    question: str,
    workflow_id: str,
    options: list[str],
    data: dict[str, Any] | None = None,
) -> InterruptContext:
    """Create a decision point interrupt context."""
    return InterruptContext(
        interrupt_type=InterruptType.DECISION_REQUIRED,
        workflow_id=workflow_id,
        title=title,
        description=question,
        data=data or {},
        options=options,
        allow_custom_input=False,
    )


# Workflow node decorator for automatic interrupt handling

T = TypeVar("T")


def with_human_approval(
    title: str,
    condition: Callable[[Any], bool] | None = None,
    options: list[str] | None = None,
):
    """Decorator to add human approval to a workflow node.

    Example:
        @with_human_approval(
            title="Approve document generation",
            condition=lambda state: state.validation_score < 0.9,
            options=["approve", "reject", "edit"],
        )
        async def generate_document(state):
            # ... generate document ...
            return state
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(state: Any) -> Any:
            # Check if approval is needed
            if condition and not condition(state):
                return await func(state)

            # Create interrupt context
            context = create_approval_interrupt(
                title=title,
                data=state.model_dump() if hasattr(state, "model_dump") else dict(state),
                workflow_id=getattr(state, "thread_id", str(uuid4())),
                options=options,
            )

            # Raise interrupt
            response = interrupt(context)

            # Process response
            if hasattr(response, "response"):
                if response.response == "reject":
                    # Set error state
                    if hasattr(state, "error"):
                        state.error = "Human rejected"
                    return state
                if response.response == "edit":
                    # Allow editing
                    if response.response_data and hasattr(state, "__dict__"):
                        for key, value in response.response_data.items():
                            if hasattr(state, key):
                                setattr(state, key, value)

            # Continue with the node
            return await func(state)

        return wrapper

    return decorator


# Command helpers for routing control


def goto(node: str | list[str]) -> Command:
    """Create a Command to go to specific node(s)."""
    return Command(goto=node)


def goto_with_update(node: str, updates: dict[str, Any]) -> Command:
    """Create a Command to go to a node with state updates."""
    return Command(goto=node, update=updates)


def resume_with_value(value: Any) -> Command:
    """Create a Command to resume with a value."""
    return Command(resume=value)


# Checkpoint management utilities


def get_checkpoint_saver(
    backend: Literal["memory", "sqlite", "postgres"] = "memory",
    connection_string: str | None = None,
) -> Any:
    """Get a checkpoint saver instance.

    Args:
        backend: Type of checkpoint storage
        connection_string: Connection string for database backends

    Returns:
        Checkpoint saver instance
    """
    if not LANGGRAPH_1_0:
        return None

    if backend == "memory":
        return MemorySaver()

    if backend == "sqlite":
        if SqliteSaver is None:
            raise ImportError("SqliteSaver not available")
        return SqliteSaver.from_conn_string(connection_string or ":memory:")

    if backend == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            if not connection_string:
                raise ValueError("Connection string required for PostgreSQL")
            return PostgresSaver.from_conn_string(connection_string)
        except ImportError:
            raise ImportError("PostgresSaver not available. Install langgraph-checkpoint-postgres")

    raise ValueError(f"Unknown backend: {backend}")


# Export all public symbols
__all__ = [
    # Enums
    "InterruptType",
    "ApprovalStatus",
    # Data classes
    "InterruptContext",
    "InterruptRequest",
    "InterruptResponse",
    # Manager
    "HumanInLoopManager",
    # Convenience functions
    "create_approval_interrupt",
    "create_validation_interrupt",
    "create_input_interrupt",
    "create_decision_interrupt",
    # Decorator
    "with_human_approval",
    # Command helpers
    "goto",
    "goto_with_update",
    "resume_with_value",
    # Checkpoint utilities
    "get_checkpoint_saver",
    # Re-exports from LangGraph
    "Command",
    "NodeInterrupt",
    "interrupt",
    # Feature flag
    "LANGGRAPH_1_0",
]
