"""Shared test fixtures for MegaAgent Pro test suite."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# ---------------------------------------------------------------------------
# Early environment setup — runs at import/collection time, BEFORE any
# module-level singletons (e.g. SecurityConfig) are created.
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-testing-only")
os.environ.setdefault("SECURITY_JWT_SECRET_KEY", "test-jwt-secret-for-testing-only")
os.environ.setdefault("CACHE_USE_FAKEREDIS", "true")
os.environ.setdefault("DEV_BYPASS_AUTH", "false")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DB_POSTGRES_PASSWORD", "test-password")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")


# ---------------------------------------------------------------------------
# Environment: ensure tests never hit real services
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Set safe environment defaults for all tests (reinforces early setup)."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-testing-only")
    monkeypatch.setenv("CACHE_USE_FAKEREDIS", "true")
    monkeypatch.setenv("DEV_BYPASS_AUTH", "false")
    monkeypatch.setenv("ENV", "test")


# ---------------------------------------------------------------------------
# Mock Settings (JWT / Security)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_jwt_settings():
    """Mock AppSettings with JWT configuration."""
    settings = Mock()
    settings.security.jwt_secret_key.get_secret_value.return_value = (
        "test-secret-key-12345"
    )
    settings.security.jwt_algorithm = "HS256"
    settings.security.jwt_expiration_minutes = 30
    settings.security.jwt_refresh_expiration_days = 7
    return settings


@pytest.fixture
def mock_api_key_settings():
    """Mock AppSettings with API key configuration."""
    settings = Mock()
    settings.security.api_key_prefix = "ma_"
    settings.security.api_key_length = 32
    settings.features.enable_api_auth = False
    return settings


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_jwt_token(mock_jwt_settings):
    """Generate a valid JWT token for testing."""
    from unittest.mock import patch

    with patch("api.auth.get_settings", return_value=mock_jwt_settings):
        from api.auth import create_access_token

        return create_access_token(
            user_id="test-user-001",
            email="test@example.com",
            role="admin",
            settings=mock_jwt_settings,
        )


@pytest.fixture
def auth_headers(valid_jwt_token):
    """HTTP headers with valid Bearer token."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_response():
    """Standard mock LLM response."""
    return {
        "output": "This is a test LLM response.",
        "model": "test-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Mock LLM client that returns canned responses."""
    client = AsyncMock()
    client.acomplete.return_value = mock_llm_response
    client.agenerate.return_value = mock_llm_response
    return client


# ---------------------------------------------------------------------------
# Mock Supabase
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for database and storage operations."""
    client = MagicMock()

    # Table operations
    table = MagicMock()
    table.select.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.maybe_single.return_value = table
    table.execute.return_value = MagicMock(data=[], count=0)
    client.table.return_value = table

    # Storage operations
    storage = MagicMock()
    storage.from_.return_value = storage
    storage.upload.return_value = MagicMock(path="test/file.pdf")
    storage.get_public_url.return_value = "https://example.com/test/file.pdf"
    client.storage = storage

    # RPC
    client.rpc.return_value = MagicMock(
        execute=MagicMock(return_value=MagicMock(data=[]))
    )

    return client


# ---------------------------------------------------------------------------
# Mock Memory Manager
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager with all stores."""
    mm = AsyncMock()
    mm.alog_audit = AsyncMock()
    mm.awrite = AsyncMock()
    mm.aretrieve = AsyncMock(return_value=[])
    mm.aconsolidate = AsyncMock()
    mm.asnapshot_thread = AsyncMock(return_value=[])
    return mm


# ---------------------------------------------------------------------------
# Mock Redis (via fakeredis)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_redis():
    """FakeRedis instance for cache testing."""
    try:
        import fakeredis.aioredis

        return fakeredis.aioredis.FakeRedis()
    except ImportError:
        pytest.skip("fakeredis not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def utc_now():
    """Current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)
