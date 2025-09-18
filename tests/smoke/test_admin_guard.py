"""Tests for admin access control."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat


@pytest.fixture
def mock_admin_message():
    """Mock message from admin user."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789  # Admin user ID
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -987654321
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_regular_message():
    """Mock message from regular user."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 987654321  # Regular user ID
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -987654321
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_settings():
    """Mock settings with admin user ID."""
    with patch('interface.telegram.handlers.get_settings') as mock_get_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.telegram_admin_user_id = 123456789
        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj


class TestAdminGuard:
    """Test admin access control."""

    @pytest.mark.asyncio
    async def test_admin_can_access_admin_commands(self, mock_admin_message, mock_settings):
        """Test that admin user can access admin commands."""
        from interface.telegram.handlers import cmd_admin

        mock_admin_message.text = "/admin"

        with patch('interface.telegram.handlers.admin_adapter') as mock_admin_adapter:
            await cmd_admin(mock_admin_message)

        # Should show admin menu, not access denied
        mock_admin_message.answer.assert_called_once()
        call_args = mock_admin_message.answer.call_args[0]
        assert "Административные команды" in call_args[0]
        assert "Недостаточно прав" not in call_args[0]

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_admin_commands(self, mock_regular_message, mock_settings):
        """Test that regular user cannot access admin commands."""
        from interface.telegram.handlers import cmd_admin

        mock_regular_message.text = "/admin"

        with patch('interface.telegram.handlers.admin_adapter') as mock_admin_adapter:
            await cmd_admin(mock_regular_message)

        # Should show access denied message
        mock_regular_message.answer.assert_called_once()
        call_args = mock_regular_message.answer.call_args[0]
        assert "Недостаточно прав" in call_args[0]

    @pytest.mark.asyncio
    async def test_admin_subcommands_require_admin(self, mock_regular_message, mock_settings):
        """Test that admin subcommands also require admin access."""
        from interface.telegram.handlers import cmd_admin

        mock_regular_message.text = "/admin providers"

        await cmd_admin(mock_regular_message)

        # Should show access denied, not execute subcommand
        mock_regular_message.answer.assert_called_once()
        call_args = mock_regular_message.answer.call_args[0]
        assert "Недостаточно прав" in call_args[0]

    def test_is_admin_function(self, mock_settings):
        """Test is_admin helper function."""
        from interface.telegram.handlers import is_admin

        # Admin user
        assert is_admin(123456789) is True

        # Regular user
        assert is_admin(987654321) is False

        # Unknown user
        assert is_admin(111111111) is False

    def test_is_admin_no_admin_configured(self):
        """Test is_admin when no admin is configured."""
        with patch('interface.telegram.handlers.get_settings') as mock_get_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.telegram_admin_user_id = None
            mock_get_settings.return_value = mock_settings_obj

            from interface.telegram.handlers import is_admin

            # No one should be admin if not configured
            assert is_admin(123456789) is False
            assert is_admin(987654321) is False