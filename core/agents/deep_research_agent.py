"""Deep Research Agent based on LangGraph Deep Search patterns.

Implements adaptive multi-agent research with:
- Dynamic research planning
- Subagent spawning for parallel investigation
- Iterative refinement based on findings
- Report synthesis from multiple sources
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResearchPhase(str, Enum):
    """Phases of deep research."""

    SCOPE_CLARIFICATION = "scope_clarification"  # NEW: Query clarification
    PLANNING = "planning"
    EXPLORING = "exploring"
    INVESTIGATING = "investigating"
    EVALUATING = "evaluating"  # NEW: Evidence sufficiency check
    SYNTHESIZING = "synthesizing"
    REFINING = "refining"
    COMPLETE = "complete"


class SourceType(str, Enum):
    """Types of research sources."""

    WEB = "web"
    ACADEMIC = "academic"
    DATABASE = "database"
    DOCUMENT = "document"
    EXPERT = "expert"
    INTERNAL = "internal"


@dataclass
class ResearchQuestion:
    """A research question to investigate."""

    id: str
    question: str
    parent_id: str | None = None
    priority: int = 1
    depth: int = 0
    max_depth: int = 3
    source_types: list[SourceType] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchFinding:
    """A finding from research."""

    id: str
    question_id: str
    content: str
    source: str
    source_type: SourceType
    confidence: float = 0.8
    relevance: float = 0.8
    citations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question_id": self.question_id,
            "content": self.content[:500],  # Truncate for summary
            "source": self.source,
            "source_type": self.source_type.value,
            "confidence": self.confidence,
            "relevance": self.relevance,
            "citations": self.citations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ResearchPlan:
    """A plan for conducting research."""

    id: str
    main_question: str
    sub_questions: list[ResearchQuestion] = field(default_factory=list)
    strategy: str = "breadth_first"
    max_depth: int = 3
    max_findings: int = 50
    time_budget_seconds: float = 300
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "main_question": self.main_question,
            "sub_questions": len(self.sub_questions),
            "strategy": self.strategy,
            "max_depth": self.max_depth,
            "max_findings": self.max_findings,
            "time_budget_seconds": self.time_budget_seconds,
        }


@dataclass
class ResearchReport:
    """Final research report."""

    question: str
    summary: str
    key_findings: list[str]
    detailed_findings: list[ResearchFinding]
    sources: list[str]
    confidence: float
    coverage: float
    recommendations: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "detailed_findings_count": len(self.detailed_findings),
            "sources_count": len(self.sources),
            "confidence": self.confidence,
            "coverage": self.coverage,
            "recommendations": self.recommendations,
            "gaps": self.gaps,
        }


class ResearchTool(ABC):
    """Abstract base class for research tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ResearchFinding]:
        pass


class WebSearchTool(ResearchTool):
    """Web search research tool."""

    def __init__(
        self,
        search_fn: Callable[[str, int], Coroutine[Any, Any, list[dict[str, Any]]]] | None = None,
    ):
        self._search_fn = search_fn

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def source_type(self) -> SourceType:
        return SourceType.WEB

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ResearchFinding]:
        if self._search_fn is None:
            return []

        try:
            results = await self._search_fn(query, max_results)
            findings = []
            for i, result in enumerate(results):
                findings.append(
                    ResearchFinding(
                        id=f"web_{i}_{hash(query) % 10000}",
                        question_id="",
                        content=result.get("content", result.get("snippet", "")),
                        source=result.get("url", result.get("source", "web")),
                        source_type=SourceType.WEB,
                        confidence=result.get("score", 0.7),
                    )
                )
            return findings
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []


class DatabaseSearchTool(ResearchTool):
    """Database/RAG search research tool."""

    def __init__(
        self,
        retriever: Callable[[str, int], Coroutine[Any, Any, list[tuple[str, float]]]] | None = None,
    ):
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "database_search"

    @property
    def source_type(self) -> SourceType:
        return SourceType.DATABASE

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[ResearchFinding]:
        if self._retriever is None:
            return []

        try:
            results = await self._retriever(query, max_results)
            findings = []
            for i, (content, score) in enumerate(results):
                findings.append(
                    ResearchFinding(
                        id=f"db_{i}_{hash(query) % 10000}",
                        question_id="",
                        content=content,
                        source="internal_database",
                        source_type=SourceType.DATABASE,
                        confidence=score,
                    )
                )
            return findings
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            return []


