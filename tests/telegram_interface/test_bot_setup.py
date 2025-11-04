from __future__ import annotations

from types import SimpleNamespace

from config.settings import get_settings
from core.groupagents.mega_agent import MegaAgent
from core.memory.memory_manager import MemoryManager
from telegram_interface.handlers import register_handlers
from telegram_interface.handlers.context import BotContext


def test_bot_context_authorization() -> None:
    ctx = BotContext(mega_agent=SimpleNamespace(), settings=get_settings(), allowed_user_ids=[1, 2])
    assert ctx.is_authorized(1)
    assert not ctx.is_authorized(3)
    assert not ctx.is_authorized(None)


def test_register_handlers_adds_handlers() -> None:
    settings = get_settings()
    mega_agent = MegaAgent(memory_manager=MemoryManager())

    class DummyApplication:
        def __init__(self) -> None:
            self.handlers = []
            self.bot_data = {}

        def add_handler(self, handler) -> None:  # pragma: no cover - simple storage
            self.handlers.append(handler)

    app = DummyApplication()
    register_handlers(app, mega_agent=mega_agent, settings=settings)
    assert app.handlers
    assert "bot_context" in app.bot_data
