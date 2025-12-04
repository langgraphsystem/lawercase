"""Letter/document generation handlers."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext

logger = structlog.get_logger(__name__)

_TELEGRAM_SAFE_CHUNK = 3800


def _split_for_telegram(text: str) -> list[str]:
    """Split long responses into Telegram-friendly chunks."""
    if len(text) <= _TELEGRAM_SAFE_CHUNK:
        return [text]
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(length, start + _TELEGRAM_SAFE_CHUNK)
        chunks.append(text[start:end])
        start = end
    return chunks


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        update.effective_message.reply_text("🚫 Access denied.")
    logger.warning("telegram.letter.unauthorized", user_id=user_id)
    return False


async def generate_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a letter/document for the active case.

    Usage: /generate_letter <title or type>
    Examples:
        /generate_letter cover letter
        /generate_letter recommendation request
        /generate_letter petition summary
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.generate_letter.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.generate_letter.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.generate_letter.no_args", user_id=user_id)
        await message.reply_text(
            "📝 *Генерация документов*\n\n"
            "Использование: `/generate_letter <тип документа>`\n\n"
            "*Примеры:*\n"
            "• `/generate_letter cover letter` — Сопроводительное письмо\n"
            "• `/generate_letter recommendation` — Запрос рекомендательного письма\n"
            "• `/generate_letter petition summary` — Краткое изложение петиции\n"
            "• `/generate_letter RFE response` — Ответ на RFE",
            parse_mode="Markdown",
        )
        return

    title = " ".join(context.args)
    logger.info("telegram.generate_letter.processing", user_id=user_id, title_length=len(title))

    try:
        active_case = await bot_context.get_active_case(update)
        if not active_case:
            await message.reply_text(
                "❌ Активный кейс не выбран.\n\n"
                "Сначала выберите кейс:\n"
                "• `/case_create <название>` — создать новый\n"
                "• `/case_get <case_id>` — открыть существующий\n"
                "• `/case_list` — список всех кейсов",
                parse_mode="Markdown",
            )
            return

        # Show progress message
        progress_msg = await message.reply_text(
            f"📝 Генерирую документ: *{title}*\n"
            f"📁 Кейс: `{active_case[:8]}...`\n\n"
            "⏳ Анализирую данные кейса и создаю текст...",
            parse_mode="Markdown",
        )

        payload = {
            "document_type": "letter",
            "content_data": {"title": title},
            "case_id": active_case,
        }
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.GENERATE,
            action="letter",
            payload=payload,
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        logger.info(
            "telegram.generate_letter.command_created",
            user_id=user_id,
            command_id=command.command_id,
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.generate_letter.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            document = response.result.get("document", {})
            content = document.get("content") or document.get("text") or document.get("body")
            doc_title = document.get("title", title)
            doc_format = document.get("format", "markdown")

            # Delete progress message
            try:
                await progress_msg.delete()
            except Exception:  # nosec B110 - optional cleanup
                pass

            if content:
                # Send document with content
                header = (
                    f"📝 *Документ сгенерирован*\n"
                    f"📋 Тип: {doc_title}\n"
                    f"📁 Кейс: `{active_case[:8]}...`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                )

                # Split content if too long
                full_text = header + content
                chunks = _split_for_telegram(full_text)

                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply_text(chunk, parse_mode="Markdown")
                    else:
                        await message.reply_text(
                            f"_(продолжение {i+1}/{len(chunks)})_\n\n{chunk}", parse_mode="Markdown"
                        )

                logger.info(
                    "telegram.generate_letter.sent",
                    user_id=user_id,
                    format=doc_format,
                    content_length=len(content),
                    chunks=len(chunks),
                )
            else:
                # Fallback: no content returned
                await message.reply_text(
                    f"📝 *Документ создан*\n\n"
                    f"Название: {doc_title}\n"
                    f"Формат: {doc_format}\n\n"
                    "⚠️ Контент документа недоступен. "
                    "Попробуйте `/ask сгенерируй {title}` для получения текста.",
                    parse_mode="Markdown",
                )
                logger.warning(
                    "telegram.generate_letter.no_content",
                    user_id=user_id,
                    document_keys=list(document.keys()),
                )
        else:
            # Delete progress message
            try:
                await progress_msg.delete()
            except Exception:  # nosec B110 - optional cleanup
                pass

            error_msg = response.error or "generation failed"
            await message.reply_text(f"❌ Ошибка генерации: {error_msg}", parse_mode=None)
            logger.error("telegram.generate_letter.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.generate_letter.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Ошибка: {e!s}", parse_mode=None)


def get_handlers(bot_context: BotContext):
    return [CommandHandler("generate_letter", generate_letter)]
