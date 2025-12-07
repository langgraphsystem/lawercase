"""Administrative and common command handlers."""

from __future__ import annotations

import asyncio
import os

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole

from .context import BotContext
from .response_utils import send_response

logger = structlog.get_logger(__name__)


HELP_TEXT = """📋 Доступные команды MegaAgent EB-1A:

🗂️ Управление кейсами:
/case_create — Создать новый кейс
/case_get — Открыть кейс по ID
/case_list — Список всех кейсов
/case_active — Показать активный кейс
/case_update — Редактировать кейс
/case_delete — Удалить кейс
/case_archive — Архивировать кейс

📝 Анкетирование:
/intake_start — Начать анкетирование
/intake_status — Прогресс анкеты
/intake_resume — Продолжить с паузы
/intake_cancel — Отменить анкету

📊 EB-1A Анализ:
/eb1_potential — Быстрая оценка потенциала
/eb1_analyze — Полный анализ критериев

🔍 Поиск и память:
/ask — Спросить MegaAgent
/kb_search — Поиск в базе знаний
/memory_search — Поиск по всей памяти
/kb_stats — Статистика базы знаний
/memory_stats — Полная статистика памяти

📄 Документы:
/generate_letter — Сгенерировать письмо
(Отправьте PDF файл для загрузки)

🔌 MCP Инструменты:
/mcp_status — Статус MCP серверов
/mcp_connect — Подключиться к MCP
/mcp_tools — Список доступных инструментов
/mcp_query — Запрос через MCP агента
/mcp_disconnect — Отключиться от MCP

⚙️ Система:
/menu — Главное меню
/status — Статус системы
/cancel — Отменить текущее действие
/help — Эта справка"""


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
            # Increased timeout to allow slow database queries (semantic + RFE)
            ask_timeout = float(os.getenv("TELEGRAM_ASK_TIMEOUT", "65.0"))
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
                await send_response(
                    message=message,
                    text=llm_answer,
                    filename="response.txt",
                    parse_mode=None,  # LLM responses may have special chars
                )
                logger.info(
                    "telegram.ask.sent",
                    user_id=user_id,
                    response_length=len(llm_answer),
                )
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


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu with inline keyboard buttons."""
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.menu.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return

    keyboard = [
        [
            InlineKeyboardButton("📁 Мои кейсы", callback_data="menu_cases"),
            InlineKeyboardButton("➕ Новый кейс", callback_data="menu_new_case"),
        ],
        [
            InlineKeyboardButton("📝 Анкета", callback_data="menu_intake"),
            InlineKeyboardButton("📊 EB-1A анализ", callback_data="menu_eb1"),
        ],
        [
            InlineKeyboardButton("🔍 Поиск", callback_data="menu_search"),
            InlineKeyboardButton("📄 Документы", callback_data="menu_docs"),
        ],
        [
            InlineKeyboardButton("⚙️ Статус", callback_data="menu_status"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "🏠 *Главное меню MegaAgent EB-1A*\n\n" "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    logger.info("telegram.menu.sent", user_id=user_id)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id if update.effective_user else None
    action = query.data

    logger.info("telegram.menu.callback", user_id=user_id, action=action)

    responses = {
        "menu_cases": "📁 *Управление кейсами:*\n\n"
        "/case_list — Список всех кейсов\n"
        "/case_active — Текущий активный кейс\n"
        "/case_get <id> — Открыть кейс",
        "menu_new_case": "➕ *Создание кейса:*\n\n"
        "Используйте команду:\n"
        "`/case_create Название | Описание`\n\n"
        "Пример:\n"
        "`/case_create John Smith | EB-1A petition for researcher`",
        "menu_intake": "📝 *Анкетирование клиента:*\n\n"
        "/intake_start — Начать анкету\n"
        "/intake_status — Прогресс\n"
        "/intake_resume — Продолжить\n"
        "/intake_cancel — Отменить",
        "menu_eb1": "📊 *EB-1A Анализ:*\n\n"
        "/eb1_potential — Быстрая оценка\n"
        "/eb1_analyze — Полный анализ критериев",
        "menu_search": "🔍 *Поиск:*\n\n"
        "/ask <вопрос> — Спросить MegaAgent\n"
        "/kb_search <запрос> — Поиск в базе знаний\n"
        "/memory_search <запрос> — Поиск по памяти",
        "menu_docs": "📄 *Документы:*\n\n"
        "/generate_letter <тип> — Генерация письма\n\n"
        "Для загрузки PDF просто отправьте файл в чат.",
        "menu_status": "⚙️ Используйте /status для проверки системы",
        "menu_help": "❓ Используйте /help для полного списка команд",
    }

    text = responses.get(action, "Неизвестное действие")
    await query.edit_message_text(text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system status and diagnostics."""
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.status.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return

    message = update.effective_message
    await message.reply_text("⏳ Проверяю статус системы...")

    try:
        # Check MegaAgent status
        mega_agent = bot_context.mega_agent
        agent_status = "✅ Активен" if mega_agent else "❌ Не инициализирован"

        # Check memory status
        memory_status = "❌ Недоступна"
        memory_records = 0
        if hasattr(mega_agent, "memory") and mega_agent.memory:
            memory_status = "✅ Подключена"
            try:
                # Try to get stats from memory
                if hasattr(mega_agent.memory, "stats"):
                    stats = await mega_agent.memory.stats()
                    memory_records = stats.get("total_records", 0)
            except Exception:  # nosec B110 - optional stats
                pass

        # Get active case
        active_case = await bot_context.get_active_case(update)
        case_status = f"`{active_case}`" if active_case else "Не выбран"

        # Build status message
        status_text = (
            "⚙️ *Статус системы MegaAgent EB-1A*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 *MegaAgent:* {agent_status}\n"
            f"💾 *Память:* {memory_status}\n"
            f"📊 *Записей:* {memory_records}\n"
            f"📁 *Активный кейс:* {case_status}\n"
            f"👤 *User ID:* `{user_id}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Система работает нормально"
        )

        await message.reply_text(status_text, parse_mode="Markdown")
        logger.info("telegram.status.sent", user_id=user_id)

    except Exception as e:
        logger.exception("telegram.status.error", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Ошибка получения статуса: {e!s}")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current operation and clear user state."""
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.cancel.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not _is_authorized(bot_context, update):
        return

    # Clear any pending operations in user_data
    cleared_items = []

    if context.user_data:
        # Clear pending PDF
        if "pending_pdf" in context.user_data:
            del context.user_data["pending_pdf"]
            cleared_items.append("PDF загрузка")

        # Clear intake state
        if "intake_state" in context.user_data:
            del context.user_data["intake_state"]
            cleared_items.append("Анкета")

        # Clear any pending confirmations
        if "pending_confirmation" in context.user_data:
            del context.user_data["pending_confirmation"]
            cleared_items.append("Подтверждение")

    if cleared_items:
        text = "🚫 Отменено:\n• " + "\n• ".join(cleared_items)
    else:
        text = "✅ Нет активных операций для отмены."

    await update.effective_message.reply_text(text)
    logger.info("telegram.cancel.done", user_id=user_id, cleared=cleared_items)


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
        CommandHandler("menu", menu_command),
        CommandHandler("status", status_command),
        CommandHandler("cancel", cancel_command),
        CommandHandler("ask", ask_command),
        # Fallback regex to catch '/ask@bot' or formatting edge cases
        MessageHandler(filters.TEXT & filters.Regex(r"^/ask(?:@[A-Za-z0-9_]+)?\b"), ask_command),
        # Menu callback handler
        CallbackQueryHandler(menu_callback, pattern="^menu_"),
    ]


def get_unknown_handler() -> MessageHandler:
    return MessageHandler(filters.COMMAND, unknown_command)
