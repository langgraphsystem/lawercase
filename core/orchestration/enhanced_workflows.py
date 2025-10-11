"""Enhanced orchestration patterns for complex workflows.

This module provides advanced workflow patterns including:
- Error recovery with retry mechanisms
- Conditional routing optimization
- Human-in-the-loop workflows
- Complex multi-agent coordination
- Parallel execution with fan-out/fan-in
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ..memory.models import AuditEvent
from .workflow_graph import WorkflowState

if TYPE_CHECKING:
    from ..memory.memory_manager import MemoryManager

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ============================================================================
# ENHANCED STATE MODELS
# ============================================================================


class RetryStrategy(str, Enum):
    """Retry strategies for error recovery."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


class WorkflowStage(str, Enum):
    """Workflow execution stages."""

    INIT = "init"
    VALIDATION = "validation"
    PROCESSING = "processing"
    REVIEW = "review"
    APPROVAL = "approval"
    COMPLETION = "completion"
    ERROR = "error"


class HumanFeedback(BaseModel):
    """Human feedback for HITL workflows."""

    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reviewer_id: str = Field(..., description="ID of human reviewer")
    approved: bool = Field(..., description="Approval decision")
    comments: str | None = Field(default=None, description="Review comments")
    suggested_changes: dict[str, Any] | None = Field(default=None)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class ErrorContext(BaseModel):
    """Detailed error context for recovery."""

    error_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_type: str = Field(..., description="Error category")
    error_message: str = Field(..., description="Error details")
    failed_node: str = Field(..., description="Node where error occurred")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_strategy: RetryStrategy = Field(default=RetryStrategy.EXPONENTIAL_BACKOFF)
    recoverable: bool = Field(default=True, description="Can be recovered")
    stack_trace: str | None = Field(default=None)


class EnhancedWorkflowState(WorkflowState):
    """Extended workflow state with enhanced orchestration features."""

    # Error recovery
    errors: list[ErrorContext] = Field(default_factory=list)
    retry_state: dict[str, int] = Field(default_factory=dict, description="Retry counters per node")

    # Human-in-the-loop
    awaiting_human_feedback: bool = Field(default=False)
    human_feedback: list[HumanFeedback] = Field(default_factory=list)
    feedback_timeout: datetime | None = Field(default=None)

    # Workflow stage tracking
    current_stage: WorkflowStage = Field(default=WorkflowStage.INIT)
    stage_history: list[tuple[WorkflowStage, datetime]] = Field(default_factory=list)
    checkpoints: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Parallel execution tracking
    parallel_tasks: dict[str, Any] = Field(default_factory=dict)
    parallel_results: dict[str, Any] = Field(default_factory=dict)
    parallel_errors: dict[str, str] = Field(default_factory=dict)

    # Routing optimization
    routing_decision: str | None = Field(default=None, description="Last routing decision")
    routing_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    routing_alternatives: list[str] = Field(default_factory=list)
    routing_history: list[tuple[str, str, float]] = Field(default_factory=list)

    # Performance metrics
    node_execution_times: dict[str, float] = Field(default_factory=dict)
    total_execution_time: float | None = Field(default=None)
    workflow_start_time: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ERROR RECOVERY MECHANISMS
# ============================================================================


