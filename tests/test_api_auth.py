"""Tests for API authentication module.

This module tests the API authentication including:
- JWT token creation and verification
- API key validation
- Password hashing
- Authentication dependencies
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Import the authentication module
from api.auth import (
    RoleChecker,
    TokenData,
    User,
    create_access_token,
    create_refresh_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_api_key_async,
    verify_password,
    verify_token,
)
from core.exceptions import InvalidTokenError, TokenExpiredError


class TestPasswordUtilities:
    """Tests for password hashing utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "my_secret_password"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 20  # Bcrypt hashes are long

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "my_secret_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "my_secret_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_unique(self):
        """Test that same password produces different hashes (salting)."""
        password = "my_secret_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salting
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token functions."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.security.jwt_secret_key.get_secret_value.return_value = "test-secret-key-12345"
        settings.security.jwt_algorithm = "HS256"
        settings.security.jwt_expiration_minutes = 30
        settings.security.jwt_refresh_expiration_days = 7
        return settings

    def test_create_access_token(self, mock_settings):
        """Test access token creation."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            token = create_access_token(
                user_id="user-123",
                email="test@example.com",
                role="lawyer",
                settings=mock_settings,
            )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

    def test_create_refresh_token(self, mock_settings):
        """Test refresh token creation."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            token = create_refresh_token(user_id="user-123", settings=mock_settings)

        assert token is not None
        assert isinstance(token, str)

    def test_verify_token_valid(self, mock_settings):
        """Test verifying a valid token."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            token = create_access_token(
                user_id="user-123",
                email="test@example.com",
                role="lawyer",
                settings=mock_settings,
            )

            token_data = verify_token(token, mock_settings)

        assert token_data.user_id == "user-123"
        assert token_data.email == "test@example.com"
        assert token_data.role == "lawyer"

    def test_verify_token_expired(self, mock_settings):
        """Test verifying an expired token."""
        # Set expiration to -1 minute (already expired)
        mock_settings.security.jwt_expiration_minutes = -1

        with patch("api.auth.get_settings", return_value=mock_settings):
            token = create_access_token(
                user_id="user-123",
                email="test@example.com",
                role="lawyer",
                settings=mock_settings,
            )

            with pytest.raises(TokenExpiredError):
                verify_token(token, mock_settings)

    def test_verify_token_invalid(self, mock_settings):
        """Test verifying an invalid token."""
        with pytest.raises(InvalidTokenError):
            verify_token("invalid-token-string", mock_settings)


class TestAPIKeyFunctions:
    """Tests for API key functions."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.security.api_key_prefix = "ma_"
        settings.security.api_key_length = 32
        settings.features.enable_api_auth = False  # Development mode
        return settings

    def test_generate_api_key(self, mock_settings):
        """Test API key generation."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            key = generate_api_key(mock_settings)

        assert key.startswith("ma_")
        assert len(key) >= 32

    def test_generate_api_key_uniqueness(self, mock_settings):
        """Test that generated API keys are unique."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            keys = [generate_api_key(mock_settings) for _ in range(10)]

        # All keys should be unique
        assert len(set(keys)) == 10

    def test_hash_api_key(self):
        """Test API key hashing."""
        key = "ma_test_api_key_12345"
        hashed = hash_api_key(key)

        # SHA-256 produces 64 character hex string
        assert len(hashed) == 64
        # Same key should produce same hash
        assert hash_api_key(key) == hashed

    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "ma_test_key_1"
        key2 = "ma_test_key_2"

        assert hash_api_key(key1) != hash_api_key(key2)

    def test_verify_api_key_format_invalid_prefix(self, mock_settings):
        """Test API key verification rejects invalid prefix."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            # Key without correct prefix
            assert verify_api_key("invalid_prefix_key") is False

    def test_verify_api_key_format_too_short(self, mock_settings):
        """Test API key verification rejects short keys."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            # Key too short
            assert verify_api_key("ma_short") is False

    def test_verify_api_key_dev_mode(self, mock_settings):
        """Test API key verification in development mode."""
        # Development mode - should accept format-valid keys
        mock_settings.features.enable_api_auth = False

        with patch("api.auth.get_settings", return_value=mock_settings):
            key = generate_api_key(mock_settings)
            assert verify_api_key(key) is True


