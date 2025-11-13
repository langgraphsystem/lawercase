from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from core.agents import ComplexityResult, TaskTier
from core.groupagents import mega_agent as mega_agent_module
from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                         MegaAgentCommand, UserRole)


class DummySubAgent:
    def __init__(self, *args, **kwargs):
        pass


class _SupervisorResult:
    def __init__(self, payload: dict[str, object]):
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


class StubSupervisor:
    def __init__(self):
        self.run_task_calls: list = []

    async def run_task(self, request, executor):
        self.run_task_calls.append(request)
        return _SupervisorResult({"plan": [], "rationale": "stub", "results": []})


class DummyAnalyzer:
    def __init__(self):
        self.result = ComplexityResult(
            tier=TaskTier.LANGCHAIN,
            score=0.2,
            reasons=["default"],
            recommended_agent="rag_pipeline_agent",
            requires_supervisor=False,
            estimated_steps=1,
            estimated_cost=1.0,
        )

    async def analyze(self, command):
        return self.result


@pytest.fixture
def mega_agent_fixture(monkeypatch):
    module = mega_agent_module
    for name in ("CaseAgent", "WriterAgent", "EB1Agent", "ValidatorAgent"):
        monkeypatch.setattr(module, name, DummySubAgent)

    class DummyRBAC:
        def check_permission(self, *args, **kwargs):
            return True

    monkeypatch.setattr(module, "get_rbac_manager", lambda: DummyRBAC())
    monkeypatch.setattr(module.security_config, "prompt_detection_enabled", False)
    monkeypatch.setattr(module.security_config, "audit_enabled", False)
    monkeypatch.setattr(module, "get_prompt_detector", lambda: None)
    monkeypatch.setattr(module, "get_audit_trail", lambda: None)

    analyzer = DummyAnalyzer()
    supervisor = StubSupervisor()
    agent = MegaAgent(
        memory_manager=None,
        complexity_analyzer=analyzer,
        supervisor_agent=supervisor,
    )
    agent._log_command_start = AsyncMock()
    agent._log_command_completion = AsyncMock()
    agent._log_command_error = AsyncMock()
    return agent, supervisor, analyzer


@pytest.mark.asyncio
async def test_handle_command_routes_to_supervisor(mega_agent_fixture):
    agent, supervisor, analyzer = mega_agent_fixture
    analyzer.result = ComplexityResult(
        tier=TaskTier.DEEP,
        score=0.9,
        reasons=["High complexity"],
        recommended_agent="supervisor_agent",
        requires_supervisor=True,
        estimated_steps=6,
        estimated_cost=9.0,
    )
    command = MegaAgentCommand(
        user_id="lawyer-42",
        command_type=CommandType.EB1,
        action="full_petition",
        payload={"documents": ["doc1", "doc2"]},
    )

    response = await agent.handle_command(command, user_role=UserRole.ADMIN)

    assert response.tier is TaskTier.DEEP
    assert response.routing_metadata
    assert response.routing_metadata.get("agent") == "supervisor_agent"
    assert response.success, response.error


@pytest.mark.asyncio
async def test_handle_command_uses_fast_path(monkeypatch, mega_agent_fixture):
    agent, supervisor, analyzer = mega_agent_fixture
    analyzer.result = ComplexityResult(
        tier=TaskTier.LANGCHAIN,
        score=0.25,
        reasons=["simple ask"],
        recommended_agent="rag_pipeline_agent",
        requires_supervisor=False,
        estimated_steps=1,
        estimated_cost=1.0,
    )
    dispatched = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setattr(agent, "_dispatch_to_agent", dispatched)

    command = MegaAgentCommand(
        user_id="user-quick",
        command_type=CommandType.ASK,
        action="question",
        payload={"question": "Hello?"},
    )

    response = await agent.handle_command(command, user_role=UserRole.ADMIN)

    dispatched.assert_awaited()
    assert not supervisor.run_task_calls
    assert response.tier is TaskTier.LANGCHAIN
    assert response.success
