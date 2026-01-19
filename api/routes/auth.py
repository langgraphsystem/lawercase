"""Authentication endpoints for JWT-based login."""

from __future__ import annotations

from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr

from api.deps import get_current_user
from core.security.config import SecurityConfig

router = APIRouter()

# Demo users for MVP - replace with database lookup in production
# Passwords loaded from environment or use defaults for local dev
_DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "demo1234")

DEMO_USERS: dict[str, dict] = {
    "admin@eb1a.com": {"password": _DEMO_PASSWORD, "user_id": "admin-001", "roles": ["admin"]},
    "lawyer@eb1a.com": {"password": _DEMO_PASSWORD, "user_id": "lawyer-001", "roles": ["lawyer"]},
    "client@eb1a.com": {"password": _DEMO_PASSWORD, "user_id": "client-001", "roles": ["viewer"]},
}

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
    user = DEMO_USERS.get(request.email)

    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    config = SecurityConfig()
    expires_delta = timedelta(hours=TOKEN_EXPIRE_HOURS)
    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": user["user_id"],
        "user_id": user["user_id"],
        "email": request.email,
        "roles": user["roles"],
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds()),
        user_id=user["user_id"],
        roles=user["roles"],
    )


@router.get("/me")
async def get_current_user_info(claims: dict = Depends(get_current_user)) -> dict:
    """Get current user info from JWT token."""
    return {
        "user_id": claims.get("user_id") or claims.get("sub"),
        "email": claims.get("email"),
        "roles": claims.get("roles") or [],
        "issued_at": claims.get("iat"),
        "expires_at": claims.get("exp"),
    }
