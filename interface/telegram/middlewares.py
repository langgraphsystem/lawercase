"""Telegram bot middlewares."""

import logging
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.types.base import TelegramObject


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Structured logging middleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        data['correlation_id'] = correlation_id

        # Extract event info
        event_info = self._extract_event_info(event)

        start_time = time.time()

        try:
            # Log incoming event
            logger.info(
                "telegram_event",
                extra={
                    "event": "incoming",
                    "correlation_id": correlation_id,
                    **event_info
                }
            )

            # Call handler
            result = await handler(event, data)

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "telegram_event",
                extra={
                    "event": "completed",
                    "correlation_id": correlation_id,
                    "latency_ms": round(duration_ms, 2),
                    **event_info
                }
            )

            return result

        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "telegram_event",
                extra={
                    "event": "error",
                    "correlation_id": correlation_id,
                    "latency_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    **event_info
                }
            )
            raise

    def _extract_event_info(self, event: TelegramObject) -> Dict[str, Any]:
        """Extract relevant info from event."""
        info = {}

        if isinstance(event, Message):
            info.update({
                "user_id": event.from_user.id if event.from_user else None,
                "chat_id": event.chat.id,
                "message_id": event.message_id,
                "cmd": self._extract_command(event),
                "has_document": bool(event.document),
                "has_photo": bool(event.photo)
            })

        return info

    def _extract_command(self, message: Message) -> Optional[str]:
        """Extract command from message."""
        if message.text and message.text.startswith('/'):
            return message.text.split()[0][1:]  # Remove /
        return None


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting middleware."""

    def __init__(self):
        self.user_requests: Dict[int, list] = {}
        self.rate_limit_window = 60  # 1 minute
        self.max_requests_per_window = 20

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = time.time()

        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < self.rate_limit_window
            ]
        else:
            self.user_requests[user_id] = []

        # Check rate limit
        if len(self.user_requests[user_id]) >= self.max_requests_per_window:
            await event.answer(
                "⚠️ Слишком много запросов. Попробуйте через минуту.",
                show_alert=True
            )
            return

        # Add current request
        self.user_requests[user_id].append(current_time)

        return await handler(event, data)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Global error handling middleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Unhandled error in handler: {e}", exc_info=True)

            if isinstance(event, Message):
                try:
                    await event.answer("❌ Произошла ошибка. Попробуйте позже.")
                except Exception:
                    pass  # Ignore if can't send error message

            # Don't re-raise to prevent bot crash
            return None


def setup_middlewares(dp):
    """Setup all middlewares."""
    dp.middleware.setup(LoggingMiddleware())
    dp.middleware.setup(RateLimitMiddleware())
    dp.middleware.setup(ErrorHandlingMiddleware())