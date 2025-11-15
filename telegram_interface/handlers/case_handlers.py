"""Case-related Telegram handlers."""

from __future__ import annotations

from typing import Any

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext

logger = structlog.get_logger(__name__)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _extract_case_payload(
    result: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """
    Normalizes MegaAgent responses by surfacing the actual case payload and ID.

    Returns:
        (result_dict, case_dict, case_id)
    """
    result_dict = result or {}
    case_data = result_dict.get("case")
    if not isinstance(case_data, dict):
        case_result = result_dict.get("case_result")
        if isinstance(case_result, dict):
            nested_case = case_result.get("case")
            if isinstance(nested_case, dict):
                case_data = nested_case
    if not isinstance(case_data, dict):
        case_data = {}

    case_id = result_dict.get("case_id") or case_data.get("case_id")
    return result_dict, case_data, case_id


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("🚫 Access denied.")
    logger.warning("telegram.case.unauthorized", user_id=user_id)
    return False


async def case_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_get.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
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
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        logger.info(
            "telegram.case_get.command_created", user_id=user_id, command_id=command.command_id
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.case_get.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            result_payload, case_data, normalized_case_id = _extract_case_payload(response.result)
            title = (
                case_data.get("title")
                or result_payload.get("title")
                or result_payload.get("case_title")
                or "(no title)"
            )
            status = (
                case_data.get("status")
                or result_payload.get("status")
                or result_payload.get("case_status")
                or "unknown"
            )
            display_case_id = normalized_case_id or case_id
            await message.reply_text(f"📁 {display_case_id}: {title}\nStatus: {status}")
            logger.info(
                "telegram.case_get.sent",
                user_id=user_id,
                case_id=display_case_id,
                status=status,
            )
        else:
            error_msg = response.error or "case not found"
            # Use parse_mode=None to avoid Markdown parsing errors
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error(
                "telegram.case_get.failed", user_id=user_id, case_id=case_id, error=error_msg
            )
    except Exception as e:
        logger.exception(
            "telegram.case_get.exception", user_id=user_id, case_id=case_id, error=str(e)
        )
        # Use parse_mode=None to avoid Markdown parsing errors
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def case_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_create.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.case_create.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /case_create <title> | optional description")
        return

    raw = " ".join(context.args)
    parts = [part.strip() for part in raw.split("|", 1)]
    title = parts[0]
    description = parts[1] if len(parts) > 1 else None

    try:
        # Prepare case creation payload with required fields
        payload = {
            "title": title,
            "description": description or f"Case: {title}",  # description is required
            "case_type": "immigration",  # default to immigration (most common type)
            "client_id": str(update.effective_user.id),  # use telegram user_id as client_id
        }

        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="create",
            payload=payload,
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)

        if response.success and response.result:
            result_payload, case_data, case_id = _extract_case_payload(response.result)
            reply_case_id = case_id or result_payload.get("case_id")
            if reply_case_id:
                await bot_context.set_active_case(update, reply_case_id)
            case_title = case_data.get("title") or result_payload.get("title") or title
            await message.reply_text(
                f"📁 Case created: {case_title}\nID: {reply_case_id or 'unknown'}"
            )
            logger.info("telegram.case_create.success", user_id=user_id, case_id=reply_case_id)
        else:
            error_msg = response.error or "case creation failed"
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error("telegram.case_create.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.case_create.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def case_active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_active.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    active_case = await bot_context.get_active_case(update)
    if not active_case:
        await message.reply_text("ℹ️ No active case. Use /case_create or /case_get to select one.")
        return

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": active_case},
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        if response.success and response.result:
            result_payload, case_data, case_id = _extract_case_payload(response.result)
            case_id_display = case_id or active_case
            case_title = case_data.get("title") or result_payload.get("title") or "(no title)"
            case_status = case_data.get("status") or result_payload.get("status") or "unknown"
            await message.reply_text(
                f"📌 Active case: {case_id_display}\nTitle: {case_title}\nStatus: {case_status}"
            )
        else:
            await message.reply_text(
                f"⚠️ Active case id {active_case} not found (maybe deleted).",
                parse_mode=None,
            )
    except Exception as e:
        logger.exception("telegram.case_active.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


def get_handlers(bot_context: BotContext):
    return [
        CommandHandler("case_create", case_create),
        CommandHandler("case_get", case_get),
        CommandHandler("case_active", case_active),
    ]
