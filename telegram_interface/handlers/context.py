"""Shared context utilities for Telegram handlers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import structlog

from config.settings import AppSettings
from core.groupagents.mega_agent import MegaAgent

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BotContext:
    mega_agent: MegaAgent
    settings: AppSettings
    allowed_user_ids: Sequence[int] | None = None

    def is_authorized(self, user_id: int | None) -> bool:
        if user_id is None:
            logger.warning("telegram.auth.missing_user_id")
            return False
        if not self.allowed_user_ids:
            logger.debug("telegram.auth.open", user_id=user_id)
            return True
        allowed = user_id in self.allowed_user_ids
        if allowed:
            logger.debug("telegram.auth.allowed", user_id=user_id)
        else:
            logger.warning("telegram.auth.denied", user_id=user_id)
        return allowed
