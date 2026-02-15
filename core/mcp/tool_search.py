"""MCP Tool Search - Dynamic Tool Loading System.

This module implements intelligent tool discovery and dynamic loading for MCP servers.
Instead of loading all tools upfront (which can exceed context limits), tools are
discovered and loaded on-demand based on the current task context.

Key features:
- Semantic tool search using embeddings
- Tool usage analytics and caching
- Context-aware tool recommendations
- Automatic tool versioning and updates
- Tool dependency management

Based on 2025-2026 research on efficient MCP tool management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categories of MCP tools."""

    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    WEB = "web"
    CODE = "code"
    DOCUMENT = "document"
    SEARCH = "search"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    UTILITY = "utility"
    CUSTOM = "custom"


class ToolPriority(str, Enum):
    """Tool loading priority levels."""

    CRITICAL = "critical"  # Always loaded
    HIGH = "high"  # Loaded for most tasks
    MEDIUM = "medium"  # Loaded on demand
    LOW = "low"  # Rarely needed
    DEPRECATED = "deprecated"  # Should not be loaded


@dataclass
class ToolMetadata:
    """Metadata for an MCP tool."""

    tool_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    server: str = ""  # MCP server name
    version: str = "1.0.0"

    # Descriptions
    description: str = ""
    detailed_description: str = ""
    examples: list[str] = field(default_factory=list)

    # Categorization
    category: ToolCategory = ToolCategory.UTILITY
    tags: list[str] = field(default_factory=list)
    priority: ToolPriority = ToolPriority.MEDIUM

    # Schema
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    # Dependencies
    requires_auth: bool = False
    dependencies: list[str] = field(default_factory=list)  # Other tool names
    incompatible_with: list[str] = field(default_factory=list)

    # Analytics
    usage_count: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_used: datetime | None = None

    # Embeddings (for semantic search)
    embedding: list[float] | None = None
    embedding_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "server": self.server,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "priority": self.priority.value,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
        }


class ToolSearchResult(BaseModel):
    """Result from tool search."""

    tool_id: str
    name: str
    server: str
    description: str
    relevance_score: float = Field(ge=0, le=1)
    category: ToolCategory
    priority: ToolPriority

    # Match details
    matched_keywords: list[str] = Field(default_factory=list)
    semantic_score: float = 0.0
    usage_score: float = 0.0


class ToolRecommendation(BaseModel):
    """Tool recommendation with reasoning."""

    tools: list[ToolSearchResult]
    reasoning: str
    estimated_context_tokens: int
    alternative_tools: list[str] = Field(default_factory=list)


