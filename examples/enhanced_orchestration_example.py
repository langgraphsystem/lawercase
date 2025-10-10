"""Example usage of Enhanced Orchestration features.

This example demonstrates:
1. Error recovery with automatic retries
2. Human-in-the-loop workflows
3. Conditional routing optimization
4. Parallel agent execution
5. Complex workflow patterns
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.memory.memory_manager import MemoryManager
from core.memory.models import AuditEvent
from core.orchestration.enhanced_workflows import (
    EnhancedWorkflowState,
    ErrorRecoveryManager,
    HumanFeedback,
    HumanReviewManager,
    RetryStrategy,
    RouterOptimizer,
    create_enhanced_orchestration,
    execute_parallel_agents,
)

# ============================================================================
# EXAMPLE 1: Error Recovery with Retry
# ============================================================================


async def example_error_recovery():
    """Demonstrate error recovery with automatic retries."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Error Recovery with Automatic Retries")
    print("=" * 70)

    # Create error manager
    error_manager = ErrorRecoveryManager(
        max_retries=3, default_strategy=RetryStrategy.EXPONENTIAL_BACKOFF, base_delay=1.0
    )

    # Create workflow state
    state = EnhancedWorkflowState(
        thread_id="error-recovery-example", user_id="demo-user", query="test query"
    )

    # Simulate a recoverable error (e.g., network timeout)
    print("\n1. Simulating recoverable error (ConnectionError)...")
    error = ConnectionError("Network timeout")
    state = await error_manager.handle_error(state, error, "api_call_node")

    print(f"   ✓ Error captured: {state.errors[0].error_type}")
    print(f"   ✓ Retry count: {state.errors[0].retry_count}")
    print(f"   ✓ Recoverable: {state.errors[0].recoverable}")
    print(f"   ✓ Next step: {state.workflow_step}")

    # Check if retry should happen
    should_retry = error_manager.should_retry(state.errors[0])
    print(f"   ✓ Should retry: {should_retry}")

    # Simulate non-recoverable error
    print("\n2. Simulating non-recoverable error (ValueError)...")
    state2 = EnhancedWorkflowState(thread_id="error-recovery-example-2", user_id="demo-user")
    error2 = ValueError("Invalid input format")
    state2 = await error_manager.handle_error(state2, error2, "validation_node")

    print(f"   ✓ Error captured: {state2.errors[0].error_type}")
    print(f"   ✓ Recoverable: {state2.errors[0].recoverable}")
    print(f"   ✓ Workflow marked as: {state2.workflow_step}")

    return state


# ============================================================================
# EXAMPLE 2: Human-in-the-Loop Workflow
# ============================================================================


