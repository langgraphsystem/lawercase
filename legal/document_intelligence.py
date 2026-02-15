"""Legal Document Intelligence for EB-1A Processing.

Provides intelligent document analysis:
- Document type classification
- Section extraction
- Entity recognition (legal entities, dates, requirements)
- Legal analysis generation
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Types of legal documents."""

    PETITION = "petition"
    RECOMMENDATION_LETTER = "recommendation_letter"
    EVIDENCE = "evidence"
    EXHIBIT = "exhibit"
    RFE_RESPONSE = "rfe_response"
    COVER_LETTER = "cover_letter"
    FORM_I140 = "form_i140"
    USCIS_DECISION = "uscis_decision"
    POLICY_MEMO = "policy_memo"
    CASE_LAW = "case_law"
    REGULATION = "regulation"
    UNKNOWN = "unknown"


class EntityCategory(str, Enum):
    """Categories of extracted entities."""

    PERSON = "person"
    ORGANIZATION = "organization"
    DATE = "date"
    LEGAL_CITATION = "legal_citation"
    CRITERION = "criterion"
    REQUIREMENT = "requirement"
    EVIDENCE_TYPE = "evidence_type"
    LOCATION = "location"
    MONETARY = "monetary"


@dataclass
class ExtractedEntity:
    """An entity extracted from legal document."""

    id: str
    text: str
    category: EntityCategory
    start_pos: int
    end_pos: int
    confidence: float = 0.8
    normalized_value: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category.value,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value,
        }


@dataclass
class DocumentSection:
    """A section of a legal document."""

    id: str
    title: str
    content: str
    section_type: str
    start_pos: int
    end_pos: int
    subsections: list[DocumentSection] = field(default_factory=list)
    entities: list[ExtractedEntity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "section_type": self.section_type,
            "content_length": len(self.content),
            "subsections": len(self.subsections),
            "entities": len(self.entities),
        }


@dataclass
class LegalAnalysis:
    """Analysis result for a legal document."""

    document_id: str
    document_type: DocumentType
    sections: list[DocumentSection] = field(default_factory=list)
    entities: list[ExtractedEntity] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    criteria_mentioned: list[str] = field(default_factory=list)
    requirements_identified: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.8
    analysis_time_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "sections": len(self.sections),
            "entities": len(self.entities),
            "key_points": self.key_points[:5],
            "criteria_mentioned": self.criteria_mentioned,
            "requirements_identified": self.requirements_identified[:5],
            "risks": self.risks[:3],
            "recommendations": self.recommendations[:3],
            "confidence": self.confidence,
            "analysis_time_ms": self.analysis_time_ms,
        }


# EB-1A Criteria mapping
EB1A_CRITERIA = {
    "awards": "Evidence of receipt of lesser nationally or internationally recognized prizes or awards for excellence",
    "membership": "Evidence of membership in associations in the field which require outstanding achievements",
    "press": "Evidence of published material about the alien in professional or major trade publications",
    "judging": "Evidence of participation as a judge of the work of others in the field",
    "contributions": "Evidence of original scientific, scholarly, artistic, athletic, or business-related contributions of major significance",
    "authorship": "Evidence of authorship of scholarly articles in professional journals or major media",
    "exhibitions": "Evidence of display of work at artistic exhibitions or showcases",
    "leading_role": "Evidence of performance in a leading or critical role for distinguished organizations",
    "high_salary": "Evidence of commanding a high salary or remuneration for services",
    "commercial_success": "Evidence of commercial successes in the performing arts",
}


