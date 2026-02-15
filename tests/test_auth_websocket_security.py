from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

import api.routes.document_monitor as document_monitor_routes
from core.agui import middleware as agui_middleware

JWT_TEST_SECRET = "test-jwt-secret"


def _make_token(user_id: str, role: str = "user") -> str:
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "roles": [role],
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_TEST_SECRET, algorithm="HS256")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_thread_state(thread_id: str, user_id: str) -> None:
    state = {
        "thread_id": thread_id,
        "user_id": user_id,
        "case_id": "case-1",
        "document_type": "petition",
        "status": "generating",
        "sections": [],
        "exhibits": [],
        "logs": [],
        "started_at": datetime.now().isoformat(),
        "error_message": None,
    }
    asyncio.run(document_monitor_routes.workflow_store.save_state(thread_id, state))


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", JWT_TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


@pytest.fixture
def client() -> TestClient:
    document_monitor_routes.workflow_store._memory_store.clear()
    document_monitor_routes.ws_manager.active_connections.clear()

    app = FastAPI()
    app.include_router(agui_middleware.router)
    app.include_router(document_monitor_routes.router)
    return TestClient(app)


def test_agui_ws_without_token_close_4401(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        "/agui/ws/case-1"
    ) as ws:
        ws.receive_text()
    assert exc.value.code == 4401


def test_agui_ws_invalid_token_close_4401(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        "/agui/ws/case-1",
        headers=_auth_headers("invalid-token"),
    ) as ws:
        ws.receive_text()
    assert exc.value.code == 4401


def test_document_ws_without_token_close_4401(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        "/api/ws/document/thread-1"
    ) as ws:
        ws.receive_text()
    assert exc.value.code == 4401


def test_document_ws_foreign_thread_close_4403(client: TestClient) -> None:
    thread_id = "thread-owned-by-alice"
    _seed_thread_state(thread_id=thread_id, user_id="alice")
    token = _make_token("bob")

    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        f"/api/ws/document/{thread_id}",
        headers=_auth_headers(token),
    ) as ws:
        ws.receive_text()
    assert exc.value.code == 4403


def test_document_ws_missing_thread_close_4404(client: TestClient) -> None:
    token = _make_token("alice")
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        "/api/ws/document/non-existent-thread",
        headers=_auth_headers(token),
    ) as ws:
        ws.receive_text()
    assert exc.value.code == 4404


def test_document_ws_owner_connected(client: TestClient) -> None:
    thread_id = "thread-owned-by-alice"
    _seed_thread_state(thread_id=thread_id, user_id="alice")
    token = _make_token("alice")

    with client.websocket_connect(
        f"/api/ws/document/{thread_id}",
        headers=_auth_headers(token),
    ) as ws:
        message = ws.receive_json()
        assert message["type"] == "connected"
        assert message["thread_id"] == thread_id
