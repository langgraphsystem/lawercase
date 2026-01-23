"""
Smart Document Upload Handlers with AI Classification.

Handles photo and document uploads with automatic classification:
1. User uploads photo/document at any time
2. OCR extracts text
3. AI classifies document type (passport, diploma, award, etc.)
4. User confirms or selects correct category
5. Document saved with proper tags and linked to appropriate section

Works independently of intake flow - documents uploaded at any time
will be correctly categorized and linked.
"""

from __future__ import annotations

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext.filters import MessageFilter

from core.memory.models import MemoryRecord
from core.services.document_classifier import (
    DOCUMENT_TYPES,
    DocumentCategory,
    DocumentType,
    get_document_classifier,
)

from .context import BotContext

logger = structlog.get_logger(__name__)

# Callback prefixes
CALLBACK_CONFIRM = "doc_confirm"
CALLBACK_CHANGE = "doc_change"
CALLBACK_SELECT = "doc_select"
CALLBACK_CANCEL = "doc_cancel"

# Upload mode flag key
UPLOAD_MODE_KEY = "smart_upload_mode"


class UploadModeFilter(MessageFilter):
    """Filter that only matches when upload mode is active."""

    def filter(self, message) -> bool:
        """Check if upload mode is active in user_data."""
        # This filter is used with context - we'll check in handler instead
        # For now, always return True and let handler decide
        return True


class UploadModeActiveFilter(MessageFilter):
    """Custom filter that checks if upload_mode is active via callback_data context."""

    def __init__(self) -> None:
        super().__init__()
        self._upload_mode_users: set[int] = set()

    def add_user(self, user_id: int) -> None:
        """Mark user as having upload mode active."""
        self._upload_mode_users.add(user_id)

    def remove_user(self, user_id: int) -> None:
        """Mark user as having upload mode inactive."""
        self._upload_mode_users.discard(user_id)

    def filter(self, message) -> bool:
        """Check if user has upload mode active."""
        if message.from_user:
            return message.from_user.id in self._upload_mode_users
        return False


# Global filter instance
upload_mode_filter = UploadModeActiveFilter()


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Get BotContext from application bot_data."""
    return context.application.bot_data["bot_context"]


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    """Check if user is authorized."""
    user_id = update.effective_user.id if update.effective_user else None
    return bot_context.is_authorized(user_id)


async def upload_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    /upload - Start document upload mode.

    Bypasses intake flow to allow uploading documents at any time.
    Documents will be classified by AI and linked to appropriate sections.
    """
    bot_ctx = _bot_context(context)

    if not await _is_authorized(bot_ctx, update):
        return

    message = update.effective_message
    if not message:
        return

    # Set upload mode flag
    context.user_data[UPLOAD_MODE_KEY] = True
    # Add user to filter so document handler matches
    upload_mode_filter.add_user(update.effective_user.id)

    await message.reply_text(
        "📤 *Режим загрузки документов*\n\n"
        "Отправьте фото или документ.\n"
        "AI автоматически определит тип документа и привяжет его к соответствующему разделу.\n\n"
        "📎 Поддерживаемые форматы: фото, изображения, PDF, документы\n\n"
        "Для отмены: /cancel\\_upload",
        parse_mode=None,
    )

    logger.info(
        "smart_upload.mode_enabled",
        user_id=str(update.effective_user.id),
    )


