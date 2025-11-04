from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from core.orchestration.eb1a_nodes import build_eb1a_workflow


def test_build_eb1a_workflow_returns_graph() -> None:
    workflow = build_eb1a_workflow()
    assert workflow is not None
