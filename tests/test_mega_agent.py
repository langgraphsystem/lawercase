"""Tests for core.groupagents.mega_agent -- MegaAgent orchestrator.

All external dependencies (MemoryManager, ComplexityAnalyzer, SupervisorAgent,
IntelligentRouter, CaseAgent, EB1Agent, WriterAgent, ValidatorAgent, security
helpers, DB manager, etc.) are fully mocked so that MegaAgent is tested in
complete isolation.
"""

from __future__ import annotations

import os

# Ensure security config can be instantiated during import
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from unittest.mock import AsyncMock, MagicMock

import pytest

_PATCH_PREFIX = "core.groupagents.mega_agent"


@pytest.fixture(autouse=True)
def _isolate_mega_agent(monkeypatch):
    """Patch every external dependency that MegaAgent touches during init."""

    # --- security helpers (module-level calls inside __init__) ---
    mock_rbac = MagicMock()
    mock_rbac.check_permission.return_value = True
    monkeypatch.setattr(f"{_PATCH_PREFIX}.get_rbac_manager", lambda: mock_rbac)

    mock_prompt_det = MagicMock()
    mock_prompt_det.analyze.return_value = MagicMock(
        is_injection=False, confidence=0.0, injection_types=[]
    )
    monkeypatch.setattr(f"{_PATCH_PREFIX}.get_prompt_detector", lambda: mock_prompt_det)

    mock_audit = MagicMock()
    monkeypatch.setattr(f"{_PATCH_PREFIX}.get_audit_trail", lambda: mock_audit)

    # security_config -- make sure features are "enabled" but harmless
    mock_sec_cfg = MagicMock()
    mock_sec_cfg.prompt_detection_enabled = False
    mock_sec_cfg.audit_enabled = False
    mock_sec_cfg.rbac_strict_mode = False
    monkeypatch.setattr(f"{_PATCH_PREFIX}.security_config", mock_sec_cfg)

    # --- DB manager ---
    monkeypatch.setattr(f"{_PATCH_PREFIX}.get_db_manager", lambda: None)

    # --- MemoryManager ---
    mock_memory_cls = MagicMock()
    mock_memory_inst = MagicMock()
    mock_memory_inst.alog_audit = AsyncMock()
    mock_memory_inst.aretrieve = AsyncMock(return_value=[])
    mock_memory_inst.aretrieve_all_sources = AsyncMock(return_value=[])
    mock_memory_inst.awrite = AsyncMock()
    mock_memory_cls.return_value = mock_memory_inst
    monkeypatch.setattr(f"{_PATCH_PREFIX}.MemoryManager", mock_memory_cls)

    # --- ComplexityAnalyzer ---
    mock_ca_cls = MagicMock()
    mock_ca_inst = MagicMock()
    mock_ca_inst.analyze = AsyncMock()
    mock_ca_cls.return_value = mock_ca_inst
    monkeypatch.setattr(f"{_PATCH_PREFIX}.ComplexityAnalyzer", mock_ca_cls)

    # --- Sub-agents ---
    for agent_cls_name in (
        "CaseAgent",
        "EB1Agent",
        "WriterAgent",
        "ValidatorAgent",
        "SupervisorAgent",
    ):
        mock_cls = MagicMock()
        mock_cls.return_value = MagicMock()
        monkeypatch.setattr(f"{_PATCH_PREFIX}.{agent_cls_name}", mock_cls)


from core.agents.complexity_analyzer import TaskTier
from core.groupagents.mega_agent import (
    CommandType,
    MegaAgent,
    MegaAgentCommand,
    MegaAgentResponse,
    Permission,
    RoutingDecision,
    UserRole,
)


