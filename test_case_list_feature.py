"""Quick smoke test for /case_list feature."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio()
async def test_case_list_handler_registration():
    """Test that case_list handler is properly registered."""
    from telegram_interface.handlers.case_handlers import get_handlers
    from telegram_interface.handlers.context import BotContext

    # Mock BotContext
    mock_context = MagicMock(spec=BotContext)

    # Get handlers
    handlers = get_handlers(mock_context)

    # Check that we have at least 5 handlers (including case_list)
    assert len(handlers) >= 5, f"Expected at least 5 handlers, got {len(handlers)}"

    # Find case_list handler
    case_list_handler = None
    for handler in handlers:
        if hasattr(handler, "callback") and hasattr(handler.callback, "__name__"):
            if handler.callback.__name__ == "case_list":
                case_list_handler = handler
                break

    assert case_list_handler is not None, "case_list handler not found in registered handlers"
    print("✅ case_list handler is properly registered")


@pytest.mark.asyncio()
async def test_case_list_help_text():
    """Test that /case_list is included in help text."""
    from telegram_interface.handlers.admin_handlers import HELP_TEXT

    assert "/case_list" in HELP_TEXT, "/case_list command missing from help text"
    assert "[page]" in HELP_TEXT, "page parameter not documented in help text"
    print("✅ /case_list is documented in help text")


@pytest.mark.asyncio()
async def test_case_list_basic_flow():
    """Test basic case_list flow with mocked dependencies."""
    from telegram import Chat, Message, Update, User
    from telegram.ext import ContextTypes

    from core.groupagents.mega_agent import MegaAgentResponse
    from telegram_interface.handlers.case_handlers import case_list

    # Create mock update
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.username = "testuser"

    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 12345

    mock_message = MagicMock(spec=Message)
    mock_message.reply_text = AsyncMock()

    mock_update = MagicMock(spec=Update)
    mock_update.effective_user = mock_user
    mock_update.effective_message = mock_message
    mock_update.effective_chat = mock_chat

    # Create mock context
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.args = []  # No page argument

    # Mock BotContext
    mock_bot_context = MagicMock()
    mock_bot_context.is_authorized = MagicMock(return_value=True)
    mock_bot_context.thread_id_for_update = MagicMock(return_value="thread_123")

    # Mock MegaAgent response
    mock_mega_agent = MagicMock()
    mock_response = MegaAgentResponse(
        command_id="cmd-123",
        success=True,
        result={
            "case_result": {
                "cases": [
                    {
                        "case_id": "case-123-abc",
                        "title": "Test EB-1A Petition",
                        "status": "draft",
                    },
                    {
                        "case_id": "case-456-def",
                        "title": "Test H-1B Application",
                        "status": "in_progress",
                    },
                ],
                "count": 2,
            }
        },
        metadata={},
    )
    mock_mega_agent.handle_command = AsyncMock(return_value=mock_response)
    mock_bot_context.mega_agent = mock_mega_agent

    mock_context.application.bot_data = {"bot_context": mock_bot_context}

    # Call the handler
    await case_list(mock_update, mock_context)

    # Verify message was sent
    mock_message.reply_text.assert_called_once()
    call_args = mock_message.reply_text.call_args
    message_text = call_args[1]["text"] if "text" in call_args[1] else call_args[0][0]

    # Check that response contains expected elements
    assert "Ваши кейсы" in message_text or "Your Cases" in message_text
    # Check for escaped version (MarkdownV2)
    assert "EB\\-1A" in message_text or "EB-1A" in message_text
    assert "draft" in message_text
    assert "in_progress" in message_text or "in\\_progress" in message_text
    print("✅ case_list basic flow works correctly")


@pytest.mark.asyncio()
async def test_case_list_empty_state():
    """Test case_list with no cases (empty state)."""
    from telegram import Message, Update, User
    from telegram.ext import ContextTypes

    from core.groupagents.mega_agent import MegaAgentResponse
    from telegram_interface.handlers.case_handlers import case_list

    # Create mock update
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345

    mock_message = MagicMock(spec=Message)
    mock_message.reply_text = AsyncMock()

    mock_update = MagicMock(spec=Update)
    mock_update.effective_user = mock_user
    mock_update.effective_message = mock_message

    # Create mock context
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.args = []

    # Mock BotContext
    mock_bot_context = MagicMock()
    mock_bot_context.is_authorized = MagicMock(return_value=True)
    mock_bot_context.thread_id_for_update = MagicMock(return_value="thread_123")

    # Mock MegaAgent response with no cases
    mock_mega_agent = MagicMock()
    mock_response = MegaAgentResponse(
        command_id="cmd-456",
        success=True,
        result={"case_result": {"cases": [], "count": 0}},
        metadata={},
    )
    mock_mega_agent.handle_command = AsyncMock(return_value=mock_response)
    mock_bot_context.mega_agent = mock_mega_agent

    mock_context.application.bot_data = {"bot_context": mock_bot_context}

    # Call the handler
    await case_list(mock_update, mock_context)

    # Verify empty state message
    mock_message.reply_text.assert_called_once()
    call_args = mock_message.reply_text.call_args
    message_text = call_args[1]["text"] if "text" in call_args[1] else call_args[0][0]

    assert "нет кейсов" in message_text or "no cases" in message_text.lower()
    assert "case_create" in message_text
    print("✅ case_list empty state works correctly")


if __name__ == "__main__":
    print("Running /case_list feature smoke tests...\n")

    asyncio.run(test_case_list_handler_registration())
    asyncio.run(test_case_list_help_text())
    asyncio.run(test_case_list_basic_flow())
    asyncio.run(test_case_list_empty_state())

    print("\n✅ All smoke tests passed!")
