"""Context Engineering Module.

Provides adaptive context formation for LLM interactions:
- ContextManager: Central context orchestration
- AdvancedContextManager: Extended with scoring, compression, pipelines
- ContextPipeline: Processing pipelines for context transformation
- ContextCompressor: Intelligent context compression
- PriorityScorer: Relevance-based prioritization
- IsolatedContext: Isolated context windows for parallel subagents
- ContextSynthesizer: Merge results from multiple isolated contexts

Usage:
    # Advanced Context Management
    from core.context import AdvancedContextManager

    manager = AdvancedContextManager(max_tokens=100000)
    manager.add_case_data(case_info)
    result = await manager.build_advanced_context(
        query="Analyze EB-1A eligibility",
        task_type="legal_analysis"
    )

    # Isolated Context for Parallel Agents
    from core.context import IsolatedContextPool, ContextSynthesizer

    pool = IsolatedContextPool(max_total_tokens=500000)
    ctx1 = pool.create("research_1", task="Research topic A")
    ctx2 = pool.create("research_2", task="Research topic B")

    # After parallel execution
    synthesizer = ContextSynthesizer()
    result = await synthesizer.synthesize_pool(pool, query="main question")
"""

from __future__ import annotations

from .context_compressor import (
    CompressionResult,
    CompressionStrategy,
    ContextCompressor,
)
from .context_manager import (
    # Advanced (v2.0)
    AdvancedContextManager,
    BuiltContext,
    ContextBlock,
    ContextBlockType,
    ContextConfig,
    # Basic
    ContextManager,
    ContextTemplate,
    ContextType,
    create_advanced_context_manager,
    get_context_manager,
)
from .context_pipelines import (
    ComposeStage,
    ContextPipeline,
    EnrichStage,
    FilterStage,
    PipelineContext,
    PipelineStage,
    TransformStage,
    TruncateStage,
)
from .context_synthesizer import (
    ContextSynthesizer,
    SynthesisConfig,
    SynthesisResult,
    SynthesisStrategy,
)
from .isolated_context import (
    ContextMessage,
    ContextState,
    IsolatedContext,
    IsolatedContextPool,
)
from .priority_scorer import (
    PriorityScorer,
    ScoredItem,
    ScoringStrategy,
)

__all__ = [
    # Advanced Manager (v2.0)
    "AdvancedContextManager",
    "BuiltContext",
    "ComposeStage",
    "CompressionResult",
    "CompressionStrategy",
    "ContextBlock",
    "ContextBlockType",
    # Compression
    "ContextCompressor",
    "ContextConfig",
    # Basic Manager
    "ContextManager",
    "ContextMessage",
    # Pipelines
    "ContextPipeline",
    "ContextState",
    # Context Synthesis
    "ContextSynthesizer",
    "ContextTemplate",
    "ContextType",
    "EnrichStage",
    "FilterStage",
    # Isolated Context (v2.0)
    "IsolatedContext",
    "IsolatedContextPool",
    "PipelineContext",
    "PipelineStage",
    # Scoring
    "PriorityScorer",
    "ScoredItem",
    "ScoringStrategy",
    "SynthesisConfig",
    "SynthesisResult",
    "SynthesisStrategy",
    "TransformStage",
    "TruncateStage",
    "create_advanced_context_manager",
    "get_context_manager",
]