# ===================================================================
# 1. UserRole enum values
# ===================================================================
class TestUserRole:
    def test_admin_value(self):
        assert UserRole.ADMIN.value == "admin"

    def test_lawyer_value(self):
        assert UserRole.LAWYER.value == "lawyer"

    def test_paralegal_value(self):
        assert UserRole.PARALEGAL.value == "paralegal"

    def test_client_value(self):
        assert UserRole.CLIENT.value == "client"

    def test_viewer_value(self):
        assert UserRole.VIEWER.value == "viewer"

    def test_all_members(self):
        expected = {"ADMIN", "LAWYER", "PARALEGAL", "CLIENT", "VIEWER"}
        assert {m.name for m in UserRole} == expected

    def test_is_string_enum(self):
        assert isinstance(UserRole.ADMIN, str)


# ===================================================================
# 2. CommandType enum values
# ===================================================================
class TestCommandType:
    def test_all_command_types(self):
        expected = {
            "ASK",
            "TRAIN",
            "VALIDATE",
            "GENERATE",
            "CASE",
            "SEARCH",
            "WORKFLOW",
            "ADMIN",
            "TOOL",
            "EB1",
            "DEEP_RESEARCH",
        }
        assert {m.name for m in CommandType} == expected

    def test_ask_value(self):
        assert CommandType.ASK.value == "ask"

    def test_deep_research_value(self):
        assert CommandType.DEEP_RESEARCH.value == "deep_research"


# ===================================================================
# 3. MegaAgent instantiation with all None defaults
# ===================================================================
class TestMegaAgentInit:
    def test_instantiation_defaults(self):
        agent = MegaAgent()
        assert agent is not None
        assert agent.memory is not None
        assert agent.complexity_analyzer is not None
        assert agent.case_agent is not None
        assert agent.writer_agent is not None
        assert agent.eb1_agent is not None
        assert agent.validator_agent is not None
        assert agent.supervisor_agent is not None

    def test_instantiation_with_explicit_none(self):
        agent = MegaAgent(
            memory_manager=None,
            complexity_analyzer=None,
            supervisor_agent=None,
            llm_router=None,
            use_chain_of_thought=True,
        )
        assert agent.use_cot is True

    def test_cot_disabled(self):
        agent = MegaAgent(use_chain_of_thought=False)
        assert agent.use_cot is False

    def test_llm_router_stored(self):
        mock_router = MagicMock()
        agent = MegaAgent(llm_router=mock_router)
        assert agent.llm_router is mock_router

    def test_user_roles_cache_starts_empty(self):
        agent = MegaAgent()
        assert agent._user_roles == {}

    def test_command_stats_starts_empty(self):
        agent = MegaAgent()
        assert agent._command_stats == {}


# ===================================================================
# 4. get_stats() returns expected structure
# ===================================================================
class TestGetStats:
    @pytest.mark.asyncio
    async def test_stats_structure_empty(self):
        agent = MegaAgent()
        stats = await agent.get_stats()
        assert "command_stats" in stats
        assert "total_commands" in stats
        assert "registered_users" in stats
        assert "available_agents" in stats

    @pytest.mark.asyncio
    async def test_stats_initial_values(self):
        agent = MegaAgent()
        stats = await agent.get_stats()
        assert stats["command_stats"] == {}
        assert stats["total_commands"] == 0
        assert stats["registered_users"] == 0
        assert isinstance(stats["available_agents"], list)
        assert len(stats["available_agents"]) > 0

    @pytest.mark.asyncio
    async def test_stats_after_update(self):
        agent = MegaAgent()
        agent._update_stats(CommandType.ASK)
        agent._update_stats(CommandType.ASK)
        agent._update_stats(CommandType.CASE)
        stats = await agent.get_stats()
        assert stats["command_stats"]["ask"] == 2
        assert stats["command_stats"]["case"] == 1
        assert stats["total_commands"] == 3


# ===================================================================
# 5. health_check() returns expected structure
# ===================================================================
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_structure(self):
        agent = MegaAgent()
        result = await agent.health_check()
        assert "status" in result
        assert "memory_system" in result
        assert "case_agent" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        agent = MegaAgent()
        result = await agent.health_check()
        assert result["status"] == "healthy"
        assert result["memory_system"] is True
        assert result["case_agent"] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        agent = MegaAgent()
        # Break memory to force unhealthy path
        agent.memory = None
        result = await agent.health_check()
        # memory_system will be False but status still "healthy" because
        # the None check doesn't raise
        assert result["memory_system"] is False


