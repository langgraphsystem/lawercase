"""Smoke tests for Telegram bot commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat, Document


@pytest.fixture
def mock_message():
    """Mock Telegram message."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -987654321
    message.answer = AsyncMock()
    message.bot = MagicMock()
    return message


@pytest.fixture
def mock_adapters():
    """Mock all adapters."""
    with patch('interface.telegram.handlers.case_adapter') as case_adapter, \
         patch('interface.telegram.handlers.document_adapter') as doc_adapter, \
         patch('interface.telegram.handlers.ingest_adapter') as ingest_adapter, \
         patch('interface.telegram.handlers.rag_adapter') as rag_adapter, \
         patch('interface.telegram.handlers.health_adapter') as health_adapter, \
         patch('interface.telegram.handlers.admin_adapter') as admin_adapter:

        yield {
            'case': case_adapter,
            'document': doc_adapter,
            'ingest': ingest_adapter,
            'rag': rag_adapter,
            'health': health_adapter,
            'admin': admin_adapter
        }


class TestBasicCommands:
    """Test basic bot commands."""

    @pytest.mark.asyncio
    async def test_start_command(self, mock_message, mock_adapters):
        """Test /start command."""
        from interface.telegram.handlers import cmd_start
        from aiogram.fsm.context import FSMContext

        mock_state = MagicMock(spec=FSMContext)
        mock_state.clear = AsyncMock()

        await cmd_start(mock_message, mock_state)

        mock_state.clear.assert_called_once()
        mock_message.answer.assert_called_once()

        # Check welcome message content
        call_args = mock_message.answer.call_args[0]
        assert "Добро пожаловать" in call_args[0]
        assert "/case_new" in call_args[0]

    @pytest.mark.asyncio
    async def test_help_command(self, mock_message, mock_adapters):
        """Test /help command."""
        from interface.telegram.handlers import cmd_help

        await cmd_help(mock_message)

        mock_message.answer.assert_called_once()

        # Check help content
        call_args = mock_message.answer.call_args[0]
        assert "Справка" in call_args[0]
        assert "/case_new" in call_args[0]
        assert "/ask" in call_args[0]


class TestCaseManagement:
    """Test case management commands."""

    @pytest.mark.asyncio
    async def test_case_new_success(self, mock_message, mock_adapters):
        """Test successful case creation."""
        from interface.telegram.handlers import cmd_case_new
        from aiogram.fsm.context import FSMContext

        mock_message.text = "/case_new Test Case Title"
        mock_state = MagicMock(spec=FSMContext)

        # Mock successful case creation
        mock_adapters['case'].create_case.return_value = "abc123"

        await cmd_case_new(mock_message, mock_state)

        # Verify adapter was called with correct parameters
        mock_adapters['case'].create_case.assert_called_once_with(
            title="Test Case Title",
            user_id=123456789,
            chat_id=-987654321
        )

        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Дело создано" in call_args[0]
        assert "abc123" in call_args[0]

    @pytest.mark.asyncio
    async def test_case_new_no_title(self, mock_message, mock_adapters):
        """Test case creation without title."""
        from interface.telegram.handlers import cmd_case_new
        from aiogram.fsm.context import FSMContext

        mock_message.text = "/case_new"
        mock_state = MagicMock(spec=FSMContext)

        await cmd_case_new(mock_message, mock_state)

        # Should not call adapter
        mock_adapters['case'].create_case.assert_not_called()

        # Should show usage instructions
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Введите название" in call_args[0]

    @pytest.mark.asyncio
    async def test_case_use_success(self, mock_message, mock_adapters):
        """Test successful case selection."""
        from interface.telegram.handlers import cmd_case_use

        mock_message.text = "/case_use abc123"

        # Mock case found
        mock_adapters['case'].get_case.return_value = {
            'id': 'abc123',
            'title': 'Test Case',
            'status': 'active',
            'document_count': 5
        }
        mock_adapters['case'].set_active_case.return_value = True

        await cmd_case_use(mock_message)

        # Verify adapter calls
        mock_adapters['case'].get_case.assert_called_once_with(
            identifier="abc123",
            user_id=123456789
        )
        mock_adapters['case'].set_active_case.assert_called_once_with(
            chat_id=-987654321,
            case_id='abc123'
        )

        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Активное дело выбрано" in call_args[0]


