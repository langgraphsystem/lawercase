from __future__ import annotations

from fastapi.testclient import TestClient

from api import deps
from api.main import app
from core.groupagents.mega_agent import MegaAgentResponse


class _FakeAgent:
    async def handle_command(self, command, user_role):
        return MegaAgentResponse(
            command_id=command.command_id,
            success=True,
            result={"echo": command.payload},
            agent_used="fake",
        )


def _fake_user():
    return {"sub": "tester", "roles": ["admin"]}


def _fake_role(claims):
    return deps.UserRole.ADMIN


def _fake_agent():
    return _FakeAgent()


def test_agent_command_route() -> None:
    app.dependency_overrides[deps.get_current_user] = _fake_user
    app.dependency_overrides[deps.map_role] = _fake_role
    app.dependency_overrides[deps.get_agent] = _fake_agent

    client = TestClient(app)
    response = client.post(
        "/v1/agent/command",
        json={
            "user_id": "tester",
            "command_type": "ask",
            "action": "echo",
            "payload": {"question": "Hello"},
        },
        headers={"Authorization": "Bearer fake"},
    )

    try:
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["result"]["echo"] == {"question": "Hello"}
    finally:
        app.dependency_overrides.clear()
