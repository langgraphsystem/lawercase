from __future__ import annotations

import asyncio
import os

from core.dto.llm_response import LLMResponse
from core.dto.task_request import TaskRequest
from .base import BaseLLMProvider, ProviderError


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None) -> None:
        super().__init__(api_key=api_key)

    async def acompletion(self, task: TaskRequest) -> LLMResponse:
        if not self._api_key:
            raise ProviderError("GEMINI_API_KEY is not configured")

        await asyncio.sleep(0.06)
        tokens_in = len(task.prompt.split())
        tokens_out = max(14, tokens_in // 4)
        latency_ms = 60.0
        cost_usd = (tokens_in + tokens_out) * 1.8e-6
        content = f"[gemini] response to: {task.prompt[:200]}"
        return LLMResponse(
            request_id=os.urandom(8).hex(),
            text=content,
            provider=self.name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            metadata={"model": "gemini-pro"},
        )

    def requires_api_key(self) -> bool:
        return True