class ErrorRecoveryManager:
    """Manages error recovery and retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        default_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
    ):
        self.max_retries = max_retries
        self.default_strategy = default_strategy
        self.base_delay = base_delay

    def should_retry(self, error_ctx: ErrorContext) -> bool:
        """Determine if error should be retried."""
        if not error_ctx.recoverable:
            return False
        if error_ctx.retry_count >= error_ctx.max_retries:
            return False
        return error_ctx.retry_strategy != RetryStrategy.NO_RETRY

    async def get_retry_delay(self, error_ctx: ErrorContext) -> float:
        """Calculate retry delay based on strategy."""
        if error_ctx.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        if error_ctx.retry_strategy == RetryStrategy.FIXED_DELAY:
            return self.base_delay
        if error_ctx.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return self.base_delay * (2**error_ctx.retry_count)
        return 0.0

    async def handle_error(
        self, state: EnhancedWorkflowState, error: Exception, node_name: str
    ) -> EnhancedWorkflowState:
        """Handle error and update state."""
        error_ctx = ErrorContext(
            error_type=type(error).__name__,
            error_message=str(error),
            failed_node=node_name,
            retry_count=state.retry_state.get(node_name, 0),
            max_retries=self.max_retries,
            retry_strategy=self.default_strategy,
            recoverable=self._is_recoverable(error),
            stack_trace=str(error),
        )

        state.errors.append(error_ctx)
        state.retry_state[node_name] = error_ctx.retry_count + 1
        state.current_stage = WorkflowStage.ERROR

        if self.should_retry(error_ctx):
            delay = await self.get_retry_delay(error_ctx)
            if delay > 0:
                await asyncio.sleep(delay)
            # Mark for retry
            state.workflow_step = f"retry_{node_name}"
        else:
            # Mark as failed
            state.error = f"Max retries exceeded for {node_name}: {error!s}"
            state.workflow_step = "failed"

        return state

    def _is_recoverable(self, error: Exception) -> bool:
        """Determine if error is recoverable."""
        # Non-recoverable errors
        non_recoverable = (ValueError, TypeError, KeyError, AttributeError)
        if isinstance(error, non_recoverable):
            return False

        # Recoverable errors (network, timeout, etc.)
        recoverable = (ConnectionError, TimeoutError, OSError)
        if isinstance(error, recoverable):
            return True

        # Default: assume recoverable
        return True


# ============================================================================
# HUMAN-IN-THE-LOOP WORKFLOWS
# ============================================================================


class HumanReviewManager:
    """Manages human-in-the-loop workflows."""

    def __init__(self, default_timeout_minutes: int = 60):
        self.default_timeout_minutes = default_timeout_minutes
        self.pending_reviews: dict[str, EnhancedWorkflowState] = {}

    async def request_human_review(
        self, state: EnhancedWorkflowState, reason: str, timeout_minutes: int | None = None
    ) -> EnhancedWorkflowState:
        """Request human review and pause workflow."""
        timeout = timeout_minutes or self.default_timeout_minutes
        state.awaiting_human_feedback = True
        state.feedback_timeout = datetime.utcnow() + timedelta(minutes=timeout)
        state.workflow_step = "awaiting_human_feedback"

        # Store review request
        review_id = f"review_{state.thread_id}_{len(state.human_feedback)}"
        self.pending_reviews[review_id] = state

        # Log audit event
        if state.event:
            state.event = AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id,
                thread_id=state.thread_id,
                source="enhanced_workflow",
                action="human_review_requested",
                payload={
                    "reason": reason,
                    "timeout_minutes": timeout,
                    "review_id": review_id,
                },
                tags=["human_review"],
            )

        return state

    async def submit_human_feedback(
        self, review_id: str, feedback: HumanFeedback
    ) -> EnhancedWorkflowState | None:
        """Submit human feedback and resume workflow."""
        if review_id not in self.pending_reviews:
            return None

        state = self.pending_reviews.pop(review_id)
        state.human_feedback.append(feedback)
        state.awaiting_human_feedback = False
        state.feedback_timeout = None

        if feedback.approved:
            state.workflow_step = "human_approved"
        else:
            state.workflow_step = "human_rejected"

        return state

    async def check_timeout(self, state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Check if human feedback timeout expired."""
        if state.awaiting_human_feedback and state.feedback_timeout:
            if datetime.utcnow() > state.feedback_timeout:
                state.awaiting_human_feedback = False
                state.workflow_step = "human_feedback_timeout"
                state.error = "Human feedback timeout expired"
                state.current_stage = WorkflowStage.ERROR

        return state


# ============================================================================
# CONDITIONAL ROUTING OPTIMIZATION
# ============================================================================