async def example_human_in_loop():
    """Demonstrate human-in-the-loop workflow."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Human-in-the-Loop Workflow")
    print("=" * 70)

    # Create review manager
    review_manager = HumanReviewManager(default_timeout_minutes=60)

    # Create workflow state
    state = EnhancedWorkflowState(
        thread_id="hitl-example",
        user_id="content-creator",
        query="Generate legal document",
    )

    # Request human review
    print("\n1. Requesting human review...")
    state = await review_manager.request_human_review(
        state, reason="Quality check required", timeout_minutes=30
    )

    print(f"   ✓ Awaiting human feedback: {state.awaiting_human_feedback}")
    print(f"   ✓ Feedback timeout: {state.feedback_timeout}")
    print(f"   ✓ Workflow step: {state.workflow_step}")

    # Get review ID
    review_id = next(iter(review_manager.pending_reviews.keys()))
    print(f"   ✓ Review ID: {review_id}")

    # Simulate human approval
    print("\n2. Simulating human approval...")
    feedback = HumanFeedback(
        reviewer_id="senior-lawyer",
        approved=True,
        comments="Document quality is excellent. Approved for finalization.",
        confidence_score=0.95,
    )

    updated_state = await review_manager.submit_human_feedback(review_id, feedback)

    print(f"   ✓ Review approved: {updated_state.human_feedback[0].approved}")
    print(f"   ✓ Reviewer comments: {updated_state.human_feedback[0].comments}")
    print(f"   ✓ Confidence score: {updated_state.human_feedback[0].confidence_score}")
    print(f"   ✓ Next step: {updated_state.workflow_step}")

    # Example with rejection
    print("\n3. Example of rejection with suggested changes...")
    state3 = EnhancedWorkflowState(thread_id="hitl-example-3", user_id="writer")
    state3 = await review_manager.request_human_review(state3, "Initial draft review")

    review_id_3 = next(iter(review_manager.pending_reviews.keys()))
    rejection_feedback = HumanFeedback(
        reviewer_id="senior-editor",
        approved=False,
        comments="Needs improvement in section 3",
        suggested_changes={
            "section_3": "Add more detail about regulatory compliance",
            "tone": "Make language more formal",
        },
    )

    rejected_state = await review_manager.submit_human_feedback(review_id_3, rejection_feedback)

    print(f"   ✓ Rejected: {not rejected_state.human_feedback[0].approved}")
    print(f"   ✓ Suggested changes: {rejected_state.human_feedback[0].suggested_changes}")

    return updated_state


# ============================================================================
# EXAMPLE 3: Conditional Routing Optimization
# ============================================================================


async def example_routing_optimization():
    """Demonstrate conditional routing optimization."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Conditional Routing Optimization")
    print("=" * 70)

    # Create router optimizer
    router = RouterOptimizer(confidence_threshold=0.75)

    # Create workflow state
    state = EnhancedWorkflowState(
        thread_id="routing-example", user_id="system", query="complex legal query"
    )

    # Define routing options with confidence scores
    routing_options = {
        "simple_response": 0.3,  # Low confidence - too simple
        "rag_search": 0.85,  # High confidence - good match
        "multi_agent": 0.7,  # Medium confidence - possible
        "expert_consultation": 0.6,  # Medium-low - overkill
    }

    print("\n1. Evaluating routing options...")
    print("   Routing options with confidence scores:")
    for route, confidence in sorted(routing_options.items(), key=lambda x: x[1], reverse=True):
        print(f"     - {route}: {confidence:.2f}")

    # Optimize routing
    best_route, confidence = await router.optimize_routing(state, routing_options)

    print(f"\n2. Selected route: {best_route}")
    print(f"   ✓ Confidence: {confidence:.2f}")
    print(f"   ✓ Alternative routes: {state.routing_alternatives}")
    print(f"   ✓ Routing history entries: {len(state.routing_history)}")

    # Simulate low confidence routing
    print("\n3. Example of low confidence routing (triggers logging)...")
    state2 = EnhancedWorkflowState(thread_id="routing-example-2")
    state2.event = AuditEvent(event_type="routing_decision", actor="system", details={})

    low_confidence_options = {
        "fallback_route": 0.5,  # Below threshold
    }

    route2, conf2 = await router.optimize_routing(state2, low_confidence_options)
    print(f"   ✓ Route: {route2}, Confidence: {conf2:.2f}")
    print(f"   ✓ Low confidence logged: {state2.event.event_type}")

    # Get routing performance stats
    print("\n4. Routing performance statistics:")
    stats = router.get_routing_performance()
    for route, metrics in stats.items():
        print(f"\n   Route: {route}")
        print(f"     - Count: {metrics['count']}")
        print(f"     - Avg confidence: {metrics['avg_confidence']:.2f}")
        print(f"     - Min confidence: {metrics['min_confidence']:.2f}")
        print(f"     - Max confidence: {metrics['max_confidence']:.2f}")

    return state


# ============================================================================
# EXAMPLE 4: Parallel Agent Execution
# ============================================================================


