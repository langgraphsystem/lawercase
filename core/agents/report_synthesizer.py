"""Report Synthesizer - Standalone module for synthesizing research reports.

Re-exports ReportSynthesizer from deep_research_agent and provides
additional synthesis utilities.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from .deep_research_agent import (
    ReportSynthesizer as BaseReportSynthesizer,
    ResearchFinding,
    ResearchPlan,
    ResearchReport,
)

logger = structlog.get_logger(__name__)


class ReportFormat(str, Enum):
    """Output format for reports."""

    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PLAIN_TEXT = "plain_text"
    STRUCTURED = "structured"


class ReportSection(str, Enum):
    """Standard report sections."""

    EXECUTIVE_SUMMARY = "executive_summary"
    METHODOLOGY = "methodology"
    KEY_FINDINGS = "key_findings"
    DETAILED_ANALYSIS = "detailed_analysis"
    SOURCES = "sources"
    RECOMMENDATIONS = "recommendations"
    LIMITATIONS = "limitations"
    APPENDIX = "appendix"


@dataclass
class SynthesisConfig:
    """Configuration for report synthesis."""

    format: ReportFormat = ReportFormat.MARKDOWN
    include_sections: list[ReportSection] = field(
        default_factory=lambda: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.KEY_FINDINGS,
            ReportSection.DETAILED_ANALYSIS,
            ReportSection.SOURCES,
            ReportSection.RECOMMENDATIONS,
        ]
    )
    max_key_findings: int = 10
    max_detailed_findings: int = 20
    include_citations: bool = True
    include_confidence_scores: bool = True
    min_finding_relevance: float = 0.5
    language: str = "en"


@dataclass
class SectionContent:
    """Content for a report section."""

    section: ReportSection
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredReport:
    """A fully structured research report."""

    report_id: str
    question: str
    sections: list[SectionContent] = field(default_factory=list)
    findings: list[ResearchFinding] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    coverage: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        parts = [f"# {self.question}\n"]

        for section in self.sections:
            parts.append(f"\n## {section.title}\n")
            parts.append(section.content)

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "question": self.question,
            "sections": [
                {"section": s.section.value, "title": s.title, "content": s.content}
                for s in self.sections
            ],
            "findings_count": len(self.findings),
            "sources_count": len(self.sources),
            "confidence": self.confidence,
            "coverage": self.coverage,
            "generated_at": self.generated_at.isoformat(),
        }


class EnhancedReportSynthesizer(BaseReportSynthesizer):
    """Enhanced Report Synthesizer with additional capabilities.

    Extends base synthesizer with:
    - Multiple output formats
    - Configurable sections
    - Citation management
    - Quality scoring
    """

    def __init__(
        self,
        llm_caller: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        config: SynthesisConfig | None = None,
    ):
        super().__init__(llm_caller=llm_caller)
        self.config = config or SynthesisConfig()
        self._synthesis_count = 0

    async def synthesize_structured(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None = None,
    ) -> StructuredReport:
        """Synthesize findings into a structured report.

        Args:
            question: Research question
            findings: List of research findings
            plan: Optional research plan

        Returns:
            StructuredReport with sections
        """
        self._synthesis_count += 1
        report_id = f"report_{self._synthesis_count}_{int(datetime.now(UTC).timestamp())}"

        # Filter findings by relevance
        filtered_findings = [
            f for f in findings if f.relevance >= self.config.min_finding_relevance
        ]

        # Sort by relevance
        sorted_findings = sorted(
            filtered_findings,
            key=lambda f: f.relevance * f.confidence,
            reverse=True,
        )

        # Build sections
        sections = []

        for section_type in self.config.include_sections:
            section_content = await self._build_section(
                section_type,
                question,
                sorted_findings,
                plan,
            )
            if section_content:
                sections.append(section_content)

        sources = {f.source for f in sorted_findings}
        sources = list(sources)
        avg_confidence = (
            sum(f.confidence for f in sorted_findings) / len(sorted_findings)
            if sorted_findings
            else 0.0
        )
        coverage = min(len(sorted_findings) / 20, 1.0)

        report = StructuredReport(
            report_id=report_id,
            question=question,
            sections=sections,
            findings=sorted_findings[: self.config.max_detailed_findings],
            sources=sources,
            confidence=avg_confidence,
            coverage=coverage,
            metadata={
                "total_findings": len(findings),
                "filtered_findings": len(filtered_findings),
                "format": self.config.format.value,
            },
        )

        logger.info(
            "synthesizer.report_created",
            report_id=report_id,
            sections=len(sections),
            findings=len(sorted_findings),
        )

        return report

    async def _build_section(
        self,
        section_type: ReportSection,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent | None:
        """Build a specific report section."""

        builders = {
            ReportSection.EXECUTIVE_SUMMARY: self._build_executive_summary,
            ReportSection.METHODOLOGY: self._build_methodology,
            ReportSection.KEY_FINDINGS: self._build_key_findings,
            ReportSection.DETAILED_ANALYSIS: self._build_detailed_analysis,
            ReportSection.SOURCES: self._build_sources,
            ReportSection.RECOMMENDATIONS: self._build_recommendations,
            ReportSection.LIMITATIONS: self._build_limitations,
        }

        builder = builders.get(section_type)
        if builder:
            return await builder(question, findings, plan)

        return None

    async def _build_executive_summary(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build executive summary section."""
        key_findings = await self._extract_key_findings(question, findings)
        summary = await self._generate_summary(question, key_findings, findings)

        return SectionContent(
            section=ReportSection.EXECUTIVE_SUMMARY,
            title="Executive Summary",
            content=summary,
            metadata={"key_findings_count": len(key_findings)},
        )

    async def _build_methodology(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build methodology section."""
        # Count sources by type
        source_types = {}
        for f in findings:
            st = f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type)
            source_types[st] = source_types.get(st, 0) + 1

        methodology = [
            "### Research Methodology",
            "",
            f"This research analyzed **{len(findings)}** findings from multiple sources.",
            "",
            "**Source Distribution:**",
        ]

        for source_type, count in source_types.items():
            methodology.append(f"- {source_type}: {count} findings")

        if plan:
            methodology.extend(
                [
                    "",
                    f"**Strategy:** {plan.strategy}",
                    f"**Sub-questions investigated:** {len(plan.sub_questions)}",
                ]
            )

        return SectionContent(
            section=ReportSection.METHODOLOGY,
            title="Methodology",
            content="\n".join(methodology),
            metadata={"source_types": source_types},
        )

    async def _build_key_findings(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build key findings section."""
        key_findings = await self._extract_key_findings(question, findings)

        content_parts = ["### Key Findings", ""]

        for i, finding in enumerate(key_findings[: self.config.max_key_findings], 1):
            content_parts.append(f"{i}. {finding}")
            content_parts.append("")

        return SectionContent(
            section=ReportSection.KEY_FINDINGS,
            title="Key Findings",
            content="\n".join(content_parts),
            metadata={"count": len(key_findings)},
        )

    async def _build_detailed_analysis(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build detailed analysis section."""
        content_parts = ["### Detailed Analysis", ""]

        # Group by source type
        by_source: dict[str, list[ResearchFinding]] = {}
        for f in findings[: self.config.max_detailed_findings]:
            st = f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type)
            if st not in by_source:
                by_source[st] = []
            by_source[st].append(f)

        for source_type, source_findings in by_source.items():
            content_parts.append(f"#### From {source_type.replace('_', ' ').title()}")
            content_parts.append("")

            for f in source_findings[:5]:
                content_parts.append(f"**Finding** (Confidence: {f.confidence:.2f})")
                content_parts.append(f"> {f.content[:300]}...")
                if self.config.include_citations and f.citations:
                    content_parts.append(f"*Citations: {', '.join(f.citations[:3])}*")
                content_parts.append("")

        return SectionContent(
            section=ReportSection.DETAILED_ANALYSIS,
            title="Detailed Analysis",
            content="\n".join(content_parts),
            metadata={"source_types": list(by_source.keys())},
        )

    async def _build_sources(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build sources section."""
        sources = {f.source for f in findings}
        sources = list(sources)

        content_parts = ["### Sources", ""]

        for i, source in enumerate(sources[:20], 1):
            content_parts.append(f"{i}. {source}")

        if len(sources) > 20:
            content_parts.append(f"... and {len(sources) - 20} more sources")

        return SectionContent(
            section=ReportSection.SOURCES,
            title="Sources",
            content="\n".join(content_parts),
            metadata={"total_sources": len(sources)},
        )

    async def _build_recommendations(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build recommendations section."""
        key_findings = await self._extract_key_findings(question, findings)
        recommendations = await self._generate_recommendations(question, key_findings)

        content_parts = ["### Recommendations", ""]

        for i, rec in enumerate(recommendations, 1):
            content_parts.append(f"{i}. {rec}")
            content_parts.append("")

        return SectionContent(
            section=ReportSection.RECOMMENDATIONS,
            title="Recommendations",
            content="\n".join(content_parts),
            metadata={"count": len(recommendations)},
        )

    async def _build_limitations(
        self,
        question: str,
        findings: list[ResearchFinding],
        plan: ResearchPlan | None,
    ) -> SectionContent:
        """Build limitations section."""
        gaps = await self._identify_gaps(question, findings)

        content_parts = [
            "### Limitations and Gaps",
            "",
            "The following limitations were identified:",
            "",
        ]

        for gap in gaps:
            content_parts.append(f"- {gap}")

        # Add general limitations
        content_parts.extend(
            [
                "",
                "**General Limitations:**",
                f"- Analysis based on {len(findings)} findings",
                "- Findings may not represent complete picture",
                "- Confidence scores are estimates",
            ]
        )

        return SectionContent(
            section=ReportSection.LIMITATIONS,
            title="Limitations and Gaps",
            content="\n".join(content_parts),
            metadata={"gaps": gaps},
        )

    def format_report(
        self,
        report: StructuredReport,
        output_format: ReportFormat | None = None,
    ) -> str:
        """Format report to specified output format.

        Args:
            report: Report to format
            output_format: Output format (defaults to config)

        Returns:
            Formatted report string
        """
        output_format = output_format or self.config.format

        if output_format == ReportFormat.MARKDOWN:
            return report.to_markdown()

        if output_format == ReportFormat.JSON:
            import json

            return json.dumps(report.to_dict(), indent=2)

        if output_format == ReportFormat.PLAIN_TEXT:
            parts = [f"REPORT: {report.question}\n"]
            parts.append("=" * 50)
            for section in report.sections:
                parts.append(f"\n{section.title.upper()}\n")
                parts.append("-" * 30)
                content = section.content.replace("#", "").replace("*", "").replace(">", "")
                parts.append(content)
            return "\n".join(parts)

        if output_format == ReportFormat.HTML:
            import html

            parts = [f"<h1>{html.escape(report.question)}</h1>"]
            for section in report.sections:
                parts.append(f"<h2>{html.escape(section.title)}</h2>")
                content = section.content.replace("\n\n", "</p><p>")
                content = content.replace("**", "<strong>").replace("**", "</strong>")
                parts.append(f"<p>{content}</p>")
            return "\n".join(parts)

        return str(report.to_dict())


# Re-export
ReportSynthesizer = EnhancedReportSynthesizer

__all__ = [
    "BaseReportSynthesizer",
    "EnhancedReportSynthesizer",
    "ReportFormat",
    "ReportSection",
    "ReportSynthesizer",
    "ResearchReport",
    "SectionContent",
    "StructuredReport",
    "SynthesisConfig",
]