@dataclass
class ScopeClarification:
    """Result of scope clarification phase."""

    original_query: str
    clarified_query: str
    ambiguities_found: list[str] = field(default_factory=list)
    clarifications_made: list[str] = field(default_factory=list)
    scope_boundaries: dict[str, str] = field(default_factory=dict)
    is_clear: bool = False
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "clarified_query": self.clarified_query,
            "ambiguities_found": self.ambiguities_found,
            "clarifications_made": self.clarifications_made,
            "is_clear": self.is_clear,
            "confidence": self.confidence,
        }


@dataclass
class EvidenceSufficiency:
    """Result of evidence sufficiency evaluation."""

    is_sufficient: bool
    coverage_score: float  # 0-1: how much of the query is covered
    confidence_score: float  # 0-1: confidence in findings
    diversity_score: float  # 0-1: source diversity
    depth_score: float  # 0-1: depth of investigation
    gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    should_continue: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_sufficient": self.is_sufficient,
            "coverage_score": self.coverage_score,
            "confidence_score": self.confidence_score,
            "diversity_score": self.diversity_score,
            "depth_score": self.depth_score,
            "gaps": self.gaps,
            "should_continue": self.should_continue,
            "reason": self.reason,
        }

    @property
    def overall_score(self) -> float:
        """Calculate overall sufficiency score."""
        return (
            self.coverage_score * 0.3
            + self.confidence_score * 0.3
            + self.diversity_score * 0.2
            + self.depth_score * 0.2
        )


class ScopeClarifier:
    """Clarifies and refines research scope before investigation."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller
        self._ambiguity_keywords = [
            "best",
            "good",
            "better",
            "should",
            "could",
            "might",
            "some",
            "many",
            "few",
            "several",
            "various",
            "it",
            "they",
            "this",
            "that",
            "those",
        ]

    async def clarify(
        self,
        query: str,
        context: str = "",
        domain: str = "general",
    ) -> ScopeClarification:
        """Analyze and clarify query scope."""
        result = ScopeClarification(
            original_query=query,
            clarified_query=query,
        )

        # Identify ambiguities
        ambiguities = self._identify_ambiguities(query)
        result.ambiguities_found = ambiguities

        # Use LLM for clarification
        if self._llm_caller and ambiguities:
            clarified, clarifications, boundaries = await self._llm_clarify(
                query, ambiguities, context, domain
            )
            result.clarified_query = clarified
            result.clarifications_made = clarifications
            result.scope_boundaries = boundaries
        elif not ambiguities:
            result.is_clear = True
            result.confidence = 0.9

        # Assess clarity
        result.is_clear = len(result.ambiguities_found) == 0 or len(result.clarifications_made) > 0
        result.confidence = 0.9 if result.is_clear else 0.5

        return result

    def _identify_ambiguities(self, query: str) -> list[str]:
        """Identify potential ambiguities in query."""
        ambiguities = []
        query_lower = query.lower()
        words = query_lower.split()

        # Check for ambiguous keywords
        for keyword in self._ambiguity_keywords:
            if keyword in words:
                ambiguities.append(f"Ambiguous term: '{keyword}'")

        # Check for missing context
        if len(words) < 5:
            ambiguities.append("Query may be too brief for comprehensive research")

        # Check for multiple questions
        if query.count("?") > 1:
            ambiguities.append("Multiple questions detected - consider splitting")

        # Check for time-sensitive terms without date
        time_terms = ["latest", "recent", "current", "new", "updated"]
        for term in time_terms:
            if term in query_lower and not any(c.isdigit() for c in query):
                ambiguities.append(f"Time-sensitive term '{term}' without date specification")

        return ambiguities

    async def _llm_clarify(
        self,
        query: str,
        ambiguities: list[str],
        context: str,
        domain: str,
    ) -> tuple[str, list[str], dict[str, str]]:
        """Use LLM to clarify ambiguous query."""
        if not self._llm_caller:
            return query, [], {}

        prompt = f"""Analyze this research query and clarify any ambiguities.

Query: {query}
Domain: {domain}
Context: {context}

Identified ambiguities:
{chr(10).join(f"- {a}" for a in ambiguities)}

Provide:
1. CLARIFIED QUERY: A clearer, more specific version
2. CLARIFICATIONS: What assumptions/clarifications were made (one per line)
3. SCOPE: What is IN scope and OUT of scope

