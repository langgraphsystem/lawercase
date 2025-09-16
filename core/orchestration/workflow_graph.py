from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from ..memory.rmt.buffer import compose_prompt


class WorkflowState(BaseModel):
    """State carried through LangGraph workflows (memory + case operations)."""

    thread_id: str = Field(..., description="Conversation or workflow thread id")
    user_id: Optional[str] = Field(default=None)
    query: Optional[str] = Field(default=None)

    # Inputs/Artifacts
    event: Optional[AuditEvent] = None

    # Case-specific data
    case_id: Optional[str] = Field(default=None, description="Current case ID")
    case_operation: Optional[str] = Field(default=None, description="Requested case operation")
    case_data: Optional[Dict[str, Any]] = Field(default=None, description="Input payload for case operations")

    # Agent results
    case_result: Optional[Dict[str, Any]] = Field(default=None, description="Result of the CaseAgent execution")

    # Outputs/Derived
    reflected: List[MemoryRecord] = Field(default_factory=list)
    retrieved: List[MemoryRecord] = Field(default_factory=list)
    rmt_slots: Dict[str, str] = Field(default_factory=dict)

    # Multi-agent coordination hooks
    next_agent: Optional[str] = Field(default=None)
    agent_results: Dict[str, Any] = Field(default_factory=dict)

    # Error handling
    error: Optional[str] = None


def _ensure_langgraph() -> None:
    try:
        from langgraph.graph import StateGraph  # noqa: F401
        from langgraph.checkpoint.memory import MemorySaver  # noqa: F401
    except Exception as exc:  # pragma: no cover - import-time guard
        raise RuntimeError(
            "LangGraph is required for workflow execution. Install with: pip install langgraph"
        ) from exc


