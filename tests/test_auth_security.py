from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace

from fastapi import FastAPI
import httpx
from jose import jwt
import pytest

from api.routes import llm as llm_routes, metrics as metrics_routes
import api.routes.document_monitor as document_monitor_routes
from core.agui import middleware as agui_middleware

JWT_TEST_SECRET = "test-jwt-secret"


def _make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "email": f"{user_id}@test.local",
        "role": role,
        "roles": [role],
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_TEST_SECRET, algorithm="HS256")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_thread_state(thread_id: str, user_id: str, status: str = "generating") -> None:
    state = {
        "thread_id": thread_id,
        "user_id": user_id,
        "case_id": "case-1",
        "document_type": "petition",
        "status": status,
        "sections": [],
        "exhibits": [],
        "logs": [],
        "started_at": datetime.now().isoformat(),
        "error_message": None,
    }
    await document_monitor_routes.workflow_store.save_state(thread_id, state)


async def _seed_thread_state_aware_started_at(thread_id: str, user_id: str) -> None:
    state = {
        "thread_id": thread_id,
        "user_id": user_id,
        "case_id": "case-1",
        "document_type": "petition",
        "status": "generating",
        "sections": [],
        "exhibits": [],
        "logs": [],
        "started_at": datetime.now(UTC).isoformat(),
        "error_message": None,
    }
    await document_monitor_routes.workflow_store.save_state(thread_id, state)


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", JWT_TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    # Align AppSettings security secret with the test JWT secret
    monkeypatch.setenv("SECURITY_JWT_SECRET_KEY", JWT_TEST_SECRET)
    # Invalidate cached settings so the new env vars take effect
    from core.config.production_settings import get_settings as _gs
    _gs.cache_clear()
    import core.config.production_settings as _prod_settings
    _prod_settings._settings = None


@pytest.fixture(autouse=True)
def fake_agui_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeSSEEvent:
        def __init__(self, payload: dict[str, str]) -> None:
            self.payload = payload

        def to_sse(self) -> str:
            return f"data: {json.dumps(self.payload)}\n\n"

    class _FakeAdapter:
        async def run_workflow(self, **_: object):
            yield _FakeSSEEvent({"type": "RUN_FINISHED"})

        async def stream_agent_response(self, **_: object):
            yield _FakeSSEEvent({"type": "TEXT_MESSAGE_CONTENT", "delta": "ok"})
            yield _FakeSSEEvent({"type": "RUN_FINISHED"})

        def submit_validation_result(self, **_: object) -> bool:
            return True

    monkeypatch.setattr(agui_middleware, "get_agui_adapter", lambda: _FakeAdapter())


