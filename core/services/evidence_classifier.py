"""EB-1A Evidence Classifier.

Inspired by USCIS's Evidence Classifier ML system that automatically
categorizes and tags documents submitted with petitions.

Features:
- Automatic document classification by EB-1A criterion
- Multi-label classification (documents can support multiple criteria)
- Confidence scoring for each classification
- RFE risk assessment
- Document quality scoring
- Consistency checking across documents
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EB1ACriterion(str, Enum):
    """EB-1A regulatory criteria from 8 CFR 204.5(h)(3)."""

    AWARDS = "awards"  # (i) Nationally/internationally recognized prizes or awards
    MEMBERSHIP = "membership"  # (ii) Membership in associations requiring outstanding achievement
    PUBLISHED_MATERIAL = "published_material"  # (iii) Published material about the alien
    JUDGING = "judging"  # (iv) Participation as a judge of the work of others
    ORIGINAL_CONTRIBUTION = (
        "original_contribution"  # (v) Original contributions of major significance
    )
    SCHOLARLY_ARTICLES = "scholarly_articles"  # (vi) Authorship of scholarly articles
    EXHIBITIONS = "exhibitions"  # (vii) Display of work at artistic exhibitions
    LEADING_ROLE = "leading_role"  # (viii) Leading or critical role in distinguished organizations
    HIGH_SALARY = "high_salary"  # (ix) High salary or remuneration
    COMMERCIAL_SUCCESS = "commercial_success"  # (x) Commercial successes in performing arts


class DocumentType(str, Enum):
    """Types of evidence documents."""

    AWARD_CERTIFICATE = "award_certificate"
    RECOMMENDATION_LETTER = "recommendation_letter"
    EMPLOYMENT_LETTER = "employment_letter"
    PUBLICATION = "publication"
    CITATION_REPORT = "citation_report"
    PATENT = "patent"
    MEDIA_ARTICLE = "media_article"
    MEMBERSHIP_CERTIFICATE = "membership_certificate"
    CONTRACT = "contract"
    PAY_STUB = "pay_stub"
    TAX_RETURN = "tax_return"
    EXHIBITION_CATALOG = "exhibition_catalog"
    REVIEW_INVITATION = "review_invitation"
    CV_RESUME = "cv_resume"
    DEGREE_CERTIFICATE = "degree_certificate"
    OTHER = "other"


class RFERiskLevel(str, Enum):
    """Risk level for receiving an RFE."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CriterionEvidence:
    """Evidence supporting a specific criterion."""

    criterion: EB1ACriterion
    confidence: float  # 0-1
    supporting_documents: list[str] = field(default_factory=list)
    evidence_strength: str = ""  # weak, moderate, strong
    missing_elements: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Result of document classification."""

    document_id: str
    document_type: DocumentType
    document_type_confidence: float

    # Multi-label classification - which criteria this document supports
    supported_criteria: list[CriterionEvidence] = field(default_factory=list)

    # Quality assessment
    quality_score: float = 0.0  # 0-1
    quality_issues: list[str] = field(default_factory=list)

    # Extracted key information
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    extracted_dates: list[str] = field(default_factory=list)
    extracted_metrics: dict[str, Any] = field(default_factory=dict)

    # Metadata
    classified_at: datetime = field(default_factory=datetime.utcnow)
    classifier_version: str = "1.0.0"


@dataclass
class CaseEvidenceAssessment:
    """Overall evidence assessment for an EB-1A case."""

    case_id: str

    # Criterion coverage
    criteria_met: list[EB1ACriterion] = field(default_factory=list)
    criteria_partial: list[EB1ACriterion] = field(default_factory=list)
    criteria_weak: list[EB1ACriterion] = field(default_factory=list)

    # Detailed criterion analysis
    criterion_evidence: dict[EB1ACriterion, CriterionEvidence] = field(default_factory=dict)

    # RFE risk
    rfe_risk: RFERiskLevel = RFERiskLevel.MEDIUM
    rfe_risk_factors: list[str] = field(default_factory=list)

    # Consistency
    consistency_score: float = 0.0
    consistency_issues: list[str] = field(default_factory=list)

    # Recommendations
    missing_documents: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)

    # Overall strength
    overall_score: float = 0.0  # 0-100
    approval_probability: float = 0.0  # 0-1

    assessed_at: datetime = field(default_factory=datetime.utcnow)


class EvidenceClassifier:
    """
    AI-powered Evidence Classifier for EB-1A petitions.

    Uses pattern matching, keyword analysis, and optionally LLM
    to classify documents and assess evidence strength.
    """

    # Keywords indicating each criterion
    CRITERION_KEYWORDS = {
        EB1ACriterion.AWARDS: [
            "award",
            "prize",
            "medal",
            "honor",
            "recognition",
            "winner",
            "recipient",
            "bestowed",
            "conferred",
            "distinguished",
            "excellence",
            "outstanding",
            "achievement",
            "first place",
            "gold",
            "national",
            "international",
            "prestigious",
        ],
        EB1ACriterion.MEMBERSHIP: [
            "member",
            "membership",
            "fellow",
            "association",
            "society",
            "academy",
            "elected",
            "invited",
            "selective",
            "outstanding achievements",
            "peer review",
            "recognition by experts",
        ],
        EB1ACriterion.PUBLISHED_MATERIAL: [
            "article about",
            "featured in",
            "interview",
            "profile",
            "news coverage",
            "press",
            "media",
            "newspaper",
            "magazine",
            "television",
            "radio",
            "documentary",
            "subject of",
        ],
        EB1ACriterion.JUDGING: [
            "judge",
            "reviewer",
            "peer review",
            "evaluate",
            "assessment",
            "panel",
            "committee",
            "referee",
            "editor",
            "grant review",
            "manuscript review",
            "thesis committee",
        ],
        EB1ACriterion.ORIGINAL_CONTRIBUTION: [
            "original",
            "contribution",
            "innovative",
            "groundbreaking",
            "pioneering",
            "novel",
            "breakthrough",
            "significant impact",
            "widely adopted",
            "paradigm shift",
            "influential",
        ],
        EB1ACriterion.SCHOLARLY_ARTICLES: [
            "publication",
            "paper",
            "journal",
            "conference",
            "proceedings",
            "author",
            "co-author",
            "peer-reviewed",
            "cited",
            "citation",
            "h-index",
            "impact factor",
        ],
        EB1ACriterion.EXHIBITIONS: [
            "exhibition",
            "gallery",
            "museum",
            "showcase",
            "display",
            "artistic",
            "solo show",
            "group show",
            "retrospective",
        ],
        EB1ACriterion.LEADING_ROLE: [
            "director",
            "founder",
            "CEO",
            "CTO",
            "president",
            "vice president",
            "chief",
            "head",
            "lead",
            "principal",
            "manager",
            "distinguished",
            "critical role",
            "key contributor",
        ],
        EB1ACriterion.HIGH_SALARY: [
            "salary",
            "compensation",
            "remuneration",
            "income",
            "wage",
            "earnings",
            "pay",
            "bonus",
            "stock",
            "equity",
            "percentile",
            "above average",
            "top earner",
        ],
        EB1ACriterion.COMMERCIAL_SUCCESS: [
            "box office",
            "sales",
            "revenue",
            "platinum",
            "gold record",
            "bestseller",
            "commercial",
            "ratings",
            "viewership",
            "downloads",
        ],
    }

    # Document type patterns
    DOCUMENT_PATTERNS = {
        DocumentType.AWARD_CERTIFICATE: [
            r"certificate.*award",
            r"award.*certificate",
            r"this\s+is\s+to\s+certify",
            r"presented\s+to",
            r"in\s+recognition\s+of",
        ],
        DocumentType.RECOMMENDATION_LETTER: [
            r"letter\s+of\s+recommendation",
            r"i\s+am\s+writing\s+to\s+recommend",
            r"it\s+is\s+my\s+pleasure\s+to\s+recommend",
            r"dear\s+uscis",
            r"to\s+whom\s+it\s+may\s+concern",
        ],
        DocumentType.EMPLOYMENT_LETTER: [
            r"employment\s+verification",
            r"this\s+letter\s+confirms",
            r"employed\s+as",
            r"current\s+position",
            r"job\s+title",
        ],
        DocumentType.CITATION_REPORT: [
            r"citation\s+report",
            r"google\s+scholar",
            r"h-index",
            r"total\s+citations",
            r"web\s+of\s+science",
            r"scopus",
        ],
        DocumentType.PATENT: [
            r"patent\s+number",
            r"united\s+states\s+patent",
            r"inventor",
            r"claims",
            r"abstract.*invention",
        ],
        DocumentType.MEDIA_ARTICLE: [
            r"published\s+in",
            r"by\s+[a-z]+\s+staff",
            r"reporter",
            r"news\s+article",
            r"press\s+release",
        ],
        DocumentType.PAY_STUB: [
            r"pay\s+stub",
            r"earnings\s+statement",
            r"gross\s+pay",
            r"net\s+pay",
            r"deductions",
        ],
        DocumentType.TAX_RETURN: [
            r"form\s+w-2",
            r"form\s+1040",
            r"adjusted\s+gross\s+income",
            r"tax\s+return",
            r"internal\s+revenue",
        ],
    }

    # RFE risk factors
    RFE_RISK_FACTORS = {
        "insufficient_criteria": "Less than 3 criteria with strong evidence",
        "weak_recommendations": "Recommendation letters lack specific achievements",
        "no_independent_evidence": "No evidence from independent sources",
        "inconsistent_dates": "Dates are inconsistent across documents",
        "missing_metrics": "No quantifiable metrics provided",
        "poor_quality_copies": "Document copies are illegible or incomplete",
        "no_english_translations": "Foreign documents lack certified translations",
        "outdated_evidence": "Evidence is more than 5 years old",
        "self-serving_only": "Only self-serving evidence, no third-party verification",
    }

    def __init__(self, llm_client: Any | None = None):
        """
        Initialize Evidence Classifier.

        Args:
            llm_client: Optional LLM client for advanced classification
        """
        self.llm_client = llm_client
        self._classification_history: list[ClassificationResult] = []
        logger.info("EvidenceClassifier initialized")

    async def classify_document(
        self,
        document_id: str,
        content: str,
        filename: str | None = None,
    ) -> ClassificationResult:
        """
        Classify a single document.

        Args:
            document_id: Unique document identifier
            content: Document text content
            filename: Original filename (optional)

        Returns:
            ClassificationResult with document type and supported criteria
        """
        content_lower = content.lower()

        # Detect document type
        doc_type, doc_confidence = self._detect_document_type(content_lower, filename)

        # Detect supported criteria
        supported_criteria = self._detect_criteria(content_lower)

        # Extract key information
        entities = self._extract_entities(content)
        dates = self._extract_dates(content)
        metrics = self._extract_metrics(content)

        # Assess quality
        quality_score, quality_issues = self._assess_document_quality(content, doc_type)

        result = ClassificationResult(
            document_id=document_id,
            document_type=doc_type,
            document_type_confidence=doc_confidence,
            supported_criteria=supported_criteria,
            quality_score=quality_score,
            quality_issues=quality_issues,
            extracted_entities=entities,
            extracted_dates=dates,
            extracted_metrics=metrics,
        )

        self._classification_history.append(result)

        logger.info(
            "Document classified",
            document_id=document_id,
            document_type=doc_type.value,
            criteria_count=len(supported_criteria),
            quality_score=quality_score,
        )

        return result

    async def assess_case_evidence(
        self,
        case_id: str,
        classifications: list[ClassificationResult],
    ) -> CaseEvidenceAssessment:
        """
        Assess overall evidence strength for an EB-1A case.

        Args:
            case_id: Case identifier
            classifications: List of classified documents

        Returns:
            CaseEvidenceAssessment with overall analysis
        """
        assessment = CaseEvidenceAssessment(case_id=case_id)

        # Aggregate evidence by criterion
        criterion_docs: dict[EB1ACriterion, list[CriterionEvidence]] = {
            c: [] for c in EB1ACriterion
        }

        for classification in classifications:
            for evidence in classification.supported_criteria:
                criterion_docs[evidence.criterion].append(evidence)

        # Assess each criterion
        for criterion, evidences in criterion_docs.items():
            if not evidences:
                continue

            # Calculate aggregate strength
            avg_confidence = sum(e.confidence for e in evidences) / len(evidences)
            doc_count = len(evidences)

            # Determine evidence level
            if avg_confidence >= 0.7 and doc_count >= 2:
                strength = "strong"
                assessment.criteria_met.append(criterion)
            elif avg_confidence >= 0.5 or doc_count >= 1:
                strength = "moderate"
                assessment.criteria_partial.append(criterion)
            else:
                strength = "weak"
                assessment.criteria_weak.append(criterion)

            # Create combined evidence
            combined = CriterionEvidence(
                criterion=criterion,
                confidence=avg_confidence,
                supporting_documents=[
                    doc_id
                    for c in classifications
                    for e in c.supported_criteria
                    if e.criterion == criterion
                    for doc_id in [c.document_id]
                ],
                evidence_strength=strength,
                missing_elements=self._get_missing_elements(criterion, evidences),
                recommendations=self._get_criterion_recommendations(criterion, strength),
            )

            assessment.criterion_evidence[criterion] = combined

        # Check RFE risk
        assessment.rfe_risk, assessment.rfe_risk_factors = self._calculate_rfe_risk(
            assessment, classifications
        )

        # Check consistency
        assessment.consistency_score, assessment.consistency_issues = self._check_consistency(
            classifications
        )

        # Generate recommendations
        assessment.missing_documents = self._identify_missing_documents(assessment)
        assessment.improvement_suggestions = self._generate_suggestions(assessment)

        # Calculate overall score
        assessment.overall_score = self._calculate_overall_score(assessment)
        assessment.approval_probability = self._estimate_approval_probability(assessment)

        logger.info(
            "Case evidence assessed",
            case_id=case_id,
            criteria_met=len(assessment.criteria_met),
            rfe_risk=assessment.rfe_risk.value,
            overall_score=assessment.overall_score,
        )

        return assessment

    def _detect_document_type(
        self, content: str, filename: str | None
    ) -> tuple[DocumentType, float]:
        """Detect document type from content and filename."""
        best_type = DocumentType.OTHER
        best_confidence = 0.0

        for doc_type, patterns in self.DOCUMENT_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matches += 1

            confidence = matches / len(patterns) if patterns else 0
            if confidence > best_confidence:
                best_confidence = confidence
                best_type = doc_type

        # Boost confidence from filename
        if filename:
            filename_lower = filename.lower()
            if "award" in filename_lower or "certificate" in filename_lower:
                if best_type == DocumentType.AWARD_CERTIFICATE:
                    best_confidence = min(1.0, best_confidence + 0.2)
            elif "recommendation" in filename_lower or "letter" in filename_lower:
                if best_type == DocumentType.RECOMMENDATION_LETTER:
                    best_confidence = min(1.0, best_confidence + 0.2)

        return best_type, best_confidence

    def _detect_criteria(self, content: str) -> list[CriterionEvidence]:
        """Detect which EB-1A criteria the document supports."""
        results = []

        for criterion, keywords in self.CRITERION_KEYWORDS.items():
            matches = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword in content:
                    matches += 1
                    matched_keywords.append(keyword)

            if matches > 0:
                confidence = min(1.0, matches / 5)  # Normalize
                strength = "strong" if matches >= 5 else "moderate" if matches >= 2 else "weak"

                results.append(
                    CriterionEvidence(
                        criterion=criterion,
                        confidence=confidence,
                        evidence_strength=strength,
                    )
                )

        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results

    def _extract_entities(self, content: str) -> dict[str, Any]:
        """Extract named entities from document."""
        entities: dict[str, Any] = {
            "organizations": [],
            "people": [],
            "locations": [],
        }

        # Simple pattern-based extraction
        # Organizations (capitalized multi-word phrases)
        org_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
        orgs = re.findall(org_pattern, content)
        entities["organizations"] = list(set(orgs))[:10]

        return entities

    def _extract_dates(self, content: str) -> list[str]:
        """Extract dates from document."""
        date_patterns = [
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)

        return list(set(dates))[:20]

    def _extract_metrics(self, content: str) -> dict[str, Any]:
        """Extract quantifiable metrics from document."""
        metrics: dict[str, Any] = {}

        # Citations
        citation_match = re.search(r"(\d+)\s*citations?", content, re.IGNORECASE)
        if citation_match:
            metrics["citations"] = int(citation_match.group(1))

        # H-index
        hindex_match = re.search(r"h-index[:\s]*(\d+)", content, re.IGNORECASE)
        if hindex_match:
            metrics["h_index"] = int(hindex_match.group(1))

        # Salary/Amount
        salary_match = re.search(
            r"\$[\d,]+(?:\.\d{2})?|\b(\d{1,3}(?:,\d{3})*)\s*(?:dollars?|USD)",
            content,
            re.IGNORECASE,
        )
        if salary_match:
            amount_str = (
                salary_match.group(0)
                .replace("$", "")
                .replace(",", "")
                .replace("dollars", "")
                .replace("USD", "")
                .strip()
            )
            try:
                metrics["amount"] = float(amount_str)
            except ValueError:
                pass

        # Years of experience
        exp_match = re.search(r"(\d+)\s*years?\s*(?:of\s+)?experience", content, re.IGNORECASE)
        if exp_match:
            metrics["years_experience"] = int(exp_match.group(1))

        # Publications count
        pub_match = re.search(r"(\d+)\s*publications?", content, re.IGNORECASE)
        if pub_match:
            metrics["publications"] = int(pub_match.group(1))

        return metrics

    def _assess_document_quality(
        self, content: str, doc_type: DocumentType
    ) -> tuple[float, list[str]]:
        """Assess document quality."""
        score = 1.0
        issues = []

        # Check length
        if len(content) < 100:
            score -= 0.3
            issues.append("Document content is too short")
        elif len(content) < 500:
            score -= 0.1
            issues.append("Document content may be incomplete")

        # Check for specific required elements by type
        if doc_type == DocumentType.RECOMMENDATION_LETTER:
            required = ["sincerely", "signature", "position", "organization"]
            for req in required:
                if req not in content.lower():
                    score -= 0.1
                    issues.append(f"Missing recommended element: {req}")

        elif doc_type == DocumentType.AWARD_CERTIFICATE:
            required = ["date", "award", "organization"]
            for req in required:
                if req not in content.lower():
                    score -= 0.1
                    issues.append(f"Missing element: {req}")

        # Check for potential OCR issues
        if re.search(r"[^\x00-\x7F]{5,}", content):
            score -= 0.1
            issues.append("Potential OCR quality issues detected")

        return max(0, score), issues

    def _calculate_rfe_risk(
        self,
        assessment: CaseEvidenceAssessment,
        classifications: list[ClassificationResult],
    ) -> tuple[RFERiskLevel, list[str]]:
        """Calculate RFE risk level."""
        risk_factors = []
        risk_score = 0

        # Check criteria count
        if len(assessment.criteria_met) < 3:
            risk_factors.append(self.RFE_RISK_FACTORS["insufficient_criteria"])
            risk_score += 30

        # Check for independent evidence
        has_independent = any(
            c.document_type in [DocumentType.MEDIA_ARTICLE, DocumentType.CITATION_REPORT]
            for c in classifications
        )
        if not has_independent:
            risk_factors.append(self.RFE_RISK_FACTORS["no_independent_evidence"])
            risk_score += 20

        # Check document quality
        avg_quality = sum(c.quality_score for c in classifications) / max(len(classifications), 1)
        if avg_quality < 0.5:
            risk_factors.append(self.RFE_RISK_FACTORS["poor_quality_copies"])
            risk_score += 15

        # Check for metrics
        has_metrics = any(c.extracted_metrics for c in classifications)
        if not has_metrics:
            risk_factors.append(self.RFE_RISK_FACTORS["missing_metrics"])
            risk_score += 10

        # Determine risk level
        if risk_score >= 50:
            risk_level = RFERiskLevel.CRITICAL
        elif risk_score >= 30:
            risk_level = RFERiskLevel.HIGH
        elif risk_score >= 15:
            risk_level = RFERiskLevel.MEDIUM
        else:
            risk_level = RFERiskLevel.LOW

        return risk_level, risk_factors

    def _check_consistency(
        self, classifications: list[ClassificationResult]
    ) -> tuple[float, list[str]]:
        """Check consistency across documents."""
        issues = []
        score = 1.0

        # Check date consistency
        all_dates = []
        for c in classifications:
            all_dates.extend(c.extracted_dates)

        # More consistency checks can be added here

        return score, issues

    def _get_missing_elements(
        self, criterion: EB1ACriterion, evidences: list[CriterionEvidence]
    ) -> list[str]:
        """Identify missing evidence elements for a criterion."""
        missing = []

        # Criterion-specific requirements
        requirements = {
            EB1ACriterion.AWARDS: [
                "Proof of award receipt",
                "Criteria for award selection",
                "Number of recipients",
                "National/international scope",
            ],
            EB1ACriterion.MEMBERSHIP: [
                "Membership certificate",
                "Organization bylaws showing requirements",
                "Evidence of peer review for admission",
            ],
            EB1ACriterion.SCHOLARLY_ARTICLES: [
                "Published articles",
                "Citation report",
                "Journal impact factors",
            ],
            EB1ACriterion.ORIGINAL_CONTRIBUTION: [
                "Letters from experts",
                "Evidence of adoption/impact",
                "Publications describing contribution",
            ],
            EB1ACriterion.HIGH_SALARY: [
                "Pay stubs or employment letter",
                "Industry salary statistics",
                "Tax returns",
            ],
        }

        # This is simplified - in production, would check actual evidence
        if criterion in requirements:
            avg_confidence = sum(e.confidence for e in evidences) / max(len(evidences), 1)
            if avg_confidence < 0.7:
                missing.extend(requirements[criterion])

        return missing

    def _get_criterion_recommendations(self, criterion: EB1ACriterion, strength: str) -> list[str]:
        """Get recommendations for improving criterion evidence."""
        recommendations = []

        if strength == "weak":
            recommendations.append(f"Add more supporting documents for {criterion.value}")

        criterion_tips = {
            EB1ACriterion.AWARDS: [
                "Include documentation showing award selection criteria",
                "Provide evidence of national/international recognition",
            ],
            EB1ACriterion.SCHOLARLY_ARTICLES: [
                "Include citation report from Google Scholar or Web of Science",
                "Highlight highly-cited publications",
            ],
            EB1ACriterion.ORIGINAL_CONTRIBUTION: [
                "Obtain letters from independent experts in the field",
                "Document real-world impact and adoption",
            ],
        }

        if criterion in criterion_tips and strength != "strong":
            recommendations.extend(criterion_tips[criterion])

        return recommendations

    def _identify_missing_documents(self, assessment: CaseEvidenceAssessment) -> list[str]:
        """Identify missing documents for the case."""
        missing = []

        # Essential documents
        essentials = [
            ("Recommendation letters from independent experts", 3),
            ("Citation report", 1),
            ("Employment verification letter", 1),
        ]

        # Check which criteria need more evidence
        for criterion in assessment.criteria_partial + assessment.criteria_weak:
            missing.append(f"Additional evidence for {criterion.value}")

        return missing

    def _generate_suggestions(self, assessment: CaseEvidenceAssessment) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if len(assessment.criteria_met) < 3:
            suggestions.append("Focus on strengthening at least 3 criteria with robust evidence")

        if assessment.rfe_risk in [RFERiskLevel.HIGH, RFERiskLevel.CRITICAL]:
            suggestions.append("High RFE risk - consider adding more independent evidence")

        if assessment.consistency_score < 0.8:
            suggestions.append("Review documents for consistency in dates and facts")

        return suggestions

    def _calculate_overall_score(self, assessment: CaseEvidenceAssessment) -> float:
        """Calculate overall case strength score (0-100)."""
        score = 0.0

        # Criteria scoring (max 60 points)
        score += len(assessment.criteria_met) * 15
        score += len(assessment.criteria_partial) * 5

        # Consistency (max 20 points)
        score += assessment.consistency_score * 20

        # RFE risk (max 20 points)
        risk_scores = {
            RFERiskLevel.LOW: 20,
            RFERiskLevel.MEDIUM: 15,
            RFERiskLevel.HIGH: 8,
            RFERiskLevel.CRITICAL: 0,
        }
        score += risk_scores.get(assessment.rfe_risk, 0)

        return min(100, score)

    def _estimate_approval_probability(self, assessment: CaseEvidenceAssessment) -> float:
        """Estimate approval probability based on evidence."""
        # Based on overall score
        base_probability = assessment.overall_score / 100

        # Adjust based on criteria met
        if len(assessment.criteria_met) >= 3:
            base_probability = min(1.0, base_probability + 0.1)
        elif len(assessment.criteria_met) < 2:
            base_probability = max(0.0, base_probability - 0.2)

        return round(base_probability, 2)


# Singleton
_evidence_classifier: EvidenceClassifier | None = None


def get_evidence_classifier(llm_client: Any | None = None) -> EvidenceClassifier:
    """Get or create global EvidenceClassifier instance."""
    global _evidence_classifier

    if _evidence_classifier is None:
        _evidence_classifier = EvidenceClassifier(llm_client=llm_client)

    return _evidence_classifier
