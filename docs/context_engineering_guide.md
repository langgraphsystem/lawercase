# Context Engineering Guide

This guide documents the context engineering system used in this repository,
with a focus on context pipelines and their usage.

Relevant modules:
- core/context/context_manager.py
- core/context/context_pipelines.py
- core/context/context_compressor.py
- core/context/priority_scorer.py

## Overview

The system has two layers:

1) ContextManager (baseline)
   - Builds context from templates and prioritized blocks.
   - Truncates content to fit a token budget.

2) AdvancedContextManager (v2)
   - Adds scoring, compression, and optional pipelines.
   - Supports specialized block types (case data, legal refs, search results).

Context pipelines are defined in core/context/context_pipelines.py.
They provide composable, stage-based transformations.

## Pipeline Stages

Each pipeline is a sequence of stages that receive a PipelineContext and
return a modified PipelineContext.

Implemented stages:
- FilterStage: remove irrelevant sections based on length/patterns.
- TransformStage: normalize whitespace, strip HTML, apply custom transforms.
- EnrichStage: add metadata headers or extra context.
- ComposeStage: combine multiple content blocks with a template.
- TruncateStage: enforce token budget while preserving structure.

## Quick Start (ContextPipeline)

```python
from core.context.context_pipelines import (
    ContextPipeline,
    PipelineContext,
    FilterStage,
    TransformStage,
    EnrichStage,
    TruncateStage,
)

pipeline = ContextPipeline(name="custom")
pipeline.add_stage(FilterStage(min_length=50))
pipeline.add_stage(TransformStage(normalize_whitespace=True, strip_html=True))
pipeline.add_stage(EnrichStage(add_metadata_header=True))
pipeline.add_stage(TruncateStage(preserve_structure=True))

ctx = PipelineContext(
    content="raw content...",
    query="EB-1A eligibility",
    task_type="legal_analysis",
    max_tokens=4000,
)

result = await pipeline.run(ctx)
print(result.content)
```

Prebuilt pipelines:
```python
default_pipeline = ContextPipeline.default_pipeline()
legal_pipeline = ContextPipeline.legal_pipeline()
research_pipeline = ContextPipeline.research_pipeline()
```

## Advanced Context Manager Usage

```python
from core.context.context_manager import AdvancedContextManager

manager = AdvancedContextManager(max_tokens=100000)
manager.add_case_data("Case summary and facts...")
manager.add_legal_refs("Relevant CFR sections and case law...")
manager.add_examples(["Example A", "Example B"])

result = await manager.build_advanced_context(
    query="Assess EB-1A eligibility",
    task_type="legal_analysis",
    system_prompt="You are a legal assistant.",
)

print(result.content)
print(result.to_dict())
```

## Creating Agent-Specific Context (baseline)

```python
from core.context.context_manager import ContextManager, ContextTemplate, ContextType

cm = ContextManager(max_context_tokens=8000)
cm.register_template(
    ContextTemplate(
        name="writer_agent",
        description="Writer agent template",
        template="Task: {task}\nAgent: {agent_type}",
        context_type=ContextType.SYSTEM,
        max_tokens=2000,
        priority=8,
    )
)

context = cm.create_agent_context(
    agent_type="writer",
    task_description="Draft a petition letter",
    memory_snippets=["Prior award evidence..."],
    available_tools=["http.get", "pdf.generate"],
)
```

## Design Notes

- Token estimation uses ~4 characters per token.
- Use TruncateStage or AdvancedContextManager compression to fit budgets.
- Keep blocks small and well-labeled to improve scoring and retrieval.
- Prefer pipelines for deterministic formatting before LLM calls.

