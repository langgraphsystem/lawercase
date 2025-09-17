import pytest

from core.dto.task_request import TaskRequest
from core.dto.route_policy import RoutePolicy
from core.llm.router import LLMRouter, RouterExhaustedError
from core.llm.providers.base import BaseLLMProvider, ProviderError, ProviderRateLimitError
from core.dto.llm_response import LLMResponse


class FlakyProvider(BaseLLMProvider):
    name = "flaky"

    def __init__(self) -> None:
        super().__init__(api_key="dummy")
        self.calls = 0

    async def acompletion(self, task: TaskRequest) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            raise ProviderRateLimitError("rate limited")
        return LLMResponse(
            request_id="req-flaky",
            text="flaky-response",
            provider=self.name,
            tokens_in=5,
            tokens_out=5,
            cost_usd=0.0001,
            latency_ms=20.0,
        )

    def requires_api_key(self) -> bool:
        return False


class FailingProvider(BaseLLMProvider):
    name = "failing"

    def __init__(self) -> None:
        super().__init__(api_key="dummy")

    async def acompletion(self, task: TaskRequest) -> LLMResponse:
        raise ProviderError("hard failure")

    def requires_api_key(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_router_retries_and_succeeds():
    router = LLMRouter()
    router.register_provider(FlakyProvider())
    task = TaskRequest(prompt="Hello")
    policy = RoutePolicy(provider_priority=["flaky"], max_retries=2)
    response = await router.invoke(task, policy)
    assert response.text == "flaky-response"


@pytest.mark.asyncio
async def test_router_fallback():
    router = LLMRouter()
    router.register_provider(FailingProvider())
    router.register_provider(FlakyProvider())
    task = TaskRequest(prompt="Hello")
    policy = RoutePolicy(provider_priority=["failing", "flaky"], max_retries=1)
    response = await router.invoke(task, policy)
    assert response.provider == "flaky"


@pytest.mark.asyncio
async def test_router_exhausted():
    router = LLMRouter()
    router.register_provider(FailingProvider())
    task = TaskRequest(prompt="Hello")
    policy = RoutePolicy(provider_priority=["failing"], max_retries=0)
    with pytest.raises(RouterExhaustedError):
        await router.invoke(task, policy)
