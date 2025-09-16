from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from ..memory.rmt.buffer import compose_prompt


class WorkflowState(BaseModel):
    """State carried through the LangGraph workflow.

    This is intentionally simple and focused on integrating the existing
    memory components. Extend as needed for richer workflows.
    """

    thread_id: str = Field(..., description="Conversation or workflow thread id")
    user_id: Optional[str] = Field(default=None)
    query: Optional[str] = Field(default=None)

    # Inputs/Artifacts
    event: Optional[AuditEvent] = None

    # Outputs/Derived
    reflected: List[MemoryRecord] = Field(default_factory=list)
    retrieved: List[MemoryRecord] = Field(default_factory=list)
    rmt_slots: Dict[str, str] = Field(default_factory=dict)

    # Error handling
    error: Optional[str] = None


def _ensure_langgraph():
    try:
        # Deferred import so the package can be inspected without deps installed
        from langgraph.graph import StateGraph  # noqa: F401
        from langgraph.checkpoint.memory import MemorySaver  # noqa: F401
    except Exception as e:  # pragma: no cover - import-time guard
        raise RuntimeError(
            "LangGraph is required for workflow execution. Install with: pip install langgraph"
        ) from e


def build_memory_workflow(memory: MemoryManager):
    """Builds a simple LangGraph StateGraph that:
    1) Logs the incoming audit event (episodic)
    2) Reflects salient facts into semantic memory
    3) Retrieves related memories based on an optional query
    4) Updates the RMT buffer and composes a prompt preamble
    """

    _ensure_langgraph()
    from langgraph.graph import StateGraph

    graph = StateGraph(WorkflowState)

    async def node_log_event(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            await memory.alog_audit(state.event)
        return state

    async def node_reflect(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            reflected = await memory.awrite(state.event)
            state.reflected = reflected
        return state

    async def node_retrieve(state: WorkflowState) -> WorkflowState:
        if state.query:
            items = await memory.aretrieve(state.query, user_id=state.user_id)
            state.retrieved = items
        return state

    async def node_update_rmt(state: WorkflowState) -> WorkflowState:
        # Heuristic: populate RMT slots from retrieved/reflected items
        persona = ""  # Could be filled from profile/persona store later
        long_term = "\n".join(r.text for r in state.retrieved[:5]) if state.retrieved else ""
        recent = state.reflected[0].text if state.reflected else ""
        slots = {
            "persona": persona,
            "long_term_facts": long_term,
            "open_loops": "",  # future: unresolved tasks
            "recent_summary": recent,
        }
        state.rmt_slots = slots
        await memory.aset_rmt(state.thread_id, slots)
        # Compose once for convenience; callers can fetch via memory.aget_rmt too
        _ = compose_prompt(slots)
        return state

    # Register nodes
    graph.add_node("log_event", node_log_event)
    graph.add_node("reflect", node_reflect)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("update_rmt", node_update_rmt)

    # Wire edges: start -> log -> reflect -> retrieve -> update_rmt -> end
    graph.set_entry_point("log_event")
    graph.add_edge("log_event", "reflect")
    graph.add_edge("reflect", "retrieve")
    graph.add_edge("retrieve", "update_rmt")
    graph.set_finish_point("update_rmt")

    return graph

