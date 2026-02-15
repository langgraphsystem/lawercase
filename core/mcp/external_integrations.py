"""External Integrations for MCP.

Pre-built tool integrations for common services:
- Web Search (Tavily, DuckDuckGo)
- GitHub API
- Database queries
- File operations
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import structlog

from .tool_provider import (
    BaseTool,
    ToolCategory,
    ToolParameter,
    ToolProvider,
    ToolResult,
    ToolSchema,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Web Search Integration
# ============================================================================


class WebSearchTool(BaseTool):
    """Web search tool using SearchAggregator."""

    schema = ToolSchema(
        name="web_search",
        description="Search the web for information using multiple search engines",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description="Maximum number of results",
                required=False,
                default=10,
            ),
            ToolParameter(
                name="include_academic",
                type="boolean",
                description="Include academic papers from arXiv",
                required=False,
                default=False,
            ),
        ],
        category=ToolCategory.SEARCH,
    )

    def __init__(self) -> None:
        self._aggregator = None

    async def _get_aggregator(self):
        if self._aggregator is None:
            from core.search import SearchAggregator

            self._aggregator = SearchAggregator()
        return self._aggregator

    async def execute(self, **kwargs: Any) -> ToolResult:
        import time

        start = time.perf_counter()

        try:
            query = kwargs.get("query", "")
            top_k = kwargs.get("top_k", 10)
            include_academic = kwargs.get("include_academic", False)

            aggregator = await self._get_aggregator()

            if include_academic:
                response = await aggregator.search_all(query, top_k=top_k, include_arxiv=True)
            else:
                response = await aggregator.search(query, top_k=top_k)

            results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.provider.value if hasattr(r.provider, "value") else str(r.provider),
                }
                for r in response.results
            ]

            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=True,
                data={"results": results, "total": len(results)},
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=elapsed,
            )


class AcademicSearchTool(BaseTool):
    """Academic paper search via arXiv."""

    schema = ToolSchema(
        name="academic_search",
        description="Search academic papers on arXiv",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query for papers",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description="Maximum number of papers",
                required=False,
                default=5,
            ),
            ToolParameter(
                name="categories",
                type="array",
                description="arXiv categories (e.g., cs.AI, cs.LG)",
                required=False,
            ),
        ],
        category=ToolCategory.SEARCH,
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        import time

        start = time.perf_counter()

        try:
            from core.search import SearchAggregator

            query = kwargs.get("query", "")
            top_k = kwargs.get("top_k", 5)
            categories = kwargs.get("categories")

            aggregator = SearchAggregator()
            response = await aggregator.search_academic(query, top_k=top_k, categories=categories)

            papers = [
                {
                    "title": r.title,
                    "url": r.url,
                    "abstract": r.snippet,
                    "authors": r.author,
                    "arxiv_id": r.metadata.get("arxiv_id"),
                    "pdf_url": r.metadata.get("pdf_url"),
                }
                for r in response.results
            ]

            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=True,
                data={"papers": papers, "total": len(papers)},
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=elapsed)


# ============================================================================
# GitHub Integration
# ============================================================================


class GitHubSearchTool(BaseTool):
    """Search GitHub repositories."""

    schema = ToolSchema(
        name="github_search",
        description="Search GitHub repositories, code, or issues",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            ToolParameter(
                name="search_type",
                type="string",
                description="Type of search: repositories, code, issues",
                required=False,
                default="repositories",
                enum=["repositories", "code", "issues"],
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description="Maximum results",
                required=False,
                default=10,
            ),
        ],
        category=ToolCategory.API,
        requires_auth=True,
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        import time

        start = time.perf_counter()

        try:
            import httpx

            query = kwargs.get("query", "")
            search_type = kwargs.get("search_type", "repositories")
            top_k = kwargs.get("top_k", 10)

            token = os.getenv("GITHUB_TOKEN")
            headers = {"Accept": "application/vnd.github+json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/search/{search_type}",
                    params={"q": query, "per_page": top_k},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            items = data.get("items", [])[:top_k]
            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=True,
                data={"items": items, "total": data.get("total_count", 0)},
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=elapsed)


# ============================================================================
# Database Integration
# ============================================================================


class DatabaseQueryTool(BaseTool):
    """Execute database queries (Supabase)."""

    schema = ToolSchema(
        name="database_query",
        description="Query the Supabase database",
        parameters=[
            ToolParameter(
                name="table",
                type="string",
                description="Table name to query",
                required=True,
            ),
            ToolParameter(
                name="select",
                type="string",
                description="Columns to select (comma-separated or *)",
                required=False,
                default="*",
            ),
            ToolParameter(
                name="filters",
                type="object",
                description="Filter conditions as key-value pairs",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum rows to return",
                required=False,
                default=100,
            ),
        ],
        category=ToolCategory.DATABASE,
        requires_auth=True,
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        import time

        start = time.perf_counter()

        try:
            from core.storage.supabase_client import get_supabase_client

            table = kwargs.get("table", "")
            select = kwargs.get("select", "*")
            filters = kwargs.get("filters", {})
            limit = kwargs.get("limit", 100)

            client = get_supabase_client()
            query = client.table(table).select(select)

            for key, value in filters.items():
                query = query.eq(key, value)

            query = query.limit(limit)
            response = query.execute()

            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=True,
                data={"rows": response.data, "count": len(response.data)},
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=elapsed)


# ============================================================================
# LLM Integration
# ============================================================================


class LLMQueryTool(BaseTool):
    """Query LLM with task routing."""

    schema = ToolSchema(
        name="llm_query",
        description="Query an LLM with automatic model selection based on task type",
        parameters=[
            ToolParameter(
                name="prompt",
                type="string",
                description="The prompt to send to the LLM",
                required=True,
            ),
            ToolParameter(
                name="task_type",
                type="string",
                description="Type of task for model routing",
                required=False,
                default="general",
                enum=[
                    "legal_analysis",
                    "document_generation",
                    "research",
                    "code_generation",
                    "summarization",
                    "general",
                ],
            ),
            ToolParameter(
                name="temperature",
                type="number",
                description="Temperature for generation (0-1)",
                required=False,
                default=0.7,
            ),
        ],
        category=ToolCategory.GENERATION,
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        import time

        start = time.perf_counter()

        try:
            from core.llm_interface import TaskRequest, TaskRouter, TaskType

            prompt = kwargs.get("prompt", "")
            task_type_str = kwargs.get("task_type", "general")
            temperature = kwargs.get("temperature", 0.7)

            # Map string to TaskType
            task_type = (
                TaskType(task_type_str)
                if task_type_str in [t.value for t in TaskType]
                else TaskType.GENERAL
            )

            router = TaskRouter()
            response = await router.route(
                TaskRequest(
                    prompt=prompt,
                    task_type=task_type,
                    temperature=temperature,
                )
            )

            elapsed = (time.perf_counter() - start) * 1000

            return ToolResult(
                success=not response.error,
                data={
                    "content": response.content,
                    "model": response.provider.value,
                    "tokens": response.input_tokens + response.output_tokens,
                    "cost": response.cost_usd,
                },
                error=response.error,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=elapsed)


# ============================================================================
# Integration Manager
# ============================================================================


@dataclass
class IntegrationConfig:
    """Configuration for external integrations."""

    enable_web_search: bool = True
    enable_academic_search: bool = True
    enable_github: bool = True
    enable_database: bool = True
    enable_llm: bool = True


def register_all_integrations(
    provider: ToolProvider,
    config: IntegrationConfig | None = None,
) -> None:
    """Register all external integrations with a provider.

    Args:
        provider: ToolProvider to register with
        config: Optional configuration to enable/disable integrations
    """
    config = config or IntegrationConfig()

    if config.enable_web_search:
        provider.register(WebSearchTool())
        logger.info("mcp.integration.registered", name="web_search")

    if config.enable_academic_search:
        provider.register(AcademicSearchTool())
        logger.info("mcp.integration.registered", name="academic_search")

    if config.enable_github:
        provider.register(GitHubSearchTool())
        logger.info("mcp.integration.registered", name="github_search")

    if config.enable_database:
        provider.register(DatabaseQueryTool())
        logger.info("mcp.integration.registered", name="database_query")

    if config.enable_llm:
        provider.register(LLMQueryTool())
        logger.info("mcp.integration.registered", name="llm_query")


def get_default_integrations() -> list[BaseTool]:
    """Get list of default integration tools."""
    return [
        WebSearchTool(),
        AcademicSearchTool(),
        GitHubSearchTool(),
        DatabaseQueryTool(),
        LLMQueryTool(),
    ]
