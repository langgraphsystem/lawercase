"""Telegram bot handlers for MegaAgent commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

if TYPE_CHECKING:
    from telegram.ext import Application

    from config.settings import AppSettings
    from core.groupagents.mega_agent import MegaAgent

logger = structlog.get_logger(__name__)


def register_handlers(
    application: Application, *, mega_agent: MegaAgent, settings: AppSettings
) -> None:
    """Register all Telegram bot handlers."""
    # Create handler instances with dependencies
    handlers_factory = HandlersFactory(mega_agent=mega_agent, settings=settings)

    # Register command handlers
    application.add_handler(CommandHandler("start", handlers_factory.start))
    application.add_handler(CommandHandler("help", handlers_factory.help_command))
    application.add_handler(CommandHandler("ask", handlers_factory.ask))
    application.add_handler(CommandHandler("case_get", handlers_factory.case_get))
    application.add_handler(CommandHandler("memory_lookup", handlers_factory.memory_lookup))
    application.add_handler(CommandHandler("generate_letter", handlers_factory.generate_letter))

    # Handle text messages (for conversational mode)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers_factory.handle_message)
    )

    logger.info("telegram.handlers.registered")


class HandlersFactory:
    """Factory for creating Telegram bot handlers with injected dependencies."""

    def __init__(self, *, mega_agent: MegaAgent, settings: AppSettings) -> None:
        self.mega_agent = mega_agent
        self.settings = settings
        self.allowed_users = settings.allowed_user_ids()

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        if self.allowed_users is None:
            return True
        return user_id in self.allowed_users

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or "User"

        if not self._is_authorized(user_id):
            await update.message.reply_text(
                "⛔ Access denied. You are not authorized to use this bot."
            )
            logger.warning("telegram.unauthorized_access", user_id=user_id, username=username)
            return

        welcome_message = f"""
👋 *Привет, {username}!*

Я MegaAgent Pro - интеллектуальный помощник для юридической работы.

📋 *Доступные команды:*

🤖 *Основные:*
• `/ask <вопрос>` - задать вопрос агенту
• `/help` - показать справку

📁 *Дела:*
• `/case_get <case_id>` - получить информацию о деле

🧠 *Память:*
• `/memory_lookup <запрос>` - поиск в семантической памяти

✍️ *Документы:*
• `/generate_letter <заголовок>` - сгенерировать шаблон письма

Просто отправьте мне сообщение, и я постараюсь помочь!
        """
        await update.message.reply_text(welcome_message)
        logger.info("telegram.start_command", user_id=user_id, username=username)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        help_text = """
📖 *Справка по командам MegaAgent Pro*

🤖 *Работа с агентом:*
`/ask <вопрос>` - Задать вопрос MegaAgent
Пример: `/ask Какие документы нужны для визы H-1B?`

📁 *Управление делами:*
`/case_get <case_id>` - Получить информацию о деле
Пример: `/case_get CASE-2024-001`

🧠 *Поиск в памяти:*
`/memory_lookup <запрос>` - Поиск релевантной информации
Пример: `/memory_lookup иммиграционные документы`

✍️ *Генерация документов:*
`/generate_letter <заголовок>` - Создать шаблон письма
Пример: `/generate_letter Запрос дополнительных документов`

💡 *Подсказка:* Вы также можете просто написать вопрос без команды - бот поймет!
        """
        await update.message.reply_text(help_text)
        logger.info("telegram.help_command", user_id=user_id)

    async def ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ask command - query MegaAgent."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        # Extract question from command
        if not context.args:
            await update.message.reply_text(
                "❓ Пожалуйста, укажите вопрос.\nИспользование: `/ask <ваш вопрос>`"
            )
            return

        question = " ".join(context.args)
        await update.message.reply_text("🤔 Обрабатываю ваш вопрос...")

        try:
            # Call MegaAgent
            from core.groupagents.mega_agent import MegaAgentCommand, UserRole

            command = MegaAgentCommand(
                user_id=str(user_id),
                user_role=UserRole.LAWYER,
                intent="ask",
                message=question,
            )

            result = await self.mega_agent.handle_command(command)

            response = result.get("response", "Извините, не могу обработать запрос.")
            await update.message.reply_text(f"💡 *Ответ:*\n\n{response}")

            logger.info("telegram.ask_command", user_id=user_id, question=question)

        except Exception as e:
            logger.exception("telegram.ask_error", user_id=user_id, error=str(e))
            await update.message.reply_text(
                f"❌ Ошибка при обработке запроса: {e!s}\n\nПопробуйте еще раз позже."
            )

    async def case_get(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /case_get command - retrieve case information."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        if not context.args:
            await update.message.reply_text(
                "❓ Пожалуйста, укажите ID дела.\nИспользование: `/case_get <case_id>`"
            )
            return

        case_id = " ".join(context.args)
        await update.message.reply_text(f"🔍 Ищу дело {case_id}...")

        try:
            from core.groupagents.mega_agent import MegaAgentCommand, UserRole

            command = MegaAgentCommand(
                user_id=str(user_id),
                user_role=UserRole.LAWYER,
                intent="case.get",
                message=f"get case {case_id}",
                metadata={"case_id": case_id},
            )

            result = await self.mega_agent.handle_command(command)

            if result.get("status") == "not_found":
                await update.message.reply_text(f"❌ Дело `{case_id}` не найдено.")
            else:
                case_info = result.get("case", {})
                response = f"""
