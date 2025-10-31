"""Telegram bot entrypoint integrating with MegaAgent."""

from __future__ import annotations

import asyncio

import structlog
import typer
from telegram import Update
from telegram.ext import (Application, ApplicationBuilder, ContextTypes,
                          Defaults)

from config.logging import setup_logging
from config.settings import get_settings
from core.groupagents.mega_agent import MegaAgent
from core.memory.memory_manager import MemoryManager
from telegram_interface.handlers import register_handlers

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Run the MegaAgent Telegram bot.")


async def run_bot_async(*, poll_interval: float = 0.0) -> None:
    """Run the Telegram bot asynchronously."""
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    memory_manager = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory_manager)

    application: Application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .defaults(Defaults(parse_mode="Markdown"))
        .concurrent_updates(False)
        .build()
    )

    register_handlers(application, mega_agent=mega_agent, settings=settings)

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:  # type: ignore[valid-type]
        # Central error logger to avoid silent failures that can block handlers
        try:
            user_id = None
            if isinstance(update, Update) and update.effective_user:
                user_id = update.effective_user.id
            logger.exception(
                "telegram.error",
                user_id=user_id,
                error=str(context.error) if getattr(context, "error", None) else "unknown",
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("telegram.error_handler_failed")

    # Capture unhandled exceptions from handlers
    application.add_error_handler(on_error)

    logger.info("telegram.bot.starting")
    # Use run_polling which handles event loop, initialization, start, and cleanup
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        poll_interval=poll_interval, allowed_updates=Update.ALL_TYPES
    )

    logger.info("telegram.bot.running")

    # Keep running until interrupted
    try:
        # Run indefinitely
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("telegram.bot.stopping")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def run_bot(*, poll_interval: float = 0.0) -> None:
    """Run the Telegram bot using synchronous entry point."""
    asyncio.run(run_bot_async(poll_interval=poll_interval))


@cli.command()
def main(
    poll_interval: float = typer.Option(0.0, min=0.0, help="Polling interval in seconds"),
) -> None:
    """CLI entrypoint for running the Telegram bot."""
    try:
        run_bot(poll_interval=poll_interval)
    except KeyboardInterrupt:  # pragma: no cover - CLI shutdown
        logger.info("telegram.bot.interrupted")
    except Exception as exc:
        logger.exception("telegram.bot.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