# ===================================================================
# 6. set_user_role stores the role
# ===================================================================
class TestSetUserRole:
    @pytest.mark.asyncio
    async def test_set_and_retrieve(self):
        agent = MegaAgent()
        await agent.set_user_role("user_123", UserRole.ADMIN)
        assert agent._user_roles["user_123"] == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_overwrite_role(self):
        agent = MegaAgent()
        await agent.set_user_role("user_123", UserRole.CLIENT)
        await agent.set_user_role("user_123", UserRole.LAWYER)
        assert agent._user_roles["user_123"] == UserRole.LAWYER

    @pytest.mark.asyncio
    async def test_multiple_users(self):
        agent = MegaAgent()
        await agent.set_user_role("alice", UserRole.ADMIN)
        await agent.set_user_role("bob", UserRole.VIEWER)
        assert agent._user_roles["alice"] == UserRole.ADMIN
        assert agent._user_roles["bob"] == UserRole.VIEWER

    @pytest.mark.asyncio
    async def test_audit_logged_on_set(self):
        agent = MegaAgent()
        agent.memory.alog_audit = AsyncMock()
        await agent.set_user_role("user_x", UserRole.PARALEGAL)
        agent.memory.alog_audit.assert_awaited_once()


# ===================================================================
# 7. handle_command with a simple ASK command
# ===================================================================
class TestHandleCommand:
    def _make_ask_command(self, user_id: str = "user_1", query: str = "What is EB-1A?"):
        return MegaAgentCommand(
            user_id=user_id,
            command_type=CommandType.ASK,
            action="ask",
            payload={"query": query},
        )

    @pytest.mark.asyncio
    async def test_handle_ask_success(self):
        agent = MegaAgent()

        mock_decision = RoutingDecision(
            tier=TaskTier.LANGCHAIN,
            score=0.5,
            agent="supervisor_agent",
            reason="test",
        )

        agent._route_command = AsyncMock(return_value=mock_decision)
        agent._dispatch_to_agent = AsyncMock(
            return_value={"operation": "ask", "answer": "EB-1A is an immigration category."}
        )
        agent._log_command_start = AsyncMock()
        agent._log_command_completion = AsyncMock()

        command = self._make_ask_command()
        response = await agent.handle_command(command, user_role=UserRole.LAWYER)

        assert isinstance(response, MegaAgentResponse)
        assert response.success is True
        assert response.result is not None
        assert response.result["operation"] == "ask"
        assert response.command_id == command.command_id
        assert response.agent_used == "supervisor_agent"
        assert response.execution_time is not None
        assert response.execution_time >= 0.0

    @pytest.mark.asyncio
    async def test_handle_command_error_returns_failure_response(self):
        agent = MegaAgent()
        agent._route_command = AsyncMock(side_effect=RuntimeError("routing broke"))
        agent._log_command_start = AsyncMock()
        agent._log_command_error = AsyncMock()

        command = self._make_ask_command()
        response = await agent.handle_command(command, user_role=UserRole.LAWYER)

        assert response.success is False
        assert "routing broke" in response.error

    @pytest.mark.asyncio
    async def test_handle_command_records_stats(self):
        agent = MegaAgent()

        mock_decision = RoutingDecision(
            tier=TaskTier.LANGCHAIN,
            score=0.5,
            agent="supervisor_agent",
            reason="test",
        )
        agent._route_command = AsyncMock(return_value=mock_decision)
        agent._dispatch_to_agent = AsyncMock(return_value={"operation": "ask"})
        agent._log_command_start = AsyncMock()
        agent._log_command_completion = AsyncMock()

        command = self._make_ask_command()
        await agent.handle_command(command, user_role=UserRole.LAWYER)

        assert agent._command_stats.get("ask", 0) == 1

    @pytest.mark.asyncio
    async def test_handle_command_populates_routing_metadata(self):
        agent = MegaAgent()

        mock_decision = RoutingDecision(
            tier=TaskTier.LANGGRAPH,
            score=0.85,
            agent="case_agent",
            reason="complex case operation",
        )
        agent._route_command = AsyncMock(return_value=mock_decision)
        agent._dispatch_to_agent = AsyncMock(return_value={"status": "ok"})
        agent._log_command_start = AsyncMock()
        agent._log_command_completion = AsyncMock()

        command = MegaAgentCommand(
            user_id="user_1",
            command_type=CommandType.CASE,
            action="create",
            payload={"title": "Test Case"},
        )
        response = await agent.handle_command(command, user_role=UserRole.ADMIN)

        assert response.success is True
        assert response.tier == TaskTier.LANGGRAPH
        assert response.routing_metadata is not None
        assert response.routing_metadata["agent"] == "case_agent"
        assert response.routing_metadata["score"] == 0.85

    @pytest.mark.asyncio
    async def test_handle_command_uses_cached_role_when_none(self):
        agent = MegaAgent()
        # Pre-set user role in cache
        agent._user_roles["user_1"] = UserRole.ADMIN

        mock_decision = RoutingDecision(
            tier=TaskTier.LANGCHAIN,
            score=0.3,
            agent="supervisor_agent",
            reason="test",
        )
        agent._route_command = AsyncMock(return_value=mock_decision)
        agent._dispatch_to_agent = AsyncMock(return_value={"ok": True})
        agent._log_command_start = AsyncMock()
        agent._log_command_completion = AsyncMock()

        command = self._make_ask_command()
        # user_role=None so it must look up from cache
        response = await agent.handle_command(command, user_role=None)
        assert response.success is True


