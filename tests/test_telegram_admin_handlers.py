"""Comprehensive tests for telegram_interface/handlers/admin_handlers.py.

All heavy project dependencies are mocked. No real Telegram, LLM,
or database connections are used.
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out heavy third-party / project modules BEFORE admin_handlers is
# imported.  We use ``sys.modules[key] = ...`` (not setdefault) so that
# even already-cached entries are overwritten.
# ---------------------------------------------------------------------------

# Save originals FIRST (before any stubs are installed) so we can restore
# them after loading. This prevents cross-test pollution with test_mega_agent.py
# which needs the real module in sys.modules for monkeypatch to work.
_SAVED_MODULES: dict[str, types.ModuleType] = {}
for _save_key in [
    "core", "core.groupagents", "core.groupagents.mega_agent",
    "config", "config.settings", "structlog",
    "telegram_interface", "telegram_interface.handlers",
    "telegram_interface.handlers.context",
    "telegram_interface.handlers.response_utils",
    "telegram", "telegram.ext",
]:
    if _save_key in sys.modules:
        _SAVED_MODULES[_save_key] = sys.modules[_save_key]

# structlog stub -----------------------------------------------------------
_structlog = types.ModuleType("structlog")


class _FakeLogger:
    """No-op logger that accepts arbitrary keyword calls."""

    def __getattr__(self, _name: str):
        return lambda *_a, **_kw: None


_structlog.get_logger = lambda *_a, **_kw: _FakeLogger()
sys.modules["structlog"] = _structlog

# telegram stubs -----------------------------------------------------------
_telegram = types.ModuleType("telegram")


class _InlineKeyboardButton:
    def __init__(self, text: str, callback_data: str | None = None, **kw):
        self.text = text
        self.callback_data = callback_data


class _InlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


class _Update:
    pass


_telegram.InlineKeyboardButton = _InlineKeyboardButton
_telegram.InlineKeyboardMarkup = _InlineKeyboardMarkup
_telegram.Update = _Update
_telegram.Message = MagicMock
sys.modules["telegram"] = _telegram

# telegram.ext stubs -------------------------------------------------------
_telegram_ext = types.ModuleType("telegram.ext")


class _CommandHandler:
    def __init__(self, command, callback, **kw):
        self.command = command
        self.callback = callback


class _MessageHandler:
    def __init__(self, filters, callback, **kw):
        self.filters = filters
        self.callback = callback


class _CallbackQueryHandler:
    def __init__(self, callback, pattern=None, **kw):
        self.callback = callback
        self.pattern = pattern


class _ContextTypes:
    DEFAULT_TYPE = MagicMock


# Build a 'filters' namespace that supports `filters.TEXT & filters.Regex(...)`.
_filters_ns = MagicMock()
_filters_ns.COMMAND = MagicMock()
_filters_ns.TEXT = MagicMock()

_telegram_ext.CommandHandler = _CommandHandler
_telegram_ext.MessageHandler = _MessageHandler
_telegram_ext.CallbackQueryHandler = _CallbackQueryHandler
_telegram_ext.ContextTypes = _ContextTypes
_telegram_ext.filters = _filters_ns
sys.modules["telegram.ext"] = _telegram_ext

# core.groupagents.mega_agent stubs ----------------------------------------
_core = types.ModuleType("core")
_core_groupagents = types.ModuleType("core.groupagents")
_mega_agent_mod = types.ModuleType("core.groupagents.mega_agent")


class _CommandType:
    ASK = "ask"


class _UserRole:
    LAWYER = "lawyer"


class _MegaAgentCommand:
    def __init__(self, **kwargs):
        self.command_id = kwargs.get("command_id", "test-cmd-id")
        for k, v in kwargs.items():
            setattr(self, k, v)


_mega_agent_mod.CommandType = _CommandType
_mega_agent_mod.UserRole = _UserRole
_mega_agent_mod.MegaAgentCommand = _MegaAgentCommand

sys.modules["core"] = _core
sys.modules["core.groupagents"] = _core_groupagents
sys.modules["core.groupagents.mega_agent"] = _mega_agent_mod

# config.settings stub (transitively needed) --------------------------------
sys.modules.setdefault("config", types.ModuleType("config"))
sys.modules.setdefault("config.settings", types.ModuleType("config.settings"))

# telegram_interface.handlers.context stub ----------------------------------
_ti = types.ModuleType("telegram_interface")
_ti_handlers = types.ModuleType("telegram_interface.handlers")
_handler_ctx_mod = types.ModuleType("telegram_interface.handlers.context")


class _BotContext:
    """Minimal stand-in for BotContext used in tests."""

    def __init__(self, *, is_authorized_rv: bool = True, mega_agent=None, settings=None):
        self._authorized = is_authorized_rv
        self.mega_agent = mega_agent or MagicMock()
        self.settings = settings or MagicMock()

    def is_authorized(self, user_id):
        return self._authorized

    async def get_active_case(self, update):
        return None

    async def set_active_case(self, update, case_id):
        pass


_handler_ctx_mod.BotContext = _BotContext

# Give the package stubs __path__ so Python treats them as packages.
# Use empty paths so no real files are discovered from them.
_ti.__path__ = []
_ti_handlers.__path__ = []

sys.modules["telegram_interface"] = _ti
sys.modules["telegram_interface.handlers"] = _ti_handlers
sys.modules["telegram_interface.handlers.context"] = _handler_ctx_mod

# telegram_interface.handlers.response_utils stub --------------------------
_resp_utils_mod = types.ModuleType("telegram_interface.handlers.response_utils")
_resp_utils_mod.send_response = AsyncMock()
sys.modules["telegram_interface.handlers.response_utils"] = _resp_utils_mod

# ---------------------------------------------------------------------------
# Now force-load admin_handlers by compiling its source inside a module whose
# __package__ is set to our stub package.  This guarantees that the relative
# ``from .context import BotContext`` resolves via sys.modules (our stubs)
# rather than reaching out to the real context.py on disk.
# ---------------------------------------------------------------------------

import pathlib as _pl

_admin_handlers_path = (
    _pl.Path(__file__).resolve().parent.parent
    / "telegram_interface"
    / "handlers"
    / "admin_handlers.py"
)

sys.modules.pop("telegram_interface.handlers.admin_handlers", None)

_admin_mod = types.ModuleType("telegram_interface.handlers.admin_handlers")
_admin_mod.__file__ = str(_admin_handlers_path)
_admin_mod.__package__ = "telegram_interface.handlers"
_admin_mod.__loader__ = None
sys.modules["telegram_interface.handlers.admin_handlers"] = _admin_mod
_ti_handlers.admin_handlers = _admin_mod

_source = _admin_handlers_path.read_text(encoding="utf-8")
_code = compile(_source, str(_admin_handlers_path), "exec")
exec(_code, _admin_mod.__dict__)  # noqa: S102

# Public names from the module under test
HELP_TEXT = _admin_mod.HELP_TEXT
start = _admin_mod.start
help_command = _admin_mod.help_command
ask_command = _admin_mod.ask_command
menu_command = _admin_mod.menu_command
menu_callback = _admin_mod.menu_callback
status_command = _admin_mod.status_command
cancel_command = _admin_mod.cancel_command
unknown_command = _admin_mod.unknown_command
get_handlers = _admin_mod.get_handlers
get_unknown_handler = _admin_mod.get_unknown_handler

# ---------------------------------------------------------------------------
# Restore original modules in sys.modules so other test files (e.g.
# test_mega_agent.py) that already imported from these packages keep working.
# The compiled module already has its references bound, so restoring the
# originals doesn't affect it.
# ---------------------------------------------------------------------------
for _key in list(
    {
        "telegram_interface",
        "telegram_interface.handlers",
        "telegram_interface.handlers.context",
        "telegram_interface.handlers.response_utils",
        "telegram",
        "telegram.ext",
        "core",
        "core.groupagents",
        "core.groupagents.mega_agent",
        "config",
        "config.settings",
        "structlog",
    }
):
    if _key in _SAVED_MODULES:
        sys.modules[_key] = _SAVED_MODULES[_key]
    else:
        sys.modules.pop(_key, None)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_update(
    user_id: int = 12345,
    username: str = "testuser",
    text: str = "/start",
    has_user: bool = True,
):
    """Create a mock Telegram Update object."""
    update = MagicMock()
    if has_user:
        update.effective_user.id = user_id
        update.effective_user.username = username
    else:
        update.effective_user = None
    update.effective_message.reply_text = AsyncMock(return_value=MagicMock(message_id=1))
    update.effective_message.text = text
    update.effective_message.caption = None
    return update


def _make_context(*, bot_context=None, args=None, user_data=None):
    """Create a mock context with bot_data["bot_context"]."""
    ctx = MagicMock()
    bc = bot_context or _BotContext()
    ctx.application.bot_data = {"bot_context": bc}
    ctx.args = args
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


def _make_response(success: bool = True, result=None, error=None):
    """Create a mock MegaAgentResponse."""
    resp = MagicMock()
    resp.success = success
    resp.result = result
    resp.error = error
    return resp


# ---------------------------------------------------------------------------
# Tests: start
# ---------------------------------------------------------------------------


class TestStart:
    @pytest.mark.asyncio
    async def test_authorized_user_gets_welcome(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=True))

        await start(update, ctx)

        update.effective_message.reply_text.assert_any_call(
            "\U0001f44b Welcome to MegaAgent EB-1A assistant! Use /help to see available commands."
        )

    @pytest.mark.asyncio
    async def test_unauthorized_user_gets_denied(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=False))

        await start(update, ctx)

        # _is_authorized sends the denial synchronously via reply_text
        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )

    @pytest.mark.asyncio
    async def test_no_effective_user(self):
        """When effective_user is None user_id becomes None; auth fails."""
        update = _make_update(has_user=False)
        bc = _BotContext(is_authorized_rv=False)
        ctx = _make_context(bot_context=bc)

        await start(update, ctx)

        # Should NOT have sent the welcome message
        calls_text = [
            str(c) for c in update.effective_message.reply_text.call_args_list
        ]
        assert not any("Welcome" in t for t in calls_text)


# ---------------------------------------------------------------------------
# Tests: help_command
# ---------------------------------------------------------------------------


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_authorized_sends_help_text(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=True))

        await help_command(update, ctx)

        update.effective_message.reply_text.assert_any_call(HELP_TEXT)

    @pytest.mark.asyncio
    async def test_unauthorized_sends_denied(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=False))

        await help_command(update, ctx)

        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )


# ---------------------------------------------------------------------------
# Tests: ask_command
# ---------------------------------------------------------------------------


class TestAskCommand:
    @pytest.mark.asyncio
    async def test_no_args_sends_usage(self):
        update = _make_update(text="/ask")
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=True), args=[])

        await ask_command(update, ctx)

        update.effective_message.reply_text.assert_any_call("Usage: /ask <question>")

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = _make_update(text="/ask hello")
        ctx = _make_context(
            bot_context=_BotContext(is_authorized_rv=False), args=["hello"]
        )

        await ask_command(update, ctx)

        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )

    @pytest.mark.asyncio
    async def test_successful_llm_response(self):
        update = _make_update(text="/ask What is EB-1A?")
        llm_answer = "EB-1A is an immigration category for extraordinary ability."
        result = {"llm_response": llm_answer}
        response = _make_response(success=True, result=result)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["What", "is", "EB-1A?"])

        mock_send = AsyncMock()
        with patch.object(_admin_mod, "send_response", mock_send):
            await ask_command(update, ctx)

        mock_send.assert_awaited_once()
        kw = mock_send.call_args.kwargs
        assert kw["text"] == llm_answer

    @pytest.mark.asyncio
    async def test_error_response(self):
        update = _make_update(text="/ask fail")
        response = _make_response(success=False, result=None, error="LLM unavailable")

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["fail"])

        await ask_command(update, ctx)

        update.effective_message.reply_text.assert_any_call(
            "\u274c Error: LLM unavailable", parse_mode=None
        )

    @pytest.mark.asyncio
    async def test_error_response_unknown(self):
        """When response.error is None the message should contain 'unknown'."""
        update = _make_update(text="/ask fail")
        response = _make_response(success=False, result=None, error=None)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["fail"])

        await ask_command(update, ctx)

        update.effective_message.reply_text.assert_any_call(
            "\u274c Error: unknown", parse_mode=None
        )

    @pytest.mark.asyncio
    async def test_timeout_returns_timeout_message(self):
        update = _make_update(text="/ask slow question")

        mega = MagicMock()
        mega.handle_command = AsyncMock(side_effect=asyncio.TimeoutError)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["slow", "question"])

        with patch(
            "telegram_interface.handlers.admin_handlers.asyncio.wait_for",
            new_callable=AsyncMock,
            side_effect=TimeoutError,
        ):
            await ask_command(update, ctx)

        update.effective_message.reply_text.assert_any_call(
            "\u23f3 \u041f\u0440\u0435\u0432\u044b\u0448\u0435\u043d\u043e "
            "\u0432\u0440\u0435\u043c\u044f \u043e\u0436\u0438\u0434\u0430\u043d"
            "\u0438\u044f \u043e\u0442\u0432\u0435\u0442\u0430. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 "
            "\u0441\u043d\u043e\u0432\u0430."
        )

    @pytest.mark.asyncio
    async def test_args_extracted_question(self):
        """Verify the question is built by joining context.args."""
        update = _make_update(text="/ask what are the criteria")
        result = {"llm_response": "The criteria are ..."}
        response = _make_response(success=True, result=result)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["what", "are", "the", "criteria"])

        with patch.object(_admin_mod, "send_response", AsyncMock()):
            await ask_command(update, ctx)

        mega.handle_command.assert_awaited_once()
        cmd = mega.handle_command.call_args[0][0]
        assert cmd.payload["query"] == "what are the criteria"

    @pytest.mark.asyncio
    async def test_fallback_with_retrieved_memory(self):
        """When llm_response is absent but retrieved items exist, show summary."""
        update = _make_update(text="/ask something")
        retrieved = [
            {"text": "Memory item 1"},
            {"text": "Memory item 2"},
        ]
        result = {
            "llm_response": None,
            "retrieved": retrieved,
            "prompt_analysis": {"issues": "Found related items:"},
        }
        response = _make_response(success=True, result=result)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["something"])

        mock_send = AsyncMock()
        with patch.object(_admin_mod, "send_response", mock_send):
            await ask_command(update, ctx)

        # send_response should NOT have been called (no llm_response)
        mock_send.assert_not_awaited()

        # reply_text should contain the fallback with memory summary
        all_calls = update.effective_message.reply_text.call_args_list
        found = False
        for call in all_calls:
            text_arg = call[0][0] if call[0] else call.kwargs.get("text", "")
            if "Memory item 1" in text_arg and "Memory item 2" in text_arg:
                assert "Found related items:" in text_arg
                found = True
                break
        assert found, f"Expected retrieved memory summary, got: {all_calls}"

    @pytest.mark.asyncio
    async def test_fallback_no_retrieved_no_llm(self):
        """Default fallback text when no llm_response and no retrieved items."""
        update = _make_update(text="/ask something")
        result = {
            "llm_response": None,
            "retrieved": [],
            "prompt_analysis": {},
        }
        response = _make_response(success=True, result=result)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=["something"])

        with patch.object(_admin_mod, "send_response", AsyncMock()):
            await ask_command(update, ctx)

        all_calls = update.effective_message.reply_text.call_args_list
        found = any(
            "\u2705 Query processed." in (c[0][0] if c[0] else c.kwargs.get("text", ""))
            for c in all_calls
        )
        assert found, f"Expected default fallback text, got: {all_calls}"

    @pytest.mark.asyncio
    async def test_regex_fallback_when_args_empty(self):
        """When context.args is empty, handler extracts question via regex from text."""
        update = _make_update(text="/ask@MyBot what is visa")
        update.effective_message.caption = None

        result = {"llm_response": "Visa answer"}
        response = _make_response(success=True, result=result)

        mega = MagicMock()
        mega.handle_command = AsyncMock(return_value=response)
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        ctx = _make_context(bot_context=bc, args=[])

        mock_send = AsyncMock()
        with patch.object(_admin_mod, "send_response", mock_send), \
             patch(
                 "telegram_interface.handlers.admin_handlers.asyncio.wait_for",
                 new_callable=AsyncMock,
                 return_value=response,
             ):
            await ask_command(update, ctx)

        # Should have processed the question via regex fallback
        mock_send.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: menu_command
# ---------------------------------------------------------------------------


class TestMenuCommand:
    @pytest.mark.asyncio
    async def test_authorized_sends_inline_keyboard(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=True))

        await menu_command(update, ctx)

        update.effective_message.reply_text.assert_called_once()
        call_kwargs = update.effective_message.reply_text.call_args
        text_arg = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("text", "")
        assert "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e" in text_arg
        # reply_markup should be present
        assert "reply_markup" in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=False))

        await menu_command(update, ctx)

        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )


# ---------------------------------------------------------------------------
# Tests: menu_callback
# ---------------------------------------------------------------------------


class TestMenuCallback:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("action", "expected_fragment"),
        [
            ("menu_cases", "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043a\u0435\u0439\u0441\u0430\u043c\u0438"),
            ("menu_new_case", "\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043a\u0435\u0439\u0441\u0430"),
            ("menu_intake", "\u0410\u043d\u043a\u0435\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043a\u043b\u0438\u0435\u043d\u0442\u0430"),
            ("menu_eb1", "EB-1A"),
            ("menu_search", "\u041f\u043e\u0438\u0441\u043a"),
            ("menu_docs", "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u044b"),
            ("menu_status", "/status"),
            ("menu_help", "/help"),
        ],
    )
    async def test_known_actions(self, action: str, expected_fragment: str):
        update = MagicMock()
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = action
        update.callback_query = query
        update.effective_user.id = 12345

        ctx = _make_context()

        await menu_callback(update, ctx)

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        sent_text = query.edit_message_text.call_args[0][0]
        assert expected_fragment in sent_text

    @pytest.mark.asyncio
    async def test_unknown_action_returns_default_text(self):
        update = MagicMock()
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.data = "menu_nonexistent"
        update.callback_query = query
        update.effective_user.id = 12345

        ctx = _make_context()

        await menu_callback(update, ctx)

        query.edit_message_text.assert_awaited_once()
        sent_text = query.edit_message_text.call_args[0][0]
        assert sent_text == "\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435"


# ---------------------------------------------------------------------------
# Tests: status_command
# ---------------------------------------------------------------------------


class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_authorized_with_working_agent_and_memory(self):
        update = _make_update()

        mega = MagicMock()
        mega.memory = MagicMock()
        mega.memory.stats = AsyncMock(return_value={"total_records": 42})

        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        bc.get_active_case = AsyncMock(return_value="case-123")

        ctx = _make_context(bot_context=bc)

        await status_command(update, ctx)

        assert update.effective_message.reply_text.call_count >= 2
        last_text = update.effective_message.reply_text.call_args_list[-1][0][0]
        assert "\u0421\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u0441\u0442\u0435\u043c\u044b" in last_text
        assert "\u0410\u043a\u0442\u0438\u0432\u0435\u043d" in last_text
        assert "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0430" in last_text
        assert "case-123" in last_text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=False))

        await status_command(update, ctx)

        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )

    @pytest.mark.asyncio
    async def test_agent_without_memory(self):
        """mega_agent with no memory attr -> memory is unavailable."""
        update = _make_update()

        mega = MagicMock(spec=[])  # empty spec -> no attributes
        bc = _BotContext(is_authorized_rv=True, mega_agent=mega)
        bc.get_active_case = AsyncMock(return_value=None)

        ctx = _make_context(bot_context=bc)

        await status_command(update, ctx)

        assert update.effective_message.reply_text.call_count >= 2
        last_text = update.effective_message.reply_text.call_args_list[-1][0][0]
        assert "\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430" in last_text
        assert "\u041d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d" in last_text


# ---------------------------------------------------------------------------
# Tests: cancel_command
# ---------------------------------------------------------------------------


class TestCancelCommand:
    @pytest.mark.asyncio
    async def test_clears_all_pending_items(self):
        update = _make_update()
        user_data = {
            "pending_pdf": {"file_id": "abc"},
            "intake_state": {"step": 3},
            "pending_confirmation": True,
        }
        ctx = _make_context(
            bot_context=_BotContext(is_authorized_rv=True),
            user_data=user_data,
        )

        await cancel_command(update, ctx)

        assert "pending_pdf" not in ctx.user_data
        assert "intake_state" not in ctx.user_data
        assert "pending_confirmation" not in ctx.user_data

        reply = update.effective_message.reply_text.call_args[0][0]
        assert "\u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e" in reply
        assert "PDF" in reply
        assert "\u0410\u043d\u043a\u0435\u0442\u0430" in reply
        assert "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435" in reply

    @pytest.mark.asyncio
    async def test_no_pending_items(self):
        update = _make_update()
        ctx = _make_context(
            bot_context=_BotContext(is_authorized_rv=True),
            user_data={},
        )

        await cancel_command(update, ctx)

        reply = update.effective_message.reply_text.call_args[0][0]
        assert "\u041d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u0439" in reply

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = _make_update()
        ctx = _make_context(bot_context=_BotContext(is_authorized_rv=False))

        await cancel_command(update, ctx)

        update.effective_message.reply_text.assert_called_once_with(
            "\U0001f6ab Access denied."
        )

    @pytest.mark.asyncio
    async def test_partial_pending_items(self):
        """Only pending_pdf present; others absent."""
        update = _make_update()
        user_data = {"pending_pdf": {"file_id": "x"}}
        ctx = _make_context(
            bot_context=_BotContext(is_authorized_rv=True),
            user_data=user_data,
        )

        await cancel_command(update, ctx)

        assert "pending_pdf" not in ctx.user_data
        reply = update.effective_message.reply_text.call_args[0][0]
        assert "PDF" in reply
        assert "\u0410\u043d\u043a\u0435\u0442\u0430" not in reply


# ---------------------------------------------------------------------------
# Tests: unknown_command
# ---------------------------------------------------------------------------


class TestUnknownCommand:
    @pytest.mark.asyncio
    async def test_sends_warning_message(self):
        update = _make_update(text="/foobar")
        ctx = _make_context()

        await unknown_command(update, ctx)

        update.effective_message.reply_text.assert_awaited_once_with(
            "\u26a0\ufe0f Unknown command. Use /help for the list of commands."
        )

    @pytest.mark.asyncio
    async def test_no_effective_message_does_not_crash(self):
        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_message = None

        ctx = _make_context()

        # Must not raise
        await unknown_command(update, ctx)


# ---------------------------------------------------------------------------
# Tests: get_handlers / get_unknown_handler
# ---------------------------------------------------------------------------


class TestGetHandlers:
    def test_returns_correct_handler_types_and_count(self):
        bc = _BotContext()
        handlers = get_handlers(bc)

        # 6 CommandHandlers + 1 MessageHandler (regex) + 1 CallbackQueryHandler = 8
        assert len(handlers) == 8

        cmd_hs = [h for h in handlers if isinstance(h, _CommandHandler)]
        msg_hs = [h for h in handlers if isinstance(h, _MessageHandler)]
        cbq_hs = [h for h in handlers if isinstance(h, _CallbackQueryHandler)]

        assert len(cmd_hs) == 6
        assert len(msg_hs) == 1
        assert len(cbq_hs) == 1

        command_names = {h.command for h in cmd_hs}
        assert command_names == {"start", "help", "menu", "status", "cancel", "ask"}

    def test_callback_handler_has_menu_pattern(self):
        bc = _BotContext()
        handlers = get_handlers(bc)
        cbq = [h for h in handlers if isinstance(h, _CallbackQueryHandler)]
        assert len(cbq) == 1
        assert cbq[0].pattern == "^menu_"


class TestGetUnknownHandler:
    def test_returns_message_handler(self):
        handler = get_unknown_handler()
        assert isinstance(handler, _MessageHandler)
        assert handler.callback is unknown_command