async def cancel_upload_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    /cancel_upload - Exit document upload mode.
    """
    bot_ctx = _bot_context(context)

    if not await _is_authorized(bot_ctx, update):
        return

    message = update.effective_message
    if not message:
        return

    # Clear upload mode flag and pending data
    was_active = context.user_data.pop(UPLOAD_MODE_KEY, None)
    context.user_data.pop("pending_smart_upload", None)
    # Remove user from filter
    upload_mode_filter.remove_user(update.effective_user.id)

    if was_active:
        await message.reply_text(
            "❌ Режим загрузки документов отменён.\nВы можете продолжить заполнение анкеты.",
        )
        logger.info(
            "smart_upload.mode_cancelled",
            user_id=str(update.effective_user.id),
        )
    else:
        await message.reply_text("ℹ️ Режим загрузки документов не был активен.")


async def handle_smart_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle photo/document uploads with AI classification.

    Flow:
    1. Download file
    2. Run OCR to extract text
    3. Classify document type
    4. Show classification result with confirm/change buttons
    5. Save on confirmation
    """
    logger.info(
        "smart_upload.handler_called",
        user_id=str(update.effective_user.id) if update.effective_user else "unknown",
        has_photo=bool(update.effective_message and update.effective_message.photo),
        has_document=bool(update.effective_message and update.effective_message.document),
    )

    bot_ctx = _bot_context(context)

    if not await _is_authorized(bot_ctx, update):
        return None

    message = update.effective_message
    if not message:
        return None

    user_id = str(update.effective_user.id)

    # Check if upload mode is active (via /upload command)
    upload_mode_active = context.user_data.get(UPLOAD_MODE_KEY, False)

    logger.info(
        "smart_upload.check_mode",
        user_id=user_id,
        upload_mode_active=upload_mode_active,
    )

    # Only process if upload mode is explicitly enabled
    # Otherwise let intake or other handlers process
    if not upload_mode_active:
        return False  # Let next handler (intake) process

    # Get active case
    active_case_id = await bot_ctx.get_active_case(update)

    # Get file info
    file = None
    file_name = "document"
    file_type = "unknown"

    if message.document:
        file = message.document
        file_name = message.document.file_name or "document"
        file_type = message.document.mime_type or "application/octet-stream"
    elif message.photo:
        # Get largest photo
        file = message.photo[-1]
        file_name = f"photo_{file.file_id[:8]}.jpg"
        file_type = "image/jpeg"
    else:
        return None

    logger.info(
        "smart_upload.received",
        user_id=user_id,
        file_name=file_name,
        file_type=file_type,
    )

    # Send processing message
    processing_msg = await message.reply_text("📥 Получен документ...\n🔍 Анализирую содержимое...")

    try:
        # Download file
        telegram_file = await file.get_file()
        file_bytes = await telegram_file.download_as_bytearray()

        # Run OCR
        ocr_text = ""
        ocr_method = "none"

        try:
            from core.services.ocr_service import get_ocr_service

            ocr_service = get_ocr_service()
            ocr_result = await ocr_service.process_document(bytes(file_bytes), file_name, file_type)

            if ocr_result.get("extracted_text"):
                ocr_text = ocr_result["extracted_text"]
                ocr_method = ocr_result.get("method", "ocr")
                logger.info(
                    "smart_upload.ocr_complete",
                    file_name=file_name,
                    text_length=len(ocr_text),
                    method=ocr_method,
                )
        except Exception as e:
            logger.warning("smart_upload.ocr_failed", error=str(e))

        # Classify document
        classifier = get_document_classifier()
        classification = await classifier.classify(ocr_text, use_llm_fallback=True)

        # Store pending upload data
        context.user_data["pending_smart_upload"] = {
            "file_id": file.file_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_bytes": bytes(file_bytes),
            "ocr_text": ocr_text,
            "ocr_method": ocr_method,
            "classification": {
                "doc_type_id": classification.document_type.id,
                "confidence": classification.confidence,
                "matched_keywords": classification.matched_keywords,
                "suggested_tags": classification.suggested_tags,
                "eb1a_criterion": classification.eb1a_criterion,
            },
            "case_id": active_case_id,
        }

        # Build confirmation message
        doc_type = classification.document_type
        confidence_emoji = (
            "🟢"
            if classification.confidence >= 0.7
            else "🟡" if classification.confidence >= 0.4 else "🔴"
        )
        confidence_pct = int(classification.confidence * 100)

        # OCR preview (no Markdown - plain text to avoid parsing errors)
        ocr_preview = ""
        if ocr_text:
            preview_text = ocr_text[:200].replace("\n", " ")
            if len(ocr_text) > 200:
                preview_text += "..."
            ocr_preview = f"\n\n📝 Распознанный текст:\n{preview_text}"

        # EB-1A criterion info
        criterion_info = ""
        if classification.eb1a_criterion:
            criterion_info = f"\n🎯 EB-1A критерий: #{classification.eb1a_criterion}"

        # Linked question info
        question_info = ""
        if doc_type.linked_question_id:
            question_info = f"\n📋 Раздел анкеты: {doc_type.linked_question_id}"

        confirmation_text = (
            f"📄 Документ: {file_name}\n\n"
            f"🤖 AI определил тип документа:\n"
            f"{doc_type.name_ru} ({doc_type.name_en})\n\n"
            f"{confidence_emoji} Уверенность: {confidence_pct}%"
            f"{criterion_info}"
            f"{question_info}"
            f"{ocr_preview}\n\n"
            f"Это верно?"
        )

        # Build keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Да, сохранить",
                    callback_data=f"{CALLBACK_CONFIRM}:{doc_type.id}",
                ),
                InlineKeyboardButton(
                    "🔄 Изменить тип",
                    callback_data=CALLBACK_CHANGE,
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=CALLBACK_CANCEL,
                ),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.edit_text(
            confirmation_text,
            reply_markup=reply_markup,
            parse_mode=None,
        )

    except Exception as e:
        logger.exception("smart_upload.processing_failed", error=str(e))
        await processing_msg.edit_text(
            f"❌ Ошибка при обработке документа:\n{str(e)[:200]}",
            parse_mode=None,
        )


