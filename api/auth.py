"""Authentication and authorization for API.

This module provides:
- JWT token generation and validation
- API key authentication
- Role-based access control (RBAC)
- User authentication dependencies
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from core.config.production_settings import AppSettings, get_settings
from core.exceptions import InvalidTokenError, TokenExpiredError

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============================================================================
# Models
# ============================================================================


class TokenData(BaseModel):
    """JWT token payload."""

    user_id: str
    email: str
    role: str
    exp: datetime


class User(BaseModel):
    """User model."""

    user_id: str
    email: str
    role: str
    is_active: bool = True
    created_at: datetime = datetime.now(UTC)


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# Password Utilities
# ============================================================================


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Functions
# ============================================================================


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user",
    settings: AppSettings | None = None,
) -> str:
    """Create JWT access token.

    Args:
        user_id: User identifier
        email: User email
        role: User role
        settings: App settings (gets from global if None)

    Returns:
        Encoded JWT token
    """
    if settings is None:
        settings = get_settings()

    expire = datetime.now(UTC) + timedelta(minutes=settings.security.jwt_expiration_minutes)

    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }

    token = jwt.encode(
        payload,
        settings.security.jwt_secret_key.get_secret_value(),
        algorithm=settings.security.jwt_algorithm,
    )
    return token


def create_refresh_token(user_id: str, settings: AppSettings | None = None) -> str:
    """Create JWT refresh token.

    Args:
        user_id: User identifier
        settings: App settings

    Returns:
        Encoded JWT refresh token
    """
    if settings is None:
        settings = get_settings()

    expire = datetime.now(UTC) + timedelta(days=settings.security.jwt_refresh_expiration_days)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }

    token = jwt.encode(
        payload,
        settings.security.jwt_secret_key.get_secret_value(),
        algorithm=settings.security.jwt_algorithm,
    )
    return token


def verify_token(token: str, settings: AppSettings | None = None) -> TokenData:
    """Verify and decode JWT token.

    Args:
        token: JWT token string
        settings: App settings

    Returns:
        Decoded token data

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    if settings is None:
        settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.security.jwt_secret_key.get_secret_value(),
            algorithms=[settings.security.jwt_algorithm],
        )

        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        return TokenData(
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"]),
        )

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e!s}")


# ============================================================================
# API Key Functions
# ============================================================================


