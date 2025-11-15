from __future__ import annotations

import pytest

from core.groupagents.supervisor_agent import SupervisorAgent, SupervisorTaskRequest


class _ExecutorRecorder:
    def __init__(self):
        self.calls: list[str] = []

    async def __call__(self, step):
        self.calls.append(step.id)
        return {"executed": step.id, "agent": step.expected_agent}


@pytest.mark.asyncio
async def test_supervisor_agent_builds_plan_without_llm():
    agent = SupervisorAgent(llm_router=None)
    executor = _ExecutorRecorder()
    request = SupervisorTaskRequest(
        task="Prepare EB1 petition package",
        user_id="lawyer-1",
        context={"document_type": "petition", "validation_level": "comprehensive"},
    )

    result = await agent.run_task(request, executor)

    assert len(result.plan) >= 2
    assert len(result.results) == len(result.plan)
    assert all(entry.status == "completed" for entry in result.results)
    assert executor.calls  # executed at least one step


@pytest.mark.asyncio
async def test_supervisor_agent_creates_parallel_steps():
    agent = SupervisorAgent(llm_router=None)
    executor = _ExecutorRecorder()
    request = SupervisorTaskRequest(
        task="Summarize discovery artifacts",
        user_id="analyst-1",
        context={"artifacts": ["doc-a", "doc-b", "doc-c"]},
        allow_parallel=True,
    )

    result = await agent.run_task(request, executor)

    parallel_steps = [step for step in result.plan if step.get("run_mode") == "parallel"]
    assert parallel_steps, "Expected at least one parallel step"
    assert len(result.results) == len(result.plan)
