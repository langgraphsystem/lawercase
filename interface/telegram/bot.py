"""Main Telegram bot application."""

import asyncio
import logging
import signal
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import get_settings
from .handlers import register_handlers
from .middlewares import setup_middlewares

logger = logging.getLogger(__name__)


class TelegramBot:
    """Main Telegram bot application."""

    def __init__(self, token: str):
        self.token = token
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the bot."""
        try:
            # Create bot and dispatcher
            self.bot = Bot(
                token=self.token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            self.dp = Dispatcher()

            # Setup middlewares
            setup_middlewares(self.dp)

            # Register handlers
            register_handlers(self.dp)

            # Setup graceful shutdown
            self._setup_signal_handlers()

            logger.info("Starting Telegram bot...")

            # Start polling
            await self.dp.start_polling(self.bot)

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping Telegram bot...")

        if self.dp:
            await self.dp.stop_polling()

        if self.bot:
            await self.bot.session.close()

        self._shutdown_event.set()
        logger.info("Bot stopped")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()


async def create_bot() -> TelegramBot:
    """Create and configure bot instance."""
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    return TelegramBot(settings.telegram_bot_token)