"""E2E tests for API endpoints.

Tests the full API endpoints using FastAPI TestClient:
- Health checks (liveness, readiness, startup)
- LLM generation endpoints
- Case management endpoints
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

# ============================================================================
# Test App Setup
# ============================================================================


def create_test_app() -> FastAPI:
    """Create test FastAPI application with all routes."""
    from fastapi import FastAPI

    app = FastAPI(title="Test App")

    # Import and include routers
    from api.routes.health_production import router as health_router

    app.include_router(health_router, prefix="/health", tags=["Health"])

    try:
        from api.routes.llm import router as llm_router

        app.include_router(llm_router, prefix="/api/v1/llm", tags=["LLM"])
    except ImportError:
        pass

    try:
        from api.routes.case_management import router as case_router

        app.include_router(case_router, prefix="/api/v1/cases", tags=["Cases"])
    except ImportError:
        pass

    return app


@pytest.fixture
def test_app() -> FastAPI:
    """Create test application."""
    return create_test_app()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


# ============================================================================
# Health Endpoint Tests
# ============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness_check(self, client: TestClient) -> None:
        """Test liveness probe returns OK."""
        response = client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_check_healthy(self, client: TestClient) -> None:
        """Test readiness probe with mocked healthy services."""
        from api.routes.health_production import DependencyHealth, HealthStatus

        mock_db_health = DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            response_time_ms=5.0,
            message="Database healthy",
        )
        mock_redis_health = DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            response_time_ms=2.0,
            message="Redis healthy",
        )

        with (
            patch(
                "api.routes.health_production.check_database_health",
                return_value=mock_db_health,
            ),
            patch(
                "api.routes.health_production.check_redis_health",
                return_value=mock_redis_health,
            ),
        ):
            response = client.get("/health/readiness")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_check_degraded(self, client: TestClient) -> None:
        """Test readiness probe with unhealthy service."""
        from api.routes.health_production import DependencyHealth, HealthStatus

        mock_db_health = DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            response_time_ms=5.0,
        )
        mock_redis_health = DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=2.0,
            message="Connection refused",
        )

        with (
            patch(
                "api.routes.health_production.check_database_health",
                return_value=mock_db_health,
            ),
            patch(
                "api.routes.health_production.check_redis_health",
                return_value=mock_redis_health,
            ),
        ):
            response = client.get("/health/readiness")
            # Returns 503 when critical dependency is unhealthy
            assert response.status_code == 503

    def test_startup_check(self, client: TestClient) -> None:
        """Test startup probe."""
        # Mock SERVICE_START_TIME to be more than 5 seconds ago
        with patch("api.routes.health_production.SERVICE_START_TIME", 0):
            response = client.get("/health/startup")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"

    def test_detailed_health(self, client: TestClient) -> None:
        """Test detailed health endpoint."""
        from api.routes.health_production import DependencyHealth, HealthStatus

        mock_health = DependencyHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=1.0,
        )

        with (
            patch(
                "api.routes.health_production.check_database_health",
                return_value=mock_health,
            ),
            patch(
                "api.routes.health_production.check_redis_health",
                return_value=mock_health,
            ),
            patch(
                "api.routes.health_production.check_llm_health",
                return_value=mock_health,
            ),
            patch(
                "api.routes.health_production.check_memory_health",
                return_value=mock_health,
            ),
        ):
            response = client.get("/health/health")
            assert response.status_code == 200
            data = response.json()
            assert "dependencies" in data
            assert "timestamp" in data


# ============================================================================
# LLM Endpoint Tests
# ============================================================================


class TestLLMEndpoints:
    """Tests for LLM generation endpoints."""

    def test_list_models(self, client: TestClient) -> None:
        """Test GET /models returns available models."""
        response = client.get("/api/v1/llm/models")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "openai" in data["providers"]
        assert "anthropic" in data["providers"]

    def test_generate_request_validation(self, client: TestClient) -> None:
        """Test generate endpoint validates request."""
        # Missing required fields
        response = client.post("/api/v1/llm/generate", json={})
        assert response.status_code == 422  # Validation error

    def test_generate_with_mock(self, client: TestClient) -> None:
        """Test generate endpoint with mocked LLM."""
        with patch("api.routes.llm._create_generator") as mock_create:
            mock_generator = MagicMock()
            mock_result = MagicMock()
            mock_result.content = "Test response"
            mock_result.model = "gpt-4o-mini"
            mock_result.provider = MagicMock(value="openai")
            mock_result.prompt_tokens = 10
            mock_result.completion_tokens = 20
            mock_result.total_tokens = 30
            mock_result.latency_ms = 100.0
            mock_result.cached = False
            mock_result.finish_reason = "stop"

            mock_generator.generate = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_generator

            response = client.post(
                "/api/v1/llm/generate",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "gpt-4o-mini",
                    "provider": "openai",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "Test response"
            assert data["model"] == "gpt-4o-mini"

    def test_generate_invalid_provider(self, client: TestClient) -> None:
        """Test generate with invalid provider returns error."""
        response = client.post(
            "/api/v1/llm/generate",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "invalid_provider",
            },
        )
        assert response.status_code == 400

    def test_generate_stream_endpoint_exists(self, client: TestClient) -> None:
        """Test streaming endpoint exists."""
        with patch("api.routes.llm._create_generator") as mock_create:
            mock_generator = MagicMock()

            async def mock_stream(*args: Any, **kwargs: Any):
                yield MagicMock(content="Test", index=0, is_final=False, finish_reason=None)
                yield MagicMock(content="", index=1, is_final=True, finish_reason="stop")

            mock_generator.generate_stream = mock_stream
            mock_create.return_value = mock_generator

            response = client.post(
                "/api/v1/llm/generate/stream",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
            # Should return streaming response
            assert response.status_code == 200
            assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"

    def test_get_stats(self, client: TestClient) -> None:
        """Test stats endpoint."""
        response = client.get("/api/v1/llm/stats")
        assert response.status_code == 200


# ============================================================================
# Case Management Endpoint Tests
# ============================================================================


class TestCaseManagementEndpoints:
    """Tests for case management endpoints."""

    @pytest.fixture
    def mock_case_service(self):
        """Create mock case service."""
        with patch("api.routes.case_management.get_case_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    def test_get_statuses(self, client: TestClient) -> None:
        """Test GET /statuses returns available statuses."""
        response = client.get("/api/v1/cases/statuses")
        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert "case_types" in data
        assert "valid_transitions" in data

    def test_create_case(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test POST /cases creates a new case."""
        from datetime import datetime
        from uuid import uuid4

        mock_case = MagicMock()
        mock_case.case_id = uuid4()
        mock_case.user_id = "user123"
        mock_case.title = "Test Case"
        mock_case.description = "Test description"
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="draft")
        mock_case.data = {}
        mock_case.version = 1
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_case_service.create_case = AsyncMock(return_value=mock_case)

        response = client.post(
            "/api/v1/cases?user_id=user123",
            json={
                "title": "Test Case",
                "description": "Test description",
                "case_type": "eb1a",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Case"
        assert data["user_id"] == "user123"

    def test_create_case_validation(self, client: TestClient) -> None:
        """Test case creation validates required fields."""
        response = client.post(
            "/api/v1/cases?user_id=user123",
            json={"description": "No title"},  # Missing title
        )
        assert response.status_code == 422

    def test_get_case(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test GET /cases/{id} returns case."""
        from datetime import datetime

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.case_id = case_id
        mock_case.user_id = "user123"
        mock_case.title = "Test Case"
        mock_case.description = ""
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="draft")
        mock_case.data = {}
        mock_case.version = 1
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_case_service.get_case = AsyncMock(return_value=mock_case)

        response = client.get(f"/api/v1/cases/{case_id}?user_id=user123")

        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == str(case_id)

    def test_get_case_not_found(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test GET /cases/{id} returns 404 for missing case."""
        mock_case_service.get_case = AsyncMock(return_value=None)

        case_id = uuid4()
        response = client.get(f"/api/v1/cases/{case_id}?user_id=user123")

        assert response.status_code == 404

    def test_update_case(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test PUT /cases/{id} updates case."""
        from datetime import datetime

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.case_id = case_id
        mock_case.user_id = "user123"
        mock_case.title = "Updated Title"
        mock_case.description = ""
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="draft")
        mock_case.data = {}
        mock_case.version = 2
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_case_service.update_case = AsyncMock(return_value=mock_case)

        response = client.put(
            f"/api/v1/cases/{case_id}?user_id=user123",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["version"] == 2

    def test_delete_case(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test DELETE /cases/{id} soft deletes case."""
        mock_case_service.delete_case = AsyncMock(return_value=True)

        case_id = uuid4()
        response = client.delete(f"/api/v1/cases/{case_id}?user_id=user123")

        assert response.status_code == 204

    def test_delete_case_not_found(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test DELETE /cases/{id} returns 404 for missing case."""
        mock_case_service.delete_case = AsyncMock(return_value=False)

        case_id = uuid4()
        response = client.delete(f"/api/v1/cases/{case_id}?user_id=user123")

        assert response.status_code == 404

    def test_restore_case(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test POST /cases/{id}/restore restores soft-deleted case."""
        from datetime import datetime

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.case_id = case_id
        mock_case.user_id = "user123"
        mock_case.title = "Restored Case"
        mock_case.description = ""
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="draft")
        mock_case.data = {}
        mock_case.version = 1
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_case_service.restore_case = AsyncMock(return_value=mock_case)

        response = client.post(f"/api/v1/cases/{case_id}/restore?user_id=user123")

        assert response.status_code == 200

    def test_update_status(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test PATCH /cases/{id}/status updates case status."""
        from datetime import datetime

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.case_id = case_id
        mock_case.user_id = "user123"
        mock_case.title = "Test Case"
        mock_case.description = ""
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="open")
        mock_case.data = {}
        mock_case.version = 2
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_case_service.update_status = AsyncMock(return_value=mock_case)

        response = client.patch(
            f"/api/v1/cases/{case_id}/status?user_id=user123",
            json={"status": "open", "reason": "Starting work"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"

    def test_list_cases(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test GET /cases lists cases with pagination."""
        from datetime import datetime

        mock_result = MagicMock()
        mock_case = MagicMock()
        mock_case.case_id = uuid4()
        mock_case.user_id = "user123"
        mock_case.title = "Test Case"
        mock_case.description = ""
        mock_case.case_type = MagicMock(value="eb1a")
        mock_case.status = MagicMock(value="draft")
        mock_case.data = {}
        mock_case.version = 1
        mock_case.created_at = datetime.utcnow()
        mock_case.updated_at = datetime.utcnow()
        mock_case.deleted_at = None

        mock_result.cases = [mock_case]
        mock_result.total = 1
        mock_result.limit = 50
        mock_result.offset = 0
        mock_result.has_more = False

        mock_case_service.list_cases = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/cases?user_id=user123")

        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert data["total"] == 1
        assert len(data["cases"]) == 1

    def test_list_cases_with_filters(
        self, client: TestClient, mock_case_service: MagicMock
    ) -> None:
        """Test GET /cases with filter parameters."""
        mock_result = MagicMock()
        mock_result.cases = []
        mock_result.total = 0
        mock_result.limit = 50
        mock_result.offset = 0
        mock_result.has_more = False

        mock_case_service.list_cases = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/cases?user_id=user123&status=open&case_type=eb1a&limit=10")

        assert response.status_code == 200
        mock_case_service.list_cases.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================


class TestAPIIntegration:
    """Integration tests combining multiple endpoints."""

    def test_case_lifecycle(self, client: TestClient, mock_case_service: MagicMock) -> None:
        """Test complete case lifecycle: create -> update -> status change -> delete."""
        from datetime import datetime

        case_id = uuid4()

        # Create mock cases for each stage
        def create_mock_case(status: str = "draft", version: int = 1):
            mock = MagicMock()
            mock.case_id = case_id
            mock.user_id = "user123"
            mock.title = "Lifecycle Test"
            mock.description = ""
            mock.case_type = MagicMock(value="eb1a")
            mock.status = MagicMock(value=status)
            mock.data = {}
            mock.version = version
            mock.created_at = datetime.utcnow()
            mock.updated_at = datetime.utcnow()
            mock.deleted_at = None
            return mock

        # 1. Create case
        mock_case_service.create_case = AsyncMock(return_value=create_mock_case())
        response = client.post(
            "/api/v1/cases?user_id=user123",
            json={"title": "Lifecycle Test"},
        )
        assert response.status_code == 201

        # 2. Update status to open
        mock_case_service.update_status = AsyncMock(return_value=create_mock_case("open", 2))
        response = client.patch(
            f"/api/v1/cases/{case_id}/status?user_id=user123",
            json={"status": "open"},
        )
        assert response.status_code == 200

        # 3. Update status to in_progress
        mock_case_service.update_status = AsyncMock(return_value=create_mock_case("in_progress", 3))
        response = client.patch(
            f"/api/v1/cases/{case_id}/status?user_id=user123",
            json={"status": "in_progress"},
        )
        assert response.status_code == 200

        # 4. Soft delete
        mock_case_service.delete_case = AsyncMock(return_value=True)
        response = client.delete(f"/api/v1/cases/{case_id}?user_id=user123")
        assert response.status_code == 204

        # 5. Restore
        mock_case_service.restore_case = AsyncMock(return_value=create_mock_case("in_progress", 3))
        response = client.post(f"/api/v1/cases/{case_id}/restore?user_id=user123")
        assert response.status_code == 200

    @pytest.fixture
    def mock_case_service(self):
        """Create mock case service for integration tests."""
        with patch("api.routes.case_management.get_case_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service
