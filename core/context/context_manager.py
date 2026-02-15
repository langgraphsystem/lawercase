"""Context Manager for adaptive context building."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    BACKGROUND = "background"
    MEMORY = "memory"
    TOOLS = "tools"


@dataclass
class ContextTemplate:
    """Template for building context."""

    name: str
    description: str
    template: str
    max_tokens: int = 4000
    priority: int = 5  # 1-10, higher = more important
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    context_type: ContextType = ContextType.SYSTEM

    def render(self, **kwargs: Any) -> str:
        """Render template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing required field for template {self.name}: {e}")
            raise ValueError(f"Missing required field: {e}") from e


@dataclass
class ContextBlock:
    """A block of context with metadata."""

    content: str
    context_type: ContextType
    priority: int = 5
    tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    relevance_score: float = 1.0

    def __post_init__(self) -> None:
        """Estimate token count if not provided."""
        if self.tokens == 0:
            # Rough estimation: 1 token ≈ 4 characters
            self.tokens = len(self.content) // 4


class ContextManager:
    """Manages context building and optimization for LLM agents."""

    def __init__(self, max_context_tokens: int = 8000) -> None:
        """Initialize context manager.

        Args:
            max_context_tokens: Maximum tokens allowed in context window
        """
        self.max_context_tokens = max_context_tokens
        self.templates: dict[str, ContextTemplate] = {}
        self.global_context: list[ContextBlock] = []
        logger.info(f"ContextManager initialized with max_tokens={max_context_tokens}")

    def register_template(self, template: ContextTemplate) -> None:
        """Register a context template.

        Args:
            template: Template to register
        """
        self.templates[template.name] = template
        logger.debug(f"Registered template: {template.name}")

    def add_global_context(self, block: ContextBlock) -> None:
        """Add context that persists across requests.

        Args:
            block: Context block to add
        """
        self.global_context.append(block)
        logger.debug(f"Added global context: {block.source}")

    def build_context(
        self,
        template_name: str,
        additional_context: list[ContextBlock] | None = None,
        **template_vars: Any,
    ) -> str:
        """Build optimized context from template and blocks.

        Args:
            template_name: Name of template to use
            additional_context: Additional context blocks to include
            **template_vars: Variables for template rendering

        Returns:
            Optimized context string

        Raises:
            ValueError: If template not found
        """
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")

        template = self.templates[template_name]

        # Render main template
        try:
            main_content = template.render(**template_vars)
        except ValueError as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise

        main_block = ContextBlock(
            content=main_content,
            context_type=template.context_type,
            priority=template.priority,
            source=template_name,
        )

        # Combine all context blocks
        all_blocks = [main_block]
        all_blocks.extend(self.global_context)
        if additional_context:
            all_blocks.extend(additional_context)

        # Sort by priority (higher first)
        all_blocks.sort(key=lambda b: b.priority * b.relevance_score, reverse=True)

        # Build context within token limit
        return self._optimize_context(all_blocks)

    def _optimize_context(self, blocks: list[ContextBlock]) -> str:
        """Optimize context to fit within token limit.

        Args:
            blocks: Sorted list of context blocks

        Returns:
            Optimized context string
        """
        total_tokens = 0
        selected_blocks: list[ContextBlock] = []

        for block in blocks:
            if total_tokens + block.tokens <= self.max_context_tokens:
                selected_blocks.append(block)
                total_tokens += block.tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = self.max_context_tokens - total_tokens
                if remaining_tokens > 100:  # Only if we have reasonable space
                    truncated_content = self._truncate_content(block.content, remaining_tokens)
                    selected_blocks.append(
                        ContextBlock(
                            content=truncated_content,
                            context_type=block.context_type,
                            priority=block.priority,
                            tokens=remaining_tokens,
                            source=f"{block.source} (truncated)",
                        )
                    )
                    total_tokens += remaining_tokens
                break

        logger.info(
            f"Built context with {len(selected_blocks)} blocks, "
            f"{total_tokens}/{self.max_context_tokens} tokens"
        )

        # Group by context type for better organization
        context_groups: dict[ContextType, list[str]] = {}
        for block in selected_blocks:
            if block.context_type not in context_groups:
                context_groups[block.context_type] = []
            context_groups[block.context_type].append(block.content)

        # Build final context with clear sections
        sections = []
        for context_type in ContextType:
            if context_type in context_groups:
                sections.append("\n".join(context_groups[context_type]))

        return "\n\n".join(sections)

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token limit.

        Args:
            content: Content to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated content
        """
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content

        # Truncate and add indicator
        return content[: max_chars - 20] + "\n[... truncated ...]"

    def create_agent_context(
        self,
        agent_type: str,
        task_description: str,
        memory_snippets: list[str] | None = None,
        available_tools: list[str] | None = None,
    ) -> str:
        """Create context specifically for an agent.

        Args:
            agent_type: Type of agent (case, writer, validator, etc.)
            task_description: Description of current task
            memory_snippets: Relevant memory snippets
            available_tools: List of available tools

        Returns:
            Optimized context for the agent
        """
        additional_blocks = []

        # Add memory snippets
        if memory_snippets:
            for snippet in memory_snippets:
                additional_blocks.append(
                    ContextBlock(
                        content=snippet,
                        context_type=ContextType.MEMORY,
                        priority=7,
                        source="memory",
                        relevance_score=0.9,
                    )
                )

        # Add tools information
        if available_tools:
            tools_content = "Available tools:\n" + "\n".join(
                f"- {tool}" for tool in available_tools
            )
            additional_blocks.append(
                ContextBlock(
                    content=tools_content,
                    context_type=ContextType.TOOLS,
                    priority=6,
                    source="tools",
                )
            )

        # Use agent-specific template
        template_name = f"{agent_type}_agent"
        if template_name not in self.templates:
            template_name = "default_agent"

        return self.build_context(
            template_name=template_name,
            additional_context=additional_blocks,
            task=task_description,
            agent_type=agent_type,
        )

    def clear_global_context(self) -> None:
        """Clear all global context blocks."""
        self.global_context.clear()
        logger.info("Cleared global context")


# Global instance
_context_manager: ContextManager | None = None


def get_context_manager(max_tokens: int = 8000) -> ContextManager:
    """Get or create global context manager.

    Args:
        max_tokens: Maximum context tokens (only used for new instance)

    Returns:
        Global ContextManager instance
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(max_context_tokens=max_tokens)
    return _context_manager


