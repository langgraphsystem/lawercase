"""Letter/document generation handlers."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext

logger = structlog.get_logger(__name__)


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
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.generate_letter.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.generate_letter.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.generate_letter.no_args", user_id=user_id)
        await message.reply_text("Usage: /generate_letter <title>")
        return

    title = " ".join(context.args)
    logger.info("telegram.generate_letter.processing", user_id=user_id, title_length=len(title))

    try:
        active_case = await bot_context.get_active_case(update)
        if not active_case:
            await message.reply_text(
                "ℹ️ No active case. Use /case_create or /case_get to select one."
            )
            return

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
            await message.reply_text(
                f"📝 Letter generated:\nTitle: {document.get('title', title)}\nFormat: {document.get('format', 'markdown')}"
            )
            logger.info(
                "telegram.generate_letter.sent", user_id=user_id, format=document.get("format")
            )
        else:
            error_msg = response.error or "generation failed"
            # Use parse_mode=None to avoid Markdown parsing errors
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error("telegram.generate_letter.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.generate_letter.exception", user_id=user_id, error=str(e))
        # Use parse_mode=None to avoid Markdown parsing errors
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


def get_handlers(bot_context: BotContext):
    return [CommandHandler("generate_letter", generate_letter)]
