"""
AG-UI Middleware and FastAPI Router for SSE streaming.

Provides HTTP endpoints for AG-UI protocol integration.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .adapter import get_agui_adapter
from .events import AGUIEvent

logger = structlog.get_logger(__name__)

# FastAPI Router for AG-UI endpoints
router = APIRouter(prefix="/agui", tags=["AG-UI Protocol"])


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
async def run_workflow(request: AGUIRunRequest) -> StreamingResponse:
    """
    Execute workflow with AG-UI event streaming.

    Returns Server-Sent Events stream of AG-UI events.
    """
    adapter = get_agui_adapter()

    async def event_generator():
        """Generate SSE events from workflow execution."""
        try:
            async for event in adapter.run_workflow(
                case_id=request.case_id,
                operation=request.operation,
                data=request.data,
                user_id=request.user_id,
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
async def invoke_agent(request: AGUIAgentRequest) -> StreamingResponse:
    """
    Invoke single agent with AG-UI event streaming.

    Returns Server-Sent Events stream of agent response.
    """
    adapter = get_agui_adapter()

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
async def submit_validation(request: AGUIValidationRequest) -> dict[str, Any]:
    """
    Submit human validation result.

    Called by frontend when user approves/rejects a validation request.
    """
    adapter = get_agui_adapter()

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
