"""Shared context utilities for Telegram handlers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from config.settings import AppSettings
from core.groupagents.mega_agent import MegaAgent


@dataclass(frozen=True)
class BotContext:
    mega_agent: MegaAgent
    settings: AppSettings
    allowed_user_ids: Sequence[int] | None = None

    def is_authorized(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids
