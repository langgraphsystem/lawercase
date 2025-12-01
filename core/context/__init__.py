"""Context Engineering System.

This module provides adaptive context management for LLM agents:
- Dynamic context building based on task requirements
- Context compression and optimization (LLM-based and rule-based)
- Agent-specific context templates and pipelines
- Context relevance scoring with embedding support
- Accurate token counting with tiktoken
"""

from __future__ import annotations

from .compression import (
    CompressionStrategy,
    ContextCompressor,
    count_tokens,
    estimate_tokens,
    trim_to_tokens,
)
from .context_manager import (
    ContextBlock,
    ContextManager,
    ContextTemplate,
    ContextType,
    get_context_manager,
)
from .pipelines import ContextPipeline, ContextPipelineType, create_pipeline
from .relevance import ContextRelevanceScorer, RelevanceMetrics, cosine_similarity

__all__ = [
    "CompressionStrategy",
    "ContextBlock",
    "ContextCompressor",
    "ContextManager",
    "ContextPipeline",
    "ContextPipelineType",
    "ContextRelevanceScorer",
    "ContextTemplate",
    "ContextType",
    "RelevanceMetrics",
    "cosine_similarity",
    "count_tokens",
    "create_pipeline",
    "estimate_tokens",
    "get_context_manager",
    "trim_to_tokens",
]
