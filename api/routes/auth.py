"""Authentication endpoints for JWT-based login."""

from __future__ import annotations

from datetime import UTC, datetime
import os

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from api.deps import get_current_user
from core.security.config import SecurityConfig

router = APIRouter()

# Password hashing context
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User store - loaded from environment variables.
# In production, replace with database lookup (Supabase auth or users table).
# Format: DEMO_USERS_JSON='{"email":{"password_hash":"...","user_id":"...","roles":["..."]}}'
_demo_users: dict[str, dict] | None = None


def _load_users() -> dict[str, dict]:
    """Load users from environment or return empty dict.

    Users must be provisioned via DEMO_USER_PASSWORD env var (hashed at startup)
    or via a proper user database. No hardcoded credentials.
    """
    global _demo_users
    if _demo_users is not None:
        return _demo_users

    password = os.getenv("DEMO_USER_PASSWORD")
    if not password:
        _demo_users = {}
        return _demo_users

    hashed = _pwd_context.hash(password)
    _demo_users = {
        "admin@eb1a.com": {"password_hash": hashed, "user_id": "admin-001", "roles": ["admin"]},
        "lawyer@eb1a.com": {"password_hash": hashed, "user_id": "lawyer-001", "roles": ["lawyer"]},
        "client@eb1a.com": {"password_hash": hashed, "user_id": "client-001", "roles": ["viewer"]},
    }
    return _demo_users


# Token expiration
TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Login response with JWT token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    roles: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT token.

    Args:
        request: Login credentials (email, password)

    Returns:
        JWT access token with user info

    Raises:
        HTTPException: 401 if credentials invalid
    """
    users = _load_users()
    user = users.get(request.email)

    if not user or not _pwd_context.verify(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    config = SecurityConfig()
    from datetime import timedelta

    expires_delta = timedelta(hours=TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": user["user_id"],
        "user_id": user["user_id"],
        "email": request.email,
        "roles": user["roles"],
        "exp": expire,
        "iat": now,
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds()),
        user_id=user["user_id"],
        roles=user["roles"],
    )


@router.get("/me", deprecated=True)
async def get_current_user_info(claims: dict = Depends(get_current_user)) -> dict:
    """Get current user info from JWT token."""
    return {
        "user_id": claims.get("user_id") or claims.get("sub"),
        "email": claims.get("email"),
        "roles": claims.get("roles") or [],
        "issued_at": claims.get("iat"),
        "expires_at": claims.get("exp"),
    }
