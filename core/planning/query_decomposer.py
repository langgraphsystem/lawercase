"""Query Decomposer for Adaptive Research Planning.

Decomposes complex queries into manageable sub-queries:
- Semantic decomposition
- Dependency analysis
- Priority ordering
- LLM-enhanced decomposition
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any

from .strategy_selector import QueryComplexity, ResearchStrategy

logger = logging.getLogger(__name__)


class DecompositionStrategy(str, Enum):
    """Strategy for query decomposition."""

    SEMANTIC = "semantic"  # Based on semantic meaning
    STRUCTURAL = "structural"  # Based on grammatical structure
    ASPECT = "aspect"  # Based on different aspects
    TEMPORAL = "temporal"  # Based on time sequence
    HIERARCHICAL = "hierarchical"  # From general to specific


class SubQueryPriority(str, Enum):
    """Priority levels for sub-queries."""

    CRITICAL = "critical"  # Must be answered
    HIGH = "high"  # Important for complete answer
    MEDIUM = "medium"  # Adds value
    LOW = "low"  # Nice to have


@dataclass
class SubQuery:
    """A decomposed sub-query with metadata."""

    id: str
    text: str
    priority: SubQueryPriority = SubQueryPriority.MEDIUM
    estimated_complexity: QueryComplexity = QueryComplexity.MODERATE
    dependencies: list[str] = field(default_factory=list)  # IDs of dependent queries
    keywords: list[str] = field(default_factory=list)
    aspect: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "priority": self.priority.value,
            "complexity": self.estimated_complexity.value,
            "dependencies": self.dependencies,
            "keywords": self.keywords,
            "aspect": self.aspect,
        }


@dataclass
class DecomposedQuery:
    """Result of query decomposition."""

    original: str
    sub_queries: list[SubQuery] = field(default_factory=list)
    overall_complexity: QueryComplexity = QueryComplexity.MODERATE
    suggested_strategy: ResearchStrategy = ResearchStrategy.BALANCED
    decomposition_strategy: DecompositionStrategy = DecompositionStrategy.SEMANTIC
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    estimated_depth: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "sub_queries": [sq.to_dict() for sq in self.sub_queries],
            "overall_complexity": self.overall_complexity.value,
            "suggested_strategy": self.suggested_strategy.value,
            "decomposition_strategy": self.decomposition_strategy.value,
            "estimated_depth": self.estimated_depth,
        }

    def get_execution_order(self) -> list[str]:
        """Get sub-query IDs in execution order (respecting dependencies)."""
        if not self.sub_queries:
            return []

        # Topological sort
        visited: set[str] = set()
        result: list[str] = []

        def visit(query_id: str) -> None:
            if query_id in visited:
                return
            visited.add(query_id)
            for dep_id in self.dependency_graph.get(query_id, []):
                visit(dep_id)
            result.append(query_id)

        for sq in self.sub_queries:
            visit(sq.id)

        return result

    def get_parallel_groups(self) -> list[list[str]]:
        """Get groups of sub-queries that can run in parallel."""
        execution_order = self.get_execution_order()
        if not execution_order:
            return []

        groups: list[list[str]] = []
        completed: set[str] = set()

        while len(completed) < len(execution_order):
            # Find all queries whose dependencies are satisfied
            current_group = []
            for query_id in execution_order:
                if query_id in completed:
                    continue
                deps = self.dependency_graph.get(query_id, [])
                if all(d in completed for d in deps):
                    current_group.append(query_id)

            if current_group:
                groups.append(current_group)
                completed.update(current_group)
            else:
                # Circular dependency protection
                break

        return groups


class QueryDecomposer:
    """Decomposes complex queries into sub-queries.

    Features:
    - Multiple decomposition strategies
    - Dependency analysis
    - LLM-enhanced decomposition
    - Complexity estimation

    Usage:
        decomposer = QueryDecomposer()

        result = await decomposer.decompose(
            "What are the EB-1A requirements and how do I prove extraordinary ability?",
            max_sub_queries=5,
        )

        for sq in result.sub_queries:
            print(f"{sq.priority.value}: {sq.text}")
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        enable_llm: bool = True,
    ) -> None:
        self._llm_caller = llm_caller
        self._enable_llm = enable_llm

        # Question patterns for structural decomposition
        self._question_patterns = [
            (r"\b(what|how|why|when|where|who|which)\b", "interrogative"),
            (r"\band\b", "conjunction"),
            (r"\bor\b", "disjunction"),
            (r"\b(first|then|after|finally)\b", "temporal"),
            (r"\b(if|when|unless)\b", "conditional"),
        ]

        # Aspect keywords
        self._aspect_keywords = {
            "definition": ["what is", "define", "meaning of", "explain"],
            "process": ["how to", "steps", "procedure", "method"],
            "comparison": ["compare", "difference", "vs", "versus", "better"],
            "requirements": ["requirements", "criteria", "needed", "must have"],
            "examples": ["example", "instances", "cases", "show me"],
            "reasons": ["why", "reason", "because", "purpose"],
            "timeline": ["when", "deadline", "timeline", "duration"],
            "location": ["where", "location", "place"],
        }

        self._stats = {
            "queries_decomposed": 0,
            "llm_decompositions": 0,
            "rule_decompositions": 0,
        }

    async def decompose(
        self,
        query: str,
        max_sub_queries: int = 5,
        strategy: DecompositionStrategy | None = None,
        context: dict[str, Any] | None = None,
    ) -> DecomposedQuery:
        """Decompose a query into sub-queries.

        Args:
            query: The query to decompose
            max_sub_queries: Maximum number of sub-queries
            strategy: Decomposition strategy to use
            context: Additional context (prior findings, etc.)

        Returns:
            DecomposedQuery with sub-queries and metadata
        """
        self._stats["queries_decomposed"] += 1
        complexity = self._estimate_complexity(query)

        # Simple queries don't need decomposition
        if complexity == QueryComplexity.SIMPLE:
            sub_query = SubQuery(
                id="sq_0",
                text=query,
                priority=SubQueryPriority.CRITICAL,
                estimated_complexity=complexity,
            )
            return DecomposedQuery(
                original=query,
                sub_queries=[sub_query],
                overall_complexity=complexity,
                estimated_depth=1,
            )

        # Select decomposition strategy
        if not strategy:
            strategy = self._select_strategy(query)

        # Try LLM decomposition for complex queries
        if (
            self._llm_caller
            and self._enable_llm
            and complexity in (QueryComplexity.COMPLEX, QueryComplexity.EXPERT)
        ):
            llm_result = await self._llm_decompose(query, max_sub_queries, context)
            if llm_result and llm_result.sub_queries:
                self._stats["llm_decompositions"] += 1
                llm_result.decomposition_strategy = strategy
                return llm_result

        # Rule-based decomposition
        self._stats["rule_decompositions"] += 1
        return self._rule_decompose(query, max_sub_queries, strategy, complexity)

    def _select_strategy(self, query: str) -> DecompositionStrategy:
        """Select best decomposition strategy for query."""
        query_lower = query.lower()

        # Check for temporal patterns
        temporal_words = ["first", "then", "after", "before", "finally", "step"]
        if any(word in query_lower for word in temporal_words):
            return DecompositionStrategy.TEMPORAL

        # Check for comparison patterns
        if any(word in query_lower for word in ["compare", "vs", "versus", "difference"]):
            return DecompositionStrategy.ASPECT

        # Check for hierarchical patterns
        if any(word in query_lower for word in ["overview", "detail", "specific"]):
            return DecompositionStrategy.HIERARCHICAL

        # Default to semantic
        return DecompositionStrategy.SEMANTIC

    def _rule_decompose(
        self,
        query: str,
        max_sub_queries: int,
        strategy: DecompositionStrategy,
        complexity: QueryComplexity,
    ) -> DecomposedQuery:
        """Rule-based query decomposition."""
        sub_queries: list[SubQuery] = []
        query_lower = query.lower()

        if strategy == DecompositionStrategy.STRUCTURAL:
            parts = re.split(r"\band\b|\bor\b|[,;]", query, flags=re.IGNORECASE)
            parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]

            for i, subquery_part in enumerate(parts[:max_sub_queries]):
                if not any(
                    subquery_part.lower().startswith(q)
                    for q in ["what", "how", "why", "when", "where", "who"]
                ):
                    subquery_text = f"What about {subquery_part}?"
                else:
                    subquery_text = subquery_part

                sub_queries.append(
                    SubQuery(
                        id=f"sq_{i}",
                        text=subquery_text,
                        priority=SubQueryPriority.HIGH if i == 0 else SubQueryPriority.MEDIUM,
                        estimated_complexity=QueryComplexity.MODERATE,
                        dependencies=[f"sq_{i-1}"] if i > 0 else [],
                    )
                )

        elif strategy == DecompositionStrategy.ASPECT:
            # Extract aspects from query
            aspects_found = self._extract_aspects(query_lower)

            for i, (aspect, keywords) in enumerate(aspects_found[:max_sub_queries]):
                sub_text = self._generate_aspect_query(query, aspect)
                sub_queries.append(
                    SubQuery(
                        id=f"sq_{i}",
                        text=sub_text,
                        priority=SubQueryPriority.HIGH if i < 2 else SubQueryPriority.MEDIUM,
                        estimated_complexity=QueryComplexity.MODERATE,
                        aspect=aspect,
                        keywords=keywords,
                    )
                )

        elif strategy == DecompositionStrategy.HIERARCHICAL:
            # General → Specific decomposition
            levels = [
                ("Overview", SubQueryPriority.HIGH),
                ("Key concepts", SubQueryPriority.HIGH),
                ("Details", SubQueryPriority.MEDIUM),
                ("Examples", SubQueryPriority.LOW),
            ]

            for i, (level, priority) in enumerate(levels[:max_sub_queries]):
                sub_text = f"{level} of: {query}"
                sub_queries.append(
                    SubQuery(
                        id=f"sq_{i}",
                        text=sub_text,
                        priority=priority,
                        estimated_complexity=(
                            QueryComplexity.SIMPLE if i == 0 else QueryComplexity.MODERATE
                        ),
                        dependencies=[f"sq_{i-1}"] if i > 0 else [],
                    )
                )

        else:
            if "?" in query:
                questions = [q.strip() + "?" for q in query.split("?") if q.strip()]
            else:
                questions = [query]
                if "what" in query_lower:
                    questions.append(f"Why is this important in the context of: {query}")
                if "how" in query_lower:
                    questions.append(f"What are the prerequisites for: {query}")

            for i, question_item in enumerate(questions[:max_sub_queries]):
                sub_queries.append(
                    SubQuery(
                        id=f"sq_{i}",
                        text=question_item,
                        priority=SubQueryPriority.CRITICAL if i == 0 else SubQueryPriority.MEDIUM,
                        estimated_complexity=self._estimate_complexity(question_item),
                    )
                )

        # If no sub-queries generated, use original
        if not sub_queries:
            sub_queries.append(
                SubQuery(
                    id="sq_0",
                    text=query,
                    priority=SubQueryPriority.CRITICAL,
                    estimated_complexity=complexity,
                )
            )

        # Build dependency graph
        dependency_graph = {sq.id: sq.dependencies for sq in sub_queries}

        return DecomposedQuery(
            original=query,
            sub_queries=sub_queries,
            overall_complexity=complexity,
            decomposition_strategy=strategy,
            dependency_graph=dependency_graph,
            estimated_depth=self._estimate_depth(complexity, len(sub_queries)),
        )

    async def _llm_decompose(
        self,
        query: str,
        max_sub_queries: int,
        context: dict[str, Any] | None = None,
    ) -> DecomposedQuery | None:
        """LLM-based query decomposition."""
        if not self._llm_caller:
            return None

        context_str = ""
        if context and context.get("prior_findings"):
            context_str = f"\nPrior findings: {context['prior_findings'][:500]}"

        prompt = f"""Decompose this research query into {max_sub_queries} independent sub-queries.
Each sub-query should cover a different aspect and be answerable independently.

Original query: {query}
{context_str}

For each sub-query, provide:
- The sub-query text
- Priority (critical/high/medium/low)
- Dependencies (IDs of queries that must be answered first)

Format:
1. [PRIORITY] Sub-query text | DEPS: none or comma-separated IDs

Example:
1. [critical] What are the EB-1A eligibility requirements? | DEPS: none
2. [high] How is extraordinary ability defined? | DEPS: 1
3. [medium] What evidence is needed to prove extraordinary ability? | DEPS: 1,2"""

        try:
            response = await self._llm_caller(prompt)

            sub_queries: list[SubQuery] = []
            dependency_graph: dict[str, list[str]] = {}

            lines = response.strip().split("\n")
            for line in lines:
                match = re.match(
                    r"(\d+)\.\s*\[(\w+)\]\s*(.+?)\s*\|\s*DEPS:\s*(.+)", line.strip(), re.IGNORECASE
                )
                if match:
                    idx = int(match.group(1))
                    priority_str = match.group(2).lower()
                    text = match.group(3).strip()
                    deps_str = match.group(4).strip()

                    # Parse priority
                    priority = SubQueryPriority.MEDIUM
                    if priority_str == "critical":
                        priority = SubQueryPriority.CRITICAL
                    elif priority_str == "high":
                        priority = SubQueryPriority.HIGH
                    elif priority_str == "low":
                        priority = SubQueryPriority.LOW

                    # Parse dependencies
                    deps: list[str] = []
                    if deps_str.lower() != "none":
                        dep_ids = re.findall(r"\d+", deps_str)
                        deps = [f"sq_{int(d)-1}" for d in dep_ids]

                    sq_id = f"sq_{idx-1}"
                    sub_queries.append(
                        SubQuery(
                            id=sq_id,
                            text=text,
                            priority=priority,
                            estimated_complexity=self._estimate_complexity(text),
                            dependencies=deps,
                        )
                    )
                    dependency_graph[sq_id] = deps

            if sub_queries:
                return DecomposedQuery(
                    original=query,
                    sub_queries=sub_queries,
                    overall_complexity=self._estimate_complexity(query),
                    dependency_graph=dependency_graph,
                    estimated_depth=self._estimate_depth(
                        self._estimate_complexity(query), len(sub_queries)
                    ),
                )

        except Exception as e:
            logger.warning(f"LLM decomposition failed: {e}")

        return None

    def _extract_aspects(self, query_lower: str) -> list[tuple[str, list[str]]]:
        """Extract aspects from query."""
        found: list[tuple[str, list[str]]] = []

        for aspect, keywords in self._aspect_keywords.items():
            matched = [kw for kw in keywords if kw in query_lower]
            if matched:
                found.append((aspect, matched))

        # If no aspects found, use default aspects
        if not found:
            found = [
                ("definition", ["what is"]),
                ("details", ["explain"]),
            ]

        return found

    def _generate_aspect_query(self, original: str, aspect: str) -> str:
        """Generate a sub-query for a specific aspect."""
        # Extract the main subject
        subject = original.rstrip("?").rstrip(".")

        aspect_templates = {
            "definition": f"What is the definition of {subject}?",
            "process": f"What is the process or steps for {subject}?",
            "comparison": f"How does {subject} compare to alternatives?",
            "requirements": f"What are the requirements for {subject}?",
            "examples": f"What are examples of {subject}?",
            "reasons": f"Why is {subject} important?",
            "timeline": f"What is the timeline for {subject}?",
            "location": f"Where does {subject} apply?",
        }

        return aspect_templates.get(aspect, f"What about {aspect} of {subject}?")

    def _estimate_complexity(self, query: str) -> QueryComplexity:
        """Estimate query complexity."""
        word_count = len(query.split())
        question_marks = query.count("?")
        conjunctions = len(re.findall(r"\b(and|or|but)\b", query, re.IGNORECASE))

        score = 0
        score += min(word_count // 8, 3)
        score += question_marks
        score += conjunctions

        if score <= 1:
            return QueryComplexity.SIMPLE
        if score <= 3:
            return QueryComplexity.MODERATE
        if score <= 5:
            return QueryComplexity.COMPLEX
        return QueryComplexity.EXPERT

    def _estimate_depth(self, complexity: QueryComplexity, num_sub_queries: int) -> int:
        """Estimate required research depth."""
        base = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MODERATE: 2,
            QueryComplexity.COMPLEX: 3,
            QueryComplexity.EXPERT: 4,
        }
        return min(base[complexity] + (num_sub_queries // 3), 5)

    def get_stats(self) -> dict[str, Any]:
        """Get decomposer statistics."""
        return self._stats


# Factory function
def create_query_decomposer(
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> QueryDecomposer:
    """Create a query decomposer with optional LLM support."""
    return QueryDecomposer(llm_caller=llm_caller)


__all__ = [
    "DecomposedQuery",
    "DecompositionStrategy",
    "QueryDecomposer",
    "SubQuery",
    "SubQueryPriority",
    "create_query_decomposer",
]
