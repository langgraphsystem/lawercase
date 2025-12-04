"""Telegram application factory integrating MegaAgent via webhook."""

from __future__ import annotations

import structlog
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, ApplicationBuilder, ContextTypes,
                          Defaults, MessageHandler, filters)

from config.logging import setup_logging
from config.settings import AppSettings, get_settings
from core.groupagents.mega_agent import MegaAgent
from core.memory.memory_manager import MemoryManager
from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore
from telegram_interface.handlers import register_handlers
from telegram_interface.middlewares.di_injection import setup_di_middleware

logger = structlog.get_logger(__name__)


def build_application(
    *, settings: AppSettings | None = None, mega_agent: MegaAgent | None = None
) -> Application:
    """Create a telegram Application with all handlers registered."""

    # Load environment variables from .env when available (no override in production)
    try:
        load_dotenv(override=False)
        logger.debug("telegram.env.loaded")
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("telegram.env.load_failed")

    settings = settings or get_settings()
    setup_logging(settings.log_level)

    token = settings.telegram_token or settings.telegram_bot_token_legacy
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not configured")

    # CRITICAL FIX: Use SupabaseSemanticStore instead of in-memory SemanticStore
    # This ensures intake answers are persisted to database
    logger.info("telegram.memory.initializing_supabase_store")
    memory_manager = MemoryManager(semantic=SupabaseSemanticStore())
    mega_agent = mega_agent or MegaAgent(memory_manager=memory_manager)

    application: Application = (
        ApplicationBuilder()
        .token(token)
        .defaults(Defaults(parse_mode=None))
        .concurrent_updates(False)
        .build()
    )

    # Setup DI middleware to inject dependencies into all handlers
    setup_di_middleware(application)

    register_handlers(application, mega_agent=mega_agent, settings=settings)

    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else None
        chat_id = update.effective_chat.id if update.effective_chat else None
        message_id = None
        is_command = False
        entities = None
        text = None
        if update.effective_message:
            message = update.effective_message
            message_id = message.message_id
            text = message.text or message.caption
            entities = [e.type for e in (message.entities or [])]
            is_command = bool(text and text.startswith("/"))

        logger.debug(
            "telegram.update",
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            is_command=is_command,
            entities=entities,
            text=text,
            update_type=type(update).__name__,
        )

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:  # type: ignore[valid-type]
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

    application.add_handler(MessageHandler(filters.ALL, log_update, block=False), group=1)
    application.add_error_handler(on_error)

    logger.info("telegram.application.built")
    return application


async def initialize_application(application: Application) -> None:
    """Prepare the telegram Application to accept updates."""

    await application.initialize()
    await application.start()
    logger.info("telegram.application.started")


async def shutdown_application(application: Application) -> None:
    """Gracefully stop the telegram Application."""

    await application.stop()
    await application.shutdown()
    logger.info("telegram.application.stopped")


async def set_webhook(
    application: Application,
    url: str,
    *,
    secret_token: str | None = None,
    drop_pending_updates: bool = False,
) -> None:
    """Configure the Telegram webhook."""

    await application.bot.set_webhook(
        url=url,
        secret_token=secret_token,
        drop_pending_updates=drop_pending_updates,
    )
    logger.info("telegram.webhook.set", url=url, drop_pending_updates=drop_pending_updates)


async def delete_webhook(application: Application, *, drop_pending_updates: bool = False) -> None:
    """Remove the Telegram webhook configuration."""

    await application.bot.delete_webhook(drop_pending_updates=drop_pending_updates)
    logger.info("telegram.webhook.deleted", drop_pending_updates=drop_pending_updates)
