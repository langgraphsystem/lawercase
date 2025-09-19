"""Tests for the LLM Router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# Make sure the path is correct to import the router
from core.llm.router import BudgetExhaustedError, LLMProvider, LLMRouter


@pytest.fixture
def mock_openai_provider():
    """Fixture for a mocked OpenAI provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "OpenAI"
    provider.cost_per_token = 0.002
    provider.ainvoke = AsyncMock()
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """Fixture for a mocked Anthropic provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "Anthropic"
    provider.cost_per_token = 0.001
    provider.ainvoke = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_router_budget_exhaustion(mock_openai_provider):
    """
    Tests that the router raises BudgetExhaustedError when the budget is depleted.
    """
    # Arrange: High cost, low budget
    mock_openai_provider.cost_per_token = 0.5
    mock_openai_provider.ainvoke.return_value = {"text": "response", "tokens_used": 3}

    router = LLMRouter(providers=[mock_openai_provider], initial_budget=1.0)

    # Act & Assert
    with pytest.raises(BudgetExhaustedError):
        # This call should succeed (cost = 3 * 0.5 = 1.5, budget = 1.0 -> error)
        await router.ainvoke("This request will exhaust the budget")

    # Verify the budget was not spent and no call was made if budget was insufficient from the start
    assert router.budget == 1.0

    # Arrange 2: Make one successful call, then fail on the second
    router.budget = 2.0
    await router.ainvoke("First request")
    assert router.budget == 0.5  # 2.0 - 1.5 = 0.5

    with pytest.raises(BudgetExhaustedError):
        await router.ainvoke("Second request, should fail")

    assert router.budget == 0.5  # Budget remains unchanged on failed call


@pytest.mark.asyncio
async def test_router_provider_fallback(mock_openai_provider, mock_anthropic_provider):
    """
    Tests that the router falls back to the next provider if the primary one fails.
    """
    # Arrange: OpenAI fails, Anthropic succeeds
    mock_openai_provider.ainvoke.side_effect = ConnectionError("OpenAI is down")
    mock_anthropic_provider.ainvoke.return_value = {
        "text": "Hello from Anthropic",
        "tokens_used": 4,
    }

    router = LLMRouter(
        providers=[mock_openai_provider, mock_anthropic_provider],
        max_retries=1,  # No retries, just fallback
    )

    # Act
    result = await router.ainvoke("A prompt")

    # Assert
    mock_openai_provider.ainvoke.assert_called_once_with("A prompt")
    mock_anthropic_provider.ainvoke.assert_called_once_with("A prompt")
    assert result["provider"] == "Anthropic"
    assert result["response"] == "Hello from Anthropic"
    assert result["cost"] == 4 * 0.001


@pytest.mark.asyncio
async def test_router_retry_with_exponential_backoff(mocker, mock_openai_provider):
    """
    Tests that the router retries with exponential backoff on connection errors.
    """
    # Arrange
    # Mock asyncio.sleep to avoid waiting in tests and to check its call arguments
    mock_sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    # Simulate 2 failures then 1 success
    mock_openai_provider.ainvoke.side_effect = [
        ConnectionError("Network glitch"),
        ConnectionError("Network glitch again"),
        {"text": "Finally succeeded", "tokens_used": 3},
    ]

    router = LLMRouter(
        providers=[mock_openai_provider],
        max_retries=3,
        backoff_factor=0.1,  # Use a small factor for predictable testing
    )

    # Act
    result = await router.ainvoke("A prompt")

    # Assert
    # Check that ainvoke was called 3 times (2 failures + 1 success)
    assert mock_openai_provider.ainvoke.call_count == 3

    # Check that sleep was called with increasing backoff times
    assert mock_sleep.call_count == 2
    # 1st retry sleep: 0.1 * (2 ** 0) = 0.1
    mock_sleep.assert_any_call(0.1)
    # 2nd retry sleep: 0.1 * (2 ** 1) = 0.2
    mock_sleep.assert_any_call(0.2)

    assert result["provider"] == "OpenAI"
    assert result["response"] == "Finally succeeded"


@pytest.mark.asyncio
async def test_router_all_providers_fail(mock_openai_provider, mock_anthropic_provider):
    """
    Tests that the router raises the last exception if all providers fail.
    """
    # Arrange
    mock_openai_provider.ainvoke.side_effect = ConnectionError("OpenAI is down")
    mock_anthropic_provider.ainvoke.side_effect = ValueError("Anthropic has an invalid key")

    router = LLMRouter(providers=[mock_openai_provider, mock_anthropic_provider], max_retries=1)

    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        await router.ainvoke("A prompt")

    # The last exception (from Anthropic) should be raised
    assert "invalid key" in str(excinfo.value)