async def handle_upload_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle callback queries from document upload."""
    query = update.callback_query
    await query.answer()

    bot_ctx = _bot_context(context)

    if not await _is_authorized(bot_ctx, update):
        return

    data = query.data
    user_id = str(update.effective_user.id)

    # Get pending upload
    pending = context.user_data.get("pending_smart_upload")
    if not pending:
        await query.edit_message_text(
            "❌ Данные документа не найдены. Загрузите снова.",
            parse_mode=None,
        )
        return

    # Handle cancel
    if data == CALLBACK_CANCEL:
        context.user_data.pop("pending_smart_upload", None)
        await query.edit_message_text(
            "❌ Загрузка отменена.",
            parse_mode=None,
        )
        return

    # Handle change type - show category selection
    if data == CALLBACK_CHANGE:
        await _show_category_selection(query, context)
        return

    # Handle category selection
    if data.startswith(f"{CALLBACK_SELECT}:"):
        doc_type_id = data.split(":", 1)[1]
        await _save_document_with_type(query, context, bot_ctx, user_id, doc_type_id)
        return

    # Handle confirm
    if data.startswith(f"{CALLBACK_CONFIRM}:"):
        doc_type_id = data.split(":", 1)[1]
        await _save_document_with_type(query, context, bot_ctx, user_id, doc_type_id)
        return


async def _show_category_selection(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show document category selection menu."""
    # Group document types by category
    categories = {}
    for dt in DOCUMENT_TYPES:
        cat = dt.category.value
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(dt)

    # Build category buttons (show main categories first)
    priority_categories = [
        (DocumentCategory.IDENTITY, "🪪 Документы личности"),
        (DocumentCategory.EDUCATION, "🎓 Образование"),
        (DocumentCategory.EB1A_AWARDS, "🏆 Награды (EB-1A #1)"),
        (DocumentCategory.EB1A_SCHOLARLY, "📚 Публикации (EB-1A #6)"),
        (DocumentCategory.EB1A_CONTRIBUTION, "💡 Патенты (EB-1A #5)"),
        (DocumentCategory.EB1A_SALARY, "💰 Зарплата (EB-1A #9)"),
        (DocumentCategory.RECOMMENDATION_LETTER, "📝 Рекомендации"),
        (DocumentCategory.CAREER_EMPLOYMENT, "💼 Карьера"),
    ]

    keyboard = []
    for cat, label in priority_categories:
        # Get first document type in category for callback
        cat_types = [dt for dt in DOCUMENT_TYPES if dt.category == cat]
        if cat_types:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        label,
                        callback_data=f"doc_cat:{cat.value}",
                    )
                ]
            )

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=CALLBACK_CANCEL)])

    await query.edit_message_text(
        "📂 *Выберите категорию документа:*",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_category_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle category selection callback."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("doc_cat:"):
        return

    category_value = query.data.split(":", 1)[1]

    # Find document types in this category
    cat_types = [dt for dt in DOCUMENT_TYPES if dt.category.value == category_value]

    if not cat_types:
        await query.edit_message_text(
            "❌ Категория не найдена.",
            parse_mode=None,
        )
        return

    # Show document type selection within category
    keyboard = []
    for dt in cat_types[:10]:  # Limit to 10 to avoid huge keyboard
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{dt.name_ru}",
                    callback_data=f"{CALLBACK_SELECT}:{dt.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=CALLBACK_CHANGE)])

    await query.edit_message_text(
        "📄 *Выберите тип документа:*",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _save_document_with_type(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    bot_ctx: BotContext,
    user_id: str,
    doc_type_id: str,
) -> None:
    """Save document with specified type."""
    pending = context.user_data.get("pending_smart_upload")
    if not pending:
        await query.edit_message_text(
            "❌ Данные документа не найдены.",
            parse_mode=None,
        )
        return

    # Find document type
    from core.services.document_classifier import DOCUMENT_TYPES_BY_ID

    doc_type = DOCUMENT_TYPES_BY_ID.get(doc_type_id)
    if not doc_type:
        # Create generic "other" type
        doc_type = DocumentType(
            id="other",
            name_ru="Другой документ",
            name_en="Other Document",
            category=DocumentCategory.OTHER,
            linked_question_id=None,
            keywords_ru=[],
            keywords_en=[],
            tags=["document", "unclassified"],
        )

    await query.edit_message_text(
        "💾 Сохраняю документ...",
        parse_mode=None,
    )

    try:
        file_name = pending["file_name"]
        file_bytes = pending["file_bytes"]
        file_type = pending["file_type"]
        ocr_text = pending["ocr_text"]
        ocr_method = pending["ocr_method"]
        case_id = pending.get("case_id")

        # Save to document storage
        storage_path = ""
        storage_url = ""
        storage_error = None  # Track storage errors to show to user

        try:
            from core.services.document_storage import get_document_storage

            storage = get_document_storage()
            storage_result = await storage.save_document(
                file_bytes=file_bytes,
                file_name=file_name,
                file_type=file_type,
                user_id=user_id,
                case_id=case_id,
                question_id=doc_type.linked_question_id,
                metadata={
                    "document_type": doc_type.id,
                    "category": doc_type.category.value,
                    "eb1a_criterion": doc_type.eb1a_criterion,
                },
            )

            if storage_result.get("success"):
                storage_path = storage_result.get("storage_path", "")
                storage_url = storage_result.get("storage_url", "")
            else:
                # Storage returned failure
                storage_error = storage_result.get("error", "Неизвестная ошибка хранилища")
                logger.error("smart_upload.storage_failed", error=storage_error)
        except Exception as e:
            storage_error = str(e)
            logger.error("smart_upload.storage_exception", error=storage_error)

        # Build document text for memory
        max_ocr_length = 20000  # Increased from 5000 for better document coverage
        if ocr_text and len(ocr_text) > max_ocr_length:
            ocr_preview = ocr_text[:max_ocr_length]
            document_text = (
                f"📄 {doc_type.name_ru} ({doc_type.name_en})\n"
                f"Файл: {file_name}\n\n"
                f"Содержимое:\n{ocr_preview}\n\n"
                f"... (текст обрезан, полная длина: {len(ocr_text)} символов)"
            )
        elif ocr_text:
            document_text = (
                f"📄 {doc_type.name_ru} ({doc_type.name_en})\n"
                f"Файл: {file_name}\n\n"
                f"Содержимое:\n{ocr_text}"
            )
        else:
            document_text = f"📄 {doc_type.name_ru} ({doc_type.name_en})\nФайл: {file_name}"

        # Build tags
        tags = list(doc_type.tags)
        if ocr_text:
            tags.append("ocr_processed")
        if doc_type.eb1a_criterion:
            tags.append(f"eb1a_criterion_{doc_type.eb1a_criterion}")

        # Extract structured fields from document
        extracted_fields = {}
        if ocr_text:
            try:
                from core.services.field_extractor import extract_fields

                extracted_fields = await extract_fields(
                    ocr_text=ocr_text,
                    doc_type_id=doc_type.id,
                    doc_type_name=doc_type.name_ru,
                )
                if extracted_fields:
                    tags.append("fields_extracted")
                    logger.info(
                        "smart_upload.fields_extracted",
                        doc_type=doc_type.id,
                        fields_count=len(
                            [k for k, v in extracted_fields.items() if v and not k.startswith("_")]
                        ),
                    )
            except Exception as e:
                logger.warning("smart_upload.field_extraction_failed", error=str(e))

        # Create memory record
        memory_record = MemoryRecord(
            text=document_text,
            user_id=user_id,
            type="semantic",
            case_id=case_id,
            tags=tags,
            metadata={
                "source": "smart_document_upload",
                "document_type_id": doc_type.id,
                "document_type_name": doc_type.name_ru,
                "category": doc_type.category.value,
                "linked_question_id": doc_type.linked_question_id,
                "eb1a_criterion": doc_type.eb1a_criterion,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": len(file_bytes),
                "ocr_method": ocr_method,
                "ocr_text_length": len(ocr_text) if ocr_text else 0,
                "storage_path": storage_path,
                "storage_url": storage_url,
                "extracted_fields": extracted_fields if extracted_fields else None,
            },
        )

        # Save to memory
        await bot_ctx.mega_agent.memory.awrite([memory_record])

        logger.info(
            "smart_upload.saved",
            user_id=user_id,
            case_id=case_id,
            doc_type=doc_type.id,
            file_name=file_name,
            linked_question=doc_type.linked_question_id,
            eb1a_criterion=doc_type.eb1a_criterion,
        )

        # Clear pending data and upload mode
        context.user_data.pop("pending_smart_upload", None)
        context.user_data.pop(UPLOAD_MODE_KEY, None)

        # Build success message
        success_lines = [
            "✅ Документ сохранён!",
            "",
            f"📄 Тип: {doc_type.name_ru}",
        ]

        if case_id:
            success_lines.append(f"📋 Кейс: {case_id[:8]}...")

        if doc_type.linked_question_id:
            success_lines.append(f"🔗 Раздел анкеты: {doc_type.linked_question_id}")

        if doc_type.eb1a_criterion:
            success_lines.append(f"🎯 EB-1A критерий: #{doc_type.eb1a_criterion}")

        if storage_path:
            success_lines.append(f"💾 Сохранён в: {storage_path[:50]}...")

        # Show extracted fields (key ones only)
        if extracted_fields:
            key_fields = []
            # Identity fields
            if extracted_fields.get("full_name"):
                key_fields.append(f"👤 {extracted_fields['full_name']}")
            if extracted_fields.get("date_of_birth"):
                key_fields.append(f"📅 {extracted_fields['date_of_birth']}")
            # Award/Membership fields
            if extracted_fields.get("award_name"):
                key_fields.append(f"🏆 {extracted_fields['award_name']}")
            if extracted_fields.get("organization_name"):
                key_fields.append(f"🏢 {extracted_fields['organization_name']}")
            # Publication fields
            if extracted_fields.get("title"):
                key_fields.append(f"📝 {extracted_fields['title'][:50]}...")
            if extracted_fields.get("h_index"):
                key_fields.append(f"📊 h-index: {extracted_fields['h_index']}")
            # Salary fields
            if extracted_fields.get("salary_amount") and extracted_fields.get("salary_currency"):
                key_fields.append(
                    f"💰 {extracted_fields['salary_amount']} {extracted_fields['salary_currency']}"
                )

            if key_fields:
                success_lines.append("")
                success_lines.append("📋 Извлечённые данные:")
                success_lines.extend(key_fields[:5])  # Show max 5 fields

        # Show storage error warning to user
        if storage_error:
            success_lines.extend(
                [
                    "",
                    "⚠️ ВНИМАНИЕ: Файл НЕ загружен в облако!",
                    f"Ошибка: {storage_error[:100]}",
                    "Текст сохранён в память, но оригинал файла может быть утерян.",
                    "Попробуйте загрузить файл снова позже.",
                ]
            )

        success_lines.extend(
            [
                "",
                "Документ будет использован при анализе кейса.",
            ]
        )

        await query.edit_message_text(
            "\n".join(success_lines),
            parse_mode=None,
        )

        # Check if we came from intake - continue intake flow
        intake_context = context.user_data.pop("intake_document_upload", None)
        if intake_context:
            # Remove user from upload mode filter
            if query.from_user:
                upload_mode_filter.remove_user(query.from_user.id)

            logger.info(
                "smart_upload.continuing_intake",
                user_id=user_id,
                case_id=intake_context.get("case_id"),
                question_id=intake_context.get("question_id"),
            )

            # Advance intake step and send next question
            try:
                from core.storage.intake_progress import advance_step

                from .intake_handlers import _send_question_batch

                intake_case_id = intake_context.get("case_id")
                intake_user_id = intake_context.get("user_id")

                if intake_case_id and intake_user_id:
                    await advance_step(intake_user_id, intake_case_id)

                    # Send next question
                    await query.message.reply_text(
                        "✅ Документ сохранён!\nПереходим к следующему вопросу..."
                    )
                    await _send_question_batch(
                        bot_ctx,
                        query,  # Use query as update
                        intake_user_id,
                        intake_case_id,
                        context,
                    )
            except Exception as intake_error:
                logger.exception(
                    "smart_upload.intake_continue_failed",
                    error=str(intake_error),
                )
                await query.message.reply_text(
                    "⚠️ Документ сохранён, но не удалось продолжить анкетирование.\n"
                    "Используйте /intake_resume чтобы продолжить."
                )

    except Exception as e:
        logger.exception("smart_upload.save_failed", error=str(e))
        await query.edit_message_text(
            f"❌ Ошибка при сохранении:\n{str(e)[:200]}",
            parse_mode=None,
        )


def get_handlers(bot_context: BotContext) -> list:
    """Get smart upload handlers.

    Args:
        bot_context: Bot context

    Returns:
        List of Telegram handlers
    """
    return [
        # /upload command - enter upload mode (bypasses intake)
        CommandHandler("upload", upload_command),
        # /cancel_upload command - exit upload mode
        CommandHandler("cancel_upload", cancel_upload_command),
        # Handle photos and all documents (including PDF) - ONLY when upload mode is active
        MessageHandler(
            upload_mode_filter & (filters.PHOTO | filters.Document.ALL),
            handle_smart_upload,
        ),
        # Handle document classification callbacks
        CallbackQueryHandler(
            handle_upload_callback,
            pattern=f"^({CALLBACK_CONFIRM}|{CALLBACK_CHANGE}|{CALLBACK_SELECT}|{CALLBACK_CANCEL})",
        ),
        # Handle category selection
        CallbackQueryHandler(
            handle_category_callback,
            pattern="^doc_cat:",
        ),
    ]
