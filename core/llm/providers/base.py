from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.dto.llm_response import LLMResponse
from core.dto.task_request import TaskRequest


class ProviderError(RuntimeError):
    """Base provider error."""


class ProviderRateLimitError(ProviderError):
    """Raised when the provider throttles the request (HTTP 429)."""


class ProviderTransientError(ProviderError):
    """Raised on transient provider failures (HTTP 5xx)."""


class ProviderTimeoutError(ProviderError):
    """Raised when the provider exceeds timeout constraints."""


class BaseLLMProvider(ABC):
    """Abstract provider contract used by the LLM router."""

    name: str

    def __init__(self, *, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @abstractmethod
    async def acompletion(self, task: TaskRequest) -> LLMResponse:
        """Execute a completion request and return a normalized response."""

    def requires_api_key(self) -> bool:
        """Flag providers that must be configured before use."""

        return True
