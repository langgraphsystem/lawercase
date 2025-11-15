from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .eb1a_nodes import build_eb1a_workflow
from .enhanced_workflows import (EnhancedWorkflowState,
                                 create_enhanced_orchestration)
from .workflow_graph import WorkflowState, build_memory_workflow

if TYPE_CHECKING:
    from ..memory.memory_manager import MemoryManager


def setup_checkpointer(url: str | None = None):
    """Configure a LangGraph checkpointer.

    - If `url` is None, uses in-memory checkpointer (non-persistent).
    - For production, pass a database URL (e.g., sqlite:///file.db or postgres://...).
    """
    try:
        if url:
            # Note: LangGraph currently ships a SQLite checkpointer; Postgres via community
            from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore

            return SqliteSaver(url)
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore

        return MemorySaver()
    except Exception as e:  # pragma: no cover - import/runtime guard
        raise RuntimeError(
            "Failed to initialize LangGraph checkpointer. Ensure 'langgraph' is installed."
        ) from e


def build_pipeline(memory: MemoryManager, *, checkpointer: Any | None = None):
    graph = build_memory_workflow(memory)
    if checkpointer is None:
        checkpointer = setup_checkpointer(None)
    return graph.compile(checkpointer=checkpointer)


def build_enhanced_pipeline(memory: MemoryManager, *, checkpointer: Any | None = None):
    workflow, _, _, _ = create_enhanced_orchestration(memory)
    if checkpointer is None:
        checkpointer = setup_checkpointer(None)
    return workflow.compile(checkpointer=checkpointer)


def build_eb1a_pipeline(*, checkpointer: Any | None = None):
    workflow = build_eb1a_workflow()
    if checkpointer is None:
        checkpointer = setup_checkpointer(None)
    return workflow.compile(checkpointer=checkpointer)


async def run(
    graph_executable,
    initial_state: WorkflowState | EnhancedWorkflowState,
    *,
    thread_id: str | None = None,
) -> WorkflowState | EnhancedWorkflowState:
    """Run a compiled LangGraph with given initial state."""
    if thread_id is None:
        thread_id = initial_state.thread_id
    # LangGraph async interface returns an iterator of states; take the final
    final_dict: dict[str, Any] = {}
    async for step in graph_executable.astream(
        initial_state, config={"configurable": {"thread_id": thread_id}}
    ):
        # step is a dict with node names as keys
        # merge all values to get the final state
        if isinstance(step, dict):
            final_dict.update(step)
        else:
            final_dict = step

    # Convert dict back to WorkflowState or EnhancedWorkflowState
    # LangGraph returns dict, but we need to reconstruct the state object
    if isinstance(initial_state, EnhancedWorkflowState):
        # For EnhancedWorkflowState, return dict as-is (it handles dict internally)
        return final_dict  # type: ignore

    # For WorkflowState, reconstruct from dict or return initial_state with updates
    # Check if final_dict has the state or if it's nested
    for value in final_dict.values():
        if isinstance(value, WorkflowState | EnhancedWorkflowState):
            return value

    # If dict doesn't contain state object but has dict values, try to construct WorkflowState
    # This handles cases where LangGraph serializes states to dicts
    if final_dict:
        # Try to find a dict that looks like a WorkflowState (has thread_id)
        for value in final_dict.values():
            if isinstance(value, dict) and "thread_id" in value:
                try:
                    return WorkflowState.model_validate(value)
                except Exception:
                    pass

    # Fallback: return initial_state if no valid final state found
    return initial_state
