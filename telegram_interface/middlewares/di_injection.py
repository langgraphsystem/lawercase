"""Dependency Injection middleware for Telegram bot handlers.

Injects shared dependencies from DI container into bot_data,
making them accessible to all handlers.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, BaseHandler, ContextTypes

from core.di import get_container

logger = logging.getLogger(__name__)


class DIInjectionHandler(BaseHandler):
    """Handler that injects DI container dependencies into context.

    This runs before all other handlers and populates bot_data with
    shared dependencies from the DI container.

    Example:
        >>> app = Application.builder().token(token).build()
        >>> setup_di_middleware(app)
        >>> # Now all handlers can access dependencies:
        >>> async def my_handler(update, context):
        ...     mega_agent = context.bot_data["mega_agent"]
        ...     memory = context.bot_data["memory_manager"]
    """

    def __init__(self) -> None:
        """Initialize DI injection handler."""
        super().__init__(callback=self._inject_dependencies)
        self.container = get_container()
        logger.debug("telegram.di.handler_initialized")

    async def _inject_dependencies(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Inject dependencies into context.bot_data.

        Args:
            update: The Telegram update
            context: The handler context

        Injects:
            - di_container: The DI container itself
            - mega_agent: Shared MegaAgent instance
            - memory_manager: Shared MemoryManager instance
            - tool_registry: Shared ToolRegistry instance
        """
        # Only inject if not already present (idempotent)
        if "di_container" not in context.bot_data:
            context.bot_data["di_container"] = self.container
            context.bot_data["mega_agent"] = self.container.get("mega_agent")
            context.bot_data["memory_manager"] = self.container.get("memory_manager")
            context.bot_data["tool_registry"] = self.container.get("tool_registry")

            logger.debug(
                "telegram.di.dependencies_injected",
                user_id=update.effective_user.id if update.effective_user else None,
                dependencies=list(context.bot_data.keys()),
            )

    def check_update(self, update: object) -> bool:
        """Accept all updates to inject dependencies.

        Args:
            update: The update to check

        Returns:
            Always True - inject dependencies for all updates
        """
        return True


def setup_di_middleware(application: Application) -> None:
    """Setup DI middleware for Telegram bot.

    Registers the DI injection handler at group -1 (before all other handlers)
    to ensure dependencies are available to all handlers.

    Args:
        application: The Telegram application

    Example:
        >>> app = build_application(settings=settings, mega_agent=mega_agent)
        >>> setup_di_middleware(app)
        >>> # Now all handlers can access injected dependencies
    """
    handler = DIInjectionHandler()
    application.add_handler(handler, group=-1)  # Run before other handlers
    logger.info("telegram.di.middleware_installed", group=-1)
