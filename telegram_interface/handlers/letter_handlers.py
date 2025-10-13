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
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /generate_letter <title>")
        return
    title = " ".join(context.args)
    payload = {"document_type": "letter", "content_data": {"title": title}}
    command = MegaAgentCommand(
        user_id=str(update.effective_user.id),
        command_type=CommandType.GENERATE,
        action="letter",
        payload=payload,
    )
    response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
    if response.success and response.result:
        document = response.result.get("document", {})
        await message.reply_text(
            f"📝 Letter generated:\nTitle: {document.get('title', title)}\nFormat: {document.get('format', 'markdown')}"
        )
    else:
        await message.reply_text(f"❌ Error: {response.error or 'generation failed'}")


def get_handlers(bot_context: BotContext):
    return [CommandHandler("generate_letter", generate_letter)]
