"""Context Engineering System.

This module provides adaptive context management for LLM agents:
- Dynamic context building based on task requirements
- Context compression and optimization
- Agent-specific context templates
- Context relevance scoring
"""

from __future__ import annotations

from .compression import CompressionStrategy, ContextCompressor
from .context_manager import (ContextManager, ContextTemplate,
                              get_context_manager)
from .pipelines import ContextPipeline, ContextPipelineType, create_pipeline
from .relevance import ContextRelevanceScorer, RelevanceMetrics

__all__ = [
    "CompressionStrategy",
    "ContextCompressor",
    "ContextManager",
    "ContextPipeline",
    "ContextPipelineType",
    "ContextRelevanceScorer",
    "ContextTemplate",
    "RelevanceMetrics",
    "create_pipeline",
    "get_context_manager",
]