@pytest.fixture
async def client() -> httpx.AsyncClient:
    document_monitor_routes.workflow_store._memory_store.clear()

    app = FastAPI()
    app.include_router(metrics_routes.router)
    app.include_router(document_monitor_routes.router)
    app.include_router(agui_middleware.router)
    app.include_router(llm_routes.router, prefix="/v1/llm")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/metrics", headers=_auth_headers("not-a-valid-jwt"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_role(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="user-1", role="user")
    response = await client.get("/metrics", headers=_auth_headers(token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_access(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="admin-1", role="admin")
    response = await client.get("/metrics", headers=_auth_headers(token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ownership_check(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice"
    await _seed_thread_state(thread_id=thread_id, user_id="alice")

    token = _make_token(user_id="bob", role="user")
    response = await client.get(
        f"/api/document/preview/{thread_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_own_resource_access(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice"
    await _seed_thread_state(thread_id=thread_id, user_id="alice")

    token = _make_token(user_id="alice", role="user")
    response = await client.get(
        f"/api/document/preview/{thread_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_own_resource_access_with_timezone_started_at(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice-aware"
    await _seed_thread_state_aware_started_at(thread_id=thread_id, user_id="alice")

    token = _make_token(user_id="alice", role="user")
    response = await client.get(
        f"/api/document/preview/{thread_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_agui_agent_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/agui/agent",
        json={"agent_name": "mega_agent", "prompt": "hello"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agui_agent_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/agui/agent",
        headers=_auth_headers("invalid-jwt"),
        json={"agent_name": "mega_agent", "prompt": "hello"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agui_run_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/agui/run",
        json={"case_id": "case-1", "operation": "query", "data": {"query": "hello"}},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agui_run_user_id_mismatch_returns_403(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="alice", role="user")
    response = await client.post(
        "/agui/run",
        headers=_auth_headers(token),
        json={"case_id": "case-1", "operation": "query", "user_id": "bob"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agui_run_owner_access_returns_200(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="alice", role="user")
    response = await client.post(
        "/agui/run",
        headers=_auth_headers(token),
        json={"case_id": "case-1", "operation": "query"},
    )
    assert response.status_code == 200
    assert "RUN_FINISHED" in response.text


@pytest.mark.asyncio
async def test_agui_validation_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/agui/validation/submit",
        json={"validation_id": "val-1", "approved": True},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agui_validation_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/agui/validation/submit",
        headers=_auth_headers("invalid-jwt"),
        json={"validation_id": "val-1", "approved": True},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agui_validation_valid_access(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="alice", role="user")
    response = await client.post(
        "/agui/validation/submit",
        headers=_auth_headers(token),
        json={"validation_id": "val-1", "approved": True},
    )
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.asyncio
async def test_llm_models_available(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="user-1", role="user")
    response = await client.get("/v1/llm/models", headers=_auth_headers(token))
    assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
    body = response.json()
    assert "providers" in body


@pytest.mark.asyncio
async def test_llm_generate_unknown_provider_returns_400(client: httpx.AsyncClient) -> None:
    token = _make_token(user_id="user-1", role="user")
    response = await client.post(
        "/v1/llm/generate",
        headers=_auth_headers(token),
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "provider": "not-a-provider",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_llm_generate_happy_path_returns_200(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeGenerator:
        async def generate(self, **_: object) -> SimpleNamespace:
            return SimpleNamespace(
                content="ok",
                model="gpt-5.2",
                provider=SimpleNamespace(value="openai"),
                prompt_tokens=10,
                completion_tokens=3,
                total_tokens=13,
                latency_ms=12.0,
                cached=False,
                finish_reason="stop",
            )

    monkeypatch.setattr(llm_routes, "_create_generator", lambda _: _FakeGenerator())

    token = _make_token(user_id="user-1", role="user")
    response = await client.post(
        "/v1/llm/generate",
        headers=_auth_headers(token),
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "provider": "openai",
            "model": "gpt-5.2",
        },
    )

    assert response.status_code == 200
    assert response.json()["content"] == "ok"
    assert response.json()["provider"] == "openai"


@pytest.mark.asyncio
async def test_llm_generate_stream_happy_path_returns_sse(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeGenerator:
        async def generate_stream(self, **_: object):
            yield SimpleNamespace(content="hello", index=0, is_final=False, finish_reason=None)
            yield SimpleNamespace(content="", index=1, is_final=True, finish_reason="stop")

    monkeypatch.setattr(llm_routes, "_create_generator", lambda _: _FakeGenerator())

    token = _make_token(user_id="user-1", role="user")
    response = await client.post(
        "/v1/llm/generate/stream",
        headers=_auth_headers(token),
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "provider": "openai",
            "model": "gpt-5.2",
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"content": "hello"' in response.text
    assert "data: [DONE]" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "legacy_path",
    [
        "/v1/agent/process",
        "/v1/cases",
        "/v1/memory/stats",
        "/v1/workflows",
    ],
)
async def test_legacy_endpoints_removed_from_public_contract(legacy_path: str) -> None:
    from api.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get(legacy_path)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_petition_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/generate-petition",
        json={"case_id": "case-1", "document_type": "petition", "user_id": "alice"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_exhibit_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/upload-exhibit/thread-1",
        data={"exhibit_id": "1.A"},
        files={"file": ("evidence.txt", b"evidence", "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_exhibit_foreign_thread_returns_403(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice-upload"
    await _seed_thread_state(thread_id=thread_id, user_id="alice")
    token = _make_token(user_id="bob", role="user")

    response = await client.post(
        f"/api/upload-exhibit/{thread_id}",
        headers=_auth_headers(token),
        data={"exhibit_id": "1.A"},
        files={"file": ("evidence.txt", b"evidence", "text/plain")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_download_petition_pdf_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/download-petition-pdf/thread-1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_petition_pdf_foreign_thread_returns_403(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice-download"
    await _seed_thread_state(thread_id=thread_id, user_id="alice")
    token = _make_token(user_id="bob", role="user")

    response = await client.get(
        f"/api/download-petition-pdf/{thread_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pause_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/pause/thread-1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pause_foreign_thread_returns_403(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice-pause"
    await _seed_thread_state(thread_id=thread_id, user_id="alice", status="generating")
    token = _make_token(user_id="bob", role="user")

    response = await client.post(f"/api/pause/{thread_id}", headers=_auth_headers(token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_resume_unauthorized_access(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/resume/thread-1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_resume_foreign_thread_returns_403(client: httpx.AsyncClient) -> None:
    thread_id = "thread-owned-by-alice-resume"
    await _seed_thread_state(thread_id=thread_id, user_id="alice", status="paused")
    token = _make_token(user_id="bob", role="user")

    response = await client.post(f"/api/resume/{thread_id}", headers=_auth_headers(token))
    assert response.status_code == 403
