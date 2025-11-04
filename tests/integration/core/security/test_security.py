"""Integration tests for API security features (CORS, JWT, RBAC)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

# Import the app and token creator from our test app file
from tests.integration.core.security.sec_test_app import app, create_test_token


@pytest.fixture(scope="module")
def client():
    """Pytest fixture to create a TestClient for our app."""
    with TestClient(app) as c:
        yield c


# --- CORS Tests ---


def test_cors_allowed_origin(client: TestClient):
    """
    Tests that a request from a whitelisted origin is allowed.
    """
    # Arrange
    headers = {"Origin": "https://example.com"}

    # Act
    response = client.get("/public", headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"


def test_cors_disallowed_origin(client: TestClient):
    """
    Tests that a request from a non-whitelisted origin still gets a response,
    but the CORS header is not permissive.
    """
    # Arrange
    headers = {"Origin": "http://disallowed.com"}

    # Act
    response = client.get("/public", headers=headers)

    # Assert
    assert response.status_code == 200
    # The header should NOT be the disallowed origin. In a real browser, the request would be blocked.
    assert "access-control-allow-origin" not in response.headers


# --- JWT Authentication Tests ---


def test_jwt_no_token_protected_route(client: TestClient):
    """Tests that accessing a protected route without a token fails."""
    response = client.get("/protected")
    assert response.status_code == 403  # FastAPI's default for missing auth


def test_jwt_expired_token(client: TestClient):
    """Tests that an expired token is rejected."""
    # Arrange: Create a token that has already expired
    expired_token = create_test_token({"sub": "user123"}, expires_delta=timedelta(minutes=-5))
    headers = {"Authorization": f"Bearer {expired_token}"}

    # Act
    response = client.get("/protected", headers=headers)

    # Assert
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_jwt_valid_token(client: TestClient):
    """Tests that a valid token grants access to a protected route."""
    # Arrange
    valid_token = create_test_token({"sub": "user123", "roles": ["user"]})
    headers = {"Authorization": f"Bearer {valid_token}"}

    # Act
    response = client.get("/protected", headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "This is a protected route"}


# --- RBAC (Role-Based Access Control) Tests ---


def test_rbac_user_without_role(client: TestClient):
    """
    Tests that a user without the required role cannot access a protected route.
    """
    # Arrange: User has the 'user' role, but 'admin' is required
    user_token = create_test_token({"sub": "user456", "roles": ["user"]})
    headers = {"Authorization": f"Bearer {user_token}"}

    # Act
    response = client.get("/admin", headers=headers)

    # Assert
    assert response.status_code == 403
    assert "not have access" in response.json()["detail"]


def test_rbac_user_with_role(client: TestClient):
    """
    Tests that a user with the correct role can access the protected route.
    """
    # Arrange: User has the 'admin' role
    admin_token = create_test_token({"sub": "admin_user", "roles": ["user", "admin"]})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Act
    response = client.get("/admin", headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "This is an admin-only route"}
