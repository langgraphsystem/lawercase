"""Memory subsystem package for long-term (ARMT) and working (RMT) memory.

Exposes MemoryManager and data models for integration with agents and RAG.
Includes A-Mem (Agentic Memory) system based on 2025-2026 research.
"""

from __future__ import annotations

from .agentic_memory import (
    AgenticMemory,
    EntityNode,
    EntityRelation,
    MemoryNote,
    MemoryType,
)
from .episodic_memory import EpisodicMemory, EventQuery
from .memory_hierarchy import MemoryContext, MemoryHierarchy
from .memory_manager import MemoryManager
from .models import AuditEvent, MemoryRecord

__all__ = [
    "AgenticMemory",
    "AuditEvent",
    "EntityNode",
    "EntityRelation",
    "EpisodicMemory",
    "EventQuery",
    "MemoryContext",
    "MemoryHierarchy",
    "MemoryManager",
    "MemoryNote",
    "MemoryRecord",
    "MemoryType",
]