class MCPToolSearch:
    """Intelligent MCP Tool Search and Dynamic Loading System.

    This system manages tool discovery and loading for MCP servers.
    Instead of loading all tools (which can consume significant context),
    it provides semantic search and intelligent recommendations.

    Key principles:
    - Tools are indexed with semantic embeddings
    - Only load tools when needed (lazy loading)
    - Track usage patterns for better recommendations
    - Respect context window limits (aim for <10% on tools)

    Example usage:
        search = MCPToolSearch()

        # Register tools from MCP servers
        await search.register_server_tools("filesystem", server_tools)
        await search.register_server_tools("github", github_tools)

        # Search for relevant tools
        results = await search.search_tools(
            query="read and modify Python files",
            max_results=5,
            categories=[ToolCategory.FILE_SYSTEM, ToolCategory.CODE],
        )

        # Get recommendations for a task
        recommendation = await search.recommend_tools(
            task="Analyze code quality in the repository",
            context_limit=8000,  # Max tokens for tool definitions
        )

        # Load selected tools
        tools = await search.load_tools([r.tool_id for r in results])
    """

    # Context budget settings
    MAX_CONTEXT_PERCENT = 0.10  # Max 10% of context for tools
    AVG_TOOL_TOKENS = 200  # Average tokens per tool definition
    CRITICAL_TOOLS_ALWAYS_LOADED = True

    def __init__(
        self,
        embedding_client: Any | None = None,
        cache_embeddings: bool = True,
        analytics_enabled: bool = True,
    ):
        """Initialize the tool search system.

        Args:
            embedding_client: Client for generating embeddings
            cache_embeddings: Whether to cache tool embeddings
            analytics_enabled: Track tool usage analytics
        """
        self._tools: dict[str, ToolMetadata] = {}
        self._servers: dict[str, list[str]] = {}  # server -> tool_ids
        self._embedding_client = embedding_client
        self._cache_embeddings = cache_embeddings
        self._analytics_enabled = analytics_enabled
        self._embedding_cache: dict[str, list[float]] = {}

        # Keyword index for fast search
        self._keyword_index: dict[str, set[str]] = {}  # keyword -> tool_ids

        # Usage tracking
        self._usage_history: list[dict[str, Any]] = []

    async def register_tool(
        self,
        name: str,
        server: str,
        description: str,
        input_schema: dict[str, Any] | None = None,
        category: ToolCategory = ToolCategory.UTILITY,
        tags: list[str] | None = None,
        priority: ToolPriority = ToolPriority.MEDIUM,
        examples: list[str] | None = None,
    ) -> ToolMetadata:
        """Register a single tool.

        Args:
            name: Tool name
            server: MCP server name
            description: Tool description
            input_schema: JSON schema for input parameters
            category: Tool category
            tags: Search tags
            priority: Loading priority
            examples: Usage examples

        Returns:
            ToolMetadata for the registered tool
        """
        tool_id = f"{server}:{name}"

        metadata = ToolMetadata(
            tool_id=tool_id,
            name=name,
            server=server,
            description=description,
            input_schema=input_schema or {},
            category=category,
            tags=tags or [],
            priority=priority,
            examples=examples or [],
        )

        # Generate embedding if client available
        if self._embedding_client and self._cache_embeddings:
            metadata.embedding = await self._generate_embedding(
                f"{name} {description} {' '.join(tags or [])}"
            )

        # Index keywords
        self._index_tool_keywords(metadata)

        # Store
        self._tools[tool_id] = metadata
        if server not in self._servers:
            self._servers[server] = []
        if tool_id not in self._servers[server]:
            self._servers[server].append(tool_id)

        return metadata

    async def register_server_tools(
        self,
        server: str,
        tools: list[dict[str, Any]],
        default_category: ToolCategory = ToolCategory.UTILITY,
    ) -> list[ToolMetadata]:
        """Register all tools from an MCP server.

        Args:
            server: MCP server name
            tools: List of tool definitions from server
            default_category: Default category for tools

        Returns:
            List of registered ToolMetadata
        """
        registered = []

        for tool in tools:
            # Infer category from tool name/description
            category = (
                self._infer_category(
                    tool.get("name", ""),
                    tool.get("description", ""),
                )
                or default_category
            )

            # Infer tags from description
            tags = self._extract_tags(tool.get("description", ""))

            metadata = await self.register_tool(
                name=tool.get("name", ""),
                server=server,
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
                category=category,
                tags=tags,
            )
            registered.append(metadata)

        return registered

    async def search_tools(
        self,
        query: str,
        max_results: int = 10,
        categories: list[ToolCategory] | None = None,
        servers: list[str] | None = None,
        min_priority: ToolPriority = ToolPriority.LOW,
        include_deprecated: bool = False,
    ) -> list[ToolSearchResult]:
        """Search for tools matching a query.

        Uses a hybrid approach combining:
        - Keyword matching
        - Semantic similarity (if embeddings available)
        - Usage-based ranking

        Args:
            query: Search query
            max_results: Maximum results to return
            categories: Filter by categories
            servers: Filter by servers
            min_priority: Minimum priority level
            include_deprecated: Include deprecated tools

        Returns:
            List of matching tools ranked by relevance
        """
        candidates: list[tuple[str, float, list[str]]] = []  # (tool_id, score, keywords)

        # Keyword search
        query_keywords = self._tokenize(query)
        for keyword in query_keywords:
            if keyword in self._keyword_index:
                for tool_id in self._keyword_index[keyword]:
                    tool = self._tools.get(tool_id)
                    if not tool:
                        continue

                    # Apply filters
                    if categories and tool.category not in categories:
                        continue
                    if servers and tool.server not in servers:
                        continue
                    if not include_deprecated and tool.priority == ToolPriority.DEPRECATED:
                        continue
                    if self._priority_value(tool.priority) < self._priority_value(min_priority):
                        continue

                    # Calculate keyword score
                    matched = [
                        kw
                        for kw in query_keywords
                        if kw in self._keyword_index and tool_id in self._keyword_index[kw]
                    ]
                    score = len(matched) / len(query_keywords) if query_keywords else 0

                    # Boost by usage
                    usage_boost = min(tool.usage_count / 100, 0.2)  # Max 20% boost
                    score += usage_boost

                    candidates.append((tool_id, score, matched))

        # Semantic search if available
        if self._embedding_client:
            query_embedding = await self._generate_embedding(query)
            for tool_id, tool in self._tools.items():
                if tool.embedding:
                    semantic_score = self._cosine_similarity(query_embedding, tool.embedding)
                    if semantic_score > 0.5:  # Threshold
                        # Check if already in candidates
                        existing = next((c for c in candidates if c[0] == tool_id), None)
                        if existing:
                            # Combine scores
                            idx = candidates.index(existing)
                            candidates[idx] = (
                                tool_id,
                                existing[1] + semantic_score * 0.5,
                                existing[2],
                            )
                        else:
                            candidates.append((tool_id, semantic_score, []))

        # Sort by score and deduplicate
        seen = set()
        results = []
        for tool_id, score, matched in sorted(candidates, key=lambda x: -x[1]):
            if tool_id in seen:
                continue
            seen.add(tool_id)

            tool = self._tools[tool_id]
            results.append(
                ToolSearchResult(
                    tool_id=tool_id,
                    name=tool.name,
                    server=tool.server,
                    description=tool.description,
                    relevance_score=min(score, 1.0),
                    category=tool.category,
                    priority=tool.priority,
                    matched_keywords=matched,
                )
            )

            if len(results) >= max_results:
                break

        return results

    async def recommend_tools(
        self,
        task: str,
        context_limit: int = 8000,
        required_categories: list[ToolCategory] | None = None,
    ) -> ToolRecommendation:
        """Get intelligent tool recommendations for a task.

        Analyzes the task and recommends optimal tool set within context limits.

        Args:
            task: Task description
            context_limit: Maximum tokens for tool definitions
            required_categories: Categories that must be included

        Returns:
            ToolRecommendation with selected tools and reasoning
        """
        # Search for relevant tools
        search_results = await self.search_tools(
            query=task,
            max_results=20,
            categories=required_categories,
        )

        # Always include critical tools
        critical_tools = [
            self._tools[tid]
            for tid in self._tools
            if self._tools[tid].priority == ToolPriority.CRITICAL
        ]

        # Calculate context budget
        max_tools = context_limit // self.AVG_TOOL_TOKENS
        selected: list[ToolSearchResult] = []
        estimated_tokens = 0

        # Add critical tools first
        for tool in critical_tools:
            if estimated_tokens + self.AVG_TOOL_TOKENS > context_limit:
                break
            # Convert to SearchResult
            selected.append(
                ToolSearchResult(
                    tool_id=tool.tool_id,
                    name=tool.name,
                    server=tool.server,
                    description=tool.description,
                    relevance_score=1.0,
                    category=tool.category,
                    priority=tool.priority,
                )
            )
            estimated_tokens += self.AVG_TOOL_TOKENS

        # Add search results
        for result in search_results:
            if result.tool_id in [s.tool_id for s in selected]:
                continue
            if estimated_tokens + self.AVG_TOOL_TOKENS > context_limit:
                break
            selected.append(result)
            estimated_tokens += self.AVG_TOOL_TOKENS

        # Build reasoning
        reasoning_parts = [
            f"Selected {len(selected)} tools for task: '{task[:50]}...'",
            f"Context budget: {estimated_tokens}/{context_limit} tokens",
        ]
        if critical_tools:
            reasoning_parts.append(f"Included {len(critical_tools)} critical tools")
        if required_categories:
            reasoning_parts.append(f"Required categories: {[c.value for c in required_categories]}")

        # Identify alternatives
        alternatives = [
            r.name
            for r in search_results[len(selected) : len(selected) + 5]
            if r.tool_id not in [s.tool_id for s in selected]
        ]

        return ToolRecommendation(
            tools=selected,
            reasoning=". ".join(reasoning_parts),
            estimated_context_tokens=estimated_tokens,
            alternative_tools=alternatives,
        )

    async def load_tools(
        self,
        tool_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Load tool definitions for use.

        Args:
            tool_ids: List of tool IDs to load

        Returns:
            List of tool definitions ready for MCP
        """
        loaded = []

        for tool_id in tool_ids:
            tool = self._tools.get(tool_id)
            if not tool:
                continue

            # Track usage
            if self._analytics_enabled:
                tool.usage_count += 1
                tool.last_used = datetime.now(UTC)
                self._usage_history.append(
                    {
                        "tool_id": tool_id,
                        "timestamp": tool.last_used.isoformat(),
                    }
                )

            loaded.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "server": tool.server,
                }
            )

        return loaded

    def record_tool_result(
        self,
        tool_id: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record the result of a tool execution for analytics.

        Args:
            tool_id: Tool that was executed
            success: Whether execution succeeded
            latency_ms: Execution time in milliseconds
        """
        if not self._analytics_enabled:
            return

        tool = self._tools.get(tool_id)
        if not tool:
            return

        # Update success rate (exponential moving average)
        alpha = 0.1
        tool.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * tool.success_rate

        # Update latency (exponential moving average)
        tool.avg_latency_ms = alpha * latency_ms + (1 - alpha) * tool.avg_latency_ms

    def get_tool_stats(self) -> dict[str, Any]:
        """Get analytics on tool usage.

        Returns:
            Dictionary with usage statistics
        """
        if not self._analytics_enabled:
            return {"analytics_enabled": False}

        total_tools = len(self._tools)
        used_tools = sum(1 for t in self._tools.values() if t.usage_count > 0)

        # Top tools by usage
        top_tools = sorted(
            self._tools.values(),
            key=lambda t: t.usage_count,
            reverse=True,
        )[:10]

        # Category distribution
        category_counts = {}
        for tool in self._tools.values():
            category_counts[tool.category.value] = category_counts.get(tool.category.value, 0) + 1

        return {
            "total_tools": total_tools,
            "used_tools": used_tools,
            "usage_rate": used_tools / total_tools if total_tools > 0 else 0,
            "top_tools": [t.to_dict() for t in top_tools],
            "category_distribution": category_counts,
            "total_invocations": sum(t.usage_count for t in self._tools.values()),
        }

    # Private helper methods

    def _index_tool_keywords(self, tool: ToolMetadata) -> None:
        """Index tool keywords for fast search."""
        keywords = set()

        # Extract from name
        keywords.update(self._tokenize(tool.name))

        # Extract from description
        keywords.update(self._tokenize(tool.description))

        # Add tags
        for tag in tool.tags:
            keywords.update(self._tokenize(tag))

        # Add to index
        for keyword in keywords:
            if keyword not in self._keyword_index:
                self._keyword_index[keyword] = set()
            self._keyword_index[keyword].add(tool.tool_id)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into searchable keywords."""
        # Lowercase and split on non-alphanumeric
        words = re.findall(r"[a-z0-9]+", text.lower())
        # Filter short words and stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "and",
            "or",
            "is",
            "are",
        }
        return [w for w in words if len(w) > 2 and w not in stopwords]

    def _infer_category(self, name: str, description: str) -> ToolCategory | None:
        """Infer tool category from name and description."""
        text = f"{name} {description}".lower()

        category_keywords = {
            ToolCategory.FILE_SYSTEM: ["file", "directory", "read", "write", "path", "folder"],
            ToolCategory.DATABASE: ["database", "sql", "query", "table", "postgres", "redis"],
            ToolCategory.WEB: ["http", "fetch", "url", "api", "web", "request"],
            ToolCategory.CODE: ["code", "compile", "lint", "format", "syntax", "parse"],
            ToolCategory.DOCUMENT: ["document", "pdf", "text", "markdown", "docx"],
            ToolCategory.SEARCH: ["search", "find", "grep", "glob", "locate"],
            ToolCategory.COMMUNICATION: ["email", "message", "notify", "send", "chat"],
            ToolCategory.ANALYSIS: ["analyze", "evaluate", "assess", "metrics", "statistics"],
            ToolCategory.GENERATION: ["generate", "create", "produce", "synthesize"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return category

        return None

    def _extract_tags(self, description: str) -> list[str]:
        """Extract relevant tags from description."""
        tags = []

        # Look for common patterns
        patterns = {
            "async": r"\basync\b",
            "read": r"\bread\b",
            "write": r"\bwrite\b",
            "search": r"\bsearch\b",
            "create": r"\bcreate\b",
            "delete": r"\bdelete\b",
            "update": r"\bupdate\b",
            "list": r"\blist\b",
        }

        for tag, pattern in patterns.items():
            if re.search(pattern, description, re.I):
                tags.append(tag)

        return tags

    def _priority_value(self, priority: ToolPriority) -> int:
        """Get numeric value for priority comparison."""
        values = {
            ToolPriority.CRITICAL: 4,
            ToolPriority.HIGH: 3,
            ToolPriority.MEDIUM: 2,
            ToolPriority.LOW: 1,
            ToolPriority.DEPRECATED: 0,
        }
        return values.get(priority, 0)

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using the configured embedding client.

        Supports multiple embedding providers:
        - OpenAI embeddings (text-embedding-3-small/large)
        - Sentence Transformers (local)
        - Anthropic voyage embeddings
        - Custom embedding clients with embed/aembed methods

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not self._embedding_client:
            return []

        # Check cache (MD5 used for cache key only, not security)
        cache_key = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        embedding: list[float] = []

        try:
            # Try different embedding client interfaces
            if hasattr(self._embedding_client, "aembed"):
                # Async embedding method (preferred)
                result = await self._embedding_client.aembed(text)
                if isinstance(result, list):
                    embedding = result
                elif hasattr(result, "embedding"):
                    embedding = result.embedding
                elif hasattr(result, "data") and result.data:
                    embedding = result.data[0].embedding

            elif hasattr(self._embedding_client, "embed"):
                # Sync embedding method
                result = self._embedding_client.embed(text)
                if isinstance(result, list):
                    embedding = result
                elif hasattr(result, "embedding"):
                    embedding = result.embedding

            elif hasattr(self._embedding_client, "encode"):
                # Sentence Transformers style
                result = self._embedding_client.encode(text)
                if hasattr(result, "tolist"):
                    embedding = result.tolist()
                elif isinstance(result, list):
                    embedding = result

            elif hasattr(self._embedding_client, "create"):
                # OpenAI style client
                response = await self._embedding_client.create(
                    input=text,
                    model="text-embedding-3-small",
                )
                if hasattr(response, "data") and response.data:
                    embedding = response.data[0].embedding

            elif callable(self._embedding_client):
                # Direct callable
                result = self._embedding_client(text)
                if hasattr(result, "__await__"):
                    result = await result
                if isinstance(result, list):
                    embedding = result

        except Exception:
            # Return empty on any error - caller should handle gracefully
            pass

        # Cache if successful
        if embedding and self._cache_embeddings:
            self._embedding_cache[cache_key] = embedding

        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


# Singleton instance
_tool_search_instance: MCPToolSearch | None = None


def get_tool_search() -> MCPToolSearch:
    """Get or create the global tool search instance."""
    global _tool_search_instance
    if _tool_search_instance is None:
        _tool_search_instance = MCPToolSearch()
    return _tool_search_instance


__all__ = [
    "MCPToolSearch",
    "ToolCategory",
    "ToolMetadata",
    "ToolPriority",
    "ToolRecommendation",
    "ToolSearchResult",
    "get_tool_search",
]