# ============================================================================
# Enhanced Context Engineering (v2.0)
# ============================================================================

from .context_compressor import CompressionStrategy, ContextCompressor
from .context_pipelines import ContextPipeline
from .priority_scorer import PriorityScorer


class ContextBlockType(str, Enum):
    """Extended block types for context engineering."""

    SYSTEM = "system"
    USER_QUERY = "user_query"
    CASE_DATA = "case_data"
    LEGAL_REF = "legal_ref"
    EXAMPLES = "examples"
    MEMORY = "memory"
    SEARCH = "search"
    HISTORY = "history"
    CUSTOM = "custom"


@dataclass
class ContextConfig:
    """Configuration for advanced context building."""

    max_tokens: int = 100000
    reserved_for_response: int = 4000
    min_context_tokens: int = 1000

    block_budgets: dict[str, float] = field(
        default_factory=lambda: {
            "system": 0.10,
            "user_query": 0.05,
            "case_data": 0.30,
            "legal_ref": 0.20,
            "examples": 0.15,
            "memory": 0.10,
            "search": 0.05,
            "history": 0.05,
        }
    )

    compress_when_over_budget: bool = True
    compression_strategy: str = "extract"
    scoring_strategy: str = "hybrid"
    use_pipeline: bool = True

    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self.reserved_for_response


@dataclass
class BuiltContext:
    """Result of advanced context building."""

    content: str
    total_tokens: int
    blocks_included: int
    blocks_excluded: int
    compressed: bool = False
    compression_ratio: float = 1.0
    build_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "total_tokens": self.total_tokens,
            "blocks_included": self.blocks_included,
            "blocks_excluded": self.blocks_excluded,
            "compressed": self.compressed,
            "compression_ratio": self.compression_ratio,
            "build_time_ms": self.build_time_ms,
        }


