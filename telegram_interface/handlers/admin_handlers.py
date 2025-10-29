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
    "/generate_letter <title> — Generate letter draft."
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
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    await update.effective_message.reply_text(
        "👋 Welcome to MegaAgent EB-1A assistant! Use /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    await update.effective_message.reply_text(HELP_TEXT)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /ask <question>")
        return
    question = " ".join(context.args)
    command = MegaAgentCommand(
        user_id=str(update.effective_user.id),
        command_type=CommandType.ASK,
        action="ask",
        payload={"query": question},
    )
    response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
    if response.success and response.result:
        result = response.result
        llm_answer = result.get("llm_response")
        if llm_answer:
            await message.reply_text(llm_answer)
            return
        # Fallback: show prompt analysis and retrieved memory summary
        retrieved = result.get("retrieved", [])
        text = result.get("prompt_analysis", {}).get("issues") or "✅ Query processed."
        if retrieved:
            summary = "\n".join(f"• {item.get('text', '')}" for item in retrieved[:5])
            await message.reply_text(f"{text}\n{summary}")
        else:
            await message.reply_text(text)
    else:
        await message.reply_text(f"❌ Error: {response.error or 'unknown'}")


async def memory_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return
    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /memory_lookup <query>")
        return
    query = " ".join(context.args)
    command = MegaAgentCommand(
        user_id=str(update.effective_user.id),
        command_type=CommandType.ADMIN,
        action="memory_lookup",
        payload={"query": query},
    )
    response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.ADMIN)
    if response.success and response.result:
        results = response.result.get("results", [])
        lines = ["🔍 Memory hits:"]
        for item in results[:5]:
            text = item.get("text") or item.get("metadata", {}).get("summary")
            if text:
                lines.append(f"• {text}")
        await message.reply_text("\n".join(lines))
    else:
        await message.reply_text(f"❌ Error: {response.error or 'lookup failed'}")


def get_handlers(bot_context: BotContext):
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("ask", ask_command),
        CommandHandler("memory_lookup", memory_lookup_command),
    ]