class DocumentClassifier:
    """Classify legal document types."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.llm_call = llm_call
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> dict[DocumentType, list[re.Pattern]]:
        """Build regex patterns for document classification."""
        return {
            DocumentType.PETITION: [
                re.compile(r"petition\s+letter", re.I),
                re.compile(r"I-140\s+petition", re.I),
                re.compile(r"extraordinary\s+ability", re.I),
            ],
            DocumentType.RECOMMENDATION_LETTER: [
                re.compile(r"recommendation\s+letter", re.I),
                re.compile(r"letter\s+of\s+support", re.I),
                re.compile(r"to\s+whom\s+it\s+may\s+concern", re.I),
            ],
            DocumentType.RFE_RESPONSE: [
                re.compile(r"RFE\s+response", re.I),
                re.compile(r"request\s+for\s+evidence", re.I),
                re.compile(r"in\s+response\s+to.*evidence\s+request", re.I),
            ],
            DocumentType.COVER_LETTER: [
                re.compile(r"cover\s+letter", re.I),
                re.compile(r"enclosed\s+please\s+find", re.I),
            ],
            DocumentType.FORM_I140: [
                re.compile(r"Form\s+I-?140", re.I),
                re.compile(r"immigrant\s+petition", re.I),
            ],
            DocumentType.USCIS_DECISION: [
                re.compile(r"USCIS.*decision", re.I),
                re.compile(r"notice\s+of\s+action", re.I),
                re.compile(r"approval\s+notice", re.I),
            ],
            DocumentType.POLICY_MEMO: [
                re.compile(r"policy\s+memo", re.I),
                re.compile(r"USCIS\s+guidance", re.I),
            ],
            DocumentType.CASE_LAW: [
                re.compile(r"Matter\s+of\s+\w+", re.I),
                re.compile(r"\d+\s+I&N\s+Dec", re.I),
            ],
        }

    async def classify(self, text: str) -> tuple[DocumentType, float]:
        """Classify document type with confidence."""
        # Rule-based classification first
        scores = {}
        for doc_type, patterns in self._patterns.items():
            score = sum(1 for p in patterns if p.search(text[:5000]))
            if score > 0:
                scores[doc_type] = score

        if scores:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] / 3, 1.0)  # Normalize
            return best_type, confidence

        # LLM fallback for unknown types
        if self.llm_call:
            prompt = f"""Classify this legal document into one of these types:
- petition, recommendation_letter, evidence, exhibit, rfe_response,
- cover_letter, form_i140, uscis_decision, policy_memo, case_law, regulation

Document excerpt (first 2000 chars):
{text[:2000]}

Respond with just the document type."""
            try:
                result = await self.llm_call(prompt)
                for doc_type in DocumentType:
                    if doc_type.value in result.lower():
                        return doc_type, 0.7
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")

        return DocumentType.UNKNOWN, 0.3


class EntityExtractorLegal:
    """Extract legal entities from documents."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.llm_call = llm_call
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> dict[EntityCategory, list[re.Pattern]]:
        """Build regex patterns for entity extraction."""
        return {
            EntityCategory.DATE: [
                re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"),
                re.compile(
                    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                    re.I,
                ),
            ],
            EntityCategory.LEGAL_CITATION: [
                re.compile(r"\b\d+\s+I&N\s+Dec\.?\s+\d+"),
                re.compile(r"Matter\s+of\s+[A-Z][a-z]+(?:\s*,\s*\d+\s+I&N\s+Dec\.?\s+\d+)?"),
                re.compile(r"\d+\s+U\.?S\.?C\.?\s*§?\s*\d+"),
                re.compile(r"8\s+C\.?F\.?R\.?\s*§?\s*[\d.]+"),
            ],
            EntityCategory.CRITERION: [
                re.compile(r"(?:criterion|criteria)\s+(?:\d|[ivx]+)", re.I),
                re.compile(
                    r"(?:awards?|prizes?|membership|publications?|judging|contributions?|authorship|exhibitions?|leading\s+role|high\s+salary|commercial\s+success)",
                    re.I,
                ),
            ],
            EntityCategory.MONETARY: [
                re.compile(r"\$[\d,]+(?:\.\d{2})?"),
                re.compile(r"[\d,]+\s+(?:dollars|USD)", re.I),
            ],
        }

    async def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract entities from text."""
        entities = []
        entity_id = 0

        # Pattern-based extraction
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity_id += 1
                    entities.append(
                        ExtractedEntity(
                            id=f"ent_{entity_id}",
                            text=match.group(),
                            category=category,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.9,
                        )
                    )

        # LLM-enhanced extraction for complex entities
        if self.llm_call and len(text) < 10000:
            prompt = f"""Extract the following from this legal text:
