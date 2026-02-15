from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
import pytest

from api.routes import health_production as health_production_routes, metrics as metrics_routes
import api.routes.document_monitor as document_monitor_routes


def _make_token(secret: str, user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _auth_header(token: str) -> dict[str, str]:
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
        "started_at": datetime.now(UTC).isoformat(),
        "error_message": None,
    }
    asyncio.run(document_monitor_routes.workflow_store.save_state(thread_id, state))


@pytest.fixture(autouse=True)
def jwt_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


@pytest.fixture
def metrics_client() -> TestClient:
    app = FastAPI()
    app.include_router(metrics_routes.router)
    return TestClient(app)


@pytest.fixture
def document_monitor_client() -> TestClient:
    # Isolate in-memory workflow store state for each test.
    document_monitor_routes.workflow_store._memory_store.clear()
    app = FastAPI()
    app.include_router(document_monitor_routes.router)
    return TestClient(app)


@pytest.fixture
def health_production_client() -> TestClient:
    app = FastAPI()
    app.include_router(health_production_routes.router)
    return TestClient(app)


def test_metrics_without_token_returns_401(metrics_client: TestClient) -> None:
    response = metrics_client.get("/metrics")
    assert response.status_code == 401


def test_metrics_with_user_role_returns_403(metrics_client: TestClient) -> None:
    token = _make_token("test-jwt-secret", user_id="user-1", role="user")
    response = metrics_client.get("/metrics", headers=_auth_header(token))
    assert response.status_code == 403


def test_metrics_with_admin_role_returns_200(metrics_client: TestClient) -> None:
    token = _make_token("test-jwt-secret", user_id="admin-1", role="admin")
    response = metrics_client.get("/metrics", headers=_auth_header(token))
    assert response.status_code == 200


def test_health_production_metrics_without_token_returns_401(
    health_production_client: TestClient,
) -> None:
    response = health_production_client.get("/metrics")
    assert response.status_code == 401


def test_document_preview_with_foreign_thread_returns_403(
    document_monitor_client: TestClient,
) -> None:
    thread_id = "thread-owned-by-alice"
    _seed_thread_state(thread_id=thread_id, user_id="alice")

    token = _make_token("test-jwt-secret", user_id="bob", role="user")
    response = document_monitor_client.get(
        f"/api/document/preview/{thread_id}", headers=_auth_header(token)
    )

    assert response.status_code == 403


def test_generate_petition_with_mismatched_user_id_returns_403(
    document_monitor_client: TestClient,
) -> None:
    token = _make_token("test-jwt-secret", user_id="alice", role="user")
    response = document_monitor_client.post(
        "/api/generate-petition",
        headers=_auth_header(token),
        json={"case_id": "case-1", "document_type": "petition", "user_id": "bob"},
    )
    assert response.status_code == 403
