from __future__ import annotations

import asyncio
from typing import Any

from core.groupagents.mega_agent import CommandType, MegaAgent, MegaAgentCommand, UserRole
from core.groupagents.supervisor_agent import (
    PlannedSubTask,
    SupervisorAgent,
    SupervisorTaskRequest,
)


def _coerce_command_type(value: str) -> CommandType:
    """Best-effort conversion from string to CommandType."""
    try:
        return CommandType(value)
    except ValueError:
        return CommandType.ASK


async def run_with_mega_agent() -> None:
    supervisor = SupervisorAgent()
    mega_agent = MegaAgent()

    request = SupervisorTaskRequest(
        task="Draft a short petition letter and validate it",
        user_id="demo-user",
        context={
            "document_type": "petition",
            "case_inputs": {"title": "Demo Case", "description": "Example case"},
            "validation_level": "standard",
        },
        allow_parallel=True,
    )

    async def executor(step: PlannedSubTask) -> dict[str, Any]:
        command = MegaAgentCommand(
            user_id=request.user_id,
            command_type=_coerce_command_type(step.command_type),
            action=step.action,
            payload=step.payload,
            context={"supervisor_step_id": step.id, "description": step.description},
            requested_agent=step.expected_agent,
        )
        response = await mega_agent.handle_command(command, user_role=UserRole.ADMIN)
        return {
            "success": response.success,
            "agent_used": response.agent_used,
            "result": response.result,
            "error": response.error,
        }

    result = await supervisor.run_task(request, executor)

    print("Plan:")
    for step in result.plan:
        print("-", step["description"], f"(mode={step.get('run_mode')})")

    print("\nResults:")
    for item in result.results:
        print(
            f"- {item.step_id}: {item.status} (agent={item.agent})"
            + (f" error={item.error}" if item.error else "")
        )


async def run_with_stub_executor() -> None:
    supervisor = SupervisorAgent()
    request = SupervisorTaskRequest(
        task="Summarize case history and list missing evidence",
        user_id="demo-user",
        context={"case_id": "case-001"},
    )

    async def executor(step: PlannedSubTask) -> dict[str, Any]:
        return {
            "step_id": step.id,
            "command_type": step.command_type,
            "action": step.action,
            "payload": step.payload,
        }

    result = await supervisor.run_task(request, executor)
    print("Plan (stub):", result.plan)


if __name__ == "__main__":
    asyncio.run(run_with_mega_agent())
