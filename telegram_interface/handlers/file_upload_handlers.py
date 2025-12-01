"""File upload handlers for PDF document ingestion.

Handles PDF files sent to the Telegram bot, processes them through
the PDF ingestion pipeline, and stores in semantic memory with EB-1A tagging.

Supports two modes:
1. General Knowledge - reference cases for agents (no case_id)
2. Case Documents - files for specific client case (with case_id)
"""

from __future__ import annotations

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackQueryHandler, ContextTypes, MessageHandler,
                          filters)

from core.ingestion import PDFIngestionService
from core.memory.memory_manager import MemoryManager

from .context import BotContext


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Get BotContext from application bot_data."""
    return context.application.bot_data["bot_context"]


logger = structlog.get_logger(__name__)

# Callback data prefixes
CALLBACK_KNOWLEDGE = "pdf_knowledge"
CALLBACK_CASE = "pdf_case"


async def handle_pdf_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle PDF document uploads - ask user for destination.

    Shows inline keyboard to choose between:
    - General Knowledge (reference materials)
    - Case Documents (client-specific)

    Args:
        update: Telegram update containing the document
        context: Bot context with mega_agent
    """
    user = update.effective_user
    document = update.message.document

    if not document:
        return

    # Check file type
    file_name = document.file_name or "unknown.pdf"
    if not file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте PDF файл.\n" "Поддерживаемые форматы: .pdf"
        )
        return

    # Check file size (Telegram limit is 20MB for bots)
    file_size_mb = (document.file_size or 0) / (1024 * 1024)
    if file_size_mb > 20:
        await update.message.reply_text(
            f"❌ Файл слишком большой ({file_size_mb:.1f} MB).\n" "Максимальный размер: 20 MB"
        )
        return

    logger.info(
        "pdf_upload.received",
        user_id=user.id,
        file_name=file_name,
        file_size_mb=round(file_size_mb, 2),
    )

    # Store file_id in user_data for later processing
    context.user_data["pending_pdf"] = {
        "file_id": document.file_id,
        "file_name": file_name,
        "file_size_mb": file_size_mb,
        "message_id": update.message.message_id,
    }

    # Ask user where to store the document
    keyboard = [
        [
            InlineKeyboardButton(
                "📚 Общие знания (готовые кейсы)",
                callback_data=CALLBACK_KNOWLEDGE,
            ),
        ],
        [
            InlineKeyboardButton(
                "📁 Документы по кейсу клиента",
                callback_data=CALLBACK_CASE,
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📄 **Документ:** {file_name}\n"
        f"📊 **Размер:** {file_size_mb:.2f} MB\n\n"
        "Куда сохранить этот документ?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_pdf_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle callback from PDF destination selection.

    Args:
        update: Telegram update with callback query
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    bot_ctx = _bot_context(context)
    user = update.effective_user

    # Get pending PDF info
    pending_pdf = context.user_data.get("pending_pdf")
    if not pending_pdf:
        await query.edit_message_text("❌ Документ не найден. Пожалуйста, отправьте PDF снова.")
        return

    file_id = pending_pdf["file_id"]
    file_name = pending_pdf["file_name"]
    file_size_mb = pending_pdf["file_size_mb"]

    # Determine storage mode
    is_knowledge = query.data == CALLBACK_KNOWLEDGE
    storage_type = "общие знания" if is_knowledge else "документы кейса"

    logger.info(
        "pdf_upload.started",
        user_id=user.id,
        file_name=file_name,
        storage_type=storage_type,
        is_knowledge=is_knowledge,
    )

    # Update message to show processing
    await query.edit_message_text(
        f"📄 Загружаю документ: {file_name}\n"
        f"📊 Размер: {file_size_mb:.2f} MB\n"
        f"📂 Тип: {storage_type}\n"
        "⏳ Обработка..."
    )

    try:
        # Download file bytes
        tg_file = await context.bot.get_file(file_id)
        file_bytes = await tg_file.download_as_bytearray()

        # Get or create memory manager
        memory_manager = _get_memory_manager(bot_ctx)

        # Create ingestion service
        service = PDFIngestionService(
            memory_manager=memory_manager,
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Determine case_id and tags based on storage type
        if is_knowledge:
            # General knowledge - no case_id, special tags
            case_id = None
            additional_tags = ["knowledge_base", "reference_case", "approved_petition"]
        else:
            # Case documents - use active case
            case_id = await bot_ctx.get_active_case(update)
            additional_tags = ["case_document", "client_evidence"]

        # Ingest PDF
        result = await service.ingest_bytes(
            file_bytes=bytes(file_bytes),
            file_name=file_name,
            user_id=str(user.id),
            case_id=case_id,
            auto_tag_eb1a=True,
            additional_tags=additional_tags,
        )

        logger.info(
            "pdf_upload.complete",
            user_id=user.id,
            document_id=result.document_id,
            chunks_count=result.chunks_count,
            detected_criteria=result.detected_criteria,
            is_knowledge=is_knowledge,
        )

        # Format response
        if is_knowledge:
            response_lines = [
                "✅ Документ добавлен в базу знаний!",
                "",
                "📚 **Тип:** Общие знания (готовые кейсы)",
                "🤖 Агенты смогут использовать этот кейс как референс",
            ]
        else:
            response_lines = [
                "✅ Документ загружен в кейс!",
                "",
                "📁 **Тип:** Документы клиента",
            ]
            if case_id:
                response_lines.append(f"📋 **Case ID:** `{case_id}`")
            else:
                response_lines.append("⚠️ Активный кейс не выбран - документ привязан к вашему ID")

        response_lines.extend(
            [
                "",
                "📊 **Статистика:**",
                f"• Файл: {result.file_name}",
            ]
        )

        if result.page_count > 0:
            response_lines.append(f"• Страниц: {result.page_count}")

        response_lines.extend(
            [
                f"• Фрагментов: {result.chunks_count}",
                f"• Записей создано: {result.records_created}",
            ]
        )

        # Add criteria info
        if result.detected_criteria:
            response_lines.extend(
                [
                    "",
                    "🏷️ **Обнаруженные критерии EB-1A:**",
                ]
            )
            for criterion in result.detected_criteria:
                count = result.criteria_counts.get(criterion, 0)
                criterion_name = _format_criterion_name(criterion)
                response_lines.append(f"• {criterion_name} ({count} упом.)")
        else:
            response_lines.extend(
                [
                    "",
                    "ℹ️ Критерии EB-1A не обнаружены",
                ]
            )

        response_lines.extend(
            [
                "",
                "🔍 Используйте /search <запрос> для поиска в документе",
            ]
        )

        response_text = "\n".join(response_lines)
        await query.edit_message_text(response_text, parse_mode="Markdown")

        # Clear pending PDF
        context.user_data.pop("pending_pdf", None)

    except FileNotFoundError as e:
        logger.error("pdf_upload.file_error", error=str(e))
        await query.edit_message_text(
            "❌ Ошибка: файл не найден или поврежден.\n" "Попробуйте отправить документ снова."
        )

    except ValueError as e:
        logger.error("pdf_upload.format_error", error=str(e))
        await query.edit_message_text(
            f"❌ Ошибка формата: {e}\n" "Убедитесь, что файл является корректным PDF."
        )

    except Exception as e:
        logger.exception("pdf_upload.failed", error=str(e))
        await query.edit_message_text(
            "❌ Произошла ошибка при обработке документа.\n" f"Ошибка: {str(e)[:200]}"
        )


def _get_memory_manager(bot_ctx: BotContext) -> MemoryManager:
    """Get memory manager from bot context.

    Args:
        bot_ctx: Bot context with mega_agent

    Returns:
        MemoryManager instance
    """
    # Use memory from mega_agent if available
    if hasattr(bot_ctx.mega_agent, "memory") and bot_ctx.mega_agent.memory:
        return bot_ctx.mega_agent.memory

    # Fallback: use DI container's memory manager (uses SupabaseSemanticStore)
    from core.di.container import get_container

    container = get_container()
    return container.get("memory_manager")


def _format_criterion_name(criterion_tag: str) -> str:
    """Format EB-1A criterion tag for display.

    Args:
        criterion_tag: Tag like 'eb1a_awards'

    Returns:
        Human-readable name like 'Awards'
    """
    name_map = {
        "eb1a_awards": "🏆 Awards",
        "eb1a_membership": "🎖️ Membership",
        "eb1a_press": "📰 Press",
        "eb1a_judging": "⚖️ Judging",
        "eb1a_contribution": "💡 Original Contribution",
        "eb1a_scholarly": "📚 Scholarly Articles",
        "eb1a_leadership": "👔 Leading Role",
        "eb1a_salary": "💰 High Salary",
        "eb1a_commercial": "📈 Commercial Success",
    }
    return name_map.get(criterion_tag, criterion_tag)


def get_handlers(bot_context: BotContext) -> list:
    """Get file upload handlers.

    Args:
        bot_context: Bot context (stored in context.bot_data)

    Returns:
        List of Telegram handlers for file uploads
    """
    return [
        # Handle PDF documents
        MessageHandler(
            filters.Document.PDF,
            handle_pdf_document,
        ),
        # Handle callback for PDF destination selection
        CallbackQueryHandler(
            handle_pdf_callback,
            pattern=f"^({CALLBACK_KNOWLEDGE}|{CALLBACK_CASE})$",
        ),
    ]
