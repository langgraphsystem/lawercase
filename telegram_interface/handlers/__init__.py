"""Handlers registration for Telegram bot."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import chain

import structlog
from telegram.ext import Application

from config.settings import AppSettings
from core.groupagents.mega_agent import MegaAgent

from .context import BotContext

logger = structlog.get_logger(__name__)


def register_handlers(
    application: Application, *, mega_agent: MegaAgent, settings: AppSettings
) -> None:
    """Register all bot handlers on the application."""

    bot_context = BotContext(
        mega_agent=mega_agent,
        settings=settings,
        allowed_user_ids=settings.allowed_user_ids(),
    )
    application.bot_data["bot_context"] = bot_context
    logger.info(
        "telegram.handlers.context_ready",
        allowed_user_ids=bot_context.allowed_user_ids if bot_context.allowed_user_ids else "open",
    )

    from . import (admin_handlers,  # local import to avoid circular
                   case_handlers, file_upload_handlers, kb_handlers,
                   letter_handlers, scheduler_handlers, sdk_handlers)

    handler_sets: Iterable = chain(
        admin_handlers.get_handlers(bot_context),
        case_handlers.get_handlers(bot_context),
        sdk_handlers.get_handlers(bot_context),
        letter_handlers.get_handlers(bot_context),
        kb_handlers.get_handlers(bot_context),
        scheduler_handlers.get_handlers(bot_context),
        file_upload_handlers.get_handlers(bot_context),
    )

    for handler in handler_sets:
        application.add_handler(handler)

    logger.info("telegram.handlers.registered")
