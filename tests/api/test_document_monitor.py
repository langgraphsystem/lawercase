"""Tests for Document Monitor API endpoints."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from api.routes.document_monitor import router
from core.storage.document_workflow_store import get_document_workflow_store


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    """Create async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def workflow_store():
    """Get workflow store instance."""
    return get_document_workflow_store()


@pytest.mark.asyncio
async def test_start_document_generation(client):
    """Test starting document generation."""
    response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-123",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "thread_id" in data
    assert data["status"] == "generating"
    assert "message" in data


@pytest.mark.asyncio
async def test_get_document_preview_not_found(client):
    """Test getting preview for non-existent thread."""
    response = await client.get("/api/document/preview/non-existent-thread")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_document_preview_success(client, workflow_store):
    """Test getting document preview."""
    # Start generation first
    start_response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-456",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    thread_id = start_response.json()["thread_id"]

    # Get preview
    response = await client.get(f"/api/document/preview/{thread_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["thread_id"] == thread_id
    assert "status" in data
    assert "sections" in data
    assert "exhibits" in data
    assert "metadata" in data
    assert "logs" in data


@pytest.mark.asyncio
async def test_upload_exhibit_not_found(client):
    """Test uploading exhibit to non-existent thread."""
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    data = {"exhibit_id": "1.1.A"}

    response = await client.post(
        "/api/upload-exhibit/non-existent-thread",
        files=files,
        data=data,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pause_generation(client, workflow_store):
    """Test pausing document generation."""
    # Start generation
    start_response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-789",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    thread_id = start_response.json()["thread_id"]

    # Pause
    response = await client.post(f"/api/pause/{thread_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "paused"
    assert "message" in data


@pytest.mark.asyncio
async def test_pause_invalid_state(client, workflow_store):
    """Test pausing when workflow is not in valid state."""
    # Start generation
    start_response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-101",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    thread_id = start_response.json()["thread_id"]

    # First pause
    await client.post(f"/api/pause/{thread_id}")

    # Try to pause again (should fail)
    response = await client.post(f"/api/pause/{thread_id}")

    assert response.status_code == 400
    assert "cannot pause" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_generation(client, workflow_store):
    """Test resuming paused generation."""
    # Start and pause
    start_response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-202",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    thread_id = start_response.json()["thread_id"]
    await client.post(f"/api/pause/{thread_id}")

    # Resume
    response = await client.post(f"/api/resume/{thread_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "generating"
    assert "message" in data


@pytest.mark.asyncio
async def test_download_pdf_not_completed(client, workflow_store):
    """Test downloading PDF before generation completes."""
    # Start generation
    start_response = await client.post(
        "/api/generate-petition",
        json={
            "case_id": "test-case-303",
            "document_type": "petition",
            "user_id": "test-user",
        },
    )

    thread_id = start_response.json()["thread_id"]

    # Try to download (should fail - not completed)
    response = await client.get(f"/api/download-petition-pdf/{thread_id}")

    assert response.status_code == 400
    assert "not completed" in response.json()["detail"].lower()
