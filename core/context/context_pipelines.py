"""Context Processing Pipelines.

Modular pipeline system for context transformation:
- Filter: Remove irrelevant content
- Transform: Modify/format content
- Enrich: Add additional context
- Compose: Combine multiple sources
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
import re
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PipelineContext:
    """Context passed through pipeline stages."""

    content: str
    query: str = ""
    task_type: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    max_tokens: int = 100000

    @property
    def remaining_tokens(self) -> int:
        return self.max_tokens - self.tokens_used


class PipelineStage(ABC):
    """Abstract base for pipeline stages."""

    name: str = "base"

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Process context and return modified context."""


class FilterStage(PipelineStage):
    """Filter out irrelevant content."""

    name = "filter"

    def __init__(
        self,
        min_length: int = 10,
        max_length: int | None = None,
        blocked_patterns: list[str] | None = None,
        required_patterns: list[str] | None = None,
        custom_filter: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize filter stage.

        Args:
            min_length: Minimum content length
            max_length: Maximum content length (None = no limit)
            blocked_patterns: Regex patterns to remove
            required_patterns: At least one must match
            custom_filter: Custom filter function (returns True to keep)
        """
        self.min_length = min_length
        self.max_length = max_length
        self.blocked_patterns = blocked_patterns or []
        self.required_patterns = required_patterns or []
        self.custom_filter = custom_filter

    def _should_keep(self, text: str) -> bool:
        """Check if text should be kept."""
        # Length check
        if len(text) < self.min_length:
            return False
        if self.max_length and len(text) > self.max_length:
            return False

        # Blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        # Required patterns
        if self.required_patterns:
            found = any(re.search(p, text, re.IGNORECASE) for p in self.required_patterns)
            if not found:
                return False

        # Custom filter
        return not (self.custom_filter and not self.custom_filter(text))

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Filter content."""
        # Split into paragraphs/sections
        sections = re.split(r"\n\n+", ctx.content)

        # Filter sections
        filtered = [s for s in sections if self._should_keep(s)]

        ctx.content = "\n\n".join(filtered)
        ctx.tokens_used = len(ctx.content) // 4

        return ctx


class TransformStage(PipelineStage):
    """Transform/format content."""

    name = "transform"

    def __init__(
        self,
        transformations: list[Callable[[str], str]] | None = None,
        normalize_whitespace: bool = True,
        strip_html: bool = True,
        max_line_length: int | None = None,
    ) -> None:
        """Initialize transform stage.

        Args:
            transformations: Custom transform functions
            normalize_whitespace: Normalize spacing
            strip_html: Remove HTML tags
            max_line_length: Wrap long lines
        """
        self.transformations = transformations or []
        self.normalize_whitespace = normalize_whitespace
        self.strip_html = strip_html
        self.max_line_length = max_line_length

    def _normalize(self, text: str) -> str:
        """Normalize whitespace."""
        # Multiple spaces to single
        text = re.sub(r" +", " ", text)
        # Multiple newlines to double
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags."""
        return re.sub(r"<[^>]+>", "", text)

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Transform content."""
        text = ctx.content

        if self.strip_html:
            text = self._strip_html(text)

        if self.normalize_whitespace:
            text = self._normalize(text)

        # Apply custom transformations
        for transform in self.transformations:
            text = transform(text)

        ctx.content = text
        ctx.tokens_used = len(text) // 4

        return ctx


class EnrichStage(PipelineStage):
    """Enrich content with additional context."""

    name = "enrich"

    def __init__(
        self,
        enrichers: list[Callable[[PipelineContext], str]] | None = None,
        add_metadata_header: bool = False,
        add_source_citations: bool = False,
    ) -> None:
        """Initialize enrich stage.

        Args:
            enrichers: Functions that return additional context
            add_metadata_header: Add metadata as header
            add_source_citations: Add source references
        """
        self.enrichers = enrichers or []
        self.add_metadata_header = add_metadata_header
        self.add_source_citations = add_source_citations

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Enrich content."""
        parts = []

        # Add metadata header
        if self.add_metadata_header and ctx.metadata:
            header_parts = []
            if ctx.task_type:
                header_parts.append(f"Task: {ctx.task_type}")
            if ctx.query:
                header_parts.append(f"Query: {ctx.query}")
            if header_parts:
                parts.append("---\n" + "\n".join(header_parts) + "\n---")

        # Main content
        parts.append(ctx.content)

        # Apply enrichers
        for enricher in self.enrichers:
            additional = enricher(ctx)
            if additional:
                parts.append(additional)

        ctx.content = "\n\n".join(parts)
        ctx.tokens_used = len(ctx.content) // 4

        return ctx


class ComposeStage(PipelineStage):
    """Compose multiple content blocks."""

    name = "compose"

    def __init__(
        self,
        template: str | None = None,
        section_separator: str = "\n\n---\n\n",
        max_sections: int | None = None,
    ) -> None:
        """Initialize compose stage.

        Args:
            template: Format template with {content} placeholder
            section_separator: Separator between sections
            max_sections: Maximum number of sections to include
        """
        self.template = template
        self.section_separator = section_separator
        self.max_sections = max_sections

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Compose content sections."""
        # Get additional blocks from metadata
        blocks = ctx.metadata.get("content_blocks", [])

        if blocks:
            # Limit sections
            if self.max_sections:
                blocks = blocks[: self.max_sections]

            # Compose
            all_content = [ctx.content, *blocks]
            ctx.content = self.section_separator.join(all_content)

        # Apply template
        if self.template:
            ctx.content = self.template.format(
                content=ctx.content,
                query=ctx.query,
                task_type=ctx.task_type,
                **ctx.metadata,
            )

        ctx.tokens_used = len(ctx.content) // 4

        return ctx


class TruncateStage(PipelineStage):
    """Truncate content to fit token budget."""

    name = "truncate"

    def __init__(
        self,
        preserve_structure: bool = True,
        preserve_end: bool = False,
    ) -> None:
        self.preserve_structure = preserve_structure
        self.preserve_end = preserve_end

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Truncate to fit budget."""
        target_chars = ctx.remaining_tokens * 4

        if len(ctx.content) <= target_chars:
            return ctx

        if self.preserve_structure:
            # Try to break at paragraph
            if self.preserve_end:
                text = ctx.content[-target_chars:]
                para_break = text.find("\n\n")
                if para_break > 0 and para_break < len(text) // 2:
                    text = "..." + text[para_break:].strip()
            else:
                text = ctx.content[:target_chars]
                para_break = text.rfind("\n\n")
                if para_break > len(text) // 2:
                    text = text[:para_break].strip() + "..."
        elif self.preserve_end:
            text = "..." + ctx.content[-target_chars:]
        else:
            text = ctx.content[:target_chars] + "..."

        ctx.content = text
        ctx.tokens_used = len(text) // 4

        return ctx


class ContextPipeline:
    """Composable context processing pipeline.

    Usage:
        pipeline = ContextPipeline()
        pipeline.add_stage(FilterStage(min_length=50))
        pipeline.add_stage(TransformStage(normalize_whitespace=True))
        pipeline.add_stage(EnrichStage(add_metadata_header=True))
        pipeline.add_stage(TruncateStage())

        ctx = PipelineContext(
            content=raw_text,
            query="EB-1A eligibility",
            max_tokens=4000
        )

        result = await pipeline.run(ctx)
        print(result.content)
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> ContextPipeline:
        """Add a stage to the pipeline."""
        self.stages.append(stage)
        return self

    def remove_stage(self, stage_name: str) -> ContextPipeline:
        """Remove a stage by name."""
        self.stages = [s for s in self.stages if s.name != stage_name]
        return self

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        """Run all stages in sequence."""
        for stage in self.stages:
            ctx = await stage.process(ctx)
        return ctx

    def run_sync(self, ctx: PipelineContext) -> PipelineContext:
        """Run pipeline synchronously."""
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.run(ctx))
        finally:
            loop.close()

    @classmethod
    def default_pipeline(cls) -> ContextPipeline:
        """Create default processing pipeline."""
        pipeline = cls("default")
        pipeline.add_stage(FilterStage(min_length=20))
        pipeline.add_stage(
            TransformStage(
                normalize_whitespace=True,
                strip_html=True,
            )
        )
        pipeline.add_stage(TruncateStage(preserve_structure=True))
        return pipeline

    @classmethod
    def legal_pipeline(cls) -> ContextPipeline:
        """Create pipeline optimized for legal documents."""
        pipeline = cls("legal")
        pipeline.add_stage(
            FilterStage(
                min_length=30,
                required_patterns=[
                    r"\b(law|legal|statute|regulation|court|cfr|usc)\b",
                ],
            )
        )
        pipeline.add_stage(TransformStage(normalize_whitespace=True))
        pipeline.add_stage(EnrichStage(add_metadata_header=True))
        pipeline.add_stage(TruncateStage(preserve_structure=True))
        return pipeline

    @classmethod
    def research_pipeline(cls) -> ContextPipeline:
        """Create pipeline optimized for research tasks."""
        pipeline = cls("research")
        pipeline.add_stage(FilterStage(min_length=50))
        pipeline.add_stage(
            TransformStage(
                normalize_whitespace=True,
                strip_html=True,
            )
        )
        pipeline.add_stage(
            EnrichStage(
                add_metadata_header=True,
                add_source_citations=True,
            )
        )
        pipeline.add_stage(TruncateStage(preserve_structure=True))
        return pipeline