class AdvancedContextManager(ContextManager):
    """Extended context manager with priority scoring, compression, and pipelines.

    Usage:
        manager = AdvancedContextManager(max_tokens=100000)

        manager.add_case_data(case_info)
        manager.add_legal_refs(legal_docs)
        manager.add_examples(similar_cases)

        result = await manager.build_advanced_context(
            query="Is this case eligible for EB-1A?",
            task_type="legal_analysis"
        )

        # Use result.content with LLM
    """

    def __init__(
        self,
        config: ContextConfig | None = None,
        max_tokens: int = 100000,
    ) -> None:
        super().__init__(max_context_tokens=max_tokens)

        self.config = config or ContextConfig(max_tokens=max_tokens)
        self.advanced_blocks: list[tuple[str, ContextBlockType, float]] = []
        self.scorer = PriorityScorer()
        self.compressor = ContextCompressor()
        self._pipelines = {
            "default": ContextPipeline.default_pipeline(),
            "legal": ContextPipeline.legal_pipeline(),
            "research": ContextPipeline.research_pipeline(),
        }

    def add_case_data(self, content: str, priority: float = 0.9) -> AdvancedContextManager:
        """Add case-specific data."""
        self.advanced_blocks.append((content, ContextBlockType.CASE_DATA, priority))
        return self

    def add_legal_refs(self, content: str, priority: float = 0.8) -> AdvancedContextManager:
        """Add legal references."""
        self.advanced_blocks.append((content, ContextBlockType.LEGAL_REF, priority))
        return self

    def add_examples(self, examples: list[str], priority: float = 0.7) -> AdvancedContextManager:
        """Add relevant examples."""
        content = "\n\n---\n\n".join(examples)
        self.advanced_blocks.append((content, ContextBlockType.EXAMPLES, priority))
        return self

    def add_search_results(
        self, results: list[dict], priority: float = 0.6
    ) -> AdvancedContextManager:
        """Add search results."""
        formatted = []
        for r in results:
            title = r.get("title", "")
            snippet = r.get("snippet", r.get("content", ""))
            formatted.append(f"**{title}**\n{snippet}")
        content = "\n\n".join(formatted)
        self.advanced_blocks.append((content, ContextBlockType.SEARCH, priority))
        return self

    def add_memory(self, content: str, priority: float = 0.7) -> AdvancedContextManager:
        """Add retrieved memory."""
        self.advanced_blocks.append((content, ContextBlockType.MEMORY, priority))
        return self

    def clear_advanced_blocks(self) -> AdvancedContextManager:
        """Clear all advanced blocks."""
        self.advanced_blocks.clear()
        return self

    async def build_advanced_context(
        self,
        query: str = "",
        task_type: str = "general",
        system_prompt: str = "",
    ) -> BuiltContext:
        """Build optimized context with scoring and compression.

        Args:
            query: User query/task
            task_type: Type of task (legal_analysis, research, etc.)
            system_prompt: System instructions

        Returns:
            BuiltContext with optimized content
        """
        import time

        start_time = time.perf_counter()

        available = self.config.available_tokens
        sections = []
        used_tokens = 0
        included = 0
        excluded = 0

        # Add system prompt first (required)
        if system_prompt:
            sections.append(system_prompt)
            used_tokens += len(system_prompt) // 4

        # Add query
        if query:
            sections.append(f"## User Query\n{query}")
            used_tokens += len(query) // 4 + 10

        # Score and sort blocks
        scored_blocks = []
        for content, block_type, priority in self.advanced_blocks:
            score = self.scorer.score_item(
                content=content,
                query=query,
                task_type=task_type,
                source_type=block_type.value,
            )
            final_score = 0.6 * score.score + 0.4 * priority
            tokens = len(content) // 4
            scored_blocks.append((content, block_type, final_score, tokens))

        # Sort by score
        scored_blocks.sort(key=lambda x: x[2], reverse=True)

        # Select blocks within budget
        for content, block_type, _score, tokens in scored_blocks:
            if used_tokens + tokens <= available:
                header = self._get_header(block_type)
                if header:
                    sections.append(f"## {header}\n{content}")
                else:
                    sections.append(content)
                used_tokens += tokens
                included += 1
            else:
                excluded += 1

        # Combine sections
        full_content = "\n\n".join(sections)

        # Compress if needed
        compressed = False
        compression_ratio = 1.0

        if len(full_content) // 4 > available and self.config.compress_when_over_budget:
            result = await self.compressor.compress(
                text=full_content,
                target_tokens=available,
                strategy=CompressionStrategy.EXTRACT,
                query=query,
            )
            full_content = result.compressed_text
            compressed = True
            compression_ratio = result.compression_ratio

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return BuiltContext(
            content=full_content,
            total_tokens=len(full_content) // 4,
            blocks_included=included,
            blocks_excluded=excluded,
            compressed=compressed,
            compression_ratio=compression_ratio,
            build_time_ms=elapsed_ms,
        )

    def _get_header(self, block_type: ContextBlockType) -> str:
        """Get section header for block type."""
        headers = {
            ContextBlockType.CASE_DATA: "Case Information",
            ContextBlockType.LEGAL_REF: "Legal References",
            ContextBlockType.EXAMPLES: "Relevant Examples",
            ContextBlockType.MEMORY: "Previous Context",
            ContextBlockType.SEARCH: "Search Results",
            ContextBlockType.HISTORY: "Conversation History",
        }
        return headers.get(block_type, "")


def create_advanced_context_manager(
    max_tokens: int = 100000,
    task_type: str = "general",
) -> AdvancedContextManager:
    """Create pre-configured advanced context manager."""
    config = ContextConfig(max_tokens=max_tokens)

    if task_type == "legal_analysis":
        config.block_budgets["legal_ref"] = 0.30
        config.block_budgets["case_data"] = 0.35
    elif task_type == "research":
        config.block_budgets["search"] = 0.25
        config.block_budgets["examples"] = 0.20

    return AdvancedContextManager(config=config)
