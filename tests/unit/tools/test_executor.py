"""Tests for tool execution loop.

Verifies multi-turn tool calling workflow with OpenAI function calling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm_interface.openai_client import OpenAIClient
from core.tools.executor import (ToolExecutionError, execute_single_tool,
                                 execute_tool_loop)
from core.tools.tool_registry import (ToolMetadata, ToolType,
                                      get_tool_registry, reset_tool_registry)


class TestExecuteSingleTool:
    """Test single tool execution."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_tool_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_tool_registry()

    @pytest.mark.asyncio
    async def test_execute_single_tool_success(self):
        """execute_single_tool should execute tool and return result."""
        registry = get_tool_registry()

        # Register mock tool
        async def mock_tool(arg1: str) -> dict:
            return {"result": f"processed_{arg1}"}

        registry.register(
            tool_id="test_tool",
            tool=mock_tool,
            metadata=ToolMetadata(
                name="test_tool",
                description="Test tool",
                tool_type=ToolType.FUNCTION,
                enabled=True,
            ),
        )

        # Execute tool
        result = await execute_single_tool(
            tool_name="test_tool",
            arguments={"arg1": "test"},
            caller_role="admin",
        )

        assert result["status"] == "success"
        assert result["result"] == {"result": "processed_test"}

    @pytest.mark.asyncio
    async def test_execute_single_tool_not_found(self):
        """execute_single_tool should handle tool not found."""
        result = await execute_single_tool(
            tool_name="nonexistent",
            arguments={},
            caller_role="admin",
        )

        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_single_tool_permission_denied(self):
        """execute_single_tool should handle permission errors."""
        registry = get_tool_registry()

        # Register tool with role restriction
        async def admin_tool() -> dict:
            return {"result": "admin_data"}

        registry.register(
            tool_id="admin_only",
            tool=admin_tool,
            metadata=ToolMetadata(
                name="admin_only",
                description="Admin only",
                tool_type=ToolType.FUNCTION,
                allowed_roles={"admin"},
                enabled=True,
            ),
        )

        # Try to execute as non-admin
        result = await execute_single_tool(
            tool_name="admin_only",
            arguments={},
            caller_role="client",  # Not admin!
        )

        assert result["status"] == "error"
        assert "error" in result


