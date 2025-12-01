"""File upload handlers for PDF document ingestion.

Handles PDF files sent to the Telegram bot, processes them through
the PDF ingestion pipeline, and stores in semantic memory with EB-1A tagging.
"""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from core.ingestion import PDFIngestionService
from core.memory.memory_manager_v2 import MemoryManager

from .context import BotContext


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Get BotContext from application bot_data."""
    return context.application.bot_data["bot_context"]


logger = structlog.get_logger(__name__)


async def handle_pdf_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle PDF document uploads.

    Downloads the PDF, runs it through the ingestion pipeline,
    and stores chunks in semantic memory with EB-1A auto-tagging.

    Args:
        update: Telegram update containing the document
        context: Bot context with mega_agent
    """
    bot_ctx = _bot_context(context)
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
        "pdf_upload.started",
        user_id=user.id,
        file_name=file_name,
        file_size_mb=round(file_size_mb, 2),
    )

    # Send processing message
    status_msg = await update.message.reply_text(
        f"📄 Загружаю документ: {file_name}\n"
        f"📊 Размер: {file_size_mb:.2f} MB\n"
        "⏳ Обработка..."
    )

    try:
        # Download file bytes
        tg_file = await document.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        # Get or create memory manager
        memory_manager = _get_memory_manager(bot_ctx)

        # Create ingestion service
        service = PDFIngestionService(
            memory_manager=memory_manager,
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Get active case if exists
        active_case = await bot_ctx.get_active_case(update)

        # Ingest PDF
        result = await service.ingest_bytes(
            file_bytes=bytes(file_bytes),
            file_name=file_name,
            user_id=str(user.id),
            case_id=active_case,
            auto_tag_eb1a=True,
        )

        logger.info(
            "pdf_upload.complete",
            user_id=user.id,
            document_id=result.document_id,
            chunks_count=result.chunks_count,
            detected_criteria=result.detected_criteria,
        )

        # Format response
        response_lines = [
            "✅ Документ загружен в базу знаний!",
            "",
            "📊 **Статистика:**",
            f"• Файл: {result.file_name}",
            f"• Страниц: {result.page_count}" if result.page_count > 0 else None,
            f"• Фрагментов: {result.chunks_count}",
            f"• Записей создано: {result.records_created}",
        ]

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

        # Add case info
        if active_case:
            response_lines.extend(
                [
                    "",
                    f"📁 Case ID: `{active_case}`",
                ]
            )

        response_lines.extend(
            [
                "",
                "🔍 Используйте /search <запрос> для поиска в документе",
            ]
        )

        # Filter out None values
        response_text = "\n".join(line for line in response_lines if line is not None)

        await status_msg.edit_text(response_text, parse_mode="Markdown")

    except FileNotFoundError as e:
        logger.error("pdf_upload.file_error", error=str(e))
        await status_msg.edit_text(
            "❌ Ошибка: файл не найден или поврежден.\n" "Попробуйте отправить документ снова."
        )

    except ValueError as e:
        logger.error("pdf_upload.format_error", error=str(e))
        await status_msg.edit_text(
            f"❌ Ошибка формата: {e}\n" "Убедитесь, что файл является корректным PDF."
        )

    except Exception as e:
        logger.exception("pdf_upload.failed", error=str(e))
        await status_msg.edit_text(
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

    # Fallback: create new memory manager
    from core.memory.memory_manager_v2 import create_memory_manager

    return create_memory_manager()


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
    ]
