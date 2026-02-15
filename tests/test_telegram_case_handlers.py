"""Comprehensive tests for telegram_interface/handlers/case_handlers.py.

All heavy project dependencies are mocked. No real Telegram, LLM,
or database connections are used.
"""

from __future__ import annotations

from dataclasses import dataclass
import pathlib as _pl
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out heavy third-party / project modules BEFORE case_handlers is
# imported.  We use ``sys.modules[key] = ...`` (not setdefault) so that
# even already-cached entries are overwritten.
# ---------------------------------------------------------------------------

# Save originals so we can restore them after loading (preventing cross-test
# pollution with test_mega_agent.py which needs the real module in sys.modules).
_SAVED_MODULES: dict[str, types.ModuleType] = {}
for _save_key in [
    "core", "core.groupagents", "core.groupagents.mega_agent",
    "core.groupagents.eb1a_evidence_analyzer",
    "core.di", "core.di.container",
    "core.intake", "core.intake.schema",
    "core.storage", "core.storage.intake_progress",
    "config", "config.settings", "structlog",
    "telegram_interface", "telegram_interface.handlers",
    "telegram_interface.handlers.context",
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

# telegram stubs (use real library) ----------------------------------------
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler

# core.groupagents.mega_agent stubs ----------------------------------------
_core = types.ModuleType("core")
_core_groupagents = types.ModuleType("core.groupagents")
_mega_agent_mod = types.ModuleType("core.groupagents.mega_agent")


class _CommandType:
    CASE = "case"


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

# core.di.container stub (used by eb1_potential/eb1_analyze patches) --------
_core_di = types.ModuleType("core.di")
_core_di_container = types.ModuleType("core.di.container")
_core_di_container.get_container = MagicMock()
_core.di = _core_di
sys.modules["core.di"] = _core_di
sys.modules["core.di.container"] = _core_di_container

# core.groupagents.eb1a_evidence_analyzer stub ------------------------------
_core_eb1a_analyzer = types.ModuleType("core.groupagents.eb1a_evidence_analyzer")
_core_eb1a_analyzer.analyze_intake_potential_batch = AsyncMock()
_core_eb1a_analyzer.analyze_intake_for_eb1a = AsyncMock()
_core_groupagents.eb1a_evidence_analyzer = _core_eb1a_analyzer
sys.modules["core.groupagents.eb1a_evidence_analyzer"] = _core_eb1a_analyzer

# core.intake.schema stubs -------------------------------------------------


@dataclass
class _FakeProgress:
    user_id: str
    case_id: str
    current_block: str
    current_step: int = 0
    completed_blocks: list[str] | None = None


@dataclass
class _FakeBlock:
    id: str
    title: str
    questions: list[str]


_FAKE_BLOCKS: dict[str, _FakeBlock] = {
    "personal_info": _FakeBlock(
        id="personal_info", title="Personal Info", questions=["q1", "q2", "q3"]
    ),
}

_core_intake = types.ModuleType("core.intake")
_core_intake_schema = types.ModuleType("core.intake.schema")
_core_intake_schema.BLOCKS_BY_ID = _FAKE_BLOCKS
sys.modules["core.intake"] = _core_intake
sys.modules["core.intake.schema"] = _core_intake_schema

# core.storage.intake_progress stubs ---------------------------------------
_core_storage = types.ModuleType("core.storage")
_core_storage_progress = types.ModuleType("core.storage.intake_progress")
_core_storage_progress.get_progress = AsyncMock(return_value=None)
sys.modules["core.storage"] = _core_storage
sys.modules["core.storage.intake_progress"] = _core_storage_progress

# config.settings stub -----------------------------------------------------
sys.modules.setdefault("config", types.ModuleType("config"))
sys.modules.setdefault("config.settings", types.ModuleType("config.settings"))

# telegram_interface.handlers.context stub ---------------------------------
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
_ti.__path__ = []
_ti_handlers.__path__ = []

sys.modules["telegram_interface"] = _ti
sys.modules["telegram_interface.handlers"] = _ti_handlers
sys.modules["telegram_interface.handlers.context"] = _handler_ctx_mod

# ---------------------------------------------------------------------------
# Now force-load case_handlers by compiling its source inside a module whose
# __package__ is set to our stub package.  This guarantees that the relative
# ``from .context import BotContext`` resolves via sys.modules (our stubs)
# rather than reaching out to the real context.py on disk.
# ---------------------------------------------------------------------------

_case_handlers_path = (
    _pl.Path(__file__).resolve().parent.parent
    / "telegram_interface"
    / "handlers"
    / "case_handlers.py"
)

sys.modules.pop("telegram_interface.handlers.case_handlers", None)

_case_mod = types.ModuleType("telegram_interface.handlers.case_handlers")
_case_mod.__file__ = str(_case_handlers_path)
_case_mod.__package__ = "telegram_interface.handlers"
_case_mod.__loader__ = None
sys.modules["telegram_interface.handlers.case_handlers"] = _case_mod
_ti_handlers.case_handlers = _case_mod

_source = _case_handlers_path.read_text(encoding="utf-8")
_code = compile(_source, str(_case_handlers_path), "exec")
exec(_code, _case_mod.__dict__)  # noqa: S102

# Alias for tests
ch = _case_mod
_progress_mod = sys.modules["core.storage.intake_progress"]

# ---------------------------------------------------------------------------
# Restore original modules in sys.modules so other test files (e.g.
# test_mega_agent.py) that already imported from these packages keep working.
# The compiled module already has its references bound.
# ---------------------------------------------------------------------------
for _key in list(
    {
        "telegram_interface",
        "telegram_interface.handlers",
        "telegram_interface.handlers.context",
        "core",
        "core.groupagents",
        "core.groupagents.mega_agent",
        "core.groupagents.eb1a_evidence_analyzer",
        "core.di",
        "core.di.container",
        "core.intake",
        "core.intake.schema",
        "core.storage",
        "core.storage.intake_progress",
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
# Helpers for building mocks
# ---------------------------------------------------------------------------


def _make_bot_context(
    *,
    authorized: bool = True,
    allowed_user_ids: list[int] | None = None,
    active_case: str | None = None,
) -> MagicMock:
    """Create a BotContext-like mock."""
    bc = MagicMock()
    bc.is_authorized.return_value = authorized
    bc.thread_id_for_update.return_value = "tg:12345"
    bc.set_active_case = AsyncMock()
    bc.get_active_case = AsyncMock(return_value=active_case)
    bc.mega_agent = MagicMock()
    bc.mega_agent.handle_command = AsyncMock()
    return bc


def _make_update(user_id: int = 42) -> MagicMock:
    """Create an Update-like mock with effective_user and effective_message."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query = None
    return update


def _make_context(args: list[str] | None = None, bot_context: Any = None) -> MagicMock:
    """Create a telegram ext context mock."""
    ctx = MagicMock()
    ctx.args = args
    ctx.application = MagicMock()
    ctx.application.bot_data = {"bot_context": bot_context or _make_bot_context()}
    return ctx


def _make_response(
    success: bool = True,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> MagicMock:
    """Create a MegaAgentResponse-like mock."""
    resp = MagicMock()
    resp.success = success
    resp.result = result
    resp.error = error
    return resp


# ===========================================================================
# 1. _extract_case_payload
# ===========================================================================


class TestExtractCasePayload:
    """Tests for _extract_case_payload helper."""

    def test_normal_case(self):
        """Direct 'case' key with case_id at top level."""
        result = {
            "case": {"title": "My Case", "status": "draft"},
            "case_id": "abc123",
        }
        result_dict, case_data, case_id = ch._extract_case_payload(result)
        assert result_dict is result
        assert case_data["title"] == "My Case"
        assert case_id == "abc123"

    def test_nested_case_result(self):
        """case_result wrapping the real case dict."""
        result = {
            "case_result": {"case": {"title": "Nested", "status": "in_progress"}},
            "case_id": "def456",
        }
        _, case_data, case_id = ch._extract_case_payload(result)
        assert case_data["title"] == "Nested"
        assert case_id == "def456"

    def test_missing_case(self):
        """No 'case' or 'case_result' key -- returns empty dict for case_data."""
        result = {"case_id": "only_id"}
        _, case_data, case_id = ch._extract_case_payload(result)
        assert case_data == {}
        assert case_id == "only_id"

    def test_none_input(self):
        """None result should not raise."""
        result_dict, case_data, case_id = ch._extract_case_payload(None)
        assert result_dict == {}
        assert case_data == {}
        assert case_id is None

    def test_case_id_from_case_data(self):
        """case_id inside case dict when missing at top level."""
        result = {
            "case": {"title": "Inner ID", "status": "draft", "case_id": "inner123"},
        }
        _, _case_data, case_id = ch._extract_case_payload(result)
        assert case_id == "inner123"

    def test_case_key_not_dict(self):
        """If 'case' is not a dict, falls through to case_result."""
        result = {
            "case": "string_value",
            "case_result": {"case": {"title": "Fallback"}},
            "case_id": "fb1",
        }
        _, case_data, case_id = ch._extract_case_payload(result)
        assert case_data["title"] == "Fallback"
        assert case_id == "fb1"


# ===========================================================================
# 2. _is_authorized
# ===========================================================================


class TestIsAuthorized:
    @pytest.mark.asyncio
    async def test_authorized_returns_true(self):
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        assert await ch._is_authorized(bc, update) is True
        update.effective_message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_unauthorized_returns_false_and_replies(self):
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        assert await ch._is_authorized(bc, update) is False
        update.effective_message.reply_text.assert_awaited_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Access denied" in call_text


# ===========================================================================
# 3-7. case_get
# ===========================================================================


class TestCaseGet:
    @pytest.mark.asyncio
    async def test_authorized_case_found(self):
        """case_get: authorized, case found -- sets active case and replies."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(
            success=True,
            result={
                "case": {"title": "Test Case", "status": "draft"},
                "case_id": "abc123",
            },
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["abc123"], bot_context=bc)

        with patch.object(ch, "_maybe_offer_resume", new_callable=AsyncMock) as mock_resume:
            await ch.case_get(update, ctx)

        reply = update.effective_message.reply_text
        reply.assert_awaited()
        text = reply.call_args_list[0][0][0]
        assert "abc123" in text
        assert "Test Case" in text
        bc.set_active_case.assert_awaited_once_with(update, "abc123")
        mock_resume.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_args_usage_message(self):
        """case_get: no arguments -- shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_get(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "Usage" in text

    @pytest.mark.asyncio
    async def test_empty_args_usage_message(self):
        """case_get: empty args list -- shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=[], bot_context=bc)

        await ch.case_get(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "Usage" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_get: unauthorized -- returns early."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["abc"], bot_context=bc)

        await ch.case_get(update, ctx)

        # Only the access-denied message should appear
        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_case_not_found_error(self):
        """case_get: MegaAgent returns failure."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=False, error="case not found")
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["missing_id"], bot_context=bc)

        await ch.case_get(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case not found" in text

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """case_get: MegaAgent raises -- exception message shown."""
        bc = _make_bot_context(authorized=True)
        bc.mega_agent.handle_command.side_effect = RuntimeError("boom")

        update = _make_update()
        ctx = _make_context(args=["exc_id"], bot_context=bc)

        await ch.case_get(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "boom" in text


# ===========================================================================
# 8-12. case_create
# ===========================================================================


class TestCaseCreate:
    @pytest.mark.asyncio
    async def test_authorized_title_only(self):
        """case_create: title only, no description."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(
            success=True,
            result={
                "case": {"title": "New Case"},
                "case_id": "new-001",
            },
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["New", "Case"], bot_context=bc)

        await ch.case_create(update, ctx)

        bc.set_active_case.assert_awaited_once_with(update, "new-001")
        reply = update.effective_message.reply_text
        reply.assert_awaited()
        # Check MarkdownV2 message sent
        call_kwargs = reply.call_args_list[0]
        assert call_kwargs[1].get("parse_mode") == "MarkdownV2" or (
            len(call_kwargs) > 1 and "MarkdownV2" in str(call_kwargs)
        )

    @pytest.mark.asyncio
    async def test_authorized_title_and_description(self):
        """case_create: title | description."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(
            success=True,
            result={
                "case": {"title": "My Title"},
                "case_id": "td-002",
            },
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["My", "Title", "|", "Some", "description"], bot_context=bc)

        await ch.case_create(update, ctx)

        # Verify the command was called -- payload should contain description
        bc.mega_agent.handle_command.assert_awaited_once()
        bc.set_active_case.assert_awaited_once_with(update, "td-002")

    @pytest.mark.asyncio
    async def test_no_args_usage(self):
        """case_create: no arguments -- usage message."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_create(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "Usage" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_create: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["Title"], bot_context=bc)

        await ch.case_create(update, ctx)

        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_response(self):
        """case_create: MegaAgent returns error."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=False, error="creation failed")
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["Title"], bot_context=bc)

        await ch.case_create(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "creation failed" in text

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """case_create: exception during command."""
        bc = _make_bot_context(authorized=True)
        bc.mega_agent.handle_command.side_effect = ValueError("db error")

        update = _make_update()
        ctx = _make_context(args=["Title"], bot_context=bc)

        await ch.case_create(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "db error" in text


# ===========================================================================
# 13-15. case_active
# ===========================================================================


class TestCaseActive:
    @pytest.mark.asyncio
    async def test_with_active_case(self):
        """case_active: active case exists."""
        bc = _make_bot_context(authorized=True, active_case="active-001")
        response = _make_response(
            success=True,
            result={
                "case": {"title": "Active Title", "status": "in_progress"},
                "case_id": "active-001",
            },
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(bot_context=bc)

        with patch.object(ch, "_maybe_offer_resume", new_callable=AsyncMock):
            await ch.case_active(update, ctx)

        text = update.effective_message.reply_text.call_args_list[0][0][0]
        assert "active-001" in text
        assert "Active Title" in text

    @pytest.mark.asyncio
    async def test_no_active_case(self):
        """case_active: no active case."""
        bc = _make_bot_context(authorized=True, active_case=None)

        update = _make_update()
        ctx = _make_context(bot_context=bc)

        await ch.case_active(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "No active case" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_active: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(bot_context=bc)

        await ch.case_active(update, ctx)

        bc.get_active_case.assert_not_called()


# ===========================================================================
# 16-19. case_list
# ===========================================================================


class TestCaseList:
    @pytest.mark.asyncio
    async def test_first_page_with_cases(self):
        """case_list: first page returns cases."""
        bc = _make_bot_context(authorized=True)
        cases = [
            {"title": f"Case {i}", "status": "draft", "case_id": f"id-{i}"}
            for i in range(3)
        ]
        response = _make_response(
            success=True,
            result={"case_result": {"cases": cases, "count": 3}},
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_list(update, ctx)

        reply = update.effective_message.reply_text
        reply.assert_awaited_once()
        text = reply.call_args[0][0]
        assert "Case 0" in text or "Case\\ 0" in text  # MarkdownV2 escaping

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """case_list: no cases on page 1."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(
            success=True,
            result={"case_result": {"cases": [], "count": 0}},
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_list(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        # Empty first page shows a message about creating a case
        assert "нет кейсов" in text or "case_create" in text

    @pytest.mark.asyncio
    async def test_with_page_argument(self):
        """case_list: explicit page number."""
        bc = _make_bot_context(authorized=True)
        cases = [
            {"title": "Page 2 Case", "status": "review", "case_id": "p2-id"}
        ]
        response = _make_response(
            success=True,
            result={"case_result": {"cases": cases, "count": 15}},
        )
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["2"], bot_context=bc)

        await ch.case_list(update, ctx)

        reply = update.effective_message.reply_text
        reply.assert_awaited_once()
        text = reply.call_args[0][0]
        # Should show page 2
        assert "2" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_list: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(bot_context=bc)

        await ch.case_list(update, ctx)

        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_page_arg(self):
        """case_list: non-numeric page arg shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["abc"], bot_context=bc)

        await ch.case_list(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "Usage" in text


# ===========================================================================
# 20-22. case_update
# ===========================================================================


class TestCaseUpdate:
    @pytest.mark.asyncio
    async def test_authorized_with_updates(self):
        """case_update: authorized with title and description."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=True)
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(
            args=["case-001", "New", "Title", "|", "New", "Desc"], bot_context=bc
        )

        await ch.case_update(update, ctx)

        bc.mega_agent.handle_command.assert_awaited_once()
        text = update.effective_message.reply_text.call_args[0][0]
        assert "обновлён" in text or "case-001" in text

    @pytest.mark.asyncio
    async def test_no_args(self):
        """case_update: no arguments shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_update(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case_update" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_update: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["id", "Title"], bot_context=bc)

        await ch.case_update(update, ctx)

        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_case_id_only_no_changes(self):
        """case_update: case_id given but no new title/description."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["case-001"], bot_context=bc)

        await ch.case_update(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "название" in text or "описание" in text

    @pytest.mark.asyncio
    async def test_error_response(self):
        """case_update: MegaAgent returns error."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=False, error="not found")
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["case-001", "Title"], bot_context=bc)

        await ch.case_update(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "not found" in text


# ===========================================================================
# 23-25. case_delete
# ===========================================================================


class TestCaseDelete:
    @pytest.mark.asyncio
    async def test_without_confirmation_shows_buttons(self):
        """case_delete: without confirm flag shows confirmation buttons."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["del-001"], bot_context=bc)

        await ch.case_delete(update, ctx)

        reply = update.effective_message.reply_text
        reply.assert_awaited_once()
        call_kwargs = reply.call_args[1]
        assert "reply_markup" in call_kwargs
        # Should not have called handle_command yet (no confirm)
        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_confirmation(self):
        """case_delete: with 'confirm' flag executes delete."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=True)
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["del-001", "confirm"], bot_context=bc)

        await ch.case_delete(update, ctx)

        bc.mega_agent.handle_command.assert_awaited_once()
        text = update.effective_message.reply_text.call_args[0][0]
        assert "удалён" in text

    @pytest.mark.asyncio
    async def test_with_yes_confirmation(self):
        """case_delete: with 'yes' flag executes delete."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=True)
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["del-002", "yes"], bot_context=bc)

        await ch.case_delete(update, ctx)

        bc.mega_agent.handle_command.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_args(self):
        """case_delete: no args shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_delete(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case_delete" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_delete: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["id"], bot_context=bc)

        await ch.case_delete(update, ctx)

        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_response(self):
        """case_delete: MegaAgent returns error on confirmed delete."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=False, error="delete failed")
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["del-003", "confirm"], bot_context=bc)

        await ch.case_delete(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "delete failed" in text


# ===========================================================================
# 26-27. case_archive
# ===========================================================================


class TestCaseArchive:
    @pytest.mark.asyncio
    async def test_authorized(self):
        """case_archive: authorized, successful archive."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=True)
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["arch-001"], bot_context=bc)

        await ch.case_archive(update, ctx)

        bc.mega_agent.handle_command.assert_awaited_once()
        text = update.effective_message.reply_text.call_args[0][0]
        assert "архивирован" in text

    @pytest.mark.asyncio
    async def test_no_args(self):
        """case_archive: no args shows usage."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.case_archive(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case_archive" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """case_archive: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["id"], bot_context=bc)

        await ch.case_archive(update, ctx)

        bc.mega_agent.handle_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_response(self):
        """case_archive: MegaAgent returns error."""
        bc = _make_bot_context(authorized=True)
        response = _make_response(success=False, error="archive failed")
        bc.mega_agent.handle_command.return_value = response

        update = _make_update()
        ctx = _make_context(args=["arch-002"], bot_context=bc)

        await ch.case_archive(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "archive failed" in text


# ===========================================================================
# 28-29. eb1_potential
# ===========================================================================


class TestEb1Potential:
    @pytest.mark.asyncio
    async def test_authorized_with_case_id_arg(self):
        """eb1_potential: case_id provided as argument."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["pot-case-001"], bot_context=bc)

        # Mock the internal imports used by eb1_potential
        fake_result = MagicMock()
        fake_result.overall_potential_score = 75.0
        fake_result.potential_criteria_count = 4
        fake_result.llm_call_count = 1
        fake_result.risk_level = "moderate"
        fake_result.overall_assessment = "Good potential"
        fake_result.strongest_criteria = ["Awards"]
        fake_result.weakest_criteria = []
        fake_result.criteria_assessments = {}
        fake_result.priority_actions = []
        fake_result.recommendation = "Proceed"
        fake_result.warnings = []

        mock_container = MagicMock()
        mock_container.get.return_value = MagicMock()

        with (
            patch("core.di.container.get_container", return_value=mock_container),
            patch(
                "core.groupagents.eb1a_evidence_analyzer.analyze_intake_potential_batch",
                new_callable=AsyncMock,
                return_value=fake_result,
            ),
        ):
            await ch.eb1_potential(update, ctx)

        # Should have sent at least two messages: progress and result
        assert update.effective_message.reply_text.await_count >= 2

    @pytest.mark.asyncio
    async def test_no_case_id_no_active_case(self):
        """eb1_potential: no case_id arg and no active case."""
        bc = _make_bot_context(authorized=True, active_case=None)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.eb1_potential(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case_id" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """eb1_potential: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["id"], bot_context=bc)

        await ch.eb1_potential(update, ctx)

        # No further action beyond access denied
        assert update.effective_message.reply_text.await_count == 1

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """eb1_potential: exception during analysis."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["exc-case"], bot_context=bc)

        with (
            patch(
                "core.di.container.get_container",
                side_effect=RuntimeError("container failure"),
            ),
        ):
            await ch.eb1_potential(update, ctx)

        # Last message should contain error
        last_call = update.effective_message.reply_text.call_args_list[-1]
        text = last_call[0][0]
        assert "container failure" in text


# ===========================================================================
# 30-31. eb1_analyze
# ===========================================================================


class TestEb1Analyze:
    @pytest.mark.asyncio
    async def test_authorized_with_case_id_arg(self):
        """eb1_analyze: case_id provided as argument."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["ana-case-001"], bot_context=bc)

        # Create a fake CaseStrengthAnalysis-like object
        fake_analysis = MagicMock()
        fake_analysis.overall_score = 80.0
        fake_analysis.approval_probability = 0.75
        fake_analysis.risk_level = MagicMock()
        fake_analysis.risk_level.value = "moderate"
        fake_analysis.satisfied_criteria_count = 4
        fake_analysis.meets_minimum_criteria = True
        fake_analysis.criterion_evaluations = {}
        fake_analysis.strengths = ["Strong publications"]
        fake_analysis.priority_recommendations = ["Upload more docs"]
        fake_analysis.estimated_days_to_ready = 30

        mock_container = MagicMock()
        mock_container.get.return_value = MagicMock()

        with (
            patch("core.di.container.get_container", return_value=mock_container),
            patch(
                "core.groupagents.eb1a_evidence_analyzer.analyze_intake_for_eb1a",
                new_callable=AsyncMock,
                return_value=fake_analysis,
            ),
        ):
            await ch.eb1_analyze(update, ctx)

        # Should have sent at least two messages: progress and result
        assert update.effective_message.reply_text.await_count >= 2

    @pytest.mark.asyncio
    async def test_no_case_id_no_active_case(self):
        """eb1_analyze: no case_id arg, no active case."""
        bc = _make_bot_context(authorized=True, active_case=None)
        update = _make_update()
        ctx = _make_context(args=None, bot_context=bc)

        await ch.eb1_analyze(update, ctx)

        text = update.effective_message.reply_text.call_args[0][0]
        assert "case_id" in text

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """eb1_analyze: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = _make_update()
        ctx = _make_context(args=["id"], bot_context=bc)

        await ch.eb1_analyze(update, ctx)

        assert update.effective_message.reply_text.await_count == 1

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """eb1_analyze: exception during analysis."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        ctx = _make_context(args=["exc-case"], bot_context=bc)

        with patch(
            "core.di.container.get_container",
            side_effect=RuntimeError("analysis boom"),
        ):
            await ch.eb1_analyze(update, ctx)

        last_call = update.effective_message.reply_text.call_args_list[-1]
        text = last_call[0][0]
        assert "analysis boom" in text


# ===========================================================================
# 32-33. handle_case_callback
# ===========================================================================


class TestHandleCaseCallback:
    def _make_callback_update(
        self, data: str, user_id: int = 42
    ) -> MagicMock:
        """Create an Update mock with a callback_query."""
        update = _make_update(user_id=user_id)
        query = MagicMock()
        query.data = data
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        update.callback_query = query
        return update

    @pytest.mark.asyncio
    async def test_case_start_intake(self):
        """handle_case_callback: case_start_intake triggers intake_start."""
        bc = _make_bot_context(authorized=True)
        update = self._make_callback_update("case_start_intake")
        ctx = _make_context(bot_context=bc)

        mock_intake = AsyncMock()
        # Patch the intake_handlers module so the local import inside
        # handle_case_callback picks up our mock.
        intake_mod = MagicMock()
        intake_mod.intake_start = mock_intake
        with patch.dict(
            sys.modules,
            {"telegram_interface.handlers.intake_handlers": intake_mod},
        ):
            await ch.handle_case_callback(update, ctx)

        update.callback_query.answer.assert_awaited_once()
        update.callback_query.message.reply_text.assert_awaited()
        mock_intake.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_case_later(self):
        """handle_case_callback: case_later sends postpone message."""
        bc = _make_bot_context(authorized=True)
        update = self._make_callback_update("case_later")
        ctx = _make_context(bot_context=bc)

        await ch.handle_case_callback(update, ctx)

        update.callback_query.answer.assert_awaited_once()
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "позже" in text or "intake_start" in text

    @pytest.mark.asyncio
    async def test_no_callback_query(self):
        """handle_case_callback: no callback_query -- returns early."""
        bc = _make_bot_context(authorized=True)
        update = _make_update()
        update.callback_query = None
        ctx = _make_context(bot_context=bc)

        # Should not raise
        await ch.handle_case_callback(update, ctx)

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        """handle_case_callback: unauthorized."""
        bc = _make_bot_context(authorized=False)
        update = self._make_callback_update("case_start_intake")
        ctx = _make_context(bot_context=bc)

        await ch.handle_case_callback(update, ctx)

        # query.answer is still called (before auth check in the code)
        update.callback_query.answer.assert_awaited_once()


# ===========================================================================
# 34. get_handlers
# ===========================================================================


class TestGetHandlers:
    def test_returns_correct_count_and_types(self):
        """get_handlers: returns 10 handlers (9 commands + 1 callback query)."""
        bc = _make_bot_context()
        handlers = ch.get_handlers(bc)

        assert len(handlers) == 10

        command_handlers = [h for h in handlers if isinstance(h, CommandHandler)]
        callback_handlers = [h for h in handlers if isinstance(h, CallbackQueryHandler)]

        assert len(command_handlers) == 9
        assert len(callback_handlers) == 1

    def test_handler_commands_present(self):
        """get_handlers: all expected commands are registered."""
        bc = _make_bot_context()
        handlers = ch.get_handlers(bc)

        command_names = set()
        for h in handlers:
            if isinstance(h, CommandHandler):
                command_names.update(h.commands)

        expected = {
            "case_create",
            "case_get",
            "case_active",
            "case_list",
            "case_update",
            "case_delete",
            "case_archive",
            "eb1_analyze",
            "eb1_potential",
        }
        assert expected == command_names


# ===========================================================================
# Additional: _format_eb1a_potential, _format_eb1a_analysis
# ===========================================================================


class TestFormatEb1aPotential:
    def test_basic_formatting(self):
        """_format_eb1a_potential returns HTML-formatted string."""
        result = MagicMock()
        result.risk_level = "low"
        result.overall_potential_score = 85.0
        result.potential_criteria_count = 5
        result.overall_assessment = "Excellent"
        result.strongest_criteria = ["Awards", "Publications"]
        result.weakest_criteria = ["High Salary"]
        result.criteria_assessments = {
            "Awards": {"potential_score": 90, "has_potential": True, "evidence_strength": "strong"},
            "High Salary": {"potential_score": 20, "has_potential": False, "evidence_strength": None},
        }
        result.priority_actions = ["Get more docs"]
        result.recommendation = "File soon"
        result.warnings = []
        result.llm_call_count = 1

        text = ch._format_eb1a_potential(result, "abcdef1234567890")
        assert "EB-1A Potential Assessment" in text
        assert "abcdef12" in text  # case_id[:8]
        assert "85/100" in text
        assert "Excellent" in text

    def test_warnings_displayed(self):
        """Warnings are shown when present."""
        result = MagicMock()
        result.risk_level = "high"
        result.overall_potential_score = 30.0
        result.potential_criteria_count = 1
        result.overall_assessment = ""
        result.strongest_criteria = []
        result.weakest_criteria = []
        result.criteria_assessments = {}
        result.priority_actions = []
        result.recommendation = ""
        result.warnings = ["Missing personal info"]
        result.llm_call_count = 1

        text = ch._format_eb1a_potential(result, "case123")
        assert "Missing personal info" in text

    def test_heuristic_fallback_warning(self):
        """When llm_call_count==0 and no warnings, heuristic fallback warning shows."""
        result = MagicMock()
        result.risk_level = "moderate"
        result.overall_potential_score = 50.0
        result.potential_criteria_count = 2
        result.overall_assessment = ""
        result.strongest_criteria = []
        result.weakest_criteria = []
        result.criteria_assessments = {}
        result.priority_actions = []
        result.recommendation = ""
        result.warnings = None  # falsy
        result.llm_call_count = 0

        text = ch._format_eb1a_potential(result, "case456")
        assert "heuristic fallback" in text


class TestFormatEb1aAnalysis:
    def test_basic_formatting(self):
        """_format_eb1a_analysis returns HTML-formatted string."""
        analysis = MagicMock()
        analysis.overall_score = 72.0
        analysis.approval_probability = 0.65
        analysis.risk_level = MagicMock()
        analysis.risk_level.value = "moderate"
        analysis.satisfied_criteria_count = 3
        analysis.meets_minimum_criteria = True
        analysis.criterion_evaluations = {}
        analysis.strengths = ["Strong CV"]
        analysis.priority_recommendations = ["Upload more evidence"]
        analysis.estimated_days_to_ready = 45

        text = ch._format_eb1a_analysis(analysis, "abcdef1234567890")
        assert "EB-1A Analysis" in text
        assert "abcdef12" in text
        assert "72/100" in text
        assert "65%" in text
        assert "MET" in text
        assert "45 days" in text

    def test_minimum_criteria_not_met(self):
        """Shows NOT MET when meets_minimum_criteria is False."""
        analysis = MagicMock()
        analysis.overall_score = 20.0
        analysis.approval_probability = 0.1
        analysis.risk_level = MagicMock()
        analysis.risk_level.value = "critical"
        analysis.satisfied_criteria_count = 1
        analysis.meets_minimum_criteria = False
        analysis.criterion_evaluations = {}
        analysis.strengths = []
        analysis.priority_recommendations = []
        analysis.estimated_days_to_ready = None

        text = ch._format_eb1a_analysis(analysis, "weak-case")
        assert "NOT MET" in text


# ===========================================================================
# _maybe_offer_resume
# ===========================================================================


class TestMaybeOfferResume:
    @pytest.mark.asyncio
    async def test_no_progress_returns_silently(self):
        """No intake progress -- no follow-up message."""
        bc = _make_bot_context()
        update = _make_update()

        with patch(
            "telegram_interface.handlers.case_handlers.get_progress",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await ch._maybe_offer_resume(bc, update, "case1", "Title")

        # Only the main reply should have been sent before this call;
        # the function itself should not call reply_text
        assert update.effective_message.reply_text.await_count == 0

    @pytest.mark.asyncio
    async def test_completed_intake_returns_silently(self):
        """Intake complete -- no follow-up."""
        progress = _FakeProgress(
            user_id="42", case_id="case1", current_block="intake_complete"
        )
        bc = _make_bot_context()
        update = _make_update()

        with patch(
            "telegram_interface.handlers.case_handlers.get_progress",
            new_callable=AsyncMock,
            return_value=progress,
        ):
            await ch._maybe_offer_resume(bc, update, "case1", "Title")

        assert update.effective_message.reply_text.await_count == 0

    @pytest.mark.asyncio
    async def test_unfinished_intake_offers_resume(self):
        """Unfinished intake -- offers resume with inline button."""
        progress = _FakeProgress(
            user_id="42", case_id="case1", current_block="personal_info", current_step=1
        )
        bc = _make_bot_context()
        update = _make_update()

        with patch(
            "telegram_interface.handlers.case_handlers.get_progress",
            new_callable=AsyncMock,
            return_value=progress,
        ), patch(
            "telegram_interface.handlers.case_handlers.BLOCKS_BY_ID",
            _FAKE_BLOCKS,
        ):
            await ch._maybe_offer_resume(bc, update, "case1", "My Case")

        update.effective_message.reply_text.assert_awaited_once()
        call_kwargs = update.effective_message.reply_text.call_args[1]
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_no_effective_user_returns_silently(self):
        """No effective_user -- returns early."""
        bc = _make_bot_context()
        update = _make_update()
        update.effective_user = None

        await ch._maybe_offer_resume(bc, update, "case1", "Title")

        assert update.effective_message.reply_text.await_count == 0

    @pytest.mark.asyncio
    async def test_progress_lookup_exception_handled(self):
        """Exception in get_progress is caught gracefully."""
        bc = _make_bot_context()
        update = _make_update()

        with patch(
            "telegram_interface.handlers.case_handlers.get_progress",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            # Should not raise
            await ch._maybe_offer_resume(bc, update, "case1", "Title")

        assert update.effective_message.reply_text.await_count == 0
