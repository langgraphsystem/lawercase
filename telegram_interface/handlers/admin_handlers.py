"""Administrative and common command handlers."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext

logger = structlog.get_logger(__name__)


HELP_TEXT = (
    "Available commands:\n"
    "/ask <question> — Ask MegaAgent.\n"
    "/case_get <case_id> — Fetch case details.\n"
    "/memory_lookup <query> — Search semantic memory.\n"
    "/generate_letter <title> — Generate letter draft.\n"
    "/chat <prompt> — Direct GPT-5 response via OpenAI SDK.\n"
    "/models — List available OpenAI models."
)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        update.effective_message.reply_text("🚫 Access denied.")
    logger.warning("telegram.unauthorized", user_id=user_id)
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    username = update.effective_user.username if update.effective_user else None
    logger.info("telegram.start.received", user_id=user_id, username=username)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.start.unauthorized", user_id=user_id)
        return

    try:
        await update.effective_message.reply_text(
            "👋 Welcome to MegaAgent EB-1A assistant! Use /help to see available commands."
        )
        logger.info("telegram.start.sent", user_id=user_id)
    except Exception as e:
        logger.exception("telegram.start.error", user_id=user_id, error=str(e))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.help_command.received", user_id=user_id)
    try:
        await update.effective_message.reply_text(HELP_TEXT)
        logger.info("telegram.help_command.sent", user_id=user_id)
    except Exception as e:  # pragma: no cover - network/runtime
        logger.exception("telegram.help_command.error", user_id=user_id, error=str(e))


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    username = update.effective_user.username if update.effective_user else None
    logger.info("telegram.ask.received", user_id=user_id, username=username)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.ask.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.ask.no_args", user_id=user_id)
        await message.reply_text("Usage: /ask <question>")
        return

    question = " ".join(context.args)
    logger.info("telegram.ask.processing", user_id=user_id, question_length=len(question))

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.ASK,
            action="ask",
            payload={"query": question},
        )
        logger.info("telegram.ask.command_created", user_id=user_id, command_id=command.command_id)

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.ask.response_received",
            user_id=user_id,
            success=response.success,
            command_id=command.command_id,
        )

        if response.success and response.result:
            result = response.result
            llm_answer = result.get("llm_response")
            if llm_answer:
                await message.reply_text(llm_answer)
                logger.info("telegram.ask.sent", user_id=user_id, response_length=len(llm_answer))
                return
            # Fallback: show prompt analysis and retrieved memory summary
            retrieved = result.get("retrieved", [])
            text = result.get("prompt_analysis", {}).get("issues") or "✅ Query processed."
            if retrieved:
                summary = "\n".join(f"• {item.get('text', '')}" for item in retrieved[:5])
                await message.reply_text(f"{text}\n{summary}")
                logger.info(
                    "telegram.ask.sent_with_memory", user_id=user_id, retrieved_count=len(retrieved)
                )
            else:
                await message.reply_text(text)
                logger.info("telegram.ask.sent_fallback", user_id=user_id)
        else:
            error_msg = response.error or "unknown"
            # Use parse_mode=None to avoid Markdown parsing errors
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error("telegram.ask.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.ask.exception", user_id=user_id, error=str(e))
        # Use parse_mode=None to avoid Markdown parsing errors
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def memory_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    username = update.effective_user.username if update.effective_user else None
    logger.info("telegram.memory_lookup.received", user_id=user_id, username=username)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.memory_lookup.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.memory_lookup.no_args", user_id=user_id)
        await message.reply_text("Usage: /memory_lookup <query>")
        return

    query = " ".join(context.args)
    logger.info("telegram.memory_lookup.processing", user_id=user_id, query_length=len(query))

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.ADMIN,
            action="memory_lookup",
            payload={"query": query},
        )
        logger.info(
            "telegram.memory_lookup.command_created", user_id=user_id, command_id=command.command_id
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.ADMIN)
        logger.info(
            "telegram.memory_lookup.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            results = response.result.get("results", [])
            lines = ["🔍 Memory hits:"]
            for item in results[:5]:
                text = item.get("text") or item.get("metadata", {}).get("summary")
                if text:
                    lines.append(f"• {text}")
            await message.reply_text("\n".join(lines))
            logger.info("telegram.memory_lookup.sent", user_id=user_id, results_count=len(results))
        else:
            error_msg = response.error or "lookup failed"
            await message.reply_text(f"❌ Error: {error_msg}")
            logger.error("telegram.memory_lookup.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.memory_lookup.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}")


def get_handlers(bot_context: BotContext):
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("ask", ask_command),
        CommandHandler("memory_lookup", memory_lookup_command),
    ]