# ===================================================================
# 8. Permission checking works for different roles
# ===================================================================
class TestPermissionChecking:
    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self):
        agent = MegaAgent()
        for ct in CommandType:
            cmd = MegaAgentCommand(
                user_id="admin_user",
                command_type=ct,
                action="create",
                payload={},
            )
            result = await agent._check_permission(cmd, UserRole.ADMIN)
            assert result is True, f"ADMIN should have permission for {ct}"

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_case(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="viewer_user",
            command_type=CommandType.CASE,
            action="create",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.VIEWER)
        assert result is False

    @pytest.mark.asyncio
    async def test_viewer_can_read_case(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="viewer_user",
            command_type=CommandType.CASE,
            action="get",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.VIEWER)
        assert result is True

    @pytest.mark.asyncio
    async def test_client_cannot_generate_document(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="client_user",
            command_type=CommandType.GENERATE,
            action="letter",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.CLIENT)
        assert result is False

    @pytest.mark.asyncio
    async def test_lawyer_can_generate_document(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="lawyer_user",
            command_type=CommandType.GENERATE,
            action="letter",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.LAWYER)
        assert result is True

    @pytest.mark.asyncio
    async def test_client_cannot_admin(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="client_user",
            command_type=CommandType.ADMIN,
            action="batch_train",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.CLIENT)
        assert result is False

    @pytest.mark.asyncio
    async def test_paralegal_can_use_tool(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="para_user",
            command_type=CommandType.TOOL,
            action="run",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.PARALEGAL)
        assert result is True

    @pytest.mark.asyncio
    async def test_viewer_cannot_use_tool(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="viewer_user",
            command_type=CommandType.TOOL,
            action="run",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.VIEWER)
        assert result is False

    @pytest.mark.asyncio
    async def test_viewer_cannot_validate(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="viewer_user",
            command_type=CommandType.VALIDATE,
            action="document",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.VIEWER)
        assert result is False

    @pytest.mark.asyncio
    async def test_lawyer_can_validate(self):
        agent = MegaAgent()
        cmd = MegaAgentCommand(
            user_id="lawyer_user",
            command_type=CommandType.VALIDATE,
            action="document",
            payload={},
        )
        result = await agent._check_permission(cmd, UserRole.LAWYER)
        assert result is True

    @pytest.mark.asyncio
    async def test_permission_denied_surfaces_in_handle_command(self):
        """When RBAC denies access, handle_command returns success=False."""
        agent = MegaAgent()
        agent._log_command_start = AsyncMock()
        agent._log_command_error = AsyncMock()

        cmd = MegaAgentCommand(
            user_id="viewer_user",
            command_type=CommandType.ADMIN,
            action="batch_train",
            payload={},
        )
        response = await agent.handle_command(cmd, user_role=UserRole.VIEWER)
        assert response.success is False
        assert "does not have permission" in response.error


