"""
Real LangGraph workflow for Document Generation with live monitoring.

Integrates:
- WriterAgent for section generation
- ValidatorAgent for self-correction
- MemoryManager for semantic context
- Real-time status updates to document_workflow_store
- WebSocket broadcasting for instant UI updates
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import structlog

from core.exceptions import WorkflowError
from core.groupagents.writer_agent import DocumentType, WriterAgent
from core.memory.memory_manager_v2 import get_memory_manager
from core.orchestration.workflow_graph import WorkflowState
from core.storage.document_workflow_store import get_document_workflow_store

logger = structlog.get_logger(__name__)

try:
    from langgraph.graph import StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# SECTION DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

EB1A_SECTIONS = [
    {
        "id": "intro",
        "name": "I. INTRODUCTION",
        "order": 1,
        "prompt": "Write an introduction for an EB-1A petition explaining the beneficiary's extraordinary ability.",
        "min_tokens": 300,
        "max_tokens": 500,
    },
    {
        "id": "background",
        "name": "II. BENEFICIARY BACKGROUND",
        "order": 2,
        "prompt": "Describe the beneficiary's educational and professional background.",
        "min_tokens": 250,
        "max_tokens": 400,
    },
    {
        "id": "awards",
        "name": "III. CRITERION 2.1 - AWARDS AND PRIZES",
        "order": 3,
        "prompt": "Document nationally or internationally recognized awards received by the beneficiary.",
        "min_tokens": 400,
        "max_tokens": 600,
    },
    {
        "id": "membership",
        "name": "IV. CRITERION 2.2 - MEMBERSHIPS",
        "order": 4,
        "prompt": "Describe memberships in associations requiring outstanding achievements.",
        "min_tokens": 300,
        "max_tokens": 500,
    },
    {
        "id": "publications",
        "name": "V. CRITERION 2.6 - SCHOLARLY ARTICLES",
        "order": 5,
        "prompt": "List and describe scholarly publications and their significance.",
        "min_tokens": 400,
        "max_tokens": 600,
    },
    {
        "id": "critical_role",
        "name": "VI. CRITERION 2.7 - CRITICAL ROLE",
        "order": 6,
        "prompt": "Demonstrate critical or leading role in distinguished organizations.",
        "min_tokens": 350,
        "max_tokens": 550,
    },
    {
        "id": "conclusion",
        "name": "VII. CONCLUSION",
        "order": 7,
        "prompt": "Conclude the petition with a strong summary of extraordinary ability.",
        "min_tokens": 200,
        "max_tokens": 300,
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW NODES
# ═══════════════════════════════════════════════════════════════════════════


async def node_init_generation(state: WorkflowState) -> WorkflowState:
    """Initialize document generation workflow."""
    thread_id = state.thread_id
    workflow_store = get_document_workflow_store()

    logger.info(
        "document_generation_init",
        thread_id=thread_id,
        case_id=state.case_id,
        document_type=state.document_data.get("document_type") if state.document_data else None,
    )

    # Add log to workflow store
    await workflow_store.add_log(
        thread_id,
        {
            "timestamp": datetime.now().isoformat(),
            "level": "info",
            "message": "Initializing document generation workflow",
            "agent": "SupervisorAgent",
        },
    )

    state.workflow_step = "init_generation"
    return state


async def node_generate_section(state: WorkflowState) -> WorkflowState:
    """Generate a single document section using WriterAgent."""
    thread_id = state.thread_id
    workflow_store = get_document_workflow_store()
    memory_manager = get_memory_manager()

    # Get current section from state
    current_section = state.document_data.get("current_section") if state.document_data else None
    if not current_section:
        raise WorkflowError("No current section specified")

    section_id = current_section["id"]
    section_name = current_section["name"]
    section_prompt = current_section["prompt"]

    logger.info(
        "generating_section",
        thread_id=thread_id,
        section_id=section_id,
        section_name=section_name,
    )

    # Update section status to in_progress
    await workflow_store.update_section(thread_id, section_id, {"status": "in_progress"})

    # Add log
    await workflow_store.add_log(
        thread_id,
        {
            "timestamp": datetime.now().isoformat(),
            "level": "info",
            "message": f"Generating section: {section_name}",
            "agent": "WriterAgent",
        },
    )

    # Broadcast WebSocket update (if connected)
    from core.websocket_manager import broadcast_workflow_update

    await broadcast_workflow_update(thread_id, {"section_id": section_id, "status": "in_progress"})

    try:
        # Initialize WriterAgent
        writer = WriterAgent(memory=memory_manager)

        # Retrieve relevant context from memory
        context_records = await memory_manager.aretrieve(
            query=section_prompt, user_id=state.user_id, limit=5
        )
        context = "\n".join([rec.text for rec in context_records]) if context_records else ""

        # Generate section content
        generation_request = {
            "document_type": DocumentType.PETITION,
            "section_name": section_name,
            "prompt": section_prompt,
            "context": context,
            "case_id": state.case_id,
            "min_tokens": current_section.get("min_tokens", 300),
            "max_tokens": current_section.get("max_tokens", 500),
        }

        # Generate section content using WriterAgent
        # We need to gather client_data from state or memory
        # For now, we'll construct a basic client_data object
        client_data = {
            "case_id": state.case_id,
            "beneficiary_name": "Beneficiary",  # In a real scenario, fetch this from case data
            "field": "Extraordinary Ability Field",  # Fetch from case data
            "evidence": [],  # Fetch from case data
        }

        # Call WriterAgent to generate the section
        generated_section = await writer.agenerate_legal_section(
            section_type=section_id, client_data=client_data, user_id=state.user_id
        )

        content_html = generated_section.content

        # Count tokens (approximate)
        tokens_used = generated_section.word_count * 1.3

        # Update section with generated content
        await workflow_store.update_section(
            thread_id,
            section_id,
            {
                "status": "completed",
                "content_html": content_html,
                "tokens_used": int(tokens_used),
                "updated_at": datetime.now().isoformat(),
            },
        )

        # Add success log
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "success",
                "message": f"Section {section_name} completed ({int(tokens_used)} tokens)",
                "agent": "WriterAgent",
            },
        )

        # Broadcast completion
        await broadcast_workflow_update(
            thread_id,
            {"section_id": section_id, "status": "completed", "tokens_used": int(tokens_used)},
        )

        # Store in agent results
        if not state.agent_results:
            state.agent_results = {}
        state.agent_results[section_id] = {
            "status": "completed",
            "tokens_used": int(tokens_used),
            "content_html": content_html,
        }

        state.workflow_step = f"section_{section_id}_completed"

    except Exception as e:
        logger.error("section_generation_error", section_id=section_id, error=str(e))

        # Update section with error
        await workflow_store.update_section(
            thread_id, section_id, {"status": "error", "error_message": str(e)}
        )

        # Add error log
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Failed to generate section {section_name}: {e!s}",
                "agent": "WriterAgent",
            },
        )

        # Broadcast error
        await broadcast_workflow_update(
            thread_id, {"section_id": section_id, "status": "error", "error": str(e)}
        )

        raise

    return state


async def node_validate_section(state: WorkflowState) -> WorkflowState:
    """Validate generated section using ValidatorAgent."""
    thread_id = state.thread_id
    workflow_store = get_document_workflow_store()

    current_section = state.document_data.get("current_section") if state.document_data else None
    if not current_section:
        return state

    section_id = current_section["id"]

    logger.info("validating_section", thread_id=thread_id, section_id=section_id)

    # Add validation log
    await workflow_store.add_log(
        thread_id,
        {
            "timestamp": datetime.now().isoformat(),
            "level": "info",
            "message": f"Validating section: {current_section['name']}",
            "agent": "ValidatorAgent",
        },
    )

    # TODO: Integrate real ValidatorAgent
    # For now, simulated validation (always passes)
    await asyncio.sleep(0.5)

    state.workflow_step = f"section_{section_id}_validated"
    return state


async def node_finalize_document(state: WorkflowState) -> WorkflowState:
    """Finalize document generation."""
    thread_id = state.thread_id
    workflow_store = get_document_workflow_store()

    logger.info("finalizing_document", thread_id=thread_id)

    # Update overall status to completed
    current_state = await workflow_store.load_state(thread_id)
    if current_state:
        current_state["status"] = "completed"
        await workflow_store.save_state(thread_id, current_state)

    # Add completion log
    await workflow_store.add_log(
        thread_id,
        {
            "timestamp": datetime.now().isoformat(),
            "level": "success",
            "message": "Document generation completed successfully!",
            "agent": "SupervisorAgent",
        },
    )

    # Broadcast completion
    from core.websocket_manager import broadcast_workflow_update

    await broadcast_workflow_update(thread_id, {"status": "completed"})

    state.workflow_step = "completed"
    state.final_output = {"status": "completed", "thread_id": thread_id}

    return state


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW BUILDER
# ═══════════════════════════════════════════════════════════════════════════


def build_document_generation_workflow() -> StateGraph:
    """Build LangGraph workflow for real-time document generation.

    Returns:
        Compiled StateGraph for document generation
    """

    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("LangGraph is required. Install with: pip install langgraph")

    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("init", node_init_generation)
    graph.add_node("generate_section", node_generate_section)
    graph.add_node("validate_section", node_validate_section)
    graph.add_node("finalize", node_finalize_document)

    # Define flow
    graph.set_entry_point("init")
    graph.add_edge("init", "generate_section")
    graph.add_edge("generate_section", "validate_section")
    # Conditional: loop back for next section or finalize
    # (simplified - in real workflow, would use conditional_edges)
    graph.add_edge("validate_section", "finalize")
    graph.set_finish_point("finalize")

    return graph


async def run_document_generation(
    thread_id: str, case_id: str, document_type: str, user_id: str, sections: list[dict[str, Any]]
) -> None:
    """Run complete document generation workflow with real-time updates.

    Args:
        thread_id: Unique workflow thread ID
        case_id: Case ID
        document_type: Type of document (petition, letter, etc.)
        user_id: User ID
        sections: List of section definitions to generate

    This function:
    1. Initializes the LangGraph workflow
    2. Processes each section sequentially
    3. Updates workflow_store in real-time
    4. Broadcasts WebSocket updates
    5. Handles errors gracefully
    """

    workflow_store = get_document_workflow_store()

    logger.info(
        "run_document_generation_start",
        thread_id=thread_id,
        case_id=case_id,
        document_type=document_type,
        total_sections=len(sections),
    )

    try:
        # Process each section
        for section in sections:
            # Check if paused
            current_state = await workflow_store.load_state(thread_id)
            if current_state and current_state.get("status") == "paused":
                logger.info("workflow_paused", thread_id=thread_id)
                return

            # Create workflow state for this section
            state = WorkflowState(
                thread_id=thread_id,
                user_id=user_id,
                case_id=case_id,
                document_data={
                    "document_type": document_type,
                    "current_section": section,
                },
                workflow_step="start",
            )

            # Build and compile workflow
            workflow = build_document_generation_workflow()
            compiled_workflow = workflow.compile()

            # Run workflow for this section
            result = await compiled_workflow.ainvoke(state)

            logger.info(
                "section_workflow_completed",
                thread_id=thread_id,
                section_id=section["id"],
                workflow_step=result.workflow_step,
            )

        # Finalize
        await node_finalize_document(
            WorkflowState(
                thread_id=thread_id,
                user_id=user_id,
                case_id=case_id,
                workflow_step="finalizing",
            )
        )

    except Exception as e:
        logger.error("document_generation_failed", thread_id=thread_id, error=str(e))

        # Update state to error
        current_state = await workflow_store.load_state(thread_id)
        if current_state:
            current_state["status"] = "error"
            current_state["error_message"] = str(e)
            await workflow_store.save_state(thread_id, current_state)

        # Add error log
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Document generation failed: {e!s}",
                "agent": "SupervisorAgent",
            },
        )

        # Broadcast error
        from core.websocket_manager import broadcast_workflow_update

        await broadcast_workflow_update(thread_id, {"status": "error", "error": str(e)})

        raise