def build_memory_workflow(memory: MemoryManager):
    """Basic memory-oriented workflow used in demos."""

    _ensure_langgraph()
    from langgraph.graph import StateGraph

    graph = StateGraph(WorkflowState)

    async def node_log_event(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            await memory.alog_audit(state.event)
        return state

    async def node_reflect(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            state.reflected = await memory.awrite(state.event)
        return state

    async def node_retrieve(state: WorkflowState) -> WorkflowState:
        if state.query:
            state.retrieved = await memory.aretrieve(state.query, user_id=state.user_id)
        return state

    async def node_update_rmt(state: WorkflowState) -> WorkflowState:
        persona = ""
        long_term = "\n".join(record.text for record in state.retrieved[:5]) if state.retrieved else ""
        recent = state.reflected[0].text if state.reflected else ""
        slots = {
            "persona": persona,
            "long_term_facts": long_term,
            "open_loops": "",
            "recent_summary": recent,
        }
        state.rmt_slots = slots
        await memory.aset_rmt(state.thread_id, slots)
        _ = compose_prompt(slots)
        return state

    graph.add_node("log_event", node_log_event)
    graph.add_node("reflect", node_reflect)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("update_rmt", node_update_rmt)

    graph.set_entry_point("log_event")
    graph.add_edge("log_event", "reflect")
    graph.add_edge("reflect", "retrieve")
    graph.add_edge("retrieve", "update_rmt")
    graph.set_finish_point("update_rmt")

    return graph


def build_case_workflow(memory: MemoryManager, *, case_agent: Optional["CaseAgent"] = None):
    """Workflow that routes case operations through CaseAgent and updates memory."""

    _ensure_langgraph()
    from langgraph.graph import StateGraph
    from ..groupagents.case_agent import CaseAgent

    agent = case_agent or CaseAgent(memory_manager=memory)
    graph = StateGraph(WorkflowState)

    async def node_case_agent(state: WorkflowState) -> WorkflowState:
        operation = (state.case_operation or "").lower()
        if not operation:
            state.error = "case_operation is required"
            return state

        if not state.user_id:
            state.error = "user_id is required for case operations"
            return state

        payload = state.case_data or {}

        try:
            if operation == "create":
                record = await agent.acreate_case(user_id=state.user_id, case_data=payload)
                state.case_id = record.case_id
                state.case_result = {"operation": "create", "case": record.model_dump()}

            elif operation == "get":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValueError("case_id is required for get operation")
                record = await agent.aget_case(case_id=case_id, user_id=state.user_id)
                state.case_id = record.case_id
                state.case_result = {"operation": "get", "case": record.model_dump()}

            elif operation == "update":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValueError("case_id is required for update operation")
                updates_payload = payload.get("updates")
                if updates_payload is None:
                    updates = {k: v for k, v in payload.items() if k != "case_id"}
                else:
                    updates = dict(updates_payload)
                record = await agent.aupdate_case(case_id=case_id, updates=updates, user_id=state.user_id)
                state.case_id = record.case_id
                state.case_result = {"operation": "update", "case": record.model_dump()}

            elif operation == "delete":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValueError("case_id is required for delete operation")
                result = await agent.adelete_case(case_id=case_id, user_id=state.user_id)
                state.case_result = {"operation": "delete", "result": result.model_dump()}

            elif operation == "search":
                from ..groupagents.models import CaseQuery

                query = CaseQuery(**payload)
                cases = await agent.asearch_cases(query=query, user_id=state.user_id)
                state.case_result = {
                    "operation": "search",
                    "cases": [case.model_dump() for case in cases],
                    "count": len(cases),
                }

            elif operation == "start_workflow":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValueError("case_id is required for start_workflow operation")
                result = await agent.astart_workflow(case_id=case_id, user_id=state.user_id)
                state.case_id = case_id
                state.case_result = {"operation": "start_workflow", "workflow": result}

            else:
                raise ValueError(f"Unsupported case operation: {operation}")

            state.agent_results["case_agent"] = state.case_result

        except Exception as exc:  # pragma: no cover - defensive
            state.error = str(exc)
            state.case_result = {"operation": operation, "error": str(exc)}

        return state

    async def node_audit(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            await memory.alog_audit(state.event)

        if state.case_result and state.user_id:
            audit_event = AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id,
                thread_id=state.thread_id,
                source="case_workflow",
                action=f"case_{state.case_operation or 'operation'}",
                payload=state.case_result,
                tags=["case", "workflow"],
            )
            await memory.alog_audit(audit_event)

        return state

    async def node_reflect(state: WorkflowState) -> WorkflowState:
        reflections: List[MemoryRecord] = []

        if state.event is not None:
            reflections.extend(await memory.awrite(state.event))

        if state.case_result and state.user_id:
            parts = [f"case:{state.case_operation}" if state.case_operation else "case"]
            if state.case_id:
                parts.append(f"id={state.case_id}")
            case_payload = state.case_result.get("case") if isinstance(state.case_result, dict) else None
            if isinstance(case_payload, dict):
                title = case_payload.get("title")
                if title:
                    parts.append(f"title={title}")
            summary = " | ".join(parts)

            record = MemoryRecord(
                user_id=state.user_id,
                text=summary,
                source="case_workflow",
                tags=[tag for tag in ["case", state.case_operation] if tag],
            )
            reflections.extend(await memory.awrite([record]))

        state.reflected = reflections
        return state

    async def node_retrieve(state: WorkflowState) -> WorkflowState:
        query = state.query
        if not query and state.case_id:
            query = state.case_id
        if query:
            state.retrieved = await memory.aretrieve(query, user_id=state.user_id)
        return state

    async def node_update_rmt(state: WorkflowState) -> WorkflowState:
        long_term = "\n".join(record.text for record in state.retrieved[:5]) if state.retrieved else ""

        summary = ""
        if isinstance(state.case_result, dict):
            operation = state.case_result.get("operation")
            if operation:
                summary = f"Case operation: {operation}"
            if state.case_id:
                summary += f" (ID: {state.case_id})"
        if not summary and state.reflected:
            summary = state.reflected[0].text

        slots = {
            "persona": "",
            "long_term_facts": long_term,
            "open_loops": "",
            "recent_summary": summary,
        }
        state.rmt_slots = slots
        await memory.aset_rmt(state.thread_id, slots)
        _ = compose_prompt(slots)
        return state

    graph.add_node("case_agent", node_case_agent)
    graph.add_node("audit", node_audit)
    graph.add_node("reflect", node_reflect)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("update_rmt", node_update_rmt)

    graph.set_entry_point("case_agent")
    graph.add_edge("case_agent", "audit")
    graph.add_edge("audit", "reflect")
    graph.add_edge("reflect", "retrieve")
    graph.add_edge("retrieve", "update_rmt")
    graph.set_finish_point("update_rmt")

    return graph
