"""Case-related Telegram handlers."""

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
    logger.warning("telegram.case.unauthorized", user_id=user_id)
    return False


async def case_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_get.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.case_get.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.case_get.no_args", user_id=user_id)
        await message.reply_text("Usage: /case_get <case_id>")
        return

    case_id = context.args[0]
    logger.info("telegram.case_get.processing", user_id=user_id, case_id=case_id)

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": case_id},
        )
        logger.info(
            "telegram.case_get.command_created", user_id=user_id, command_id=command.command_id
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.case_get.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            case = response.result.get("case") or {}
            title = case.get("title", "(no title)")
            status = case.get("status", "unknown")
            await message.reply_text(f"📁 {case_id}: {title}\nStatus: {status}")
            logger.info("telegram.case_get.sent", user_id=user_id, case_id=case_id, status=status)
        else:
            error_msg = response.error or "case not found"
            await message.reply_text(f"❌ Error: {error_msg}")
            logger.error(
                "telegram.case_get.failed", user_id=user_id, case_id=case_id, error=error_msg
            )
    except Exception as e:
        logger.exception(
            "telegram.case_get.exception", user_id=user_id, case_id=case_id, error=str(e)
        )
        await message.reply_text(f"❌ Exception: {e!s}")


def get_handlers(bot_context: BotContext):
    return [CommandHandler("case_get", case_get)]
