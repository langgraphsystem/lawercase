from __future__ import annotations

import pytest

from core.agents import ComplexityAnalyzer, TaskTier
from core.groupagents.mega_agent import CommandType, MegaAgentCommand


@pytest.mark.asyncio
async def test_complexity_analyzer_detects_deep_tasks():
    analyzer = ComplexityAnalyzer()
    command = MegaAgentCommand(
        user_id="user-1",
        command_type=CommandType.EB1,
        action="full_petition",
        payload={"documents": ["a", "b", "c", "d"], "requires_human_review": True},
        priority=2,
    )

    result = await analyzer.analyze(command)

    assert result.tier is TaskTier.DEEP
    assert result.requires_supervisor
    assert result.recommended_agent in {"eb1_agent", "supervisor_agent", None}


@pytest.mark.asyncio
async def test_complexity_analyzer_detects_quick_tasks():
    analyzer = ComplexityAnalyzer()
    command = MegaAgentCommand(
        user_id="user-2",
        command_type=CommandType.ASK,
        action="question",
        payload={"question": "What are the EB-1A criteria?"},
    )

    result = await analyzer.analyze(command)

    assert result.tier is TaskTier.LANGCHAIN
    assert not result.requires_supervisor