Format your response with these exact headers."""

        try:
            response = await self._llm_caller(prompt)
            clarified = query
            clarifications = []
            boundaries = {}

            current_section = None
            for line in response.split("\n"):
                stripped_line = line.strip()
                if "CLARIFIED QUERY" in stripped_line.upper():
                    current_section = "query"
                    if ":" in stripped_line:
                        clarified = stripped_line.split(":", 1)[1].strip()
                elif "CLARIFICATION" in stripped_line.upper():
                    current_section = "clarifications"
                elif "SCOPE" in stripped_line.upper():
                    current_section = "scope"
                elif stripped_line and current_section:
                    if current_section == "query" and clarified == query:
                        clarified = stripped_line
                    elif current_section == "clarifications":
                        clean = stripped_line.lstrip("-•* ")
                        if clean:
                            clarifications.append(clean)
                    elif current_section == "scope":
                        if "IN:" in stripped_line.upper() or "IN SCOPE" in stripped_line.upper():
                            boundaries["in_scope"] = stripped_line.split(":", 1)[-1].strip()
                        elif (
                            "OUT:" in stripped_line.upper()
                            or "OUT OF SCOPE" in stripped_line.upper()
                        ):
                            boundaries["out_of_scope"] = stripped_line.split(":", 1)[-1].strip()

            return clarified, clarifications, boundaries
        except Exception as e:
            logger.error(f"LLM clarification failed: {e}")
            return query, [], {}


class EvidenceSufficiencyEvaluator:
    """Evaluates if collected evidence is sufficient to answer the research question."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        min_coverage: float = 0.7,
        min_confidence: float = 0.6,
        min_sources: int = 3,
        max_iterations: int = 5,
    ):
        self._llm_caller = llm_caller
        self.min_coverage = min_coverage
        self.min_confidence = min_confidence
        self.min_sources = min_sources
        self.max_iterations = max_iterations

    async def evaluate(
        self,
        question: str,
        findings: list[ResearchFinding],
        sub_questions: list[str] | None = None,
        iteration: int = 0,
    ) -> EvidenceSufficiency:
        """Evaluate evidence sufficiency."""
        result = EvidenceSufficiency(
            is_sufficient=False,
            coverage_score=0.0,
            confidence_score=0.0,
            diversity_score=0.0,
            depth_score=0.0,
        )

        if not findings:
            result.reason = "No findings collected yet"
            result.should_continue = True
            return result

        # Calculate coverage score
        result.coverage_score = self._calculate_coverage(question, findings, sub_questions)

        # Calculate confidence score
        result.confidence_score = self._calculate_confidence(findings)

        # Calculate diversity score
        result.diversity_score = self._calculate_diversity(findings)

        # Calculate depth score
        result.depth_score = self._calculate_depth(findings, sub_questions)

        # Identify gaps
        result.gaps = await self._identify_gaps(question, findings, sub_questions)

        # Determine sufficiency
        result.is_sufficient = (
            result.coverage_score >= self.min_coverage
            and result.confidence_score >= self.min_confidence
            and len({f.source for f in findings}) >= self.min_sources
        )

        # Determine if should continue
        if iteration >= self.max_iterations:
            result.should_continue = False
            result.reason = "Maximum iterations reached"
        elif result.is_sufficient:
            result.should_continue = False
            result.reason = "Evidence sufficiency threshold met"
        elif result.overall_score > 0.9:
            result.should_continue = False
            result.reason = "High confidence in current findings"
        elif iteration > 2 and result.overall_score < 0.3:
            result.should_continue = False
            result.reason = "Low progress after multiple iterations"
        else:
            result.should_continue = True
            result.reason = f"Coverage {result.coverage_score:.1%}, need more evidence"

        # Generate recommendations
        if result.should_continue:
            result.recommendations = await self._generate_recommendations(
                question, findings, result.gaps
            )

        return result

    def _calculate_coverage(
        self,
        question: str,
        findings: list[ResearchFinding],
        sub_questions: list[str] | None,
    ) -> float:
        """Calculate coverage score based on sub-questions answered."""
        if not sub_questions:
            # Simple word overlap for main question
            question_words = set(question.lower().split())
            covered_words = set()
            for finding in findings:
                finding_words = set(finding.content.lower().split())
                covered_words.update(question_words & finding_words)
            return len(covered_words) / max(len(question_words), 1)

        # Count sub-questions with relevant findings
        covered = 0
        for sub_q in sub_questions:
            sub_words = set(sub_q.lower().split())
            for finding in findings:
                finding_words = set(finding.content.lower().split())
                if len(sub_words & finding_words) >= 3:
                    covered += 1
                    break

        return covered / len(sub_questions)

    def _calculate_confidence(self, findings: list[ResearchFinding]) -> float:
        """Calculate average confidence of findings."""
        if not findings:
            return 0.0
        return sum(f.confidence for f in findings) / len(findings)

    def _calculate_diversity(self, findings: list[ResearchFinding]) -> float:
        """Calculate source diversity score."""
        if not findings:
            return 0.0

        sources = {f.source for f in findings}
        source_types = {f.source_type for f in findings}

        # Score based on unique sources and source types
        source_score = min(len(sources) / 5, 1.0)  # 5 sources = max
        type_score = min(len(source_types) / 3, 1.0)  # 3 types = max

        return (source_score + type_score) / 2

    def _calculate_depth(
        self,
        findings: list[ResearchFinding],
        sub_questions: list[str] | None,
    ) -> float:
        """Calculate depth of investigation."""
        if not findings:
            return 0.0

        # Average content length as proxy for depth
        avg_length = sum(len(f.content) for f in findings) / len(findings)
        length_score = min(avg_length / 500, 1.0)  # 500 chars = good depth

        # Number of findings
        count_score = min(len(findings) / 20, 1.0)  # 20 findings = max

        return (length_score + count_score) / 2

    async def _identify_gaps(
        self,
        question: str,
        findings: list[ResearchFinding],
        sub_questions: list[str] | None,
    ) -> list[str]:
        """Identify gaps in evidence."""
        gaps = []

        # Check sub-questions coverage
        if sub_questions:
            for sub_q in sub_questions:
                sub_words = set(sub_q.lower().split())
                has_finding = False
                for finding in findings:
                    finding_words = set(finding.content.lower().split())
                    if len(sub_words & finding_words) >= 3:
                        has_finding = True
                        break
                if not has_finding:
                    gaps.append(f"No evidence for: {sub_q[:50]}...")

        # Use LLM to identify additional gaps
        if self._llm_caller and len(gaps) < 5:
            findings_summary = "\n".join(f.content[:100] for f in findings[:5])
            prompt = f"""Identify evidence gaps for this research question.

Question: {question}

Current findings summary:
{findings_summary}

What important aspects are NOT covered? List up to 3 gaps:"""

            try:
                response = await self._llm_caller(prompt)
                for line in response.split("\n"):
                    clean = line.strip().lstrip("-•*0123456789.) ")
                    if clean and len(clean) > 10:
                        gaps.append(clean)
            except Exception:
                pass

        return gaps[:5]

    async def _generate_recommendations(
        self,
        question: str,
        findings: list[ResearchFinding],
        gaps: list[str],
    ) -> list[str]:
        """Generate recommendations for improving evidence."""
        recommendations = []

        if gaps:
            recommendations.append(f"Investigate: {gaps[0]}")

        # Check source diversity
        source_types = {f.source_type for f in findings}
        if SourceType.ACADEMIC not in source_types:
            recommendations.append("Consider academic sources for credibility")
        if SourceType.WEB not in source_types and len(findings) < 10:
            recommendations.append("Expand web search for broader coverage")

        # Check confidence
        low_confidence = [f for f in findings if f.confidence < 0.5]
        if len(low_confidence) > len(findings) // 2:
            recommendations.append("Verify low-confidence findings with additional sources")

        return recommendations[:3]


