from __future__ import annotations

from typing import Any

from ..memory.memory_manager import MemoryManager
from .workflow_graph import WorkflowState, build_memory_workflow


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


async def run(
    graph_executable, initial_state: WorkflowState, *, thread_id: str | None = None
) -> WorkflowState:
    """Run a compiled LangGraph with given initial state."""
    if thread_id is None:
        thread_id = initial_state.thread_id
    # LangGraph async interface returns an iterator of states; take the final
    final: WorkflowState = None  # type: ignore
    async for step in graph_executable.astream(
        initial_state, config={"configurable": {"thread_id": thread_id}}
    ):
        final = step
    return final
