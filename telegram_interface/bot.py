"""Telegram bot entrypoint integrating with MegaAgent."""

from __future__ import annotations

import asyncio

import structlog
import typer
from telegram.ext import Application, ApplicationBuilder, Defaults

from config.logging import setup_logging
from config.settings import get_settings
from core.groupagents.mega_agent import MegaAgent
from core.memory.memory_manager import MemoryManager
from telegram_interface.handlers import register_handlers

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Run the MegaAgent Telegram bot.")


async def run_bot(*, poll_interval: float = 0.0) -> None:
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

    logger.info("telegram.bot.starting")
    await application.initialize()
    await application.start()
    await application.start_polling(poll_interval=poll_interval)
    try:
        await application.wait_until_closed()
    finally:
        await application.stop()
        await application.shutdown()
        logger.info("telegram.bot.stopped")


@cli.command()
def main(
    poll_interval: float = typer.Option(0.0, min=0.0, help="Polling interval in seconds"),
) -> None:
    """CLI entrypoint for running the Telegram bot."""
    try:
        asyncio.run(run_bot(poll_interval=poll_interval))
    except KeyboardInterrupt:  # pragma: no cover - CLI shutdown
        logger.info("telegram.bot.interrupted")
    except Exception as exc:
        logger.exception("telegram.bot.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