class ResearchPlanner:
    """Plans research strategy and generates sub-questions."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

    async def create_plan(
        self,
        question: str,
        context: str = "",
        max_sub_questions: int = 5,
        max_depth: int = 3,
    ) -> ResearchPlan:
        """Create a research plan for a question."""
        plan_id = f"plan_{hash(question) % 100000}"

        # Generate sub-questions
        sub_questions = await self._generate_sub_questions(question, context, max_sub_questions)

        return ResearchPlan(
            id=plan_id,
            main_question=question,
            sub_questions=sub_questions,
            max_depth=max_depth,
        )

    async def _generate_sub_questions(
        self,
        question: str,
        context: str,
        max_count: int,
    ) -> list[ResearchQuestion]:
        """Generate sub-questions for investigation."""
        if self._llm_caller:
            prompt = f"""Break down this research question into {max_count} specific sub-questions.

Main Question: {question}

Context: {context}

List the sub-questions (one per line):"""
            try:
                response = await self._llm_caller(prompt)
                lines = [item.strip() for item in response.split("\n") if item.strip()]
                sub_questions = []
                for i, line in enumerate(lines[:max_count]):
                    clean_line = line.lstrip("0123456789.-) ").strip()
                    if clean_line:
                        sub_questions.append(
                            ResearchQuestion(
                                id=f"q_{i}_{hash(clean_line) % 10000}",
                                question=clean_line,
                                priority=i + 1,
                                depth=1,
                            )
                        )
                return sub_questions
            except Exception as e:
                logger.error(f"Failed to generate sub-questions: {e}")

        # Fallback: return main question as single item
        return [
            ResearchQuestion(
                id=f"q_0_{hash(question) % 10000}",
                question=question,
                priority=1,
                depth=0,
            )
        ]

    async def refine_plan(
        self,
        plan: ResearchPlan,
        findings: list[ResearchFinding],
    ) -> ResearchPlan:
        """Refine plan based on initial findings."""
        # Identify gaps
        covered_topics = set()
        for finding in findings:
            words = finding.content.lower().split()[:20]
            covered_topics.update(words)

        # Generate follow-up questions for uncovered aspects
        if self._llm_caller:
            finding_summary = "\n".join(f[:200] for f in [f.content for f in findings[:5]])
            prompt = f"""Based on these initial findings, what follow-up questions should we investigate?

