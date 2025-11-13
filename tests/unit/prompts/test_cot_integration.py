"""
Tests for Chain-of-Thought integration in agents.

Verifies that CoT prompting is correctly applied across:
- MegaAgent (ask commands, supervisor tasks)
- WriterAgent (document generation)
- SupervisorAgent (planning)
"""

from __future__ import annotations

import pytest

from core.prompts import (CoTTemplate, enhance_prompt_with_cot,
                          select_cot_template)


class TestCoTTemplateSelection:
    """Test automatic template selection based on command types."""

    def test_legal_command_selects_legal_template(self):
        """Legal-related commands should use LEGAL template."""
        template = select_cot_template("validate", "criterion")
        assert template == CoTTemplate.LEGAL

        template = select_cot_template("generate", "petition")
        assert template == CoTTemplate.LEGAL

    def test_analysis_command_selects_analytical_template(self):
        """Analysis commands should use ANALYTICAL template."""
        template = select_cot_template("validate", "check_evidence")
        assert template == CoTTemplate.ANALYTICAL

        template = select_cot_template("analyze", "review_document")
        assert template == CoTTemplate.ANALYTICAL

    def test_generation_command_selects_creative_template(self):
        """Generation commands should use CREATIVE template."""
        template = select_cot_template("generate", "write_letter")
        assert template == CoTTemplate.CREATIVE

        template = select_cot_template("create", "draft_document")
        assert template == CoTTemplate.CREATIVE

    def test_workflow_command_selects_structured_template(self):
        """Workflow commands should use STRUCTURED template."""
        template = select_cot_template("workflow", "case_processing")
        assert template == CoTTemplate.STRUCTURED

        # EB-1A petitions use LEGAL template (immigration law)
        template = select_cot_template("case", "eb1a_petition")
        assert template == CoTTemplate.LEGAL

    def test_simple_command_selects_zero_shot_template(self):
        """Simple commands should use ZERO_SHOT template."""
        template = select_cot_template("ask", "simple_question")
        assert template == CoTTemplate.ZERO_SHOT


class TestCoTPromptEnhancement:
    """Test prompt enhancement with Chain-of-Thought."""

    def test_enhance_prompt_adds_cot_structure(self):
        """Enhanced prompts should include CoT reasoning structure."""
        original = "Analyze this evidence for EB-1A criterion"
        enhanced = enhance_prompt_with_cot(original, "validate", "criterion")

        # Should be longer (added CoT template)
        assert len(enhanced) > len(original)

        # "validate" + "criterion" selects LEGAL template
        # Should include legal reasoning keywords
        assert "Issue" in enhanced or "Rule" in enhanced or "Analysis" in enhanced

    def test_enhance_with_analytical_template(self):
        """Analytical commands should get analytical CoT structure."""
        original = "Evaluate the quality of this evidence"
        enhanced = enhance_prompt_with_cot(original, "analyze", "evaluate")

        # Should include analytical structure
        assert "Analysis" in enhanced or "analysis" in enhanced

    def test_enhance_with_creative_template(self):
        """Creative commands should get creative CoT structure."""
        original = "Generate a legal brief for this case"
        enhanced = enhance_prompt_with_cot(original, "generate", "brief")

        # Should include creative structure
        assert "Purpose" in enhanced or "Audience" in enhanced or "create" in enhanced.lower()

    def test_enhance_with_legal_template(self):
        """Legal commands should get legal reasoning structure."""
        original = "Analyze this legal criterion"
        enhanced = enhance_prompt_with_cot(original, "validate", "legal_criterion")

        # Should include legal reasoning structure
        assert "Issue" in enhanced or "Rule" in enhanced or "legal" in enhanced.lower()


class TestCoTIntegration:
    """Test CoT integration in actual agent workflow."""

    def test_megaagent_uses_cot_by_default(self):
        """MegaAgent should enable CoT by default."""
        from core.groupagents.mega_agent import MegaAgent

        agent = MegaAgent()
        assert agent.use_cot is True

    def test_megaagent_can_disable_cot(self):
        """MegaAgent should allow disabling CoT."""
        from core.groupagents.mega_agent import MegaAgent

        agent = MegaAgent(use_chain_of_thought=False)
        assert agent.use_cot is False

    def test_writer_agent_uses_cot_by_default(self):
        """WriterAgent should enable CoT by default."""
        from core.groupagents.writer_agent import WriterAgent

        agent = WriterAgent()
        assert agent.use_cot is True

    def test_writer_agent_can_disable_cot(self):
        """WriterAgent should allow disabling CoT."""
        from core.groupagents.writer_agent import WriterAgent

        agent = WriterAgent(use_chain_of_thought=False)
        assert agent.use_cot is False

    def test_supervisor_agent_uses_cot_by_default(self):
        """SupervisorAgent should enable CoT by default."""
        from core.groupagents.supervisor_agent import SupervisorAgent

        agent = SupervisorAgent()
        assert agent.use_cot is True

    def test_supervisor_agent_can_disable_cot(self):
        """SupervisorAgent should allow disabling CoT."""
        from core.groupagents.supervisor_agent import SupervisorAgent

        agent = SupervisorAgent(use_chain_of_thought=False)
        assert agent.use_cot is False

    def test_megaagent_enhance_with_cot_method(self):
        """MegaAgent._enhance_with_cot() should work correctly."""
        from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                                 MegaAgentCommand)

        agent = MegaAgent(use_chain_of_thought=True)
        command = MegaAgentCommand(
            user_id="test_user",
            command_type=CommandType.ASK,
            action="query",
            payload={"query": "What is EB-1A?"},
        )

        original = "What is EB-1A?"
        enhanced = agent._enhance_with_cot(original, command)

        # Should be enhanced
        assert len(enhanced) > len(original)
        assert "step" in enhanced.lower() or "Step" in enhanced

    def test_megaagent_cot_disabled_returns_original(self):
        """MegaAgent with CoT disabled should return original prompt."""
        from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                                 MegaAgentCommand)

        agent = MegaAgent(use_chain_of_thought=False)
        command = MegaAgentCommand(
            user_id="test_user",
            command_type=CommandType.ASK,
            action="query",
            payload={"query": "What is EB-1A?"},
        )

        original = "What is EB-1A?"
        result = agent._enhance_with_cot(original, command)

        # Should NOT be enhanced when disabled
        assert result == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
