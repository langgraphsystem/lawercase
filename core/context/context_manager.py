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