class RouterOptimizer:
    """Optimizes conditional routing decisions."""

    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
        self.routing_stats: dict[str, list[float]] = {}

    async def optimize_routing(
        self, state: EnhancedWorkflowState, routing_options: dict[str, float]
    ) -> tuple[str, float]:
        """Select optimal routing based on confidence scores."""
        if not routing_options:
            return "default", 0.0

        # Sort by confidence
        sorted_options = sorted(routing_options.items(), key=lambda x: x[1], reverse=True)

        best_route, confidence = sorted_options[0]

        # Update state
        state.routing_decision = best_route
        state.routing_confidence = confidence
        state.routing_alternatives = [route for route, _ in sorted_options[1:]]
        state.routing_history.append((best_route, state.workflow_step, confidence))

        # Track statistics
        if best_route not in self.routing_stats:
            self.routing_stats[best_route] = []
        self.routing_stats[best_route].append(confidence)

        # Log low confidence routing
        if confidence < self.confidence_threshold:
            if state.event:
                state.event = AuditEvent(
                    event_id=str(uuid4()),
                    user_id=state.user_id,
                    thread_id=state.thread_id,
                    source="router_optimizer",
                    action="low_confidence_routing",
                    payload={
                        "route": best_route,
                        "confidence": confidence,
                        "alternatives": state.routing_alternatives,
                    },
                    tags=["routing", "low_confidence"],
                )

        return best_route, confidence

    def get_routing_performance(self) -> dict[str, dict[str, float]]:
        """Get routing performance statistics."""
        stats = {}
        for route, confidences in self.routing_stats.items():
            if confidences:
                stats[route] = {
                    "avg_confidence": sum(confidences) / len(confidences),
                    "min_confidence": min(confidences),
                    "max_confidence": max(confidences),
                    "count": len(confidences),
                }
        return stats


# ============================================================================
# COMPLEX WORKFLOW PATTERNS
# ============================================================================


