"""Shared context utilities for Telegram handlers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

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

    # --- Active case helpers -------------------------------------------------
    def thread_id_for_update(self, update) -> str:
        """Build deterministic thread_id for chats."""

        chat = getattr(update, "effective_chat", None)
        chat_id = chat.id if chat else "unknown"
        return f"tg:{chat_id}"

    async def set_active_case(self, update, case_id: str) -> None:
        """Persist the active case id for this chat in RMT."""

        thread_id = self.thread_id_for_update(update)
        slots: dict[str, Any] | None = await self.mega_agent.memory.aget_rmt(thread_id)
        if not slots:
            slots = {
                "persona": "",
                "long_term_facts": "",
                "open_loops": "",
                "recent_summary": "",
            }
        slots["active_case_id"] = str(case_id)
        await self.mega_agent.memory.aset_rmt(thread_id, slots)

    async def get_active_case(self, update) -> str | None:
        """Return active case id for this chat, if set."""

        thread_id = self.thread_id_for_update(update)
        slots: dict[str, Any] | None = await self.mega_agent.memory.aget_rmt(thread_id)
        if not slots:
            return None
        return slots.get("active_case_id")