async def example_parallel_execution():
    """Demonstrate parallel agent execution."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Parallel Agent Execution (Fan-out/Fan-in)")
    print("=" * 70)

    # Create workflow state
    state = EnhancedWorkflowState(
        thread_id="parallel-example",
        user_id="orchestrator",
        query="multi-faceted legal analysis",
    )

    # Define mock agent tasks
    async def research_agent(topic: str):
        """Mock research agent."""
        await asyncio.sleep(0.1)  # Simulate work
        return {"agent": "research", "topic": topic, "findings": f"Research on {topic}"}

    async def analysis_agent(data: str):
        """Mock analysis agent."""
        await asyncio.sleep(0.1)
        return {"agent": "analysis", "analysis": f"Analysis of {data}"}

    async def citation_agent(count: int):
        """Mock citation agent."""
        await asyncio.sleep(0.1)
        return {"agent": "citation", "citations": [f"Citation {i}" for i in range(count)]}

    # Create parallel tasks
    agent_tasks = {
        "research": research_agent("contract law"),
        "analysis": analysis_agent("case precedents"),
        "citations": citation_agent(5),
    }

    print("\n1. Executing 3 agents in parallel...")
    start_time = datetime.utcnow()

    state = await execute_parallel_agents(state, agent_tasks)

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    print(f"   ✓ Execution time: {elapsed:.2f}s")
    print(f"   ✓ Successful agents: {len(state.parallel_results)}")
    print(f"   ✓ Failed agents: {len(state.parallel_errors)}")

    print("\n2. Agent results:")
    for agent_name, result in state.parallel_results.items():
        print(f"   ✓ {agent_name}: {result}")

    # Example with errors
    print("\n3. Example with error handling...")

    async def failing_agent():
        raise ValueError("Agent encountered invalid data")

    state2 = EnhancedWorkflowState(thread_id="parallel-error-example")
    tasks_with_error = {
        "good_agent": research_agent("topic"),
        "bad_agent": failing_agent(),
    }

    state2 = await execute_parallel_agents(state2, tasks_with_error)

    print(f"   ✓ Successful: {list(state2.parallel_results.keys())}")
    print(f"   ✓ Failed: {list(state2.parallel_errors.keys())}")
    print(f"   ✓ Error message: {state2.parallel_errors['bad_agent']}")

    return state


# ============================================================================
# EXAMPLE 5: Full Enhanced Workflow
# ============================================================================


async def example_full_enhanced_workflow():
    """Demonstrate complete enhanced workflow with all features."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Complete Enhanced Workflow")
    print("=" * 70)

    # Create memory manager
    memory = MemoryManager()

    # Create enhanced orchestration system
    print("\n1. Creating enhanced orchestration system...")
    workflow, error_mgr, review_mgr, router_opt = create_enhanced_orchestration(
        memory=memory, max_retries=3, review_timeout_minutes=60, confidence_threshold=0.75
    )

    print("   ✓ Enhanced workflow created")
    print(f"   ✓ Error manager: max_retries={error_mgr.max_retries}")
    print(f"   ✓ Review manager: timeout={review_mgr.default_timeout_minutes}min")
    print(f"   ✓ Router optimizer: threshold={router_opt.confidence_threshold}")

    # Create initial state
    print("\n2. Creating initial workflow state...")
    initial_state = EnhancedWorkflowState(
        thread_id="full-workflow-demo",
        user_id="legal-professional",
        query="Analyze contract for compliance issues",
        event=AuditEvent(
            event_type="contract_analysis_request",
            actor="legal-professional",
            details={"contract_id": "CONTRACT-2025-001", "priority": "high"},
        ),
    )

    print(f"   ✓ Thread ID: {initial_state.thread_id}")
    print(f"   ✓ User ID: {initial_state.user_id}")
    print(f"   ✓ Current stage: {initial_state.current_stage}")

    # Compile workflow
    print("\n3. Compiling enhanced workflow...")
    compiled_workflow = workflow.compile()
    print("   ✓ Workflow compiled successfully")

    # Execute workflow
    print("\n4. Executing workflow...")
    final_state = None
    step_count = 0

    async for state_update in compiled_workflow.astream(
        initial_state, config={"configurable": {"thread_id": "full-workflow-demo"}}
    ):
        step_count += 1
        # In real usage, you'd process each state update
        final_state = state_update

    print(f"   ✓ Workflow completed in {step_count} steps")

    # Display results
    if final_state:
        print("\n5. Workflow Results:")
        print(f"   ✓ Final stage: {final_state.get('current_stage')}")
        print(f"   ✓ Total errors: {len(final_state.get('errors', []))}")
        print(f"   ✓ Human feedback count: {len(final_state.get('human_feedback', []))}")

        execution_times = final_state.get("node_execution_times", {})
        if execution_times:
            print("\n   Execution times by node:")
            for node, time_taken in execution_times.items():
                print(f"     - {node}: {time_taken:.3f}s")

        total_time = final_state.get("total_execution_time")
        if total_time:
            print(f"\n   ✓ Total execution time: {total_time:.2f}s")

    return final_state


# ============================================================================
# MAIN RUNNER
# ============================================================================


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "ENHANCED ORCHESTRATION EXAMPLES" + " " * 22 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        # Run examples
        await example_error_recovery()
        await example_human_in_loop()
        await example_routing_optimization()
        await example_parallel_execution()
        await example_full_enhanced_workflow()

        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
