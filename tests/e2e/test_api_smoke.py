from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_healthz_keys_present():
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    for key in ("status", "db", "vector", "llm"):
        assert key in data


def test_openapi_served():
    r = client.get("/openapi.yaml")
    assert r.status_code == 200
    assert "openapi" in r.text or "openapi" in r.content.decode("utf-8", errors="ignore")


def test_rag_proxy_validation_and_success():
    # Missing text -> 422
    r_bad = client.post("/rag/retrieve", json={})
    assert r_bad.status_code == 422

    # Minimal valid request -> 200
    r = client.post("/rag/retrieve", json={"text": "visa", "top_k": 2, "rerank_top_k": 2})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

