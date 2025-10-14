"""Integration tests for enhanced orchestration workflows."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from core.memory.memory_manager import MemoryManager
from core.memory.models import AuditEvent
from core.orchestration.enhanced_workflows import (
    EnhancedWorkflowState, ErrorContext, ErrorRecoveryManager, HumanFeedback,
    HumanReviewManager, RetryStrategy, RouterOptimizer, WorkflowStage,
    create_enhanced_orchestration, execute_parallel_agents)


@pytest.fixture
def memory_manager():
    """Create memory manager for testing."""
    return MemoryManager()


@pytest.fixture
def enhanced_state():
    """Create enhanced workflow state."""
    return EnhancedWorkflowState(
        thread_id="test-thread-123",
        user_id="user-456",
        query="Test query",
    )


@pytest.fixture
def error_manager():
    """Create error recovery manager."""
    return ErrorRecoveryManager(max_retries=3, base_delay=0.1)


@pytest.fixture
def review_manager():
    """Create human review manager."""
    return HumanReviewManager(default_timeout_minutes=1)


@pytest.fixture
def router_optimizer():
    """Create router optimizer."""
    return RouterOptimizer(confidence_threshold=0.75)


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_error_recovery_manager_retry_logic(error_manager, enhanced_state):
    """Test error recovery manager retry logic."""
    # Simulate error
    error = ConnectionError("Network timeout")
    state = await error_manager.handle_error(enhanced_state, error, "test_node")

    assert len(state.errors) == 1
    assert state.errors[0].error_type == "ConnectionError"
    assert state.errors[0].failed_node == "test_node"
    assert state.errors[0].recoverable is True
    assert state.retry_state["test_node"] == 1
    assert state.workflow_step == "retry_test_node"


@pytest.mark.asyncio
async def test_error_recovery_non_recoverable(error_manager, enhanced_state):
    """Test non-recoverable error handling."""
    # Simulate non-recoverable error
    error = ValueError("Invalid input")
    state = await error_manager.handle_error(enhanced_state, error, "validation_node")

    assert len(state.errors) == 1
    assert state.errors[0].recoverable is False
    assert state.workflow_step == "failed"
    assert state.error is not None


@pytest.mark.asyncio
async def test_error_recovery_max_retries(error_manager, enhanced_state):
    """Test max retries exhaustion."""
    # Simulate multiple retries
    error = ConnectionError("Network timeout")

    for _ in range(4):
        enhanced_state = await error_manager.handle_error(enhanced_state, error, "flaky_node")

    # Should fail after max retries
    assert len(enhanced_state.errors) == 4
    assert enhanced_state.workflow_step == "failed"
    assert "Max retries exceeded" in enhanced_state.error


@pytest.mark.asyncio
async def test_retry_delay_exponential_backoff(error_manager):
    """Test exponential backoff retry delays."""
    error_ctx = ErrorContext(
        error_type="ConnectionError",
        error_message="Timeout",
        failed_node="test",
        retry_count=0,
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    )

    delay_0 = await error_manager.get_retry_delay(error_ctx)
    assert delay_0 == 0.1  # base_delay * 2^0

    error_ctx.retry_count = 1
    delay_1 = await error_manager.get_retry_delay(error_ctx)
    assert delay_1 == 0.2  # base_delay * 2^1

    error_ctx.retry_count = 2
    delay_2 = await error_manager.get_retry_delay(error_ctx)
    assert delay_2 == 0.4  # base_delay * 2^2


@pytest.mark.asyncio
async def test_retry_delay_fixed(error_manager):
    """Test fixed delay retry strategy."""
    error_ctx = ErrorContext(
        error_type="ConnectionError",
        error_message="Timeout",
        failed_node="test",
        retry_count=0,
        retry_strategy=RetryStrategy.FIXED_DELAY,
    )

    for i in range(3):
        error_ctx.retry_count = i
        delay = await error_manager.get_retry_delay(error_ctx)
        assert delay == 0.1  # Always base_delay


# ============================================================================
# HUMAN-IN-THE-LOOP TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_human_review_request(review_manager, enhanced_state):
    """Test requesting human review."""
    state = await review_manager.request_human_review(
        enhanced_state, reason="Low confidence", timeout_minutes=5
    )

    assert state.awaiting_human_feedback is True
    assert state.workflow_step == "awaiting_human_feedback"
    assert state.feedback_timeout is not None
    assert len(review_manager.pending_reviews) == 1


@pytest.mark.asyncio
async def test_human_feedback_approval(review_manager, enhanced_state):
    """Test submitting approval feedback."""
    # Request review
    _ = await review_manager.request_human_review(enhanced_state, "Check quality")
    review_id = next(iter(review_manager.pending_reviews.keys()))

    # Submit approval
    feedback = HumanFeedback(
        reviewer_id="reviewer-123",
        approved=True,
        comments="Looks good!",
        confidence_score=0.9,
    )

    updated_state = await review_manager.submit_human_feedback(review_id, feedback)

    assert updated_state is not None
    assert updated_state.awaiting_human_feedback is False
    assert updated_state.workflow_step == "human_approved"
    assert len(updated_state.human_feedback) == 1
    assert updated_state.human_feedback[0].approved is True


@pytest.mark.asyncio
async def test_human_feedback_rejection(review_manager, enhanced_state):
    """Test submitting rejection feedback."""
    _ = await review_manager.request_human_review(enhanced_state, "Check quality")
    review_id = next(iter(review_manager.pending_reviews.keys()))

    feedback = HumanFeedback(
        reviewer_id="reviewer-456",
        approved=False,
        comments="Needs improvement",
        suggested_changes={"section": "update content"},
    )

    updated_state = await review_manager.submit_human_feedback(review_id, feedback)

    assert updated_state.workflow_step == "human_rejected"
    assert updated_state.human_feedback[0].suggested_changes is not None


@pytest.mark.asyncio
async def test_human_feedback_timeout(review_manager, enhanced_state):
    """Test human feedback timeout."""
    # Set very short timeout
    enhanced_state.feedback_timeout = datetime.utcnow() - timedelta(seconds=1)
    enhanced_state.awaiting_human_feedback = True

    state = await review_manager.check_timeout(enhanced_state)

    assert state.awaiting_human_feedback is False
    assert state.workflow_step == "human_feedback_timeout"
    assert state.current_stage == WorkflowStage.ERROR


# ============================================================================
# ROUTING OPTIMIZATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_router_optimizer_best_route(router_optimizer, enhanced_state):
    """Test router selects best route based on confidence."""
    routing_options = {
        "route_a": 0.6,
        "route_b": 0.9,  # Highest
        "route_c": 0.7,
    }

    route, confidence = await router_optimizer.optimize_routing(enhanced_state, routing_options)

    assert route == "route_b"
    assert confidence == 0.9
    assert enhanced_state.routing_decision == "route_b"
    assert enhanced_state.routing_confidence == 0.9
    assert "route_a" in enhanced_state.routing_alternatives
    assert "route_c" in enhanced_state.routing_alternatives


@pytest.mark.asyncio
async def test_router_optimizer_low_confidence_logging(router_optimizer, enhanced_state):
    """Test low confidence routing triggers logging."""
    routing_options = {
        "route_a": 0.5,  # Below threshold (0.75)
    }

    enhanced_state.event = AuditEvent(
        event_id=str(uuid4()),
        timestamp=datetime.utcnow(),
        user_id="system",
        thread_id=enhanced_state.thread_id,
        source="router_optimizer_test",
        action="routing_check",
        payload={},
    )

    route, confidence = await router_optimizer.optimize_routing(enhanced_state, routing_options)

    assert confidence < router_optimizer.confidence_threshold
    # Event should be updated with low confidence warning
    assert enhanced_state.event.action == "low_confidence_routing"


@pytest.mark.asyncio
async def test_router_performance_stats(router_optimizer, enhanced_state):
    """Test routing performance statistics."""
    # Execute multiple routings
    routing_sets = [
        {"route_a": 0.8},
        {"route_a": 0.9},
        {"route_b": 0.7},
        {"route_a": 0.85},
    ]

    for options in routing_sets:
        await router_optimizer.optimize_routing(enhanced_state, options)

    stats = router_optimizer.get_routing_performance()

    assert "route_a" in stats
    assert stats["route_a"]["count"] == 3
    assert 0.8 <= stats["route_a"]["avg_confidence"] <= 0.9
    assert "route_b" in stats
    assert stats["route_b"]["count"] == 1


# ============================================================================
# PARALLEL EXECUTION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_agent_execution(enhanced_state):
    """Test parallel agent execution."""

    async def mock_agent_task(name: str, delay: float):
        """Mock agent task."""
        import asyncio

        await asyncio.sleep(delay)
        return {"agent": name, "result": "success"}

    agent_tasks = {
        "agent_1": mock_agent_task("agent_1", 0.01),
        "agent_2": mock_agent_task("agent_2", 0.01),
        "agent_3": mock_agent_task("agent_3", 0.01),
    }

    state = await execute_parallel_agents(enhanced_state, agent_tasks)

    assert len(state.parallel_results) == 3
    assert "agent_1" in state.parallel_results
    assert "agent_2" in state.parallel_results
    assert "agent_3" in state.parallel_results
    assert state.node_execution_times["parallel_execution"] > 0


@pytest.mark.asyncio
async def test_parallel_execution_with_errors(enhanced_state):
    """Test parallel execution handles errors."""

    async def failing_task():
        raise ValueError("Task failed")

    async def success_task():
        return {"result": "ok"}

    agent_tasks = {
        "good_agent": success_task(),
        "bad_agent": failing_task(),
    }

    state = await execute_parallel_agents(enhanced_state, agent_tasks)

    assert "good_agent" in state.parallel_results
    assert "bad_agent" in state.parallel_errors
    assert "Task failed" in state.parallel_errors["bad_agent"]


# ============================================================================
# ENHANCED WORKFLOW STATE TESTS
# ============================================================================


def test_enhanced_workflow_state_initialization():
    """Test enhanced workflow state initialization."""
    state = EnhancedWorkflowState(
        thread_id="test-123",
        user_id="user-456",
    )

    assert state.current_stage == WorkflowStage.INIT
    assert len(state.errors) == 0
    assert len(state.human_feedback) == 0
    assert state.awaiting_human_feedback is False
    assert len(state.parallel_results) == 0
    assert state.workflow_start_time is not None


def test_enhanced_workflow_state_checkpoints():
    """Test workflow checkpointing."""
    state = EnhancedWorkflowState(thread_id="test-123")

    # Add checkpoints
    state.checkpoints["step_1"] = {"data": "value1"}
    state.checkpoints["step_2"] = {"data": "value2"}

    assert len(state.checkpoints) == 2
    assert state.checkpoints["step_1"]["data"] == "value1"


def test_enhanced_workflow_state_stage_tracking():
    """Test stage history tracking."""
    state = EnhancedWorkflowState(thread_id="test-123")

    # Track stages
    state.stage_history.append((WorkflowStage.INIT, datetime.utcnow()))
    state.stage_history.append((WorkflowStage.PROCESSING, datetime.utcnow()))
    state.stage_history.append((WorkflowStage.COMPLETION, datetime.utcnow()))

    assert len(state.stage_history) == 3
    assert state.stage_history[0][0] == WorkflowStage.INIT
    assert state.stage_history[-1][0] == WorkflowStage.COMPLETION


# ============================================================================
# INTEGRATION TEST: FULL ENHANCED WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_create_enhanced_orchestration(memory_manager):
    """Test creating enhanced orchestration system."""
    workflow, error_mgr, review_mgr, router_opt = create_enhanced_orchestration(
        memory=memory_manager,
        max_retries=5,
        review_timeout_minutes=30,
        confidence_threshold=0.8,
    )

    assert error_mgr.max_retries == 5
    assert review_mgr.default_timeout_minutes == 30
    assert router_opt.confidence_threshold == 0.8
    assert workflow is not None


@pytest.mark.asyncio
async def test_enhanced_workflow_execution_success(memory_manager):
    """Test successful enhanced workflow execution."""
    workflow, _, _, _ = create_enhanced_orchestration(memory_manager)

    # Create initial state
    initial_state = EnhancedWorkflowState(
        thread_id="test-workflow-123",
        user_id="user-789",
        query="test query",
        event=AuditEvent(
            event_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            user_id="user-789",
            thread_id="test-workflow-123",
            source="enhanced_workflow_test",
            action="workflow_test",
            payload={"test": "data"},
        ),
    )

    # Compile and run workflow
    compiled = workflow.compile()

    # Execute workflow
    final_state = None
    async for state in compiled.astream(
        initial_state, config={"configurable": {"thread_id": "test-workflow-123"}}
    ):
        final_state = state

    # Verify final state
    assert final_state is not None
    if isinstance(final_state, dict):
        values = list(final_state.values())
        if values and isinstance(values[0], dict):
            final_state = EnhancedWorkflowState.model_validate(values[0])
        else:
            final_state = EnhancedWorkflowState.model_validate(final_state)
    # The workflow should have progressed through stages
    assert len(final_state.node_execution_times) > 0
