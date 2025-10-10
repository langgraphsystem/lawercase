from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from core.groupagents.mega_agent import MegaAgent, UserRole
from core.memory.memory_manager_v2 import (
    create_dev_memory_manager,
    create_production_memory_manager,
)
from core.security.config import SecurityConfig

auth_scheme = HTTPBearer(auto_error=True)


def get_security_config() -> SecurityConfig:
    return SecurityConfig()


def get_memory_manager():
    # Toggle by env: USE_PROD_MEMORY=true
    import os

    use_prod = os.getenv("USE_PROD_MEMORY", "false").lower() == "true"
    if use_prod:
        return create_production_memory_manager(namespace=os.getenv("PINECONE_NAMESPACE") or None)
    return create_dev_memory_manager()


_agent_singleton: MegaAgent | None = None


def get_agent() -> MegaAgent:
    global _agent_singleton
    if _agent_singleton is None:
        _agent_singleton = MegaAgent(memory_manager=get_memory_manager())
    return _agent_singleton


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
    config: SecurityConfig = Depends(get_security_config),
) -> dict[str, Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")


def map_role(claims: dict[str, Any]) -> UserRole:
    roles = claims.get("roles") or []
    role = (roles[0] if roles else "viewer").lower()
    try:
        return UserRole(role)
    except Exception:
        return UserRole.VIEWER


def require_role(*allowed: UserRole):
    def _inner(claims: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        role = map_role(claims)
        if allowed and role not in allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
        return {"claims": claims, "role": role}

    return _inner
