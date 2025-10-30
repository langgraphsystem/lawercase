"""Authentication and authorization for API.

This module provides:
- JWT token generation and validation
- API key authentication
- Role-based access control (RBAC)
- User authentication dependencies
"""

from __future__ import annotations

from datetime import datetime, timedelta
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
    created_at: datetime = datetime.utcnow()


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

    expire = datetime.utcnow() + timedelta(minutes=settings.security.jwt_expiration_minutes)

    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
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

    expire = datetime.utcnow() + timedelta(days=settings.security.jwt_refresh_expiration_days)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
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


def verify_api_key(api_key: str) -> bool:
    """Verify API key.

    Args:
        api_key: API key to verify

    Returns:
        True if valid

    Note:
        In production, this should check against a database.
        For now, we'll use a simple validation.
    """
    settings = get_settings()

    # Check prefix
    if not api_key.startswith(settings.security.api_key_prefix):
        return False

    # In production: check database for valid key
    # For now: accept any key with correct prefix and length
    return len(api_key) >= settings.security.api_key_length


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user_from_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    settings: Annotated[AppSettings, Depends(get_settings)] = None,
) -> User:
    """Get current user from JWT token.

    Args:
        credentials: Bearer token from Authorization header
        settings: App settings

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
) -> User:
    """Get current user from API key.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # In production: fetch user associated with API key from database
    # For now: create a service user
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