class TestVerifyAPIKeyAsync:
    """Tests for async API key verification."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.security.api_key_prefix = "ma_"
        settings.security.api_key_length = 32
        settings.features.enable_api_auth = False
        return settings

    @pytest.mark.asyncio
    async def test_verify_api_key_async_invalid_prefix(self, mock_settings):
        """Test async verification rejects invalid prefix."""
        with patch("api.auth.get_settings", return_value=mock_settings):
            is_valid, user_data = await verify_api_key_async("invalid_key")

        assert is_valid is False
        assert user_data is None

    @pytest.mark.asyncio
    async def test_verify_api_key_async_dev_mode(self, mock_settings):
        """Test async verification in development mode."""
        mock_settings.features.enable_api_auth = False

        with patch("api.auth.get_settings", return_value=mock_settings):
            key = generate_api_key(mock_settings)
            is_valid, user_data = await verify_api_key_async(key)

        assert is_valid is True
        assert user_data is not None
        assert user_data.get("role") == "admin"


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """Test basic user creation."""
        user = User(
            user_id="user-123",
            email="test@example.com",
            role="lawyer",
        )

        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.role == "lawyer"
        assert user.is_active is True

    def test_user_inactive(self):
        """Test inactive user."""
        user = User(
            user_id="user-123",
            email="test@example.com",
            role="lawyer",
            is_active=False,
        )

        assert user.is_active is False


class TestRoleChecker:
    """Tests for RoleChecker dependency."""

    @pytest.fixture
    def admin_user(self):
        """Create admin user."""
        return User(
            user_id="admin-1",
            email="admin@example.com",
            role="admin",
        )

    @pytest.fixture
    def lawyer_user(self):
        """Create lawyer user."""
        return User(
            user_id="lawyer-1",
            email="lawyer@example.com",
            role="lawyer",
        )

    @pytest.fixture
    def client_user(self):
        """Create client user."""
        return User(
            user_id="client-1",
            email="client@example.com",
            role="client",
        )

    def test_role_checker_initialization(self):
        """Test RoleChecker initialization."""
        checker = RoleChecker(["admin", "lawyer"])
        assert checker.allowed_roles == ["admin", "lawyer"]

    @pytest.mark.asyncio
    async def test_role_checker_allows_matching_role(self, admin_user):
        """Test RoleChecker allows matching role."""
        checker = RoleChecker(["admin", "lawyer"])

        # This should not raise
        result = await checker(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_role_checker_denies_non_matching_role(self, client_user):
        """Test RoleChecker denies non-matching role."""
        from fastapi import HTTPException

        checker = RoleChecker(["admin", "lawyer"])

        with pytest.raises(HTTPException) as exc_info:
            await checker(client_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail


class TestTokenData:
    """Tests for TokenData model."""

    def test_token_data_creation(self):
        """Test TokenData creation."""
        exp = datetime.now(UTC) + timedelta(hours=1)
        token_data = TokenData(
            user_id="user-123",
            email="test@example.com",
            role="lawyer",
            exp=exp,
        )

        assert token_data.user_id == "user-123"
        assert token_data.email == "test@example.com"
        assert token_data.role == "lawyer"
        assert token_data.exp == exp


class TestAPIKeyCache:
    """Tests for API key caching behavior."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.security.api_key_prefix = "ma_"
        settings.security.api_key_length = 32
        settings.features.enable_api_auth = False
        return settings

    def test_cache_stores_results(self, mock_settings):
        """Test that verification results are cached."""
        from api.auth import _api_key_cache

        # Clear cache first
        _api_key_cache.clear()

        with patch("api.auth.get_settings", return_value=mock_settings):
            key = generate_api_key(mock_settings)
            key_hash = hash_api_key(key)

            # First call
            verify_api_key(key)

            # Check cache
            assert key_hash in _api_key_cache

    @pytest.mark.asyncio
    async def test_async_cache_stores_results(self, mock_settings):
        """Test that async verification results are cached."""
        from api.auth import _api_key_cache

        # Clear cache first
        _api_key_cache.clear()

        with patch("api.auth.get_settings", return_value=mock_settings):
            key = generate_api_key(mock_settings)
            key_hash = hash_api_key(key)

            # First call
            await verify_api_key_async(key)

            # Check cache
            assert key_hash in _api_key_cache
