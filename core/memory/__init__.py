"""Memory subsystem package for long-term (ARMT) and working (RMT) memory.

Exposes MemoryManager and data models for integration with agents and RAG.
Includes A-Mem (Agentic Memory) system based on 2025-2026 research.

Advanced features:
- ConsolidationEngine: Intelligent memory consolidation
- ImportanceScorer: Multi-factor memory importance scoring
- TieredStorageManager: Hot/warm/cold/archive storage tiers

Note: MemoryManager is now imported from memory_manager_v2 which includes:
- ConsolidationPolicy integration
- DeterministicEmbedder as default
- Better production/dev factory functions
"""

from __future__ import annotations

from .agentic_memory import AgenticMemory, EntityNode, EntityRelation, MemoryNote, MemoryType
from .consolidation_engine import (
    ConsolidationEngine,
    ConsolidationResult,
    ConsolidationStrategy,
    ImportanceScore,
    ImportanceScorer,
    MemoryEntry,
    MemoryTier,
    TieredStorageManager,
    create_consolidation_engine,
)
from .episodic_memory import EpisodicMemory, EventQuery
from .memory_hierarchy import MemoryContext, MemoryHierarchy

# Keep backward compatibility alias
from .memory_manager import MemoryManager as MemoryManagerV1

# Import MemoryManager from v2 (improved version with ConsolidationPolicy)
from .memory_manager_v2 import (
    MemoryManager,
    create_dev_memory_manager,
    create_production_memory_manager,
    create_supabase_memory_manager,
    get_memory_manager,
    reset_memory_manager,
)
from .models import AuditEvent, MemoryRecord

__all__ = [
    # Agentic Memory
    "AgenticMemory",
    # Core
    "AuditEvent",
    # Consolidation Engine (v2.0)
    "ConsolidationEngine",
    "ConsolidationResult",
    "ConsolidationStrategy",
    "EntityNode",
    "EntityRelation",
    # Episodic Memory
    "EpisodicMemory",
    "EventQuery",
    "ImportanceScore",
    "ImportanceScorer",
    # Memory Hierarchy
    "MemoryContext",
    "MemoryEntry",
    "MemoryHierarchy",
    "MemoryManager",
    # Backward compatibility
    "MemoryManagerV1",
    "MemoryNote",
    "MemoryRecord",
    "MemoryTier",
    "MemoryType",
    "TieredStorageManager",
    "create_consolidation_engine",
    # Factory functions (v2)
    "create_dev_memory_manager",
    "create_production_memory_manager",
    "create_supabase_memory_manager",
    "get_memory_manager",
    "reset_memory_manager",
]
