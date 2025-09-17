from __future__ import annotations

import asyncio
import os
from typing import Dict

from core.dto.llm_response import LLMResponse
from core.dto.task_request import TaskRequest
from .base import BaseLLMProvider, ProviderError


class OpenAIProvider(BaseLLMProvider):
    """Thin adapter around the OpenAI completion endpoint."""

    name = "openai"

    def __init__(self, api_key: str | None) -> None:
        super().__init__(api_key=api_key)

    async def acompletion(self, task: TaskRequest) -> LLMResponse:
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY is not configured")

        await asyncio.sleep(0.05)
        tokens_in = len(task.prompt.split())
        tokens_out = max(12, tokens_in // 2)
        latency_ms = 50.0
        cost_usd = (tokens_in + tokens_out) * 2.0e-6
        content = f"[openai] response to: {task.prompt[:200]}"
        return LLMResponse(
            request_id=os.urandom(8).hex(),
            text=content,
            provider=self.name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            metadata={"model": "gpt-4o-mini"},
        )

    def requires_api_key(self) -> bool:
        return True