1. Person names (attorneys, petitioners, beneficiaries)
2. Organization names (companies, universities, government agencies)
3. EB-1A criteria mentioned

Text:
{text[:3000]}

Format each entity as: CATEGORY: entity text
Categories: PERSON, ORGANIZATION, CRITERION"""
            try:
                result = await self.llm_call(prompt)
                # Parse LLM response (simplified)
                for line in result.split("\n"):
                    if ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            cat = parts[0].strip().upper()
                            value = parts[1].strip()
                            if cat in ["PERSON", "ORGANIZATION", "CRITERION"] and value:
                                entity_id += 1
                                entities.append(
                                    ExtractedEntity(
                                        id=f"ent_{entity_id}",
                                        text=value,
                                        category=EntityCategory[cat],
                                        start_pos=-1,  # Unknown position
                                        end_pos=-1,
                                        confidence=0.7,
                                    )
                                )
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {e}")

        return entities


class SectionExtractor:
    """Extract sections from legal documents."""

    def __init__(self):
        self._section_patterns = [
            re.compile(r"^(?:I{1,3}|IV|V|VI{0,3}|IX|X)\.?\s+(.+)$", re.M),  # Roman numerals
            re.compile(r"^(?:\d+\.)+\s*(.+)$", re.M),  # Numbered sections
            re.compile(r"^([A-Z][A-Z\s]+)$", re.M),  # ALL CAPS headings
            re.compile(r"^#+\s*(.+)$", re.M),  # Markdown headings
        ]

    def extract(self, text: str) -> list[DocumentSection]:
        """Extract sections from document."""
        sections = []

        # Find all potential section headers
        headers = []
        for pattern in self._section_patterns:
            for match in pattern.finditer(text):
                headers.append(
                    {
                        "title": match.group(1) if match.groups() else match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        # Sort by position
        headers.sort(key=lambda x: x["start"])

        for section_id, header in enumerate(headers, 1):
            start_pos = header["end"]
            idx = section_id - 1
            end_pos = headers[idx + 1]["start"] if idx + 1 < len(headers) else len(text)
            content = text[start_pos:end_pos].strip()

            sections.append(
                DocumentSection(
                    id=f"sec_{section_id}",
                    title=header["title"].strip(),
                    content=content[:5000],
                    section_type="body",
                    start_pos=header["start"],
                    end_pos=end_pos,
                )
            )

        return sections


class DocumentIntelligence:
    """Main class for legal document intelligence."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.llm_call = llm_call
        self.classifier = DocumentClassifier(llm_call)
        self.entity_extractor = EntityExtractorLegal(llm_call)
        self.section_extractor = SectionExtractor()

    async def analyze_document(
        self,
        text: str,
        document_id: str | None = None,
    ) -> LegalAnalysis:
        """Perform comprehensive document analysis."""
        import time

        start = time.time()

        # Generate document ID if not provided
        if not document_id:
            document_id = hashlib.md5(text[:1000].encode(), usedforsecurity=False).hexdigest()[:12]

        # Classify document
        doc_type, type_confidence = await self.classifier.classify(text)

        # Extract sections
        sections = self.section_extractor.extract(text)

        # Extract entities
        entities = await self.entity_extractor.extract(text)

        # Identify EB-1A criteria
        criteria_mentioned = []
        for criterion, description in EB1A_CRITERIA.items():
            if criterion.lower() in text.lower() or any(
                word in text.lower() for word in description.lower().split()[:3]
            ):
                criteria_mentioned.append(criterion)

        # Generate analysis with LLM
        key_points = []
        requirements = []
        risks = []
        recommendations = []

        if self.llm_call:
            prompt = f"""Analyze this EB-1A related legal document and provide:
1. KEY POINTS (3-5 main points)
2. REQUIREMENTS (what must be demonstrated)
3. RISKS (potential issues)
4. RECOMMENDATIONS (suggested actions)

Document type: {doc_type.value}
Document excerpt:
{text[:4000]}

Format your response with clear headers for each section."""

            try:
                result = await self.llm_call(prompt)
                # Parse sections (simplified)
                current_section = None
                for raw_line in result.split("\n"):
                    stripped_line = raw_line.strip()
                    if "KEY POINT" in stripped_line.upper():
                        current_section = "key_points"
                    elif "REQUIREMENT" in stripped_line.upper():
                        current_section = "requirements"
                    elif "RISK" in stripped_line.upper():
                        current_section = "risks"
                    elif "RECOMMENDATION" in stripped_line.upper():
                        current_section = "recommendations"
                    elif (
                        stripped_line.startswith(("-", "•", "*", "1", "2", "3")) and current_section
                    ):
                        clean_line = stripped_line.lstrip("-•* 0123456789.")
                        if clean_line:
                            if current_section == "key_points":
                                key_points.append(clean_line)
                            elif current_section == "requirements":
                                requirements.append(clean_line)
                            elif current_section == "risks":
                                risks.append(clean_line)
                            elif current_section == "recommendations":
                                recommendations.append(clean_line)
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")

        analysis_time = (time.time() - start) * 1000

        return LegalAnalysis(
            document_id=document_id,
            document_type=doc_type,
            sections=sections,
            entities=entities,
            key_points=key_points,
            criteria_mentioned=criteria_mentioned,
            requirements_identified=requirements,
            risks=risks,
            recommendations=recommendations,
            confidence=type_confidence,
            analysis_time_ms=analysis_time,
        )

    async def extract_eb1a_evidence(
        self,
        text: str,
        criterion: str,
    ) -> dict[str, Any]:
        """Extract evidence for specific EB-1A criterion."""
        if criterion not in EB1A_CRITERIA:
            return {"error": f"Unknown criterion: {criterion}"}

        result = {
            "criterion": criterion,
            "description": EB1A_CRITERIA[criterion],
            "evidence_found": [],
            "strength": "weak",
            "gaps": [],
        }

        if not self.llm_call:
            return result

        prompt = f"""Analyze this document for evidence supporting the EB-1A criterion:
"{EB1A_CRITERIA[criterion]}"

Document:
{text[:5000]}

Identify:
1. EVIDENCE FOUND: Specific facts/achievements that support this criterion
2. STRENGTH: weak/moderate/strong
3. GAPS: What additional evidence would strengthen the case

Format with clear sections."""

        try:
            response = await self.llm_call(prompt)
            # Parse response (simplified)
            current_section = None
            for raw_line in response.split("\n"):
                stripped_line = raw_line.strip()
                if "EVIDENCE FOUND" in stripped_line.upper():
                    current_section = "evidence"
                elif "STRENGTH" in stripped_line.upper():
                    current_section = "strength"
                    if "weak" in stripped_line.lower():
                        result["strength"] = "weak"
                    elif "moderate" in stripped_line.lower():
                        result["strength"] = "moderate"
                    elif "strong" in stripped_line.lower():
                        result["strength"] = "strong"
                elif "GAP" in stripped_line.upper():
                    current_section = "gaps"
                elif stripped_line.startswith(("-", "•", "*")) and current_section:
                    clean_line = stripped_line.lstrip("-•* ")
                    if clean_line:
                        if current_section == "evidence":
                            result["evidence_found"].append(clean_line)
                        elif current_section == "gaps":
                            result["gaps"].append(clean_line)
        except Exception as e:
            logger.warning(f"Evidence extraction failed: {e}")

        return result


def create_document_intelligence(
    llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> DocumentIntelligence:
    """Factory function to create DocumentIntelligence instance."""
    return DocumentIntelligence(llm_call=llm_call)
