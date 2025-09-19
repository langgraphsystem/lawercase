from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from core.memory.memory_manager import MemoryManager
from core.memory.models import AuditEvent
from core.orchestration.pipeline_manager import build_pipeline, run
from core.orchestration.workflow_graph import WorkflowState


async def main():
    memory = MemoryManager()

    thread_id = str(uuid.uuid4())
    user_id = "demo-user"

    # Seed an audit event (e.g., command handled)
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        user_id=user_id,
        thread_id=thread_id,
        source="demo_app",
        action="handle_command",
        payload={"summary": "User asked about renewal deadlines for Form I-765."},
        tags=["milestone"],
    )

    # Build graph and run a simple flow with a query
    graph = build_pipeline(memory)
    initial = WorkflowState(
        thread_id=thread_id, user_id=user_id, event=event, query="renewal deadlines Form I-765"
    )
    final = await run(graph, initial)

    print("--- Workflow Completed ---")
    print("Reflected items:")
    for r in final.reflected:
        print(" -", r.text)

    print("\nRetrieved items:")
    for r in final.retrieved:
        print(" -", r.text)

    print("\nRMT slots:")
    for k, v in final.rmt_slots.items():
        print(f"[{k}]\n{v}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Helpful hint if LangGraph is missing
        if "LangGraph is required" in str(e):
            print(str(e))
        else:
            raise