Original Question: {plan.main_question}

Initial Findings:
{finding_summary}

List 3 follow-up questions to fill gaps:"""
            try:
                response = await self._llm_caller(prompt)
                lines = [item.strip() for item in response.split("\n") if item.strip()]
                for i, line in enumerate(lines[:3]):
                    clean_line = line.lstrip("0123456789.-) ").strip()
                    if clean_line:
                        plan.sub_questions.append(
                            ResearchQuestion(
                                id=f"followup_{i}_{hash(clean_line) % 10000}",
                                question=clean_line,
                                priority=len(plan.sub_questions) + 1,
                                depth=2,
                            )
                        )
            except Exception as e:
                logger.error(f"Failed to refine plan: {e}")

        return plan


class ReportSynthesizer:
    """Synthesizes findings into a coherent report."""

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self._llm_caller = llm_caller

    async def synthesize(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None = None,
    ) -> ResearchReport:
        """Synthesize findings into a report."""
        # Sort findings by relevance and confidence
        sorted_findings = sorted(
            findings,
            key=lambda f: f.relevance * f.confidence,
            reverse=True,
        )

        # Extract key findings
        key_findings = await self._extract_key_findings(question, sorted_findings)

        summary = await self._generate_summary(question, key_findings, sorted_findings)

        sources = {f.source for f in sorted_findings}
        sources = list(sources)

        # Calculate confidence and coverage
        avg_confidence = (
            sum(f.confidence for f in sorted_findings) / len(sorted_findings)
            if sorted_findings
            else 0.0
        )

        coverage = min(len(sorted_findings) / 20, 1.0)  # Assume 20 findings is full coverage

        # Identify gaps and recommendations
        gaps = await self._identify_gaps(question, sorted_findings)
        recommendations = await self._generate_recommendations(question, key_findings)

        return ResearchReport(
            question=question,
            summary=summary,
            key_findings=key_findings,
            detailed_findings=sorted_findings[:20],
            sources=sources,
            confidence=avg_confidence,
            coverage=coverage,
            recommendations=recommendations,
            gaps=gaps,
        )

    async def _extract_key_findings(
        self,
        question: str,
        findings: list[ResearchFinding],
    ) -> list[str]:
        """Extract key findings from detailed findings."""
        if not findings:
            return ["No significant findings discovered."]

        if self._llm_caller:
            findings_text = "\n".join(f"- {f.content[:200]}" for f in findings[:10])
            prompt = f"""Extract 5 key findings from this research.

Question: {question}

Findings:
{findings_text}

Key findings (one per line):"""
            try:
                response = await self._llm_caller(prompt)
                return [item.strip() for item in response.split("\n") if item.strip()][:5]
            except Exception as e:
                logger.error(f"Failed to extract key findings: {e}")

        # Fallback: use first few findings
        return [f.content[:200] for f in findings[:5]]

    async def _generate_summary(
        self,
        question: str,
        key_findings: list[str],
        all_findings: list[ResearchFinding],
    ) -> str:
        """Generate executive summary."""
        if self._llm_caller:
            findings_text = "\n".join(f"- {f}" for f in key_findings)
            prompt = f"""Write a concise executive summary answering this question.

