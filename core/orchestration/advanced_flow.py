"""Advanced orchestration flow (scaffold).

This module will host an advanced LangGraph flow with RAG/CAG/KAG/MAGCC/RAC steps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ..memory.memory_manager import MemoryManager


def build_advanced_flow(memory: MemoryManager) -> Any:
    """Return a compiled advanced flow.

    For now this delegates to the advanced case workflow in ``workflow_graph``.
    """
    from .workflow_graph import build_advanced_case_workflow

    return build_advanced_case_workflow(memory).compile()