class TestDocumentHandling:
    """Test document upload and processing."""

    @pytest.mark.asyncio
    async def test_document_upload(self, mock_message, mock_adapters):
        """Test document file upload."""
        from interface.telegram.handlers import handle_document_upload

        # Mock document
        mock_message.document = MagicMock(spec=Document)
        mock_message.document.file_name = "test.pdf"
        mock_message.document.mime_type = "application/pdf"
        mock_message.document.file_size = 1024 * 1024  # 1MB
        mock_message.document.file_id = "file123"
        mock_message.caption = "Test document"

        # Mock file download
        mock_message.bot.get_file = AsyncMock()
        mock_message.bot.download_file = AsyncMock()
        mock_file_data = MagicMock()
        mock_file_data.read.return_value = b"fake pdf content"
        mock_message.bot.download_file.return_value = mock_file_data

        # Mock successful document processing
        mock_adapters['document'].add_document.return_value = {
            'success': True,
            'document_id': 'doc123'
        }

        case_id = "abc123"
        await handle_document_upload(mock_message, case_id)

        # Verify document adapter was called
        mock_adapters['document'].add_document.assert_called_once()
        call_args = mock_adapters['document'].add_document.call_args[1]
        assert call_args['case_id'] == case_id
        assert call_args['filename'] == "test.pdf"
        assert call_args['content_type'] == "application/pdf"
        assert call_args['description'] == "Test document"

        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Документ добавлен" in call_args[0]


class TestAICommands:
    """Test AI-powered commands."""

    @pytest.mark.asyncio
    async def test_ask_command_success(self, mock_message, mock_adapters):
        """Test successful AI question."""
        from interface.telegram.handlers import cmd_ask

        mock_message.text = "/ask What documents are needed?"
        mock_message.bot.send_chat_action = AsyncMock()

        # Mock active case
        mock_adapters['case'].get_active_case.return_value = {
            'id': 'abc123',
            'title': 'Test Case'
        }

        # Mock RAG response
        mock_adapters['rag'].ask_question.return_value = {
            'success': True,
            'answer': 'You need these documents: passport, certificate...',
            'sources': [
                {'title': 'Legal Guide', 'url': 'https://example.com'},
                {'title': 'Document List', 'url': ''}
            ],
            'conversation_id': 'conv123'
        }

        await cmd_ask(mock_message)

        # Verify typing indicator
        mock_message.bot.send_chat_action.assert_called_once_with(
            mock_message.chat.id, "typing"
        )

        # Verify RAG adapter call
        mock_adapters['rag'].ask_question.assert_called_once_with(
            question="What documents are needed?",
            case_id='abc123',
            user_id=123456789
        )

        # Verify response with sources
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "You need these documents" in call_args[0]
        assert "Источники" in call_args[0]
        assert "Legal Guide" in call_args[0]

    @pytest.mark.asyncio
    async def test_ask_no_active_case(self, mock_message, mock_adapters):
        """Test ask command without active case."""
        from interface.telegram.handlers import cmd_ask

        mock_message.text = "/ask What documents are needed?"

        # Mock no active case
        mock_adapters['case'].get_active_case.return_value = None

        await cmd_ask(mock_message)

        # Should not call RAG
        mock_adapters['rag'].ask_question.assert_not_called()

        # Should show error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Нет активного дела" in call_args[0]


class TestStatusCommand:
    """Test system status command."""

    @pytest.mark.asyncio
    async def test_status_command(self, mock_message, mock_adapters):
        """Test status command."""
        from interface.telegram.handlers import cmd_status

        # Mock system status
        mock_adapters['health'].get_system_status.return_value = {
            'db': 'ok',
            'vector': 'ok',
            'llm': 'degraded',
            'queue': 5,
            'cases_count': 150,
            'documents_count': 750
        }

        await cmd_status(mock_message)

        # Verify health adapter call
        mock_adapters['health'].get_system_status.assert_called_once()

        # Verify status message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Статус системы" in call_args[0]
        assert "✅" in call_args[0]  # OK status icon
        assert "⚠️" in call_args[0]  # Degraded status icon
        assert "150" in call_args[0]  # Cases count