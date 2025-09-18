#!/usr/bin/env python3
"""Telegram bot entrypoint script."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from interface.telegram.bot import create_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main bot entry point."""
    try:
        # Check configuration
        settings = get_settings()
        if not settings.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is required but not set")
            sys.exit(1)

        logger.info("Starting Mega Agent Pro Telegram Bot...")
        logger.info(f"Admin user ID: {settings.telegram_admin_user_id}")

        # Create and start bot
        bot = await create_bot()

        # Start bot (this will run until interrupted)
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())