📁 *Информация о деле*

🆔 ID: `{case_info.get('case_id', case_id)}`
📋 Статус: {case_info.get('status', 'N/A')}
👤 Клиент: {case_info.get('client_name', 'N/A')}
📅 Создано: {case_info.get('created_at', 'N/A')}

📝 Описание:
{case_info.get('description', 'Нет описания')}
                """
                await update.message.reply_text(response)

            logger.info("telegram.case_get_command", user_id=user_id, case_id=case_id)

        except Exception as e:
            logger.exception("telegram.case_get_error", user_id=user_id, error=str(e))
            await update.message.reply_text(f"❌ Ошибка при получении дела: {e!s}")

    async def memory_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /memory_lookup command - search semantic memory."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        if not context.args:
            await update.message.reply_text(
                "❓ Пожалуйста, укажите запрос для поиска.\nИспользование: `/memory_lookup <запрос>`"
            )
            return

        query = " ".join(context.args)
        await update.message.reply_text(f"🔍 Ищу в памяти: {query}...")

        try:
            from core.groupagents.mega_agent import MegaAgentCommand, UserRole

            command = MegaAgentCommand(
                user_id=str(user_id),
                user_role=UserRole.LAWYER,
                intent="memory.search",
                message=query,
            )

            result = await self.mega_agent.handle_command(command)

            results = result.get("results", [])

            if not results:
                await update.message.reply_text("🔍 Ничего не найдено по запросу.")
            else:
                response = f"🧠 *Найдено {len(results)} результатов:*\n\n"
                for i, item in enumerate(results[:5], 1):  # Show top 5
                    response += f"{i}. {item.get('content', 'N/A')}\n"
                    response += f"   📊 Релевантность: {item.get('score', 0):.2f}\n\n"

                await update.message.reply_text(response)

            logger.info("telegram.memory_lookup_command", user_id=user_id, query=query)

        except Exception as e:
            logger.exception("telegram.memory_lookup_error", user_id=user_id, error=str(e))
            await update.message.reply_text(f"❌ Ошибка при поиске: {e!s}")

    async def generate_letter(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /generate_letter command - generate letter template."""
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        if not context.args:
            await update.message.reply_text(
                "❓ Пожалуйста, укажите заголовок письма.\n"
                "Использование: `/generate_letter <заголовок>`"
            )
            return

        title = " ".join(context.args)
        await update.message.reply_text(f"✍️ Генерирую письмо: {title}...")

        try:
            from core.groupagents.mega_agent import MegaAgentCommand, UserRole

            command = MegaAgentCommand(
                user_id=str(user_id),
                user_role=UserRole.LAWYER,
                intent="generate.letter",
                message=f"generate letter: {title}",
                metadata={"title": title},
            )

            result = await self.mega_agent.handle_command(command)

            letter_text = result.get("letter", "Не удалось сгенерировать письмо.")

            response = f"""
✍️ *Сгенерированное письмо*

📋 *Тема:* {title}

---

{letter_text}

---

💡 *Совет:* Проверьте и отредактируйте текст перед отправкой.
            """

            # Split long messages
            if len(response) > 4000:
                await update.message.reply_text(response[:4000])
                await update.message.reply_text(response[4000:])
            else:
                await update.message.reply_text(response)

            logger.info("telegram.generate_letter_command", user_id=user_id, title=title)

        except Exception as e:
            logger.exception("telegram.generate_letter_error", user_id=user_id, error=str(e))
            await update.message.reply_text(f"❌ Ошибка при генерации письма: {e!s}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle plain text messages (conversational mode)."""
        if not update.effective_user or not update.message or not update.message.text:
            return

        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        message_text = update.message.text
        await update.message.reply_text("🤔 Думаю...")

        try:
            from core.groupagents.mega_agent import MegaAgentCommand, UserRole

            command = MegaAgentCommand(
                user_id=str(user_id),
                user_role=UserRole.LAWYER,
                intent="chat",
                message=message_text,
            )

            result = await self.mega_agent.handle_command(command)

            response = result.get("response", "Извините, не могу ответить на это.")
            await update.message.reply_text(response)

            logger.info(
                "telegram.message_handled", user_id=user_id, message_length=len(message_text)
            )

        except Exception as e:
            logger.exception("telegram.message_error", user_id=user_id, error=str(e))
            await update.message.reply_text(
                "❌ Извините, произошла ошибка при обработке сообщения.\n\n"
                "Попробуйте использовать команды: /help"
            )