# ===================================================================
# 9. MegaAgentCommand and MegaAgentResponse models
# ===================================================================
class TestModels:
    def test_command_defaults(self):
        cmd = MegaAgentCommand(
            user_id="u1",
            command_type=CommandType.ASK,
            action="ask",
        )
        assert cmd.command_id  # auto-generated UUID
        assert cmd.payload == {}
        assert cmd.context is None
        assert cmd.requested_agent is None
        assert cmd.requested_tier is None
        assert cmd.auto_route is True
        assert cmd.priority == 5
        assert cmd.timestamp is not None

    def test_response_success_model(self):
        resp = MegaAgentResponse(
            command_id="abc",
            success=True,
            result={"data": 1},
            agent_used="case_agent",
            execution_time=0.5,
        )
        assert resp.success is True
        assert resp.error is None
        assert resp.result == {"data": 1}

    def test_response_failure_model(self):
        resp = MegaAgentResponse(
            command_id="abc",
            success=False,
            error="something went wrong",
        )
        assert resp.success is False
        assert resp.result is None


# ===================================================================
# 10. RoutingDecision dataclass
# ===================================================================
class TestRoutingDecision:
    def test_to_dict(self):
        rd = RoutingDecision(
            tier=TaskTier.LANGGRAPH,
            score=0.7777,
            agent="case_agent",
            reason="complex",
        )
        d = rd.to_dict()
        assert d["tier"] == "langgraph"
        assert d["score"] == 0.778  # rounded to 3 decimals
        assert d["agent"] == "case_agent"
        assert d["reason"] == "complex"
        assert d["requires_supervisor"] is False
        assert d["metadata"] == {}

    def test_defaults(self):
        rd = RoutingDecision(
            tier=TaskTier.LANGCHAIN,
            score=0.0,
            agent="tool_runner",
            reason="quick",
        )
        assert rd.requires_supervisor is False
        assert rd.metadata == {}


# ===================================================================
# 11. ROLE_PERMISSIONS matrix consistency
# ===================================================================
class TestRolePermissionsMatrix:
    def test_admin_has_all_permissions(self):
        all_perms = set(Permission)
        admin_perms = set(MegaAgent.ROLE_PERMISSIONS[UserRole.ADMIN])
        assert admin_perms == all_perms

    def test_viewer_only_read(self):
        viewer_perms = MegaAgent.ROLE_PERMISSIONS[UserRole.VIEWER]
        assert viewer_perms == [Permission.READ_CASE]

    def test_client_only_read(self):
        client_perms = MegaAgent.ROLE_PERMISSIONS[UserRole.CLIENT]
        assert client_perms == [Permission.READ_CASE]

    def test_every_role_has_entry(self):
        for role in UserRole:
            assert role in MegaAgent.ROLE_PERMISSIONS

    def test_lawyer_has_no_delete_or_admin(self):
        lawyer_perms = set(MegaAgent.ROLE_PERMISSIONS[UserRole.LAWYER])
        assert Permission.DELETE_CASE not in lawyer_perms
        assert Permission.ADMIN_ACCESS not in lawyer_perms
        assert Permission.VIEW_AUDIT not in lawyer_perms

    def test_paralegal_subset_of_lawyer(self):
        para = set(MegaAgent.ROLE_PERMISSIONS[UserRole.PARALEGAL])
        lawyer = set(MegaAgent.ROLE_PERMISSIONS[UserRole.LAWYER])
        assert para.issubset(lawyer)