def build_enhanced_memory_workflow(
    memory: MemoryManager,
    error_manager: ErrorRecoveryManager | None = None,
    review_manager: HumanReviewManager | None = None,
    router_optimizer: RouterOptimizer | None = None,
) -> Any:
    """Build enhanced memory workflow with advanced patterns."""
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("LangGraph required for enhanced workflows")

    error_manager = error_manager or ErrorRecoveryManager()
    review_manager = review_manager or HumanReviewManager()
    router_optimizer = router_optimizer or RouterOptimizer()

    workflow = StateGraph(EnhancedWorkflowState)

    # ========================================================================
    # Node: Initialize
    # ========================================================================
    async def node_initialize(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Initialize workflow."""
        state.current_stage = WorkflowStage.INIT
        state.stage_history.append((WorkflowStage.INIT, datetime.utcnow()))
        state.workflow_step = "initialized"
        return state

    # ========================================================================
    # Node: Log Audit with Error Recovery
    # ========================================================================
    async def node_log_audit_safe(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Log audit event with error recovery."""
        try:
            start_time = datetime.utcnow()

            if state.event:
                await memory.alog_audit(state.event)
                state.workflow_step = "audit_logged"

            # Track execution time
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            state.node_execution_times["log_audit"] = elapsed

        except Exception as e:
            state = await error_manager.handle_error(state, e, "log_audit")

        return state

    # ========================================================================
    # Node: Reflect with Retry
    # ========================================================================
    async def node_reflect_safe(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Reflect facts with retry logic."""
        try:
            start_time = datetime.utcnow()

            if state.event:
                reflections = await memory.awrite(state.event)
                state.reflected = reflections
                state.workflow_step = "reflected"
                state.current_stage = WorkflowStage.PROCESSING

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            state.node_execution_times["reflect"] = elapsed

        except Exception as e:
            state = await error_manager.handle_error(state, e, "reflect")

        return state

    # ========================================================================
    # Node: Retrieve with Optimization
    # ========================================================================
    async def node_retrieve_optimized(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Retrieve with routing optimization."""
        try:
            start_time = datetime.utcnow()

            if state.query:
                # Determine retrieval strategy
                routing_options = {
                    "semantic_search": 0.8,  # High confidence for semantic
                    "keyword_search": 0.6,  # Medium for keyword
                    "hybrid_search": 0.9,  # Highest for hybrid
                }

                strategy, confidence = await router_optimizer.optimize_routing(
                    state, routing_options
                )

                # Execute retrieval
                records = await memory.aretrieve(state.query, user_id=state.user_id, topk=5)
                state.retrieved = records
                state.workflow_step = f"retrieved_{strategy}"

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            state.node_execution_times["retrieve"] = elapsed

        except Exception as e:
            state = await error_manager.handle_error(state, e, "retrieve")

        return state

    # ========================================================================
    # Node: Human Review Checkpoint
    # ========================================================================
    async def node_human_review_check(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Check if human review is needed."""
        # Check if review required based on confidence
        if state.routing_confidence and state.routing_confidence < 0.7:
            state = await review_manager.request_human_review(
                state, reason="Low confidence routing decision"
            )
        else:
            state.workflow_step = "review_not_needed"

        return state

    # ========================================================================
    # Node: Finalize
    # ========================================================================
    async def node_finalize(state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """Finalize workflow execution."""
        state.current_stage = WorkflowStage.COMPLETION
        state.stage_history.append((WorkflowStage.COMPLETION, datetime.utcnow()))
        state.workflow_step = "completed"

        # Calculate total execution time
        elapsed = (datetime.utcnow() - state.workflow_start_time).total_seconds()
        state.total_execution_time = elapsed

        # Create checkpoint
        state.checkpoints["final"] = {
            "reflected_count": len(state.reflected),
            "retrieved_count": len(state.retrieved),
            "errors": len(state.errors),
            "human_feedback_count": len(state.human_feedback),
            "total_time": elapsed,
        }

        return state

    # ========================================================================
    # Conditional Edge: Routing Decision
    # ========================================================================
    def route_next_step(
        state: EnhancedWorkflowState,
    ) -> Literal["human_review", "finalize", "retry", "error"]:
        """Determine next step based on state."""
        # Check for errors first
        if state.workflow_step == "failed":
            return "error"

        # Check for retry
        if state.workflow_step.startswith("retry_"):
            return "retry"

        # Check for human feedback
        if state.awaiting_human_feedback:
            return "human_review"

        # Otherwise, proceed to finalize
        return "finalize"

    # ========================================================================
    # Build Graph
    # ========================================================================
    workflow.add_node("initialize", node_initialize)
    workflow.add_node("log_audit", node_log_audit_safe)
    workflow.add_node("reflect", node_reflect_safe)
    workflow.add_node("retrieve", node_retrieve_optimized)
    workflow.add_node("human_review_check", node_human_review_check)
    workflow.add_node("finalize", node_finalize)

    # Edges
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "log_audit")
    workflow.add_edge("log_audit", "reflect")
    workflow.add_edge("reflect", "retrieve")
    workflow.add_edge("retrieve", "human_review_check")

    # Conditional routing
    workflow.add_conditional_edges(
        "human_review_check",
        route_next_step,
        {
            "human_review": "human_review_check",  # Loop back until approved
            "finalize": "finalize",
            "retry": "log_audit",  # Retry from beginning
            "error": END,
        },
    )

    workflow.add_edge("finalize", END)

    return workflow


# ============================================================================
# PARALLEL EXECUTION PATTERNS
# ============================================================================


async def execute_parallel_agents(
    state: EnhancedWorkflowState, agent_tasks: dict[str, Any]
) -> EnhancedWorkflowState:
    """Execute multiple agents in parallel (fan-out/fan-in pattern)."""
    start_time = datetime.utcnow()

    # Execute all tasks concurrently
    results = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)

    # Collect results
    for agent_name, result in zip(agent_tasks.keys(), results, strict=False):
        if isinstance(result, Exception):
            state.parallel_errors[agent_name] = str(result)
        else:
            state.parallel_results[agent_name] = result

    # Track execution time
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    state.node_execution_times["parallel_execution"] = elapsed

    return state


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_enhanced_orchestration(
    memory: MemoryManager,
    max_retries: int = 3,
    review_timeout_minutes: int = 60,
    confidence_threshold: float = 0.75,
) -> tuple[Any, ErrorRecoveryManager, HumanReviewManager, RouterOptimizer]:
    """Create enhanced orchestration system with all managers.

    Returns:
        Tuple of (workflow_graph, error_manager, review_manager, router_optimizer)
    """
    error_manager = ErrorRecoveryManager(max_retries=max_retries)
    review_manager = HumanReviewManager(default_timeout_minutes=review_timeout_minutes)
    router_optimizer = RouterOptimizer(confidence_threshold=confidence_threshold)

    workflow = build_enhanced_memory_workflow(
        memory=memory,
        error_manager=error_manager,
        review_manager=review_manager,
        router_optimizer=router_optimizer,
    )

    return workflow, error_manager, review_manager, router_optimizer
