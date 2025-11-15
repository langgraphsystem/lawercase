"""Tests for OpenAI GPT-5.1 client and function calling.

Verifies GPT-5.1 features:
- New model identifiers
- reasoning_effort="none"
- Extended prompt caching
- Function calling with tools
- Tool calls response handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm_interface.openai_client import OpenAIClient
from core.tools.tool_registry import ToolMetadata, ToolType, get_tool_registry, reset_tool_registry


class TestGPT51Models:
    """Test GPT-5.1 model support."""

    def test_default_model_is_gpt51_instant(self):
        """Default model should be gpt-5.1-chat-latest."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI"):
            client = OpenAIClient(api_key="test-key")
            assert client.model == "gpt-5.1-chat-latest"

    def test_gpt51_models_detection(self):
        """_is_gpt5_1_model() should detect GPT-5.1 models."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI"):
            # GPT-5.1 models
            for model in ["gpt-5.1-chat-latest", "gpt-5.1", "gpt-5.1-codex", "gpt-5.1-codex-mini"]:
                client = OpenAIClient(model=model, api_key="test-key")
                assert client._is_gpt5_1_model() is True

            # Non-GPT-5.1 models
            for model in ["gpt-5-2025-08-07", "gpt-5-mini", "gpt-5-nano", "o3-mini"]:
                client = OpenAIClient(model=model, api_key="test-key")
                assert client._is_gpt5_1_model() is False

    def test_reasoning_effort_none(self):
        """reasoning_effort='none' should be supported."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI"):
            client = OpenAIClient(
                model="gpt-5.1-chat-latest", reasoning_effort="none", api_key="test-key"
            )
            assert client.reasoning_effort == "none"

    def test_prompt_cache_retention(self):
        """prompt_cache_retention parameter should be stored."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI"):
            client = OpenAIClient(
                model="gpt-5.1-chat-latest", prompt_cache_retention="24h", api_key="test-key"
            )
            assert client.prompt_cache_retention == "24h"


class TestFunctionCalling:
    """Test function calling with tools parameter."""

    def test_tools_parameter_initialization(self):
        """Client should accept tools parameter."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI"):
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                            "required": ["location"],
                        },
                    },
                }
            ]

            client = OpenAIClient(
                model="gpt-5.1-chat-latest", tools=tools, tool_choice="auto", api_key="test-key"
            )

            assert client.tools == tools
            assert client.tool_choice == "auto"

    @pytest.mark.asyncio
    async def test_acomplete_with_tools_adds_to_request(self):
        """acomplete should add tools to API request."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mock
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            mock_response.model = "gpt-5.1-chat-latest"

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            # Create client with tools
            tools = [{"type": "function", "function": {"name": "test_tool"}}]
            client = OpenAIClient(model="gpt-5.1-chat-latest", tools=tools, api_key="test-key")

            # Call acomplete
            await client.acomplete("Test prompt")

            # Verify tools were added to request
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert "tools" in call_kwargs
            assert call_kwargs["tools"] == tools
            assert "tool_choice" in call_kwargs

    @pytest.mark.asyncio
    async def test_tool_calls_in_response(self):
        """Response should include tool_calls if present."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mock with tool calls
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_abc123"
            mock_tool_call.type = "function"
            mock_tool_call.function.name = "get_weather"
            mock_tool_call.function.arguments = '{"location": "San Francisco"}'

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None
            mock_response.choices[0].message.tool_calls = [mock_tool_call]
            mock_response.choices[0].finish_reason = "tool_calls"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            mock_response.model = "gpt-5.1-chat-latest"

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            # Create client
            client = OpenAIClient(model="gpt-5.1-chat-latest", api_key="test-key")

            # Call acomplete
            result = await client.acomplete("What's the weather?")

            # Verify tool_calls in response
            assert "tool_calls" in result
            assert result["requires_tool_execution"] is True
            assert len(result["tool_calls"]) == 1

            tool_call = result["tool_calls"][0]
            assert tool_call["id"] == "call_abc123"
            assert tool_call["type"] == "function"
            assert tool_call["function"]["name"] == "get_weather"
            assert tool_call["function"]["arguments"] == '{"location": "San Francisco"}'


class TestToolRegistry:
    """Test Tool Registry OpenAI format."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_tool_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_tool_registry()

    def test_get_tools_for_openai_function_type(self):
        """get_tools_for_openai should format function tools correctly."""
        registry = get_tool_registry()

        # Register a function tool
        async def test_tool(**kwargs):
            return {"result": "test"}

        registry.register(
            tool_id="test_function",
            tool=test_tool,
            metadata=ToolMetadata(
                name="test_function",
                description="Test function",
                tool_type=ToolType.FUNCTION,
                parameters={
                    "type": "object",
                    "properties": {"arg1": {"type": "string"}},
                    "required": ["arg1"],
                },
                strict=True,
                enabled=True,
            ),
        )

        # Get tools for OpenAI
        tools = registry.get_tools_for_openai()

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "test_function"
        assert tool["function"]["description"] == "Test function"
        assert tool["function"]["parameters"]["type"] == "object"
        assert tool["function"]["strict"] is True

    def test_get_tools_for_openai_builtin_types(self):
        """get_tools_for_openai should format built-in tools correctly."""
        registry = get_tool_registry()

        # Register built-in tools (no executor needed)
        for tool_type in [ToolType.FILE_SEARCH, ToolType.WEB_SEARCH, ToolType.CODE_INTERPRETER]:

            async def dummy_tool(**kwargs):
                pass

            registry.register(
                tool_id=f"builtin_{tool_type.value}",
                tool=dummy_tool,
                metadata=ToolMetadata(
                    name=f"builtin_{tool_type.value}",
                    description=f"Built-in {tool_type.value}",
                    tool_type=tool_type,
                    enabled=True,
                ),
            )

        # Get tools for OpenAI
        tools = registry.get_tools_for_openai()

        assert len(tools) == 3
        assert {"type": "file_search"} in tools
        assert {"type": "web_search"} in tools
        assert {"type": "code_interpreter"} in tools

    def test_get_tools_for_openai_rbac_filtering(self):
        """get_tools_for_openai should filter by role."""
        registry = get_tool_registry()

        # Register tool with role restriction
        async def admin_tool(**kwargs):
            return {}

        registry.register(
            tool_id="admin_only",
            tool=admin_tool,
            metadata=ToolMetadata(
                name="admin_only",
                description="Admin only tool",
                tool_type=ToolType.FUNCTION,
                allowed_roles={"admin"},
                enabled=True,
            ),
        )

        # Get tools for admin - should include tool
        tools_admin = registry.get_tools_for_openai(role="admin")
        assert len(tools_admin) == 1

        # Get tools for lawyer - should not include tool
        tools_lawyer = registry.get_tools_for_openai(role="lawyer")
        assert len(tools_lawyer) == 0

    def test_get_tools_for_openai_disabled_filtering(self):
        """get_tools_for_openai should exclude disabled tools."""
        registry = get_tool_registry()

        # Register disabled tool
        async def disabled_tool(**kwargs):
            return {}

        registry.register(
            tool_id="disabled",
            tool=disabled_tool,
            metadata=ToolMetadata(
                name="disabled",
                description="Disabled tool",
                tool_type=ToolType.FUNCTION,
                enabled=False,  # Disabled!
            ),
        )

        # Get tools - should not include disabled tool
        tools = registry.get_tools_for_openai()
        assert len(tools) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
