"""Deep Research Agent - Iterative research with scope clarification.

This agent provides:
- Scope clarification before research
- Iterative research loop with evidence evaluation
- Multi-source search (semantic memory, RFE knowledge, case documents)
- Report synthesis with citations

Three-phase architecture:
1. SCOPE: Clarify query and generate research brief
2. RESEARCH: Iterative search loop until sufficient evidence
3. WRITE: Synthesize findings into structured report
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
import structlog

if TYPE_CHECKING:
    from ..llm_interface import IntelligentRouter
    from ..memory.memory_manager import MemoryManager

logger = structlog.get_logger(__name__)


# =============================================================================
# ENUMS AND MODELS
# =============================================================================


class ResearchPhase(str, Enum):
    """Current phase of deep research."""

    SCOPE = "scope"
    RESEARCH = "research"
    SYNTHESIZE = "synthesize"
    COMPLETE = "complete"


class EvidenceStrength(str, Enum):
    """Strength of collected evidence."""

    INSUFFICIENT = "insufficient"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class ResearchBrief(BaseModel):
    """Structured research brief generated from scope clarification."""

    brief_id: str = Field(default_factory=lambda: str(uuid4()))
    original_query: str = Field(..., description="Original user query")
    clarified_query: str = Field(..., description="Clarified/expanded query")
    research_objectives: list[str] = Field(default_factory=list, description="Specific objectives")
    search_keywords: list[str] = Field(default_factory=list, description="Keywords for search")
    expected_sources: list[str] = Field(default_factory=list, description="Expected source types")
    scope_type: Literal["eb1a_criterion", "rfe_response", "case_analysis", "general"] = "general"
    eb1a_criterion: str | None = Field(None, description="EB-1A criterion if applicable")
    max_iterations: int = Field(5, ge=1, le=20, description="Max research iterations")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchFinding(BaseModel):
    """Single research finding from a source."""

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(..., description="Finding content")
    source_type: str = Field(..., description="Source type: memory, rfe, case, etc.")
    source_id: str | None = Field(None, description="Source record ID")
    relevance_score: float = Field(0.0, ge=0.0, le=1.0, description="Relevance score")
    iteration: int = Field(1, ge=1, description="Iteration when found")
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeepResearchState(BaseModel):
    """State for deep research workflow."""

    # Identifiers
    research_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(..., description="User ID")
    thread_id: str | None = Field(None, description="Conversation thread ID")

    # Phase tracking
    phase: ResearchPhase = Field(default=ResearchPhase.SCOPE)
    iteration: int = Field(0, ge=0, description="Current iteration")
    max_iterations: int = Field(5, ge=1, le=20)

    # Research brief
    brief: ResearchBrief | None = Field(None, description="Research brief")

    # Findings
    findings: list[ResearchFinding] = Field(default_factory=list)
    evidence_strength: EvidenceStrength = Field(default=EvidenceStrength.INSUFFICIENT)

    # Output
    report: str | None = Field(None, description="Final synthesized report")
    citations: list[dict[str, Any]] = Field(default_factory=list)

    # Metrics
    total_sources_searched: int = Field(0, ge=0)
    search_time_ms: float = Field(0.0, ge=0.0)
    synthesis_time_ms: float = Field(0.0, ge=0.0)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(None)

    # Error handling
    error: str | None = Field(None)


class DeepResearchResult(BaseModel):
    """Final result of deep research."""

    research_id: str
    query: str
    report: str
    findings_count: int
    evidence_strength: EvidenceStrength
    citations: list[dict[str, Any]]
    iterations_used: int
    total_time_ms: float
    success: bool = True
    error: str | None = None


# =============================================================================
# EB-1A SCOPE TEMPLATES
# =============================================================================


EB1A_SCOPE_TEMPLATES = {
    "awards": {
        "objectives": [
            "Find examples of recognized awards in the field",
            "Identify selection criteria and competitiveness",
            "Locate success patterns from approved petitions",
        ],
        "keywords": ["award", "prize", "recognition", "honor", "distinguished", "excellence"],
        "sources": ["knowledge_base", "rfe_knowledge", "case_documents"],
    },
    "membership": {
        "objectives": [
            "Find examples of selective associations",
            "Identify membership criteria requirements",
            "Locate evidence of outstanding achievement requirements",
        ],
        "keywords": ["membership", "association", "society", "selective", "outstanding"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "press": {
        "objectives": [
            "Find examples of major media coverage",
            "Identify publication significance indicators",
            "Locate patterns of successful press evidence",
        ],
        "keywords": ["press", "media", "publication", "article", "interview", "coverage"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "judging": {
        "objectives": [
            "Find examples of peer review experience",
            "Identify judging panel participation patterns",
            "Locate evidence of evaluation expertise",
        ],
        "keywords": ["judge", "review", "evaluate", "panel", "committee", "referee"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "contributions": {
        "objectives": [
            "Find examples of original contributions",
            "Identify major significance indicators",
            "Locate citation and adoption patterns",
        ],
        "keywords": ["contribution", "original", "significant", "innovation", "impact"],
        "sources": ["knowledge_base", "rfe_knowledge", "case_documents"],
    },
    "authorship": {
        "objectives": [
            "Find examples of scholarly publications",
            "Identify high-impact journal indicators",
            "Locate citation metrics patterns",
        ],
        "keywords": ["publication", "journal", "article", "author", "scholarly", "citation"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "exhibitions": {
        "objectives": [
            "Find examples of artistic exhibitions",
            "Identify leading role indicators",
            "Locate venue prestige patterns",
        ],
        "keywords": ["exhibition", "display", "showcase", "gallery", "museum", "artistic"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "leading_role": {
        "objectives": [
            "Find examples of leadership positions",
            "Identify critical role indicators",
            "Locate organizational distinction patterns",
        ],
        "keywords": ["lead", "director", "head", "chief", "distinguished", "critical"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "high_salary": {
        "objectives": [
            "Find examples of high remuneration evidence",
            "Identify salary comparison methodologies",
            "Locate industry benchmark patterns",
        ],
        "keywords": ["salary", "compensation", "remuneration", "earnings", "wage"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
    "commercial_success": {
        "objectives": [
            "Find examples of commercial achievements",
            "Identify success metrics indicators",
            "Locate box office/sales patterns",
        ],
        "keywords": ["commercial", "success", "sales", "revenue", "box office", "record"],
        "sources": ["knowledge_base", "rfe_knowledge"],
    },
}


# =============================================================================
# DEEP RESEARCH AGENT
# =============================================================================


class DeepResearchAgent:
    """
    Deep Research Agent for comprehensive, iterative research.

    Implements three-phase architecture:
    1. SCOPE: Clarify query and generate research brief
    2. RESEARCH: Iterative search loop until sufficient evidence
    3. WRITE: Synthesize findings into structured report

    Example usage:
        >>> agent = DeepResearchAgent(memory_manager=memory)
        >>> result = await agent.aresearch(
        ...     query="Analyze awards criterion for EB-1A",
        ...     user_id="user123",
        ...     max_iterations=5
        ... )
        >>> print(result.report)
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        llm_router: IntelligentRouter | None = None,
        min_findings_for_strong: int = 10,
        min_relevance_threshold: float = 0.5,
    ) -> None:
        """
        Initialize Deep Research Agent.

        Args:
            memory_manager: Memory manager for retrieval
            llm_router: LLM router for synthesis (optional)
            min_findings_for_strong: Minimum findings for "strong" evidence
            min_relevance_threshold: Minimum relevance score to keep finding
        """
        self.memory = memory_manager
        self.llm_router = llm_router
        self.min_findings_for_strong = min_findings_for_strong
        self.min_relevance_threshold = min_relevance_threshold

        self.logger = logger.bind(agent="DeepResearchAgent")

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    async def aresearch(
        self,
        query: str,
        user_id: str,
        thread_id: str | None = None,
        max_iterations: int = 5,
        scope_type: str = "general",
    ) -> DeepResearchResult:
        """
        Main research entry point with three-phase execution.

        Args:
            query: Research query
            user_id: User ID for filtering
            thread_id: Optional conversation thread
            max_iterations: Maximum research iterations
            scope_type: Type of scope (eb1a_criterion, rfe_response, etc.)

        Returns:
            DeepResearchResult with report and findings
        """
        start_time = datetime.now(UTC)

        self.logger.info(
            "deep_research.start",
            query=query[:100],
            user_id=user_id,
            max_iterations=max_iterations,
        )

        # Initialize state
        state = DeepResearchState(
            user_id=user_id,
            thread_id=thread_id,
            max_iterations=max_iterations,
        )

        try:
            # Phase 1: SCOPE - Clarify query and generate brief
            state = await self._phase_scope(state, query, scope_type)

            # Phase 2: RESEARCH - Iterative search loop
            state = await self._phase_research(state)

            # Phase 3: SYNTHESIZE - Generate report
            state = await self._phase_synthesize(state)

            state.phase = ResearchPhase.COMPLETE
            state.completed_at = datetime.now(UTC)

            total_time = (state.completed_at - start_time).total_seconds() * 1000

            self.logger.info(
                "deep_research.complete",
                research_id=state.research_id,
                findings=len(state.findings),
                iterations=state.iteration,
                evidence_strength=state.evidence_strength.value,
                total_time_ms=total_time,
            )

            return DeepResearchResult(
                research_id=state.research_id,
                query=query,
                report=state.report or "No report generated.",
                findings_count=len(state.findings),
                evidence_strength=state.evidence_strength,
                citations=state.citations,
                iterations_used=state.iteration,
                total_time_ms=total_time,
                success=True,
            )

        except Exception as e:
            self.logger.exception("deep_research.error", error=str(e))
            return DeepResearchResult(
                research_id=state.research_id,
                query=query,
                report="",
                findings_count=len(state.findings),
                evidence_strength=state.evidence_strength,
                citations=[],
                iterations_used=state.iteration,
                total_time_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
                success=False,
                error=str(e),
            )

    # =========================================================================
    # PHASE 1: SCOPE CLARIFICATION
    # =========================================================================

    async def _phase_scope(
        self,
        state: DeepResearchState,
        query: str,
        scope_type: str,
    ) -> DeepResearchState:
        """
        Phase 1: Clarify scope and generate research brief.

        Analyzes query to:
        - Detect EB-1A criterion if applicable
        - Generate specific research objectives
        - Extract search keywords
        - Determine expected sources
        """
        state.phase = ResearchPhase.SCOPE

        self.logger.info("deep_research.scope.start", query=query[:100])

        # Detect EB-1A criterion from query
        eb1a_criterion = self._detect_eb1a_criterion(query)

        # Get template if EB-1A related
        if eb1a_criterion and eb1a_criterion in EB1A_SCOPE_TEMPLATES:
            template = EB1A_SCOPE_TEMPLATES[eb1a_criterion]
            objectives = template["objectives"]
            keywords = template["keywords"]
            sources = template["sources"]
            scope_type = "eb1a_criterion"
        else:
            # Generic scope
            objectives = [
                f"Find relevant information about: {query}",
                "Identify key patterns and examples",
                "Collect supporting evidence",
            ]
            keywords = self._extract_keywords(query)
            sources = ["knowledge_base", "semantic_memory"]

        # Create research brief
        brief = ResearchBrief(
            original_query=query,
            clarified_query=self._clarify_query(query, eb1a_criterion),
            research_objectives=objectives,
            search_keywords=keywords,
            expected_sources=sources,
            scope_type=scope_type,
            eb1a_criterion=eb1a_criterion,
            max_iterations=state.max_iterations,
        )

        state.brief = brief

        self.logger.info(
            "deep_research.scope.complete",
            criterion=eb1a_criterion,
            objectives=len(objectives),
            keywords=len(keywords),
        )

        return state

    def _detect_eb1a_criterion(self, query: str) -> str | None:
        """Detect EB-1A criterion from query."""
        query_lower = query.lower()

        criterion_keywords = {
            "awards": ["award", "prize", "honor"],
            "membership": ["membership", "association", "society", "member"],
            "press": ["press", "media", "publication", "article", "coverage"],
            "judging": ["judge", "judging", "review", "panel", "referee"],
            "contributions": ["contribution", "original", "significant"],
            "authorship": ["author", "publication", "journal", "scholarly"],
            "exhibitions": ["exhibition", "display", "showcase", "gallery"],
            "leading_role": ["lead", "director", "chief", "head", "critical role"],
            "high_salary": ["salary", "compensation", "remuneration", "wage"],
            "commercial_success": ["commercial", "success", "sales", "box office"],
        }

        for criterion, keywords in criterion_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return criterion

        return None

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract search keywords from query."""
        # Simple keyword extraction (split and filter)
        words = query.lower().split()
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "for",
            "of",
            "to",
            "in",
            "on",
            "at",
            "by",
            "with",
            "and",
            "or",
        }
        keywords = [w for w in words if len(w) > 3 and w not in stopwords]
        return keywords[:10]  # Limit to 10 keywords

    def _clarify_query(self, query: str, criterion: str | None) -> str:
        """Expand and clarify the query."""
        if criterion:
            return f"EB-1A {criterion.replace('_', ' ')} criterion: {query}"
        return query

    # =========================================================================
    # PHASE 2: ITERATIVE RESEARCH LOOP
    # =========================================================================

    async def _phase_research(self, state: DeepResearchState) -> DeepResearchState:
        """
        Phase 2: Iterative research loop.

        Continues searching until:
        - Evidence is strong enough, OR
        - Maximum iterations reached
        """
        state.phase = ResearchPhase.RESEARCH

        if not state.brief:
            raise ValueError("Research brief not generated")

        self.logger.info(
            "deep_research.research.start",
            max_iterations=state.max_iterations,
        )

        while state.iteration < state.max_iterations:
            state.iteration += 1

            self.logger.info(
                "deep_research.iteration.start",
                iteration=state.iteration,
                current_findings=len(state.findings),
            )

            # Search all sources in parallel
            new_findings = await self._search_all_sources(state)

            # Add unique findings
            existing_ids = {f.source_id for f in state.findings if f.source_id}
            for finding in new_findings:
                if finding.source_id not in existing_ids:
                    state.findings.append(finding)
                    if finding.source_id:
                        existing_ids.add(finding.source_id)

            # Evaluate evidence strength
            state.evidence_strength = self._evaluate_evidence_strength(state.findings)

            self.logger.info(
                "deep_research.iteration.complete",
                iteration=state.iteration,
                new_findings=len(new_findings),
                total_findings=len(state.findings),
                evidence_strength=state.evidence_strength.value,
            )

            # Check if we have enough evidence
            if state.evidence_strength in [EvidenceStrength.STRONG, EvidenceStrength.VERY_STRONG]:
                self.logger.info(
                    "deep_research.evidence_sufficient",
                    iteration=state.iteration,
                )
                break

            # Adapt search strategy for next iteration
            if state.iteration < state.max_iterations:
                state = self._adapt_search_strategy(state)

        return state

    async def _search_all_sources(self, state: DeepResearchState) -> list[ResearchFinding]:
        """Search all sources in parallel."""
        if not self.memory:
            return []

        brief = state.brief
        if not brief:
            return []

        findings: list[ResearchFinding] = []
        search_start = datetime.now(UTC)

        # Build search queries
        queries = [brief.clarified_query]
        if brief.search_keywords:
            queries.append(" ".join(brief.search_keywords[:5]))

        # Search semantic memory
        for query in queries:
            try:
                records = await self.memory.aretrieve(
                    query=query,
                    user_id=state.user_id,
                    topk=10,
                )

                for record in records:
                    relevance = getattr(record, "confidence", 0.5)
                    if relevance >= self.min_relevance_threshold:
                        findings.append(
                            ResearchFinding(
                                content=record.text[:500],  # Truncate
                                source_type="semantic_memory",
                                source_id=record.id,
                                relevance_score=relevance,
                                iteration=state.iteration,
                                metadata={
                                    "tags": getattr(record, "tags", []),
                                    "source": getattr(record, "source", None),
                                },
                            )
                        )

                state.total_sources_searched += len(records)

            except Exception as e:
                self.logger.warning("deep_research.search.failed", error=str(e), source="semantic")

        # Search RFE knowledge if available
        if hasattr(self.memory, "semantic") and hasattr(
            self.memory.semantic, "aretrieve_rfe_knowledge"
        ):
            try:
                rfe_records = await self.memory.semantic.aretrieve_rfe_knowledge(
                    query=brief.clarified_query,
                    topk=5,
                )

                for record in rfe_records:
                    relevance = getattr(record, "confidence", 0.6)
                    if relevance >= self.min_relevance_threshold:
                        findings.append(
                            ResearchFinding(
                                content=record.text[:500],
                                source_type="rfe_knowledge",
                                source_id=record.id,
                                relevance_score=relevance,
                                iteration=state.iteration,
                                metadata={"source": "rfe_knowledge"},
                            )
                        )

                state.total_sources_searched += len(rfe_records)

            except Exception as e:
                self.logger.warning("deep_research.search.failed", error=str(e), source="rfe")

        # Track search time
        search_time = (datetime.now(UTC) - search_start).total_seconds() * 1000
        state.search_time_ms += search_time

        return findings

    def _evaluate_evidence_strength(self, findings: list[ResearchFinding]) -> EvidenceStrength:
        """Evaluate strength of collected evidence."""
        count = len(findings)

        if count == 0:
            return EvidenceStrength.INSUFFICIENT

        # Average relevance
        avg_relevance = sum(f.relevance_score for f in findings) / count

        # Scoring based on count and relevance
        if count >= self.min_findings_for_strong * 2 and avg_relevance >= 0.7:
            return EvidenceStrength.VERY_STRONG
        if count >= self.min_findings_for_strong and avg_relevance >= 0.6:
            return EvidenceStrength.STRONG
        if count >= self.min_findings_for_strong // 2 and avg_relevance >= 0.5:
            return EvidenceStrength.MODERATE
        if count >= 3:
            return EvidenceStrength.WEAK
        return EvidenceStrength.INSUFFICIENT

    def _adapt_search_strategy(self, state: DeepResearchState) -> DeepResearchState:
        """Adapt search strategy based on findings."""
        # This could be enhanced to modify search keywords based on findings
        # For now, just log the adaptation
        self.logger.debug(
            "deep_research.adapt_strategy",
            iteration=state.iteration,
            findings=len(state.findings),
        )
        return state

    # =========================================================================
    # PHASE 3: SYNTHESIS
    # =========================================================================

    async def _phase_synthesize(self, state: DeepResearchState) -> DeepResearchState:
        """
        Phase 3: Synthesize findings into report.
        """
        state.phase = ResearchPhase.SYNTHESIZE

        self.logger.info(
            "deep_research.synthesize.start",
            findings=len(state.findings),
        )

        synthesis_start = datetime.now(UTC)

        # Sort findings by relevance
        sorted_findings = sorted(
            state.findings,
            key=lambda f: f.relevance_score,
            reverse=True,
        )

        # Build report
        report_parts = []

        # Header
        if state.brief:
            report_parts.append(f"# Research Report: {state.brief.clarified_query}")
            report_parts.append("")
            report_parts.append(f"**Evidence Strength:** {state.evidence_strength.value}")
            report_parts.append(f"**Findings:** {len(state.findings)}")
            report_parts.append(f"**Iterations:** {state.iteration}")
            report_parts.append("")

        # Objectives
        if state.brief and state.brief.research_objectives:
            report_parts.append("## Research Objectives")
            for i, obj in enumerate(state.brief.research_objectives, 1):
                report_parts.append(f"{i}. {obj}")
            report_parts.append("")

        # Key Findings
        report_parts.append("## Key Findings")
        report_parts.append("")

        # Group by source type
        by_source: dict[str, list[ResearchFinding]] = {}
        for finding in sorted_findings[:20]:  # Top 20
            source = finding.source_type
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(finding)

        for source_type, source_findings in by_source.items():
            report_parts.append(f"### From {source_type.replace('_', ' ').title()}")
            report_parts.append("")
            for i, finding in enumerate(source_findings[:5], 1):  # Top 5 per source
                report_parts.append(f"**Finding {i}** (Relevance: {finding.relevance_score:.2f})")
                report_parts.append(f"> {finding.content}")
                report_parts.append("")

                # Add citation
                state.citations.append(
                    {
                        "finding_id": finding.finding_id,
                        "source_type": finding.source_type,
                        "source_id": finding.source_id,
                        "relevance": finding.relevance_score,
                    }
                )

        # Summary
        report_parts.append("## Summary")
        report_parts.append("")
        report_parts.append(
            f"Research completed with **{len(state.findings)}** findings "
            f"across **{len(by_source)}** source types. "
            f"Evidence strength is **{state.evidence_strength.value}**."
        )

        state.report = "\n".join(report_parts)

        # Track synthesis time
        state.synthesis_time_ms = (datetime.now(UTC) - synthesis_start).total_seconds() * 1000

        self.logger.info(
            "deep_research.synthesize.complete",
            report_length=len(state.report),
            citations=len(state.citations),
        )

        return state


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "DeepResearchAgent",
    "DeepResearchResult",
    "DeepResearchState",
    "EvidenceStrength",
    "ResearchBrief",
    "ResearchFinding",
    "ResearchPhase",
]
