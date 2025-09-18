"""Tests for content ingestion flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat


@pytest.fixture
def mock_message():
    """Mock Telegram message."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456789
    message.chat = MagicMock(spec=Chat)
    message.chat.id = -987654321
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_adapters():
    """Mock all required adapters."""
    with patch('interface.telegram.handlers.case_adapter') as case_adapter, \
         patch('interface.telegram.handlers.ingest_adapter') as ingest_adapter, \
         patch('interface.telegram.handlers.document_adapter') as doc_adapter:

        # Mock active case
        case_adapter.get_active_case.return_value = {
            'id': 'abc123',
            'title': 'Test Case'
        }

        yield {
            'case': case_adapter,
            'ingest': ingest_adapter,
            'document': doc_adapter
        }


class TestURLIngestion:
    """Test URL content ingestion."""

    @pytest.mark.asyncio
    async def test_learn_url_success(self, mock_message, mock_adapters):
        """Test successful URL ingestion."""
        from interface.telegram.handlers import cmd_learn_url

        mock_message.text = '/learn_url https://example.com/article title="Test Article" tags="legal,test"'

        # Mock successful ingestion
        mock_adapters['ingest'].ingest_url.return_value = {
            'success': True,
            'title': 'Test Article',
            'chunks_count': 5,
            'case_id': 'abc123'
        }

        # Mock status message
        status_msg = MagicMock()
        status_msg.edit_text = AsyncMock()
        mock_message.answer.return_value = status_msg

        await cmd_learn_url(mock_message)

        # Verify ingest adapter called with correct parameters
        mock_adapters['ingest'].ingest_url.assert_called_once()
        call_kwargs = mock_adapters['ingest'].ingest_url.call_args[1]
        assert call_kwargs['url'] == 'https://example.com/article'
        assert call_kwargs['case_id'] == 'abc123'
        assert call_kwargs['title'] == 'Test Article'
        assert call_kwargs['tags'] == ['legal', 'test']

        # Verify status messages
        mock_message.answer.assert_called_once_with("🔄 Изучаю веб-страницу...")
        status_msg.edit_text.assert_called_once()
        success_text = status_msg.edit_text.call_args[0][0]
        assert "Веб-страница изучена" in success_text
        assert "5" in success_text  # chunks count

    @pytest.mark.asyncio
    async def test_learn_url_no_active_case(self, mock_message, mock_adapters):
        """Test URL ingestion without active case."""
        from interface.telegram.handlers import cmd_learn_url

        mock_message.text = '/learn_url https://example.com/article'

        # Mock no active case
        mock_adapters['case'].get_active_case.return_value = None

        await cmd_learn_url(mock_message)

        # Should not call ingest
        mock_adapters['ingest'].ingest_url.assert_not_called()

        # Should show error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Нет активного дела" in call_args[0]

    @pytest.mark.asyncio
    async def test_learn_url_invalid_url(self, mock_message, mock_adapters):
        """Test URL ingestion with invalid URL."""
        from interface.telegram.handlers import cmd_learn_url

        mock_message.text = '/learn_url not-a-valid-url'

        await cmd_learn_url(mock_message)

        # Should not call ingest
        mock_adapters['ingest'].ingest_url.assert_not_called()

        # Should show error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0]
        assert "Некорректный URL" in call_args[0]


class TestYouTubeIngestion:
    """Test YouTube content ingestion."""

    @pytest.mark.asyncio
    async def test_learn_youtube_success(self, mock_message, mock_adapters):
        """Test successful YouTube ingestion."""
        from interface.telegram.handlers import cmd_learn_yt

        mock_message.text = '/learn_yt https://www.youtube.com/watch?v=abc123'

        # Mock successful ingestion
        mock_adapters['ingest'].ingest_youtube.return_value = {
            'success': True,
            'title': 'Test Video',
            'duration': '10:30',
            'chunks_count': 8,
            'case_id': 'abc123'
        }

        # Mock status message
        status_msg = MagicMock()
        status_msg.edit_text = AsyncMock()
        mock_message.answer.return_value = status_msg

        await cmd_learn_yt(mock_message)

        # Verify ingest adapter called
        mock_adapters['ingest'].ingest_youtube.assert_called_once_with(
            url='https://www.youtube.com/watch?v=abc123',
            case_id='abc123'
        )

        # Verify success message
        status_msg.edit_text.assert_called_once()
        success_text = status_msg.edit_text.call_args[0][0]
        assert "YouTube видео изучено" in success_text
        assert "Test Video" in success_text
        assert "10:30" in success_text


class TestDocumentProcessing:
    """Test document processing and indexing."""

    @pytest.mark.asyncio
    async def test_document_processing_calls_indexing(self, mock_adapters):
        """Test that document processing triggers indexing."""
        from interface.telegram.adapters import DocumentAdapter

        # Create real adapter instance (not mocked)
        doc_adapter = DocumentAdapter()

        with patch.object(doc_adapter, 's3_client') as mock_s3, \
             patch.object(doc_adapter, '_process_document_for_indexing') as mock_process, \
             patch.object(doc_adapter, 'documents_db', {}):

            # Mock S3 upload success
            mock_s3.upload_file = AsyncMock(return_value=True)
            mock_s3.calculate_sha256.return_value = "abc123hash"

            # Mock processing
            mock_process.return_value = None

            # Test document addition
            result = await doc_adapter.add_document(
                case_id="test_case",
                filename="test.pdf",
                content_type="application/pdf",
                file_data=b"fake pdf content",
                description="Test document"
            )

            # Verify success
            assert result['success'] is True
            assert 'document_id' in result

            # Verify S3 upload was called
            mock_s3.upload_file.assert_called_once()

            # Verify processing was triggered
            mock_process.assert_called_once()

            # Verify document metadata stored
            doc_id = result['document_id']
            assert doc_id in doc_adapter.documents_db
            doc_data = doc_adapter.documents_db[doc_id]
            assert doc_data['filename'] == "test.pdf"
            assert doc_data['case_id'] == "test_case"
            assert doc_data['hash'] == "abc123hash"

    @pytest.mark.asyncio
    async def test_text_content_indexing(self, mock_adapters):
        """Test text content indexing."""
        from interface.telegram.adapters import DocumentAdapter

        # Create real adapter instance
        doc_adapter = DocumentAdapter()

        with patch.object(doc_adapter, '_index_text_content') as mock_index, \
             patch.object(doc_adapter, 'documents_db', {}):

            # Mock indexing
            mock_index.return_value = None

            # Test text addition
            result = await doc_adapter.add_text_content(
                case_id="test_case",
                content="Important legal text content",
                title="Legal Note",
                user_id=123456789
            )

            # Verify success
            assert result['success'] is True
            assert 'document_id' in result

            # Verify indexing was called
            mock_index.assert_called_once()
            call_args = mock_index.call_args[0]
            assert call_args[1] == "Important legal text content"  # content
            assert call_args[2] == "test_case"  # case_id

            # Verify document stored
            doc_id = result['document_id']
            assert doc_id in doc_adapter.documents_db
            doc_data = doc_adapter.documents_db[doc_id]
            assert doc_data['content'] == "Important legal text content"
            assert doc_data['title'] == "Legal Note"
            assert doc_data['type'] == 'text'