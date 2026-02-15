"""
AG-UI Middleware and FastAPI Router for SSE streaming.

Provides HTTP endpoints for AG-UI protocol integration.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, Field
import structlog

from core.security.config import SecurityConfig

from .adapter import get_agui_adapter
from .events import AGUIEvent

logger = structlog.get_logger(__name__)

# FastAPI Router for AG-UI endpoints
router = APIRouter(prefix="/agui", tags=["AG-UI Protocol"])
auth_scheme = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    secret = (os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or "").strip()
    if not secret:
        secret = (SecurityConfig().jwt_secret_key or "").strip()
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret is not configured")
    return secret


def _jwt_algorithm() -> str:
    return (os.getenv("JWT_ALGORITHM") or "HS256").strip() or "HS256"


def _decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return payload


def verify_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(auth_scheme),
) -> dict[str, Any]:
    """Validate JWT from Authorization Bearer header."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return _decode_token(credentials.credentials)


def verify_jwt_from_header(authorization_header: str | None) -> dict[str, Any]:
    """Validate JWT from a raw Authorization header value."""
    if not authorization_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return _decode_token(token)


def get_token_user_id(claims: dict[str, Any]) -> str | None:
    user_id = claims.get("user_id") or claims.get("sub")
    return str(user_id) if user_id else None


def get_token_role(claims: dict[str, Any]) -> str:
    role = claims.get("role")
    if isinstance(role, str) and role.strip():
        return role.strip().lower()

    roles = claims.get("roles")
    if isinstance(roles, list) and roles:
        first_role = roles[0]
        if isinstance(first_role, str) and first_role.strip():
            return first_role.strip().lower()

    return ""


def require_role(role: str):
    """Dependency factory that enforces a specific role from JWT payload."""
    expected_role = role.strip().lower()

    def _enforce(claims: dict[str, Any] = Depends(verify_jwt)) -> dict[str, Any]:
        token_role = get_token_role(claims)
        if token_role != expected_role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return claims

    return _enforce


class AGUIRunRequest(BaseModel):
    """Request body for AG-UI workflow run."""

    case_id: str = Field(..., description="Case identifier")
    operation: str = Field(..., description="Workflow operation")
    data: dict[str, Any] | None = Field(default=None, description="Input data")
    user_id: str | None = Field(default=None, description="User identifier")


class AGUIAgentRequest(BaseModel):
    """Request body for AG-UI agent invocation."""

    agent_name: str = Field(..., description="Agent name to invoke")
    prompt: str = Field(..., description="User prompt")
    case_id: str | None = Field(default=None, description="Optional case ID")


class AGUIValidationRequest(BaseModel):
    """Request body for validation submission."""

    validation_id: str = Field(..., description="Validation request ID")
    approved: bool = Field(..., description="Approval status")
    feedback: str | None = Field(default=None, description="Optional feedback")


class AGUIMiddleware:
    """
    Middleware for AG-UI protocol integration.

    Can be used to wrap existing FastAPI apps with AG-UI support.
    """

    def __init__(self, app: Any):
        self.app = app
        self._adapter = get_agui_adapter()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """ASGI middleware interface."""
        # Pass through to main app - AG-UI endpoints handled by router
        await self.app(scope, receive, send)


@router.post("/run", response_class=StreamingResponse)
async def run_workflow(
    request: AGUIRunRequest, user_claims: dict[str, Any] = Depends(verify_jwt)
) -> StreamingResponse:
    """
    Execute workflow with AG-UI event streaming.

    Returns Server-Sent Events stream of AG-UI events.
    """
    adapter = get_agui_adapter()
    token_user_id = get_token_user_id(user_claims)
    if request.user_id and token_user_id and request.user_id != token_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    effective_user_id = request.user_id or token_user_id

    async def event_generator():
        """Generate SSE events from workflow execution."""
        try:
            async for event in adapter.run_workflow(
                case_id=request.case_id,
                operation=request.operation,
                data=request.data,
                user_id=effective_user_id,
            ):
                yield event.to_sse()
        except Exception as e:
            logger.exception("agui.run.error", error=str(e))
            error_event = AGUIEvent.run_error(error=str(e))
            yield error_event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/agent", response_class=StreamingResponse)
async def invoke_agent(
    request: AGUIAgentRequest, user_claims: dict[str, Any] = Depends(verify_jwt)
) -> StreamingResponse:
    """
    Invoke single agent with AG-UI event streaming.

    Returns Server-Sent Events stream of agent response.
    """
    adapter = get_agui_adapter()
    _ = user_claims

    async def event_generator():
        """Generate SSE events from agent response."""
        try:
            async for event in adapter.stream_agent_response(
                agent_name=request.agent_name,
                prompt=request.prompt,
                case_id=request.case_id,
            ):
                yield event.to_sse()
        except Exception as e:
            logger.exception("agui.agent.error", error=str(e))
            error_event = AGUIEvent.run_error(error=str(e))
            yield error_event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/validation/submit")
async def submit_validation(
    request: AGUIValidationRequest, user_claims: dict[str, Any] = Depends(verify_jwt)
) -> dict[str, Any]:
    """
    Submit human validation result.

    Called by frontend when user approves/rejects a validation request.
    """
    adapter = get_agui_adapter()
    _ = user_claims

    success = adapter.submit_validation_result(
        validation_id=request.validation_id,
        approved=request.approved,
        feedback=request.feedback,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Validation request not found: {request.validation_id}",
        )

    return {
        "status": "ok",
        "validation_id": request.validation_id,
        "approved": request.approved,
    }


@router.get("/health")
async def agui_health() -> dict[str, str]:
    """AG-UI endpoint health check."""
    return {"status": "ok", "protocol": "AG-UI", "version": "1.0"}


# WebSocket alternative for bi-directional communication
try:
    from fastapi import WebSocket, WebSocketDisconnect

    @router.websocket("/ws/{case_id}")
    async def agui_websocket(websocket: WebSocket, case_id: str):
        """
        WebSocket endpoint for bi-directional AG-UI communication.

        Supports both streaming events and receiving user input.
        """
        try:
            _ = verify_jwt_from_header(websocket.headers.get("authorization"))
        except HTTPException as exc:
            close_code = 4401 if exc.status_code == 401 else 4403
            await websocket.close(code=close_code)
            return

        await websocket.accept()
        adapter = get_agui_adapter()

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                operation = data.get("operation", "query")
                user_input = data.get("input", "")

                # Stream response back
                async for event in adapter.run_workflow(
                    case_id=case_id,
                    operation=operation,
                    data={"query": user_input, **data.get("data", {})},
                ):
                    await websocket.send_text(event.to_json())

        except WebSocketDisconnect:
            logger.info("agui.websocket.disconnected", case_id=case_id)
        except Exception as e:
            logger.exception("agui.websocket.error", case_id=case_id, error=str(e))
            error_event = AGUIEvent.run_error(error=str(e), case_id=case_id)
            try:
                await websocket.send_text(error_event.to_json())
            except Exception:  # nosec B110 - ignore send error on already-failed ws
                pass

except ImportError:
    # WebSocket not available
    pass


def include_agui_router(app: Any) -> None:
    """
    Include AG-UI router in FastAPI application.

    Usage:
        from core.agui.middleware import include_agui_router
        include_agui_router(app)
    """
    app.include_router(router)
    logger.info("agui.router.included", prefix="/agui")
