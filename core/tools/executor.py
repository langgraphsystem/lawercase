"""Tool execution loop for multi-turn LLM conversations.

Handles automatic tool calling workflow:
1. LLM requests tool execution
2. Execute tools via registry
3. Feed results back to LLM
4. Repeat until final answer

Based on OpenAI function calling API (March 2025).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from core.llm_interface.openai_client import OpenAIClient
from core.tools.tool_registry import ToolRegistry, get_tool_registry

logger = structlog.get_logger(__name__)


class ToolExecutionError(Exception):
    """Error during tool execution."""


async def execute_tool_loop(
    client: OpenAIClient,
    initial_prompt: str,
    tools: list[dict[str, Any]],
    *,
    max_iterations: int = 5,
    registry: ToolRegistry | None = None,
    caller_role: str = "admin",
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute LLM with tool calling loop.

    Handles:
    1. Initial LLM call with tools
    2. Tool execution when LLM requests it
    3. Feeding results back to LLM
    4. Final answer extraction

    Args:
        client: OpenAI client instance
        initial_prompt: Initial user prompt
        tools: List of available tools (OpenAI format)
        max_iterations: Maximum tool calling iterations (default: 5)
        registry: Tool registry for execution (default: global registry)
        caller_role: User role for RBAC (default: "admin")
        conversation_history: Optional existing conversation history

    Returns:
        dict with keys:
            - output: Final text response
            - tool_calls_made: List of tool calls executed
            - iterations: Number of iterations
            - conversation_history: Full conversation
            - finish_reason: How the loop ended

    Raises:
        ToolExecutionError: If max iterations exceeded or tool execution fails
    """
    registry = registry or get_tool_registry()

    # Initialize conversation history
    if conversation_history is None:
        messages = [{"role": "user", "content": initial_prompt}]
    else:
        messages = list(conversation_history)
        messages.append({"role": "user", "content": initial_prompt})

    tool_calls_made = []
    iteration = 0

    logger.info(
        "tool.loop.start",
        model=client.model,
        num_tools=len(tools),
        max_iterations=max_iterations,
        caller_role=caller_role,
    )

    while iteration < max_iterations:
        iteration += 1

        logger.debug(
            "tool.loop.iteration",
            iteration=iteration,
            message_count=len(messages),
        )

        # Call LLM with current conversation
        try:
            # Convert messages to simple prompt for OpenAI client
            # (In production, would use full messages API)
            if len(messages) == 1:
                prompt = messages[0]["content"]
            else:
                # Concatenate conversation for simple prompt format
                prompt = "\n\n".join(
                    [
                        f"{msg['role'].upper()}: {msg.get('content', '[tool call]')}"
                        for msg in messages
                    ]
                )

            response = await client.acomplete(
                prompt=prompt,
                tools=tools,
                tool_choice="auto",
            )

        except Exception as e:
            logger.exception(
                "tool.loop.llm_error",
                iteration=iteration,
                error=str(e),
            )
            raise ToolExecutionError(f"LLM call failed: {e}") from e

        # Check if LLM wants to call tools
        if not response.get("requires_tool_execution"):
            # LLM provided final answer
            logger.info(
                "tool.loop.complete",
                iterations=iteration,
                num_tool_calls=len(tool_calls_made),
                finish_reason=response.get("finish_reason", "stop"),
            )

            return {
                "output": response.get("output", ""),
                "tool_calls_made": tool_calls_made,
                "iterations": iteration,
                "conversation_history": messages,
                "finish_reason": response.get("finish_reason", "stop"),
                "usage": response.get("usage", {}),
            }

        # Execute tool calls
        tool_calls = response.get("tool_calls", [])

        logger.info(
            "tool.loop.executing_tools",
            iteration=iteration,
            num_tools=len(tool_calls),
            tools=[tc["function"]["name"] for tc in tool_calls],
        )

        # Add assistant message with tool calls
        messages.append(
            {
                "role": "assistant",
                "content": response.get("output", ""),
                "tool_calls": tool_calls,
            }
        )

        # Execute each tool call
        for tool_call in tool_calls:
            tool_id = tool_call["id"]
            func_name = tool_call["function"]["name"]
            arguments_str = tool_call["function"]["arguments"]

            try:
                # Parse arguments
                arguments = json.loads(arguments_str)

                logger.debug(
                    "tool.loop.executing",
                    tool_id=tool_id,
                    function=func_name,
                    arguments=arguments,
                )

                # Execute tool
                tool_result = await registry.invoke(
                    tool_id=func_name,
                    caller_role=caller_role,
                    arguments=arguments,
                )

                # Record successful execution
                tool_calls_made.append(
                    {
                        "id": tool_id,
                        "function": func_name,
                        "arguments": arguments,
                        "result": tool_result,
                        "status": "success",
                    }
                )

                # Add tool result to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps(tool_result),
                    }
                )

                logger.info(
                    "tool.loop.executed",
                    tool_id=tool_id,
                    function=func_name,
                    success=True,
                )

            except json.JSONDecodeError as e:
                logger.error(
                    "tool.loop.json_error",
                    tool_id=tool_id,
                    function=func_name,
                    arguments_str=arguments_str,
                    error=str(e),
                )

                # Add error result to conversation
                error_msg = f"Error parsing arguments: {e}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps({"error": error_msg}),
                    }
                )

                tool_calls_made.append(
                    {
                        "id": tool_id,
                        "function": func_name,
                        "arguments": arguments_str,
                        "error": error_msg,
                        "status": "error",
                    }
                )

            except KeyError as e:
                logger.error(
                    "tool.loop.not_found",
                    tool_id=tool_id,
                    function=func_name,
                    error=str(e),
                )

                # Tool not found in registry
                error_msg = f"Tool '{func_name}' not found"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps({"error": error_msg}),
                    }
                )

                tool_calls_made.append(
                    {
                        "id": tool_id,
                        "function": func_name,
                        "arguments": arguments,
                        "error": error_msg,
                        "status": "error",
                    }
                )

            except PermissionError as e:
                logger.error(
                    "tool.loop.permission_denied",
                    tool_id=tool_id,
                    function=func_name,
                    caller_role=caller_role,
                    error=str(e),
                )

                # Permission denied
                error_msg = f"Permission denied: {e}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps({"error": error_msg}),
                    }
                )

                tool_calls_made.append(
                    {
                        "id": tool_id,
                        "function": func_name,
                        "arguments": arguments,
                        "error": error_msg,
                        "status": "error",
                    }
                )

            except Exception as e:
                logger.exception(
                    "tool.loop.execution_error",
                    tool_id=tool_id,
                    function=func_name,
                    error=str(e),
                )

                # Generic execution error
                error_msg = f"Execution error: {e}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": json.dumps({"error": error_msg}),
                    }
                )

                tool_calls_made.append(
                    {
                        "id": tool_id,
                        "function": func_name,
                        "arguments": arguments,
                        "error": error_msg,
                        "status": "error",
                    }
                )

        # Continue loop with tool results

    # Max iterations reached
    logger.warning(
        "tool.loop.max_iterations",
        max_iterations=max_iterations,
        num_tool_calls=len(tool_calls_made),
    )

    raise ToolExecutionError(f"Maximum iterations ({max_iterations}) exceeded without final answer")


async def execute_single_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    registry: ToolRegistry | None = None,
    caller_role: str = "admin",
) -> dict[str, Any]:
    """Execute a single tool without LLM loop.

    Convenience function for direct tool execution.

    Args:
        tool_name: Tool identifier
        arguments: Tool arguments
        registry: Tool registry (default: global)
        caller_role: User role for RBAC

    Returns:
        Tool execution result

    Raises:
        KeyError: If tool not found
        PermissionError: If caller lacks permission
        ToolExecutionError: If execution fails
    """
    registry = registry or get_tool_registry()

    logger.info(
        "tool.execute_single",
        tool=tool_name,
        arguments=arguments,
        caller_role=caller_role,
    )

    try:
        result = await registry.invoke(
            tool_id=tool_name,
            caller_role=caller_role,
            arguments=arguments,
        )

        logger.info(
            "tool.execute_single.success",
            tool=tool_name,
        )

        return {"result": result, "status": "success"}

    except Exception as e:
        logger.exception(
            "tool.execute_single.error",
            tool=tool_name,
            error=str(e),
        )

        return {
            "error": str(e),
            "status": "error",
        }