Question: {question}

Key Findings:
{findings_text}

Summary (2-3 paragraphs):"""
            try:
                return await self._llm_caller(prompt)
            except Exception as e:
                logger.error(f"Failed to generate summary: {e}")

        # Fallback
        return f"Research on '{question}' yielded {len(all_findings)} findings. " + " ".join(
            key_findings[:3]
        )

    async def _identify_gaps(
        self,
        question: str,
        findings: list[ResearchFinding],
    ) -> list[str]:
        """Identify research gaps."""
        if not self._llm_caller:
            return []

        findings_summary = "\n".join(f.content[:100] for f in findings[:5])
        prompt = f"""What aspects of this question were NOT adequately covered?

Question: {question}

Covered topics:
{findings_summary}

List gaps (one per line):"""
        try:
            response = await self._llm_caller(prompt)
            return [item.strip() for item in response.split("\n") if item.strip()][:3]
        except Exception:
            return []

    async def _generate_recommendations(
        self,
        question: str,
        key_findings: list[str],
    ) -> list[str]:
        """Generate actionable recommendations."""
        if not self._llm_caller:
            return []

        findings_text = "\n".join(f"- {f}" for f in key_findings)
        prompt = f"""Based on these findings, provide 3 actionable recommendations.

Question: {question}

Key Findings:
{findings_text}

