"""Simple bot test - minimal working version."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA"  # pragma: allowlist secret  # nosec


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я MegaAgent Pro бот и я работаю!\n\n"
        "Доступные команды:\n"
        "• /start - Начать работу\n"
        "• /help - Показать справку\n"
        "• /ask - Задать вопрос\n"
        "• /test - Проверить работу\n\n"
        "Просто напишите мне что-нибудь!"
    )
    logger.info(f"User {user.id} ({user.username}) started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "📖 Справка:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/ask - Задать вопрос (в разработке)\n"
        "/test - Проверить работу бота\n\n"
        "Вы также можете просто написать сообщение!"
    )


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ask command."""
    if not context.args:
        await update.message.reply_text("Использование: /ask <ваш вопрос>")
        return

    question = " ".join(context.args)
    await update.message.reply_text(
        f"🤔 Вы спросили: {question}\n\n"
        "⚙️ Интеграция с AI в разработке.\n"
        "Пока что бот просто показывает ваш вопрос."
    )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to verify bot is working."""
    await update.message.reply_text(
        "✅ Бот работает отлично!\n\n"
        "Все системы в норме:\n"
        "• Получение сообщений: ✅\n"
        "• Отправка ответов: ✅\n"
        "• Обработка команд: ✅\n\n"
        "Попробуйте написать что-нибудь!"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    user_message = update.message.text
    await update.message.reply_text(
        f"💬 Вы написали: {user_message}\n\n"
        "✅ Я получил ваше сообщение!\n"
        "🚀 Бот работает корректно!\n\n"
        "Используйте /help для списка команд."
    )
    logger.info(f"Received message: {user_message}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")


def main() -> None:
    """Start the bot."""
    print("🚀 Starting bot...")
    print(f"Token: {BOT_TOKEN[:20]}...")

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("test", test_command))

    # Handle all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Register error handler
    application.add_error_handler(error_handler)

    print("✅ Bot is ready!")
    print("📱 Open Telegram and send /start to @lawercasebot")
    print("🔄 Polling for updates...")

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