def generate_api_key(settings: AppSettings | None = None) -> str:
    """Generate new API key.

    Args:
        settings: App settings

    Returns:
        API key string
    """
    if settings is None:
        settings = get_settings()

    key = secrets.token_urlsafe(settings.security.api_key_length)
    return f"{settings.security.api_key_prefix}{key}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage.

    Args:
        api_key: API key to hash

    Returns:
        Hashed API key
    """
    import hashlib

    return hashlib.sha256(api_key.encode()).hexdigest()


# In-memory cache for verified API keys (TTL + max size to prevent DoS)
try:
    from cachetools import TTLCache

    _api_key_cache: dict[str, tuple[bool, datetime]] = TTLCache(maxsize=1024, ttl=300)
except ImportError:
    # Fallback: plain dict with manual TTL check (bounded by periodic cleanup)
    _api_key_cache: dict[str, tuple[bool, datetime]] = {}
_API_KEY_CACHE_TTL = timedelta(minutes=5)
_API_KEY_CACHE_MAX_SIZE = 1024


def _cache_put(key: str, value: tuple[bool, datetime]) -> None:
    """Store in cache with size bound. Evicts oldest entries if full."""
    if len(_api_key_cache) >= _API_KEY_CACHE_MAX_SIZE:
        # Remove oldest ~10% to avoid evicting on every insert
        to_remove = list(_api_key_cache.keys())[: _API_KEY_CACHE_MAX_SIZE // 10]
        for k in to_remove:
            _api_key_cache.pop(k, None)
    _api_key_cache[key] = value


async def verify_api_key_from_db(api_key: str) -> dict | None:
    """Verify API key against database.

    Args:
        api_key: API key to verify

    Returns:
        User data if valid, None otherwise
    """
    try:
        from supabase import create_client

        settings = get_settings()

        # Get Supabase credentials
        supabase_url = getattr(settings, "supabase_url", None)
        supabase_key = getattr(settings, "supabase_service_key", None) or getattr(
            settings, "supabase_anon_key", None
        )

        if not supabase_url or not supabase_key:
            return None

        client = create_client(supabase_url, supabase_key)

        # Hash the API key for lookup
        key_hash = hash_api_key(api_key)

        # Query database for API key
        response = (
            client.table("api_keys")
            .select("user_id, email, role, is_active, expires_at")
            .eq("key_hash", key_hash)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if not response.data:
            return None

        # Check expiration
        key_data = response.data
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"].replace("Z", "+00:00"))
            if expires_at < datetime.now(UTC):
                return None

        return key_data

    except Exception:
        # If database check fails, return None (deny access)
        return None


def verify_api_key(api_key: str) -> bool:
    """Verify API key format and cache (sync-safe, no database call).

    For full verification including database lookup, use verify_api_key_async().

    Args:
        api_key: API key to verify

    Returns:
        True if valid format and cached as valid, or auth is disabled
    """
    settings = get_settings()

    # Check prefix format
    if not api_key.startswith(settings.security.api_key_prefix):
        return False

    # Check minimum length
    if len(api_key) < settings.security.api_key_length:
        return False

    # Check cache first
    cache_key = hash_api_key(api_key)
    now = datetime.now(UTC)
    if cache_key in _api_key_cache:
        is_valid, cached_at = _api_key_cache[cache_key]
        if now - cached_at < _API_KEY_CACHE_TTL:
            return is_valid

    # If API auth is disabled (development mode), accept format-valid keys
    if not settings.features.enable_api_auth:
        _cache_put(cache_key, (True, now))
        return True

    # Cannot do async DB call from sync context safely.
    # Return False to force callers to use verify_api_key_async().
    return False


async def verify_api_key_async(api_key: str) -> tuple[bool, dict | None]:
    """Async version of API key verification.

    Args:
        api_key: API key to verify

    Returns:
        Tuple of (is_valid, user_data)
    """
    settings = get_settings()

    # Check format
    if not api_key.startswith(settings.security.api_key_prefix):
        return False, None

    if len(api_key) < settings.security.api_key_length:
        return False, None

    # Check cache
    cache_key = hash_api_key(api_key)
    if cache_key in _api_key_cache:
        is_valid, cached_at = _api_key_cache[cache_key]
        if datetime.now(UTC) - cached_at < _API_KEY_CACHE_TTL:
            return is_valid, None if not is_valid else {"cached": True}

    # Development mode bypass
    if not settings.features.enable_api_auth:
        _cache_put(cache_key, (True, datetime.now(UTC)))
        return True, {"user_id": "dev_user", "role": "admin", "email": "dev@local"}

    # Database verification
    user_data = await verify_api_key_from_db(api_key)
    is_valid = user_data is not None

    # Cache result
    _cache_put(cache_key, (is_valid, datetime.now(UTC)))

    return is_valid, user_data


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user_from_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    settings: Annotated[AppSettings, Depends(get_settings)] = None,
) -> User | None:
    """Get current user from JWT token.

    Returns None when no credentials are provided so that
    get_current_user can fall through to API key authentication.

    Args:
        credentials: Bearer token from Authorization header
        settings: App settings

    Returns:
        Current user or None if no token provided

    Raises:
        HTTPException: If token is present but invalid
    """
    if not credentials:
        return None

    try:
        token_data = verify_token(credentials.credentials, settings)

        # In production: fetch user from database
        # For now: create user from token data
        user = User(
            user_id=token_data.user_id,
            email=token_data.email,
            role=token_data.role,
        )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
            )

        return user

    except (InvalidTokenError, TokenExpiredError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_api_key(
    api_key: Annotated[str | None, Depends(api_key_scheme)] = None,
) -> User | None:
    """Get current user from API key.

    Returns None when no API key is provided so that
    get_current_user can fall through to JWT authentication.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Current user or None if no key provided

    Raises:
        HTTPException: If key is present but invalid
    """
    if not api_key:
        return None

    # Use async verification to get user data
    is_valid, user_data = await verify_api_key_async(api_key)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Create user from database data or default service user
    if user_data and not user_data.get("cached"):
        return User(
            user_id=user_data.get("user_id", "service"),
            email=user_data.get("email", "service@megaagent.com"),
            role=user_data.get("role", "service"),
            is_active=user_data.get("is_active", True),
        )

    # Fallback for cached or development mode
    return User(
        user_id="service",
        email="service@megaagent.com",
        role="service",
    )


async def get_current_user(
    token_user: Annotated[User | None, Depends(get_current_user_from_token)] = None,
    api_key_user: Annotated[User | None, Depends(get_current_user_from_api_key)] = None,
    settings: Annotated[AppSettings, Depends(get_settings)] = None,
) -> User:
    """Get current user from either JWT token or API key.

    Tries JWT first, then API key. If auth is disabled, returns a test user.

    Args:
        token_user: User from JWT token
        api_key_user: User from API key
        settings: App settings

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails and is required
    """
    # If auth is disabled (e.g., in development), return test user
    if not settings.features.enable_api_auth:
        return User(
            user_id="test_user",
            email="test@example.com",
            role="admin",
        )

    # Try JWT token first
    if token_user:
        return token_user

    # Then try API key
    if api_key_user:
        return api_key_user

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


# ============================================================================
# Role-Based Access Control
# ============================================================================


class RoleChecker:
    """Dependency for checking user roles.

    Example:
        @app.get("/admin")
        async def admin_only(user: User = Depends(RoleChecker(["admin"]))):
            return {"message": "Admin access granted"}
    """

    def __init__(self, allowed_roles: list[str]):
        """Initialize role checker.

        Args:
            allowed_roles: List of allowed role names
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        """Check if user has required role.

        Args:
            user: Current user

        Returns:
            User if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}",
            )
        return user


# Convenience dependencies for common roles
require_admin = RoleChecker(["admin"])
require_service = RoleChecker(["admin", "service"])
require_user = RoleChecker(["admin", "service", "user"])


# ============================================================================
# Optional Authentication
# ============================================================================


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    api_key: Annotated[str | None, Depends(api_key_scheme)] = None,
) -> User | None:
    """Get user if authenticated, None otherwise.

    Useful for endpoints that have different behavior for authenticated users.

    Args:
        credentials: Bearer token
        api_key: API key

    Returns:
        User if authenticated, None otherwise
    """
    try:
        if credentials:
            return await get_current_user_from_token(credentials)
        if api_key:
            return await get_current_user_from_api_key(api_key)
    except HTTPException:
        pass

    return None
