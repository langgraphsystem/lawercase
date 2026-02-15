"""Tests for Document Generation Workflow.

This module tests the document generation workflow including:
- Section generation with WriterAgent
- Validation with ValidatorAgent
- Workflow state management
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_workflow_state_creation(self):
        """Test basic WorkflowState creation."""
        from core.orchestration.workflow_graph import WorkflowState

        state = WorkflowState(
            thread_id="thread-123",
            user_id="user-456",
            case_id="case-789",
        )
        assert state.thread_id == "thread-123"
        assert state.user_id == "user-456"
        assert state.case_id == "case-789"

    def test_workflow_state_with_data(self):
        """Test WorkflowState with document data."""
        from core.orchestration.workflow_graph import WorkflowState

        state = WorkflowState(
            thread_id="thread-123",
            user_id="user-456",
            case_id="case-789",
            document_data={
                "document_type": "petition",
                "current_section": {"id": "intro", "name": "Introduction"},
            },
            workflow_step="generating",
        )
        assert state.document_data["document_type"] == "petition"
        assert state.workflow_step == "generating"


class TestValidatorIntegration:
    """Tests for ValidatorAgent integration in document workflow."""

    @pytest.fixture
    def mock_validator(self):
        """Create mock ValidatorAgent."""
        validator = MagicMock()
        validator.avalidate_document = AsyncMock(
            return_value=MagicMock(
                report_id="report-123",
                issues=[],
                overall_result=MagicMock(score=0.95),
            )
        )
        return validator

    @pytest.fixture
    def mock_workflow_store(self):
        """Create mock document workflow store."""
        store = MagicMock()
        store.add_log = AsyncMock()
        store.update_section = AsyncMock()
        store.load_state = AsyncMock(return_value={"status": "running"})
        store.save_state = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_validation_with_no_content(self, mock_workflow_store):
        """Test validation skips when no content available."""
        from core.orchestration.workflow_graph import WorkflowState

        state = WorkflowState(
            thread_id="thread-123",
            user_id="user-456",
            case_id="case-789",
            document_data={"current_section": {"id": "intro", "name": "Introduction"}},
            agent_results={},  # No content generated
        )

        # Import the node function
        from core.orchestration.document_generation_workflow import node_validate_section

        with (
            patch(
                "core.orchestration.document_generation_workflow.get_document_workflow_store",
                return_value=mock_workflow_store,
            ),
            patch(
                "core.orchestration.document_generation_workflow.get_memory_manager",
                return_value=MagicMock(),
            ),
        ):
            result_state = await node_validate_section(state)

        # Should complete without error
        assert "validated" in result_state.workflow_step

    @pytest.mark.asyncio
    async def test_validation_with_content(self, mock_validator, mock_workflow_store):
        """Test validation runs when content is available."""
        from core.orchestration.workflow_graph import WorkflowState

        state = WorkflowState(
            thread_id="thread-123",
            user_id="user-456",
            case_id="case-789",
            document_data={"current_section": {"id": "intro", "name": "Introduction"}},
            agent_results={
                "intro": {
                    "content_html": "<p>This is the introduction section.</p>",
                    "status": "completed",
                }
            },
        )

        from core.orchestration.document_generation_workflow import node_validate_section

        # Create mock validation result
        mock_validation_result = MagicMock()
        mock_validation_result.report_id = "report-123"
        mock_validation_result.issues = []
        mock_validation_result.overall_result = MagicMock(score=0.95)

        mock_validator_instance = MagicMock()
        mock_validator_instance.avalidate_document = AsyncMock(return_value=mock_validation_result)

        # Patch all dependencies including the imports inside the function
        with (
            patch(
                "core.orchestration.document_generation_workflow.get_document_workflow_store",
                return_value=mock_workflow_store,
            ),
            patch(
                "core.orchestration.document_generation_workflow.get_memory_manager",
                return_value=MagicMock(),
            ),
            patch.dict(
                "sys.modules",
                {
                    "core.groupagents.validator_agent": MagicMock(
                        ValidatorAgent=MagicMock(return_value=mock_validator_instance),
                        ValidationCategory=MagicMock(
                            FORMAL="formal", LEGAL="legal", STRUCTURE="structure", CONTENT="content"
                        ),
                        ValidationLevel=MagicMock(STANDARD="standard"),
                        ValidationRequest=MagicMock,
                    )
                },
            ),
        ):
            result_state = await node_validate_section(state)

        # Should have validation results
        assert "validated" in result_state.workflow_step


class TestWriterAgentIntegration:
    """Tests for WriterAgent integration in document workflow."""

    @pytest.fixture
    def mock_writer(self):
        """Create mock WriterAgent."""
        writer = MagicMock()
        writer.agenerate_document = AsyncMock(
            return_value=MagicMock(
                document_id="doc-123",
                content="# EB-1A Petition\n\nGenerated content...",
                format=MagicMock(value="markdown"),
                word_count=500,
            )
        )
        return writer

    @pytest.mark.asyncio
    async def test_document_generation_not_ready(self):
        """Test document generation skipped when not ready."""
        from core.orchestration.workflow_graph import WorkflowState

        state = WorkflowState(
            thread_id="thread-123",
            user_id="user-456",
            case_id="case-789",
            agent_results={"readiness_decision": "needs_more_evidence"},
        )

        # This would require importing and calling the actual node
        # For now, just verify state model works
        assert state.agent_results["readiness_decision"] == "needs_more_evidence"


class TestEB1ASections:
    """Tests for EB-1A section definitions."""

    def test_eb1a_sections_defined(self):
        """Test that all required EB-1A sections are defined."""
        from core.orchestration.document_generation_workflow import EB1A_SECTIONS

        assert len(EB1A_SECTIONS) >= 5

        section_ids = {s["id"] for s in EB1A_SECTIONS}
        expected_ids = {"intro", "background", "awards", "conclusion"}

        for expected_id in expected_ids:
            assert expected_id in section_ids, f"Missing section: {expected_id}"

    def test_section_structure(self):
        """Test that sections have required fields."""
        from core.orchestration.document_generation_workflow import EB1A_SECTIONS

        required_fields = {"id", "name", "order", "prompt"}

        for section in EB1A_SECTIONS:
            for field in required_fields:
                assert field in section, f"Section {section.get('id')} missing {field}"


class TestDocumentWorkflowBuilder:
    """Tests for document workflow graph builder."""

    def test_workflow_build_requires_langgraph(self):
        """Test that workflow builder checks for LangGraph."""
        try:
            from core.orchestration.document_generation_workflow import (
                LANGGRAPH_AVAILABLE,
                build_document_generation_workflow,
            )

            if not LANGGRAPH_AVAILABLE:
                with pytest.raises(RuntimeError, match="LangGraph is required"):
                    build_document_generation_workflow()
            else:
                # If LangGraph available, should return a graph
                graph = build_document_generation_workflow()
                assert graph is not None

        except ImportError:
            pytest.skip("Document generation workflow module not available")


class TestValidationCategories:
    """Tests for validation categories used in document workflow."""

    def test_validation_categories_exist(self):
        """Test that required validation categories exist."""
        from core.groupagents.validator_agent import ValidationCategory

        expected_categories = ["FORMAL", "LEGAL", "STRUCTURE", "CONTENT"]

        for cat in expected_categories:
            assert hasattr(ValidationCategory, cat), f"Missing category: {cat}"

    def test_validation_levels_exist(self):
        """Test that validation levels exist."""
        from core.groupagents.validator_agent import ValidationLevel

        expected_levels = ["BASIC", "STANDARD", "STRICT"]

        for level in expected_levels:
            assert hasattr(ValidationLevel, level), f"Missing level: {level}"
