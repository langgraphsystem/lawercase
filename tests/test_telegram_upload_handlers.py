"""
Comprehensive tests for Telegram upload handlers.

Covers:
- telegram_interface/handlers/file_upload_handlers.py (PDF upload + callback)
- telegram_interface/handlers/smart_upload_handlers.py (smart AI-classified upload)
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Lightweight stubs so we can import the handler modules without pulling in
# real Telegram / heavy dependencies that are hard to install in CI.
# ---------------------------------------------------------------------------


@dataclass
class _FakeIngestionResult:
    document_id: str = "doc-001"
    file_name: str = "test.pdf"
    page_count: int = 5
    chunks_count: int = 10
    records_created: int = 10
    detected_criteria: list = None
    criteria_counts: dict = None

    def __post_init__(self):
        if self.detected_criteria is None:
            self.detected_criteria = ["eb1a_awards"]
        if self.criteria_counts is None:
            self.criteria_counts = {"eb1a_awards": 3}


# ---------------------------------------------------------------------------
# Helpers to build mock Telegram objects
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 12345):
    user = MagicMock()
    user.id = user_id
    return user


def _make_document(file_name: str = "test.pdf", file_size: int = 1_000_000, file_id: str = "file-abc"):
    doc = MagicMock()
    doc.file_name = file_name
    doc.file_size = file_size
    doc.file_id = file_id
    doc.mime_type = "application/pdf"
    return doc


def _make_message(document=None, photo=None, message_id: int = 1):
    msg = MagicMock()
    msg.document = document
    msg.photo = photo
    msg.message_id = message_id
    msg.reply_text = AsyncMock()
    return msg


def _make_update(user=None, message=None, callback_query=None):
    update = MagicMock()
    update.effective_user = user or _make_user()
    update.effective_message = message
    update.message = message
    update.callback_query = callback_query
    update.effective_chat = MagicMock()
    update.effective_chat.id = 999
    return update


def _make_callback_query(data: str = "pdf_knowledge"):
    q = MagicMock()
    q.data = data
    q.answer = AsyncMock()
    q.edit_message_text = AsyncMock()
    q.message = MagicMock()
    q.message.reply_text = AsyncMock()
    return q


def _make_context(user_data: dict | None = None, bot_context: MagicMock | None = None):
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    ctx.application = MagicMock()
    ctx.application.bot_data = {"bot_context": bot_context or _make_bot_context()}
    ctx.bot = MagicMock()
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"%PDF-1.4 fake content"))
    ctx.bot.get_file = AsyncMock(return_value=tg_file)
    return ctx


def _make_bot_context(authorized: bool = True, active_case: str | None = None, has_memory: bool = True):
    bot_ctx = MagicMock()
    bot_ctx.is_authorized = MagicMock(return_value=authorized)
    bot_ctx.get_active_case = AsyncMock(return_value=active_case)

    mega_agent = MagicMock()
    if has_memory:
        mega_agent.memory = MagicMock()
        mega_agent.memory.awrite = AsyncMock()
    else:
        mega_agent.memory = None

    bot_ctx.mega_agent = mega_agent
    return bot_ctx


# ============================================================================
# FILE UPLOAD HANDLERS TESTS
# ============================================================================


class TestHandlePdfDocument:
    """Tests for handle_pdf_document."""

    @pytest.mark.asyncio
    async def test_valid_pdf_shows_keyboard(self):
        """1. Valid PDF received -> shows inline keyboard for Knowledge vs Case."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_document

        doc = _make_document(file_name="evidence.pdf", file_size=5_000_000)
        msg = _make_message(document=doc)
        update = _make_update(message=msg)
        ctx = _make_context()

        await handle_pdf_document(update, ctx)

        msg.reply_text.assert_awaited_once()
        call_kwargs = msg.reply_text.call_args
        # Should include the file name in the response
        assert "evidence.pdf" in call_kwargs.args[0]
        # Should provide reply_markup (InlineKeyboardMarkup)
        assert "reply_markup" in call_kwargs.kwargs
        # Should store pending_pdf in user_data
        assert "pending_pdf" in ctx.user_data
        assert ctx.user_data["pending_pdf"]["file_id"] == "file-abc"

    @pytest.mark.asyncio
    async def test_non_pdf_rejected(self):
        """2. Non-PDF file (.docx) is rejected with error message."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_document

        doc = _make_document(file_name="resume.docx")
        msg = _make_message(document=doc)
        update = _make_update(message=msg)
        ctx = _make_context()

        await handle_pdf_document(update, ctx)

        msg.reply_text.assert_awaited_once()
        text = msg.reply_text.call_args.args[0]
        assert "pdf" in text.lower() or "PDF" in text
        # Should NOT store pending_pdf
        assert "pending_pdf" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(self):
        """3. File > 20 MB is rejected."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_document

        doc = _make_document(file_name="huge.pdf", file_size=25 * 1024 * 1024)
        msg = _make_message(document=doc)
        update = _make_update(message=msg)
        ctx = _make_context()

        await handle_pdf_document(update, ctx)

        msg.reply_text.assert_awaited_once()
        text = msg.reply_text.call_args.args[0]
        assert "20" in text  # mentions 20 MB limit
        assert "pending_pdf" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_no_document_returns_early(self):
        """4. No document attached -> returns immediately without reply."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_document

        msg = _make_message(document=None)
        update = _make_update(message=msg)
        ctx = _make_context()

        await handle_pdf_document(update, ctx)

        msg.reply_text.assert_not_awaited()


class TestHandlePdfCallback:
    """Tests for handle_pdf_callback."""

    @pytest.mark.asyncio
    async def test_knowledge_mode_processes(self):
        """5. CALLBACK_KNOWLEDGE triggers ingestion with no case_id."""
        from telegram_interface.handlers.file_upload_handlers import (
            CALLBACK_KNOWLEDGE,
            handle_pdf_callback,
        )

        bot_ctx = _make_bot_context(active_case=None)
        query = _make_callback_query(data=CALLBACK_KNOWLEDGE)
        update = _make_update(callback_query=query)
        ctx = _make_context(
            user_data={
                "pending_pdf": {
                    "file_id": "file-abc",
                    "file_name": "knowledge.pdf",
                    "file_size_mb": 1.5,
                    "message_id": 1,
                }
            },
            bot_context=bot_ctx,
        )

        fake_result = _FakeIngestionResult()

        with patch(
            "telegram_interface.handlers.file_upload_handlers.PDFIngestionService"
        ) as mock_service:
            instance = mock_service.return_value
            instance.ingest_bytes = AsyncMock(return_value=fake_result)

            await handle_pdf_callback(update, ctx)

        query.answer.assert_awaited_once()
        # Should have called edit_message_text at least twice (processing + result)
        assert query.edit_message_text.await_count >= 2
        # pending_pdf should be cleared
        assert "pending_pdf" not in ctx.user_data
        # ingestion was called with case_id=None (knowledge mode)
        call_kwargs = instance.ingest_bytes.call_args.kwargs
        assert call_kwargs.get("case_id") is None

    @pytest.mark.asyncio
    async def test_case_mode_with_active_case(self):
        """6. CALLBACK_CASE with active case passes case_id to ingestion."""
        from telegram_interface.handlers.file_upload_handlers import (
            CALLBACK_CASE,
            handle_pdf_callback,
        )

        bot_ctx = _make_bot_context(active_case="case-xyz-123")
        query = _make_callback_query(data=CALLBACK_CASE)
        update = _make_update(callback_query=query)
        ctx = _make_context(
            user_data={
                "pending_pdf": {
                    "file_id": "file-abc",
                    "file_name": "evidence.pdf",
                    "file_size_mb": 2.0,
                    "message_id": 2,
                }
            },
            bot_context=bot_ctx,
        )

        fake_result = _FakeIngestionResult()

        with patch(
            "telegram_interface.handlers.file_upload_handlers.PDFIngestionService"
        ) as mock_service:
            instance = mock_service.return_value
            instance.ingest_bytes = AsyncMock(return_value=fake_result)

            await handle_pdf_callback(update, ctx)

        call_kwargs = instance.ingest_bytes.call_args.kwargs
        assert call_kwargs.get("case_id") == "case-xyz-123"

    @pytest.mark.asyncio
    async def test_no_pending_pdf_shows_error(self):
        """7. No pending_pdf in user_data -> shows error message."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_callback

        query = _make_callback_query(data="pdf_knowledge")
        update = _make_update(callback_query=query)
        ctx = _make_context(user_data={})  # no pending_pdf

        await handle_pdf_callback(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        text = query.edit_message_text.call_args.args[0]
        assert "не найден" in text.lower() or "не найден" in text

    @pytest.mark.asyncio
    async def test_ingestion_error_handled(self):
        """8. Exception during ingestion is caught and reported."""
        from telegram_interface.handlers.file_upload_handlers import handle_pdf_callback

        bot_ctx = _make_bot_context()
        query = _make_callback_query(data="pdf_knowledge")
        update = _make_update(callback_query=query)
        ctx = _make_context(
            user_data={
                "pending_pdf": {
                    "file_id": "file-abc",
                    "file_name": "bad.pdf",
                    "file_size_mb": 1.0,
                    "message_id": 3,
                }
            },
            bot_context=bot_ctx,
        )

        with patch(
            "telegram_interface.handlers.file_upload_handlers.PDFIngestionService"
        ) as mock_service:
            instance = mock_service.return_value
            instance.ingest_bytes = AsyncMock(side_effect=RuntimeError("parse failed"))

            await handle_pdf_callback(update, ctx)

        # Last call to edit_message_text should contain error indicator
        last_text = query.edit_message_text.call_args.args[0]
        assert "ошибк" in last_text.lower() or "parse failed" in last_text.lower()


class TestFormatCriterionName:
    """Tests for _format_criterion_name."""

    def test_known_tags(self):
        """9. Known EB-1A tags return human-readable names."""
        from telegram_interface.handlers.file_upload_handlers import _format_criterion_name

        assert "Awards" in _format_criterion_name("eb1a_awards")
        assert "Membership" in _format_criterion_name("eb1a_membership")
        assert "Press" in _format_criterion_name("eb1a_press")
        assert "Judging" in _format_criterion_name("eb1a_judging")
        assert "Contribution" in _format_criterion_name("eb1a_contribution")
        assert "Scholarly" in _format_criterion_name("eb1a_scholarly")
        assert "Leading Role" in _format_criterion_name("eb1a_leadership")
        assert "Salary" in _format_criterion_name("eb1a_salary")
        assert "Commercial" in _format_criterion_name("eb1a_commercial")

    def test_unknown_tag_returns_raw(self):
        """10. Unknown tag is returned as-is."""
        from telegram_interface.handlers.file_upload_handlers import _format_criterion_name

        assert _format_criterion_name("something_else") == "something_else"
        assert _format_criterion_name("") == ""


class TestGetMemoryManager:
    """Tests for _get_memory_manager."""

    def test_from_mega_agent(self):
        """11. Returns mega_agent.memory when available."""
        from telegram_interface.handlers.file_upload_handlers import _get_memory_manager

        bot_ctx = _make_bot_context(has_memory=True)
        result = _get_memory_manager(bot_ctx)
        assert result is bot_ctx.mega_agent.memory

    def test_fallback_to_di_container(self):
        """12. Falls back to DI container when mega_agent.memory is None."""
        from telegram_interface.handlers.file_upload_handlers import _get_memory_manager

        bot_ctx = _make_bot_context(has_memory=False)

        fake_manager = MagicMock()
        with patch(
            "core.di.container.get_container"
        ) as mock_get_container:
            container = MagicMock()
            container.get.return_value = fake_manager
            mock_get_container.return_value = container

            result = _get_memory_manager(bot_ctx)

        assert result is fake_manager
        container.get.assert_called_once_with("memory_manager")


class TestFileUploadGetHandlers:
    """Tests for file_upload_handlers.get_handlers."""

    def test_returns_correct_count(self):
        """13. get_handlers returns exactly 2 handlers (Message + Callback)."""
        from telegram_interface.handlers.file_upload_handlers import get_handlers

        bot_ctx = _make_bot_context()
        handlers = get_handlers(bot_ctx)
        assert len(handlers) == 2


# ============================================================================
# SMART UPLOAD HANDLERS TESTS
# ============================================================================


class TestUploadModeFilter:
    """Tests for UploadModeFilter."""

    def test_always_returns_true(self):
        """14. filter() always returns True regardless of message content."""
        from telegram_interface.handlers.smart_upload_handlers import UploadModeFilter

        f = UploadModeFilter()
        assert f.filter(MagicMock()) is True
        assert f.filter(None) is True


class TestUploadCommand:
    """Tests for upload_command."""

    @pytest.mark.asyncio
    async def test_sets_upload_mode_flag(self):
        """15. /upload sets UPLOAD_MODE_KEY in user_data."""
        from telegram_interface.handlers.smart_upload_handlers import (
            UPLOAD_MODE_KEY,
            upload_command,
        )

        bot_ctx = _make_bot_context(authorized=True)
        msg = _make_message()
        update = _make_update(message=msg)
        ctx = _make_context(bot_context=bot_ctx)

        await upload_command(update, ctx)

        assert ctx.user_data[UPLOAD_MODE_KEY] is True
        msg.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unauthorized_returns(self):
        """16. Unauthorized user -> early return, no mode set."""
        from telegram_interface.handlers.smart_upload_handlers import (
            UPLOAD_MODE_KEY,
            upload_command,
        )

        bot_ctx = _make_bot_context(authorized=False)
        msg = _make_message()
        update = _make_update(message=msg)
        ctx = _make_context(bot_context=bot_ctx)

        await upload_command(update, ctx)

        assert UPLOAD_MODE_KEY not in ctx.user_data
        msg.reply_text.assert_not_awaited()


class TestCancelUploadCommand:
    """Tests for cancel_upload_command."""

    @pytest.mark.asyncio
    async def test_clears_mode_when_active(self):
        """17. Clears upload mode and confirms cancellation."""
        from telegram_interface.handlers.smart_upload_handlers import (
            UPLOAD_MODE_KEY,
            cancel_upload_command,
        )

        bot_ctx = _make_bot_context(authorized=True)
        msg = _make_message()
        update = _make_update(message=msg)
        ctx = _make_context(
            user_data={UPLOAD_MODE_KEY: True, "pending_smart_upload": {"some": "data"}},
            bot_context=bot_ctx,
        )

        await cancel_upload_command(update, ctx)

        assert UPLOAD_MODE_KEY not in ctx.user_data
        assert "pending_smart_upload" not in ctx.user_data
        msg.reply_text.assert_awaited_once()
        text = msg.reply_text.call_args.args[0]
        assert "отменён" in text.lower() or "отменен" in text.lower()

    @pytest.mark.asyncio
    async def test_not_active_shows_info(self):
        """18. If upload mode was not active, shows info message."""
        from telegram_interface.handlers.smart_upload_handlers import cancel_upload_command

        bot_ctx = _make_bot_context(authorized=True)
        msg = _make_message()
        update = _make_update(message=msg)
        ctx = _make_context(user_data={}, bot_context=bot_ctx)

        await cancel_upload_command(update, ctx)

        msg.reply_text.assert_awaited_once()
        text = msg.reply_text.call_args.args[0]
        assert "не был" in text.lower() or "не активен" in text.lower()


class TestHandleSmartUpload:
    """Tests for handle_smart_upload."""

    @pytest.mark.asyncio
    async def test_upload_mode_not_active_returns_false(self):
        """19. Without upload mode active, returns False to let next handler run."""
        from telegram_interface.handlers.smart_upload_handlers import handle_smart_upload

        bot_ctx = _make_bot_context(authorized=True)
        doc = _make_document(file_name="photo.jpg")
        msg = _make_message(document=doc)
        update = _make_update(message=msg)
        ctx = _make_context(user_data={}, bot_context=bot_ctx)

        result = await handle_smart_upload(update, ctx)

        assert result is False

    @pytest.mark.asyncio
    async def test_unauthorized_returns_none(self):
        """20. Unauthorized user -> returns None."""
        from telegram_interface.handlers.smart_upload_handlers import (
            UPLOAD_MODE_KEY,
            handle_smart_upload,
        )

        bot_ctx = _make_bot_context(authorized=False)
        doc = _make_document()
        msg = _make_message(document=doc)
        update = _make_update(message=msg)
        ctx = _make_context(
            user_data={UPLOAD_MODE_KEY: True},
            bot_context=bot_ctx,
        )

        result = await handle_smart_upload(update, ctx)

        assert result is None

    @pytest.mark.asyncio
    async def test_processes_photo_with_ocr_classification(self):
        """21. Photo with upload mode active -> OCR + classification + confirmation keyboard."""
        from telegram_interface.handlers.smart_upload_handlers import (
            UPLOAD_MODE_KEY,
            handle_smart_upload,
        )

        bot_ctx = _make_bot_context(authorized=True, active_case="case-abc")

        # Create a photo list (telegram provides list of PhotoSize)
        photo_item = MagicMock()
        photo_item.file_id = "photo-file-id"
        photo_item.get_file = AsyncMock()
        tg_file = MagicMock()
        tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake-image-data"))
        photo_item.get_file.return_value = tg_file

        msg = _make_message(photo=[photo_item])
        update = _make_update(message=msg)
        ctx = _make_context(
            user_data={UPLOAD_MODE_KEY: True},
            bot_context=bot_ctx,
        )

        # Build a fake ClassificationResult
        fake_doc_type = MagicMock()
        fake_doc_type.id = "passport"
        fake_doc_type.name_ru = "Паспорт"
        fake_doc_type.name_en = "Passport"
        fake_doc_type.linked_question_id = "doc_passport"
        fake_doc_type.eb1a_criterion = None

        fake_classification = MagicMock()
        fake_classification.document_type = fake_doc_type
        fake_classification.confidence = 0.85
        fake_classification.matched_keywords = ["passport"]
        fake_classification.suggested_tags = ["identity"]
        fake_classification.eb1a_criterion = None

        mock_classifier = MagicMock()
        mock_classifier.classify = AsyncMock(return_value=fake_classification)

        with patch(
            "telegram_interface.handlers.smart_upload_handlers.get_ocr_service",
            create=True,
        ) as mock_get_ocr, patch(
            "telegram_interface.handlers.smart_upload_handlers.get_document_classifier",
            return_value=mock_classifier,
        ):
            mock_ocr = MagicMock()
            mock_ocr.process_document = AsyncMock(
                return_value={"extracted_text": "PASSPORT Russian Federation", "method": "tesseract"}
            )
            mock_get_ocr.return_value = mock_ocr

            await handle_smart_upload(update, ctx)

        # Should have stored pending_smart_upload
        assert "pending_smart_upload" in ctx.user_data
        pending = ctx.user_data["pending_smart_upload"]
        assert pending["file_id"] == "photo-file-id"
        assert pending["classification"]["doc_type_id"] == "passport"
        assert pending["classification"]["confidence"] == 0.85

        # Processing message was sent
        msg.reply_text.assert_awaited_once()
        processing_msg = msg.reply_text.return_value
        processing_msg.edit_text.assert_awaited_once()


class TestHandleUploadCallback:
    """Tests for handle_upload_callback."""

    @pytest.mark.asyncio
    async def test_confirm_saves_document(self):
        """22. doc_confirm callback saves document and clears pending data."""
        from telegram_interface.handlers.smart_upload_handlers import (
            CALLBACK_CONFIRM,
            handle_upload_callback,
        )

        bot_ctx = _make_bot_context(authorized=True, active_case="case-abc")
        query = _make_callback_query(data=f"{CALLBACK_CONFIRM}:passport")
        update = _make_update(callback_query=query)

        pending = {
            "file_id": "file-abc",
            "file_name": "passport.jpg",
            "file_type": "image/jpeg",
            "file_bytes": b"fake-content",
            "ocr_text": "Passport text",
            "ocr_method": "tesseract",
            "classification": {
                "doc_type_id": "passport",
                "confidence": 0.9,
                "matched_keywords": ["passport"],
                "suggested_tags": ["identity"],
                "eb1a_criterion": None,
            },
            "case_id": "case-abc",
        }
        ctx = _make_context(
            user_data={"pending_smart_upload": pending, "smart_upload_mode": True},
            bot_context=bot_ctx,
        )

        fake_doc_type = MagicMock()
        fake_doc_type.id = "passport"
        fake_doc_type.name_ru = "Паспорт"
        fake_doc_type.name_en = "Passport"
        fake_doc_type.category = MagicMock()
        fake_doc_type.category.value = "identity"
        fake_doc_type.linked_question_id = "doc_passport"
        fake_doc_type.eb1a_criterion = None
        fake_doc_type.tags = ["intake", "identity"]

        with patch(
            "telegram_interface.handlers.smart_upload_handlers.DOCUMENT_TYPES_BY_ID",
            {"passport": fake_doc_type},
            create=True,
        ), patch(
            "telegram_interface.handlers.smart_upload_handlers.get_document_storage",
            create=True,
        ) as mock_storage_fn, patch(
            "telegram_interface.handlers.smart_upload_handlers.extract_fields",
            create=True,
        ) as mock_extract:
            mock_storage = MagicMock()
            mock_storage.save_document = AsyncMock(
                return_value={"success": True, "storage_path": "/docs/passport.jpg", "storage_url": "https://example.com/passport.jpg"}
            )
            mock_storage_fn.return_value = mock_storage

            mock_extract.return_value = {"full_name": "John Doe"}

            await handle_upload_callback(update, ctx)

        query.answer.assert_awaited_once()
        # Document saved via mega_agent.memory.awrite
        bot_ctx.mega_agent.memory.awrite.assert_awaited_once()
        # pending_smart_upload should be cleared
        assert "pending_smart_upload" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_cancel_clears_pending(self):
        """23. CALLBACK_CANCEL clears pending data."""
        from telegram_interface.handlers.smart_upload_handlers import (
            CALLBACK_CANCEL,
            handle_upload_callback,
        )

        bot_ctx = _make_bot_context(authorized=True)
        query = _make_callback_query(data=CALLBACK_CANCEL)
        update = _make_update(callback_query=query)
        ctx = _make_context(
            user_data={"pending_smart_upload": {"some": "data"}},
            bot_context=bot_ctx,
        )

        await handle_upload_callback(update, ctx)

        query.answer.assert_awaited_once()
        assert "pending_smart_upload" not in ctx.user_data
        text = query.edit_message_text.call_args.args[0]
        assert "отмен" in text.lower()

    @pytest.mark.asyncio
    async def test_change_shows_category_selection(self):
        """24. CALLBACK_CHANGE triggers _show_category_selection."""
        from telegram_interface.handlers.smart_upload_handlers import (
            CALLBACK_CHANGE,
            handle_upload_callback,
        )

        bot_ctx = _make_bot_context(authorized=True)
        query = _make_callback_query(data=CALLBACK_CHANGE)
        update = _make_update(callback_query=query)
        ctx = _make_context(
            user_data={"pending_smart_upload": {"some": "data"}},
            bot_context=bot_ctx,
        )

        with patch(
            "telegram_interface.handlers.smart_upload_handlers._show_category_selection",
            new_callable=AsyncMock,
        ) as mock_show:
            await handle_upload_callback(update, ctx)

        mock_show.assert_awaited_once_with(query, ctx)

    @pytest.mark.asyncio
    async def test_no_pending_data_shows_error(self):
        """25. No pending_smart_upload -> shows error message."""
        from telegram_interface.handlers.smart_upload_handlers import handle_upload_callback

        bot_ctx = _make_bot_context(authorized=True)
        query = _make_callback_query(data="doc_confirm:passport")
        update = _make_update(callback_query=query)
        ctx = _make_context(user_data={}, bot_context=bot_ctx)

        await handle_upload_callback(update, ctx)

        query.answer.assert_awaited_once()
        text = query.edit_message_text.call_args.args[0]
        assert "не найден" in text.lower()


class TestHandleCategoryCallback:
    """Tests for handle_category_callback."""

    @pytest.mark.asyncio
    async def test_valid_category_shows_doc_types(self):
        """26. Valid category shows document type buttons."""
        from telegram_interface.handlers.smart_upload_handlers import handle_category_callback

        query = _make_callback_query(data="doc_cat:identity")
        update = _make_update(callback_query=query)
        ctx = _make_context()

        await handle_category_callback(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        call_kwargs = query.edit_message_text.call_args.kwargs
        # Should have reply_markup with document type buttons
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_invalid_category_shows_error(self):
        """27. Invalid/nonexistent category shows error."""
        from telegram_interface.handlers.smart_upload_handlers import handle_category_callback

        query = _make_callback_query(data="doc_cat:nonexistent_xyz")
        update = _make_update(callback_query=query)
        ctx = _make_context()

        await handle_category_callback(update, ctx)

        query.answer.assert_awaited_once()
        text = query.edit_message_text.call_args.args[0]
        assert "не найден" in text.lower()

    @pytest.mark.asyncio
    async def test_non_doc_cat_prefix_returns_early(self):
        """Callback data without doc_cat: prefix returns early."""
        from telegram_interface.handlers.smart_upload_handlers import handle_category_callback

        query = _make_callback_query(data="some_other_data")
        update = _make_update(callback_query=query)
        ctx = _make_context()

        await handle_category_callback(update, ctx)

        query.answer.assert_awaited_once()
        # edit_message_text should not be called because we return early
        query.edit_message_text.assert_not_awaited()


class TestIsAuthorized:
    """Tests for _is_authorized helper."""

    @pytest.mark.asyncio
    async def test_authorized_true(self):
        """28. Authorized user returns True."""
        from telegram_interface.handlers.smart_upload_handlers import _is_authorized

        bot_ctx = _make_bot_context(authorized=True)
        update = _make_update(user=_make_user(user_id=100))

        result = await _is_authorized(bot_ctx, update)

        assert result is True

    @pytest.mark.asyncio
    async def test_unauthorized_false(self):
        """29. Unauthorized user returns False."""
        from telegram_interface.handlers.smart_upload_handlers import _is_authorized

        bot_ctx = _make_bot_context(authorized=False)
        update = _make_update(user=_make_user(user_id=999))

        result = await _is_authorized(bot_ctx, update)

        assert result is False


class TestSmartUploadGetHandlers:
    """Tests for smart_upload_handlers.get_handlers."""

    def test_returns_correct_handler_count(self):
        """30. get_handlers returns exactly 5 handlers."""
        from telegram_interface.handlers.smart_upload_handlers import get_handlers

        bot_ctx = _make_bot_context()
        handlers = get_handlers(bot_ctx)
        # 2 CommandHandlers + 1 MessageHandler + 2 CallbackQueryHandlers = 5
        assert len(handlers) == 5