Recommendations (one per line):"""
        try:
            response = await self._llm_caller(prompt)
            return [item.strip() for item in response.split("\n") if item.strip()][:3]
        except Exception:
            return []


class DeepResearchAgent:
    """Main Deep Research Agent orchestrating the research process.

    Implements:
    - Scope Clarification: Query refinement before research
    - Iterative Research Loop: Cyclic search until evidence sufficiency
    - Evidence Evaluation: Continuous assessment of findings
    """

    def __init__(
        self,
        tools: list[ResearchTool] | None = None,
        planner: ResearchPlanner | None = None,
        synthesizer: ReportSynthesizer | None = None,
        scope_clarifier: ScopeClarifier | None = None,
        evidence_evaluator: EvidenceSufficiencyEvaluator | None = None,
        max_concurrent_searches: int = 5,
        min_evidence_coverage: float = 0.7,
        min_evidence_confidence: float = 0.6,
    ):
        self.tools = tools or []
        self.planner = planner or ResearchPlanner()
        self.synthesizer = synthesizer or ReportSynthesizer()
        self.scope_clarifier = scope_clarifier or ScopeClarifier()
        self.evidence_evaluator = evidence_evaluator or EvidenceSufficiencyEvaluator(
            min_coverage=min_evidence_coverage,
            min_confidence=min_evidence_confidence,
        )
        self.max_concurrent = max_concurrent_searches

        self._phase = ResearchPhase.SCOPE_CLARIFICATION
        self._findings: list[ResearchFinding] = []
        self._scope_result: ScopeClarification | None = None
        self._evidence_history: list[EvidenceSufficiency] = []
        self._stats = {
            "questions_researched": 0,
            "findings_collected": 0,
            "sources_consulted": 0,
            "iterations_completed": 0,
            "scope_clarifications": 0,
        }

    async def research(
        self,
        question: str,
        context: str = "",
        domain: str = "general",
        max_iterations: int = 5,
        time_budget_seconds: float = 300,
        skip_clarification: bool = False,
    ) -> ResearchReport:
        """Execute deep research on a question.

        The research process follows these phases:
        1. SCOPE_CLARIFICATION: Clarify and refine the query
        2. PLANNING: Create research plan with sub-questions
        3. EXPLORING: Initial broad exploration
        4. INVESTIGATING + EVALUATING: Iterative loop until evidence sufficient
        5. SYNTHESIZING: Compile findings into report
        6. COMPLETE: Finalize and return

        Args:
            question: The research question
            context: Additional context for the research
            domain: Domain of research (e.g., "legal", "technical")
            max_iterations: Maximum research iterations
            time_budget_seconds: Time limit for research
            skip_clarification: Skip scope clarification phase

        Returns:
            ResearchReport with findings, summary, and recommendations
        """
        import time

        start_time = time.monotonic()
        self._findings = []
        self._evidence_history = []

        # ========================================
        # Phase 1: SCOPE CLARIFICATION (NEW)
        # ========================================
        working_question = question
        if not skip_clarification:
            self._phase = ResearchPhase.SCOPE_CLARIFICATION
            self._scope_result = await self.scope_clarifier.clarify(question, context, domain)
            if self._scope_result.is_clear:
                working_question = self._scope_result.clarified_query
                self._stats["scope_clarifications"] += 1
                logger.info(f"Query clarified: {working_question[:100]}...")

        # ========================================
        # Phase 2: PLANNING
        # ========================================
        self._phase = ResearchPhase.PLANNING
        plan = await self.planner.create_plan(working_question, context)
        sub_questions = [q.question for q in plan.sub_questions]

        # ========================================
        # Phase 3: INITIAL EXPLORATION
        # ========================================
        self._phase = ResearchPhase.EXPLORING
        self._findings = await self._explore(plan)
        logger.info(f"Initial exploration: {len(self._findings)} findings")

        # ========================================
        # Phase 4: ITERATIVE RESEARCH LOOP (NEW)
        # Continues until evidence is sufficient or limits reached
        # ========================================
        for iteration in range(max_iterations):
            elapsed = time.monotonic() - start_time
            remaining_time = time_budget_seconds - elapsed

            # Check time budget
            if remaining_time < time_budget_seconds * 0.1:
                logger.info(f"Time budget exhausted at iteration {iteration}")
                break

            # ---- EVALUATING Phase ----
            self._phase = ResearchPhase.EVALUATING
            evidence_eval = await self.evidence_evaluator.evaluate(
                working_question,
                self._findings,
                sub_questions,
                iteration,
            )
            self._evidence_history.append(evidence_eval)

            logger.info(
                f"Iteration {iteration}: coverage={evidence_eval.coverage_score:.1%}, "
                f"confidence={evidence_eval.confidence_score:.1%}, "
                f"sufficient={evidence_eval.is_sufficient}"
            )

            # Check if evidence is sufficient - EXIT LOOP
            if not evidence_eval.should_continue:
                logger.info(f"Research complete: {evidence_eval.reason}")
                break

            # ---- INVESTIGATING Phase ----
            self._phase = ResearchPhase.INVESTIGATING

            # Refine plan based on findings and gaps
            plan = await self.planner.refine_plan(plan, self._findings)

            # Prioritize investigation based on gaps
            questions_to_investigate = []

            # Add gap-based questions from evidence evaluation
            for gap in evidence_eval.gaps[:2]:
                questions_to_investigate.append(
                    ResearchQuestion(
                        id=f"gap_{iteration}_{len(questions_to_investigate)}",
                        question=gap,
                        priority=1,
                        depth=iteration + 1,
                    )
                )

            # Add uncovered sub-questions
            for q in plan.sub_questions:
                if not any(f.question_id == q.id for f in self._findings):
                    questions_to_investigate.append(q)
                    if len(questions_to_investigate) >= 5:
                        break

            if not questions_to_investigate:
                logger.info("No more questions to investigate")
                break

            # Investigate with time awareness
            new_findings = await self._investigate(
                questions_to_investigate[:5],
                timeout=remaining_time * 0.3,
            )
            self._findings.extend(new_findings)
            self._stats["iterations_completed"] += 1

            logger.info(f"Iteration {iteration} found {len(new_findings)} new findings")

        # ========================================
        # Phase 5: SYNTHESIS
        # ========================================
        self._phase = ResearchPhase.SYNTHESIZING
        report = await self.synthesizer.synthesize(working_question, self._findings, plan)

        # Add evidence evaluation info to report
        if self._evidence_history:
            final_eval = self._evidence_history[-1]
            report.metadata["evidence_evaluation"] = final_eval.to_dict()
            report.metadata["iterations"] = len(self._evidence_history)

        if self._scope_result:
            report.metadata["scope_clarification"] = self._scope_result.to_dict()

        self._phase = ResearchPhase.COMPLETE

        self._stats["questions_researched"] += 1
        self._stats["findings_collected"] += len(self._findings)
        unique_sources = {f.source for f in self._findings}
        self._stats["sources_consulted"] += len(unique_sources)

        return report

    async def _explore(self, plan: ResearchPlan) -> list[ResearchFinding]:
        """Initial exploration phase."""
        findings: list[ResearchFinding] = []

        # Search main question across all tools
        tasks = []
        for tool in self.tools:
            tasks.append(tool.search(plan.main_question, max_results=5))

        # Search sub-questions
        for question in plan.sub_questions[:3]:
            for tool in self.tools:
                tasks.append(tool.search(question.question, max_results=3))

        # Execute searches concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_search(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[limited_search(t) for t in tasks], return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                findings.extend(result)

        return findings

    async def _investigate(
        self,
        questions: list[ResearchQuestion],
        timeout: float | None = None,
    ) -> list[ResearchFinding]:
        """Investigate specific questions with optional timeout."""
        findings: list[ResearchFinding] = []

        tasks = []
        for question in questions:
            for tool in self.tools:
                tasks.append(tool.search(question.question, max_results=3))

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_search(task):
            async with semaphore:
                return await task

        try:
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*[limited_search(t) for t in tasks], return_exceptions=True),
                    timeout=timeout,
                )
            else:
                results = await asyncio.gather(
                    *[limited_search(t) for t in tasks], return_exceptions=True
                )

            for result in results:
                if isinstance(result, list):
                    findings.extend(result)
        except TimeoutError:
            logger.warning(f"Investigation timeout after {timeout}s")

        return findings

    def get_status(self) -> dict[str, Any]:
        """Get current research status."""
        return {
            "phase": self._phase.value,
            "findings_count": len(self._findings),
            "evidence_history": [e.to_dict() for e in self._evidence_history],
            "scope_clarification": self._scope_result.to_dict() if self._scope_result else None,
            "stats": self._stats,
        }

    def get_evidence_progress(self) -> dict[str, Any]:
        """Get evidence collection progress."""
        if not self._evidence_history:
            return {"status": "not_started"}

        latest = self._evidence_history[-1]
        return {
            "is_sufficient": latest.is_sufficient,
            "overall_score": latest.overall_score,
            "coverage": latest.coverage_score,
            "confidence": latest.confidence_score,
            "diversity": latest.diversity_score,
            "iterations": len(self._evidence_history),
            "gaps_remaining": latest.gaps,
            "should_continue": latest.should_continue,
            "reason": latest.reason,
        }


# Factory functions
def create_deep_research_agent(
    tools: list[ResearchTool] | None = None,
    llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    max_concurrent: int = 5,
    min_evidence_coverage: float = 0.7,
    min_evidence_confidence: float = 0.6,
) -> DeepResearchAgent:
    """Create a Deep Research Agent with default configuration.

    Args:
        tools: List of research tools (web search, database, etc.)
        llm_caller: Async function for LLM calls
        max_concurrent: Maximum concurrent searches
        min_evidence_coverage: Minimum coverage threshold (0-1)
        min_evidence_confidence: Minimum confidence threshold (0-1)

    Returns:
        Configured DeepResearchAgent instance
    """
    planner = ResearchPlanner(llm_caller=llm_caller)
    synthesizer = ReportSynthesizer(llm_caller=llm_caller)
    scope_clarifier = ScopeClarifier(llm_caller=llm_caller)
    evidence_evaluator = EvidenceSufficiencyEvaluator(
        llm_caller=llm_caller,
        min_coverage=min_evidence_coverage,
        min_confidence=min_evidence_confidence,
    )

    return DeepResearchAgent(
        tools=tools or [],
        planner=planner,
        synthesizer=synthesizer,
        scope_clarifier=scope_clarifier,
        evidence_evaluator=evidence_evaluator,
        max_concurrent_searches=max_concurrent,
        min_evidence_coverage=min_evidence_coverage,
        min_evidence_confidence=min_evidence_confidence,
    )


__all__ = [
    "DatabaseSearchTool",
    # Core Agent
    "DeepResearchAgent",
    # Evidence Evaluation (NEW)
    "EvidenceSufficiency",
    "EvidenceSufficiencyEvaluator",
    "ReportSynthesizer",
    "ResearchFinding",
    # Research Phases
    "ResearchPhase",
    "ResearchPlan",
    # Planning & Synthesis
    "ResearchPlanner",
    # Data Classes
    "ResearchQuestion",
    "ResearchReport",
    # Research Tools
    "ResearchTool",
    # Scope Clarification (NEW)
    "ScopeClarification",
    "ScopeClarifier",
    "SourceType",
    "WebSearchTool",
    "create_deep_research_agent",
]