class TestExecuteToolLoop:
    """Test multi-turn tool execution loop."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_tool_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_tool_registry()

    @pytest.mark.asyncio
    async def test_execute_tool_loop_no_tools_needed(self):
        """execute_tool_loop should handle responses without tool calls."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mocks
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Direct answer"
            mock_response.choices[0].message.tool_calls = None
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            mock_response.model = "gpt-5.1"

            # Return same response every time (using return_value, not side_effect)
            mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            # Create client and execute
            client = OpenAIClient(api_key="test-key")

            result = await execute_tool_loop(
                client=client,
                initial_prompt="Hello",
                tools=[],
            )

            assert result["iterations"] >= 1
            assert result["finish_reason"] == "stop"
            assert len(result["tool_calls_made"]) == 0
            assert "output" in result

    @pytest.mark.asyncio
    async def test_execute_tool_loop_single_tool_call(self):
        """execute_tool_loop should execute single tool and get final answer."""
        registry = get_tool_registry()

        # Register mock tool
        async def get_weather(location: str) -> dict:
            return {"location": location, "temperature": 72, "conditions": "sunny"}

        registry.register(
            tool_id="get_weather",
            tool=get_weather,
            metadata=ToolMetadata(
                name="get_weather",
                description="Get weather",
                tool_type=ToolType.FUNCTION,
                parameters={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
                enabled=True,
            ),
        )

        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mocks
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            # First call: LLM requests tool
            mock_response_1 = MagicMock()
            mock_response_1.choices = [MagicMock()]
            mock_response_1.choices[0].message.content = None

            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_123"
            mock_tool_call.type = "function"
            mock_tool_call.function.name = "get_weather"
            mock_tool_call.function.arguments = '{"location": "San Francisco"}'

            mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
            mock_response_1.choices[0].finish_reason = "tool_calls"
            mock_response_1.usage = MagicMock(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            )
            mock_response_1.model = "gpt-5.1"

            # Second call: LLM provides final answer
            mock_response_2 = MagicMock()
            mock_response_2.choices = [MagicMock()]
            mock_response_2.choices[0].message.content = (
                "The weather in San Francisco is sunny and 72°F"
            )
            mock_response_2.choices[0].message.tool_calls = None
            mock_response_2.choices[0].finish_reason = "stop"
            mock_response_2.usage = MagicMock(
                prompt_tokens=20, completion_tokens=10, total_tokens=30
            )
            mock_response_2.model = "gpt-5.1"

            mock_client_instance.chat.completions.create = AsyncMock(
                side_effect=[mock_response_1, mock_response_2]
            )

            # Create client and execute
            client = OpenAIClient(api_key="test-key")

            tools = registry.get_tools_for_openai()

            result = await execute_tool_loop(
                client=client,
                initial_prompt="What's the weather in San Francisco?",
                tools=tools,
                caller_role="admin",
            )

            assert result["iterations"] == 2
            assert len(result["tool_calls_made"]) == 1
            assert result["tool_calls_made"][0]["function"] == "get_weather"
            assert result["tool_calls_made"][0]["status"] == "success"
            assert "The weather" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_tool_loop_max_iterations(self):
        """execute_tool_loop should raise error if max iterations exceeded."""
        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mocks - always return tool calls
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_123"
            mock_tool_call.type = "function"
            mock_tool_call.function.name = "dummy"
            mock_tool_call.function.arguments = "{}"

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None
            mock_response.choices[0].message.tool_calls = [mock_tool_call]
            mock_response.choices[0].finish_reason = "tool_calls"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            mock_response.model = "gpt-5.1"

            mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            # Create client
            client = OpenAIClient(api_key="test-key")

            # Execute with low max_iterations
            with pytest.raises(ToolExecutionError) as exc_info:
                await execute_tool_loop(
                    client=client,
                    initial_prompt="Test",
                    tools=[],
                    max_iterations=2,
                )

            assert "Maximum iterations" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_tool_loop_tool_error_handling(self):
        """execute_tool_loop should handle tool execution errors gracefully."""
        registry = get_tool_registry()

        # Register tool that raises error
        async def broken_tool() -> dict:
            raise RuntimeError("Tool broken!")

        registry.register(
            tool_id="broken",
            tool=broken_tool,
            metadata=ToolMetadata(
                name="broken",
                description="Broken tool",
                tool_type=ToolType.FUNCTION,
                enabled=True,
            ),
        )

        with patch("core.llm_interface.openai_client.AsyncOpenAI") as mock_openai:
            # Setup mocks
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            # First call: LLM requests broken tool
            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_123"
            mock_tool_call.type = "function"
            mock_tool_call.function.name = "broken"
            mock_tool_call.function.arguments = "{}"

            mock_response_1 = MagicMock()
            mock_response_1.choices = [MagicMock()]
            mock_response_1.choices[0].message.content = None
            mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
            mock_response_1.choices[0].finish_reason = "tool_calls"
            mock_response_1.usage = MagicMock(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            )
            mock_response_1.model = "gpt-5.1"

            # Second call: LLM acknowledges error
            mock_response_2 = MagicMock()
            mock_response_2.choices = [MagicMock()]
            mock_response_2.choices[0].message.content = "Tool encountered an error"
            mock_response_2.choices[0].message.tool_calls = None
            mock_response_2.choices[0].finish_reason = "stop"
            mock_response_2.usage = MagicMock(
                prompt_tokens=20, completion_tokens=10, total_tokens=30
            )
            mock_response_2.model = "gpt-5.1"

            mock_client_instance.chat.completions.create = AsyncMock(
                side_effect=[mock_response_1, mock_response_2]
            )

            # Create client
            client = OpenAIClient(api_key="test-key")

            tools = registry.get_tools_for_openai()

            result = await execute_tool_loop(
                client=client,
                initial_prompt="Call broken tool",
                tools=tools,
                caller_role="admin",
            )

            # Should complete despite tool error
            assert result["iterations"] == 2
            assert len(result["tool_calls_made"]) == 1
            assert result["tool_calls_made"][0]["status"] == "error"
            assert "error" in result["tool_calls_made"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
