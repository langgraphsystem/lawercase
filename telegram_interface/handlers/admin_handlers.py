"""Administrative and common command handlers."""

from __future__ import annotations

import asyncio
import os

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext

logger = structlog.get_logger(__name__)

_TELEGRAM_MAX_CHARS = 4096
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


HELP_TEXT = (
    "Available commands:\n"
    "/case_create <title> | <description> — Create a new case.\n"
    "/case_get <case_id> — Fetch case details.\n"
    "/case_active — Show current active case.\n"
    "/case_list [page] — List all your cases.\n"
    "/ask <question> — Ask MegaAgent.\n"
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
    logger.debug("telegram.start.auth_check", user_id=user_id)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.start.unauthorized", user_id=user_id)
        return

    try:
        sent = await update.effective_message.reply_text(
            "👋 Welcome to MegaAgent EB-1A assistant! Use /help to see available commands."
        )
        logger.info(
            "telegram.start.sent", user_id=user_id, message_id=getattr(sent, "message_id", None)
        )
    except Exception as e:
        logger.exception("telegram.start.error", user_id=user_id, error=str(e))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.help_command.received", user_id=user_id)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.help_command.unauthorized", user_id=user_id)
        return
    try:
        sent = await update.effective_message.reply_text(HELP_TEXT)
        logger.info(
            "telegram.help_command.sent",
            user_id=user_id,
            message_id=getattr(sent, "message_id", None),
        )
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
    # Derive question from args or raw text (fallback for edge cases like mentions)
    question = ""
    if context.args:
        question = " ".join(context.args).strip()
    else:
        raw = (message.text or message.caption or "").strip()
        try:
            import re

            m = re.match(r"^/ask(?:@[A-Za-z0-9_]+)?\s*(.*)$", raw)
            if m:
                question = (m.group(1) or "").strip()
        except Exception:  # nosec B110 - regex best-effort
            pass

    if not question:
        logger.warning("telegram.ask.no_args", user_id=user_id)
        try:
            await message.reply_text("Usage: /ask <question>")
            logger.info("telegram.ask.usage_sent", user_id=user_id)
        except Exception as e:
            logger.exception("telegram.ask.usage_send_failed", user_id=user_id, error=str(e))
        return
    logger.info("telegram.ask.processing", user_id=user_id, question_length=len(question))

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.ASK,
            action="ask",
            payload={"query": question},
        )
        logger.info("telegram.ask.command_created", user_id=user_id, command_id=command.command_id)

        try:
            ask_timeout = float(os.getenv("TELEGRAM_ASK_TIMEOUT", "45.0"))
            response = await asyncio.wait_for(
                bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER),
                timeout=ask_timeout,
            )
        except TimeoutError:
            await message.reply_text("⏳ Превышено время ожидания ответа. Попробуйте снова.")
            logger.error(
                "telegram.ask.timeout",
                user_id=user_id,
                command_id=command.command_id,
                timeout_seconds=ask_timeout,
            )
            return
        logger.info(
            "telegram.ask.response_received",
            user_id=user_id,
            success=response.success,
            command_id=command.command_id,
        )
        # Log LLM provider/model if available
        try:
            if response.success and response.result:
                prov = response.result.get("llm_provider")
                mdl = response.result.get("llm_model")
                if prov or mdl:
                    logger.info("telegram.ask.llm_used", user_id=user_id, provider=prov, model=mdl)
        except Exception:  # nosec B110 - optional logging
            pass

        if response.success and response.result:
            result = response.result
            llm_answer = result.get("llm_response")
            # DEBUG: Log what we got from MegaAgent
            logger.info(
                "telegram.ask.result_debug",
                user_id=user_id,
                has_llm_response=bool(llm_answer),
                llm_response_length=len(llm_answer or ""),
                llm_response_type=type(llm_answer).__name__,
                llm_response_repr=(
                    repr(llm_answer[:200] if isinstance(llm_answer, str) else str(llm_answer)[:200])
                    if llm_answer
                    else None
                ),
                result_keys=list(result.keys()),
            )
            if llm_answer:
                chunks = _split_for_telegram(llm_answer)
                for idx, chunk in enumerate(chunks):
                    try:
                        sent = await message.reply_text(chunk)
                        logger.info(
                            "telegram.ask.sent",
                            user_id=user_id,
                            response_length=len(chunk),
                            chunk_index=idx,
                            chunks_total=len(chunks),
                            message_id=getattr(sent, "message_id", None),
                        )
                    except Exception as e:
                        logger.exception("telegram.ask.send_failed", user_id=user_id, error=str(e))
                        break
                return
            # Fallback: show prompt analysis and retrieved memory summary
            retrieved = result.get("retrieved", [])
            text = result.get("prompt_analysis", {}).get("issues") or "✅ Query processed."
            if retrieved:
                summary = "\n".join(f"• {item.get('text', '')}" for item in retrieved[:5])
                try:
                    sent = await message.reply_text(f"{text}\n{summary}")
                    logger.info(
                        "telegram.ask.sent_with_memory",
                        user_id=user_id,
                        retrieved_count=len(retrieved),
                        message_id=getattr(sent, "message_id", None),
                    )
                except Exception as e:
                    logger.exception("telegram.ask.send_failed", user_id=user_id, error=str(e))
                logger.info(
                    "telegram.ask.sent_with_memory", user_id=user_id, retrieved_count=len(retrieved)
                )
            else:
                try:
                    sent = await message.reply_text(text)
                    logger.info(
                        "telegram.ask.sent_fallback",
                        user_id=user_id,
                        message_id=getattr(sent, "message_id", None),
                    )
                except Exception as e:
                    logger.exception("telegram.ask.send_failed", user_id=user_id, error=str(e))
        else:
            error_msg = response.error or "unknown"
            # Use parse_mode=None to avoid Markdown parsing errors
            try:
                sent = await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
                logger.error(
                    "telegram.ask.failed",
                    user_id=user_id,
                    error=error_msg,
                    message_id=getattr(sent, "message_id", None),
                )
            except Exception as e:
                logger.exception("telegram.ask.send_failed", user_id=user_id, error=str(e))
    except Exception as e:
        logger.exception("telegram.ask.exception", user_id=user_id, error=str(e))
        # Use parse_mode=None to avoid Markdown parsing errors
        try:
            await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)
        except Exception:  # nosec B110 - optional logging
            pass


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


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    text = update.effective_message.text if update.effective_message else ""
    logger.warning("telegram.unknown_command", user_id=user_id, text=text)
    if update.effective_message:
        try:
            sent = await update.effective_message.reply_text(
                "⚠️ Unknown command. Use /help for the list of commands."
            )
            logger.info(
                "telegram.unknown_command.sent",
                user_id=user_id,
                message_id=getattr(sent, "message_id", None),
            )
        except Exception as e:
            logger.exception("telegram.unknown_command.send_failed", user_id=user_id, error=str(e))


def get_handlers(bot_context: BotContext):
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("ask", ask_command),
        # Fallback regex to catch '/ask@bot' or formatting edge cases
        MessageHandler(filters.TEXT & filters.Regex(r"^/ask(?:@[A-Za-z0-9_]+)?\b"), ask_command),
        CommandHandler("memory_lookup", memory_lookup_command),
    ]


def get_unknown_handler() -> MessageHandler:
    return MessageHandler(filters.COMMAND, unknown_command)
