"""LLM API endpoints with streaming support.

Provides REST API for LLM generation:
- POST /generate - Non-streaming generation
- POST /generate/stream - Server-Sent Events streaming
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.llm import (
    LLMProvider,
    Message,
    ResponseGenerator,
    create_response_generator,
)
from core.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class MessageRequest(BaseModel):
    """Chat message in request."""

    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")


class GenerateRequest(BaseModel):
    """Request for LLM generation."""

    messages: list[MessageRequest] = Field(..., description="Chat messages")
    model: str = Field(default="gpt-4o-mini", description="Model identifier")
    provider: str = Field(default="openai", description="LLM provider")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    stream: bool = Field(default=False, description="Enable streaming")
    context: dict[str, Any] | None = Field(default=None, description="RAG context to include")


class GenerateResponse(BaseModel):
    """Response from LLM generation."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    finish_reason: str = "stop"


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_provider(provider_str: str) -> LLMProvider:
    """Parse provider string to enum."""
    provider_map = {
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
        "google": LLMProvider.GOOGLE,
    }
    provider = provider_map.get(provider_str.lower())
    if not provider:
        raise ValueError(f"Unknown provider: {provider_str}")
    return provider


def _create_generator(request: GenerateRequest) -> ResponseGenerator:
    """Create response generator from request."""
    provider = _parse_provider(request.provider)
    return create_response_generator(
        provider=provider,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/generate", response_model=GenerateResponse, tags=["LLM"])
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate LLM response.

    Non-streaming endpoint for single response generation.

    Args:
        request: Generation request with messages and configuration

    Returns:
        Generated response with metadata

    Example:
        POST /api/v1/llm/generate
        {
            "messages": [
                {"role": "user", "content": "What is EB-1A visa?"}
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.7
        }
    """
    try:
        generator = _create_generator(request)

        messages = [Message(role=msg.role, content=msg.content) for msg in request.messages]

        result = await generator.generate(
            messages=messages,
            context=request.context,
        )

        return GenerateResponse(
            content=result.content,
            model=result.model,
            provider=result.provider.value,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            latency_ms=result.latency_ms,
            cached=result.cached,
            finish_reason=result.finish_reason,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("generation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generation failed",
        ) from e


@router.post("/generate/stream", tags=["LLM"])
async def generate_stream(request: GenerateRequest) -> StreamingResponse:
    """Generate streaming LLM response.

    Server-Sent Events (SSE) endpoint for streaming responses.

    Args:
        request: Generation request with messages and configuration

    Returns:
        StreamingResponse with SSE events

    Example:
        POST /api/v1/llm/generate/stream
        {
            "messages": [
                {"role": "user", "content": "Explain EB-1A requirements"}
            ],
            "model": "gpt-4o-mini",
            "stream": true
        }

    SSE Format:
        data: {"content": "The ", "index": 0, "is_final": false}
        data: {"content": "EB-1A", "index": 1, "is_final": false}
        ...
        data: {"content": "", "index": 50, "is_final": true, "finish_reason": "stop"}
        data: [DONE]
    """
    import json

    async def event_generator():
        """Generate SSE events."""
        try:
            generator = _create_generator(request)

            messages = [Message(role=msg.role, content=msg.content) for msg in request.messages]

            async for chunk in generator.generate_stream(
                messages=messages,
                context=request.context,
            ):
                event_data = {
                    "content": chunk.content,
                    "index": chunk.index,
                    "is_final": chunk.is_final,
                }
                if chunk.finish_reason:
                    event_data["finish_reason"] = chunk.finish_reason

                yield f"data: {json.dumps(event_data)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("stream_generation_failed", error=str(e))
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models", tags=["LLM"])
async def list_models() -> dict[str, Any]:
    """List available LLM models by provider.

    Returns:
        Dictionary of providers and their available models
    """
    return {
        "providers": {
            "openai": {
                "models": [
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-4-turbo",
                    "gpt-4",
                    "gpt-3.5-turbo",
                ],
                "default": "gpt-4o-mini",
            },
            "anthropic": {
                "models": [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                ],
                "default": "claude-3-5-sonnet-20241022",
            },
            "google": {
                "models": [
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemini-pro",
                ],
                "default": "gemini-1.5-flash",
            },
        }
    }


@router.get("/stats", tags=["LLM"])
async def get_stats() -> dict[str, Any]:
    """Get LLM generation statistics.

    Returns:
        Statistics about LLM usage
    """
    # Create a temporary generator to get stats
    # In production, this would be a singleton or stored globally
    return {
        "message": "Statistics tracking requires persistent generator instance",
        "note": "Use MetricsCollector for production statistics",
    }
