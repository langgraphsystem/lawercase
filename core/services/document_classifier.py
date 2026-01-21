"""
Universal Document Classifier for EB-1A Case Management.

Classifies uploaded documents using OCR + LLM to determine:
1. Document type (passport, diploma, award, publication, etc.)
2. Category (intake, eb1a_criterion, career, recommendation, etc.)
3. Linked question_id or evidence slot

Works independently of intake flow - documents can be uploaded at any time
and will be correctly categorized and linked to the appropriate section.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Timeout for LLM classification (seconds)
LLM_CLASSIFICATION_TIMEOUT = 60  # 1 minute


class DocumentCategory(str, Enum):
    """High-level document categories."""

    # Intake - Basic Info
    IDENTITY = "identity"  # Passport, birth certificate, ID
    EDUCATION = "education"  # Diplomas, transcripts, certificates

    # EB-1A Criteria Evidence
    EB1A_AWARDS = "eb1a_awards"  # Awards, prizes, honors (Criterion 1)
    EB1A_MEMBERSHIP = "eb1a_membership"  # Membership in elite organizations (Criterion 2)
    EB1A_PRESS = "eb1a_press"  # Press/media coverage (Criterion 3)
    EB1A_JUDGING = "eb1a_judging"  # Judging others' work (Criterion 4)
    EB1A_CONTRIBUTION = "eb1a_contribution"  # Original contributions (Criterion 5)
    EB1A_SCHOLARLY = "eb1a_scholarly"  # Scholarly articles (Criterion 6)
    EB1A_EXHIBITION = "eb1a_exhibition"  # Artistic exhibitions (Criterion 7)
    EB1A_LEADERSHIP = "eb1a_leadership"  # Leading/critical role (Criterion 8)
    EB1A_SALARY = "eb1a_salary"  # High salary evidence (Criterion 9)
    EB1A_COMMERCIAL = "eb1a_commercial"  # Commercial success (Criterion 10)

    # Career / Employment
    CAREER_EMPLOYMENT = "career_employment"  # Employment contracts, offer letters
    CAREER_RECOMMENDATION = "career_recommendation"  # Employer recommendations

    # Recommendations
    RECOMMENDATION_LETTER = "recommendation_letter"  # Expert recommendation letters

    # Other
    OTHER = "other"  # Unclassified documents


@dataclass
class DocumentType:
    """Definition of a document type with classification hints."""

    id: str
    name_ru: str
    name_en: str
    category: DocumentCategory
    linked_question_id: str | None  # Link to intake question if applicable
    keywords_ru: list[str]  # OCR keywords for classification (Russian)
    keywords_en: list[str]  # OCR keywords for classification (English)
    tags: list[str]  # Tags to apply when saving
    eb1a_criterion: int | None = None  # EB-1A criterion number (1-10)


# Universal Document Taxonomy
DOCUMENT_TYPES: list[DocumentType] = [
    # === IDENTITY DOCUMENTS ===
    DocumentType(
        id="passport",
        name_ru="Паспорт",
        name_en="Passport",
        category=DocumentCategory.IDENTITY,
        linked_question_id="doc_passport",
        keywords_ru=["паспорт", "passport", "российская федерация", "гражданин"],
        keywords_en=["passport", "citizen", "nationality", "date of birth"],
        tags=["intake", "basic_info", "document", "identity"],
    ),
    DocumentType(
        id="birth_certificate",
        name_ru="Свидетельство о рождении",
        name_en="Birth Certificate",
        category=DocumentCategory.IDENTITY,
        linked_question_id="doc_birth_certificate",
        keywords_ru=["свидетельство о рождении", "актовая запись", "родился", "мать", "отец"],
        keywords_en=["birth certificate", "certificate of birth", "born", "mother", "father"],
        tags=["intake", "basic_info", "document", "identity"],
    ),
    DocumentType(
        id="national_id",
        name_ru="Удостоверение личности",
        name_en="National ID",
        category=DocumentCategory.IDENTITY,
        linked_question_id="doc_passport",
        keywords_ru=["удостоверение личности", "id card", "идентификационный"],
        keywords_en=["identity card", "national id", "identification"],
        tags=["intake", "basic_info", "document", "identity"],
    ),
    # === EDUCATION DOCUMENTS ===
    DocumentType(
        id="school_certificate",
        name_ru="Аттестат о среднем образовании",
        name_en="School Certificate",
        category=DocumentCategory.EDUCATION,
        linked_question_id="doc_school_certificate",
        keywords_ru=["аттестат", "среднее образование", "школа", "окончил"],
        keywords_en=["school certificate", "high school", "secondary education", "graduated"],
        tags=["intake", "school", "document", "education"],
    ),
    DocumentType(
        id="bachelor_diploma",
        name_ru="Диплом бакалавра",
        name_en="Bachelor's Degree",
        category=DocumentCategory.EDUCATION,
        linked_question_id="doc_diploma",
        keywords_ru=["диплом", "бакалавр", "высшее образование", "присвоена квалификация"],
        keywords_en=["diploma", "bachelor", "degree", "university", "conferred"],
        tags=["intake", "university", "document", "education"],
    ),
    DocumentType(
        id="master_diploma",
        name_ru="Диплом магистра",
        name_en="Master's Degree",
        category=DocumentCategory.EDUCATION,
        linked_question_id="doc_diploma",
        keywords_ru=["диплом", "магистр", "магистратура"],
        keywords_en=["master", "masters degree", "graduate"],
        tags=["intake", "university", "document", "education"],
    ),
    DocumentType(
        id="phd_diploma",
        name_ru="Диплом кандидата/доктора наук",
        name_en="PhD/Doctorate",
        category=DocumentCategory.EDUCATION,
        linked_question_id="doc_diploma",
        keywords_ru=["кандидат наук", "доктор наук", "диссертация", "ученая степень", "phd"],
        keywords_en=["phd", "doctorate", "doctor of philosophy", "dissertation"],
        tags=["intake", "university", "document", "education", "phd"],
    ),
    DocumentType(
        id="transcript",
        name_ru="Приложение к диплому / Транскрипт",
        name_en="Academic Transcript",
        category=DocumentCategory.EDUCATION,
        linked_question_id="doc_transcript",
        keywords_ru=["приложение к диплому", "транскрипт", "оценки", "зачетная книжка", "выписка"],
        keywords_en=["transcript", "academic record", "grades", "courses", "credits"],
        tags=["intake", "university", "document", "education"],
    ),
    # === EB-1A CRITERION 1: AWARDS ===
    DocumentType(
        id="award_certificate",
        name_ru="Награда / Премия",
        name_en="Award Certificate",
        category=DocumentCategory.EB1A_AWARDS,
        linked_question_id="doc_awards",
        keywords_ru=[
            "награда",
            "премия",
            "лауреат",
            "победитель",
            "грамота",
            "медаль",
            "диплом победителя",
        ],
        keywords_en=["award", "prize", "winner", "laureate", "medal", "honor", "recognition"],
        tags=["intake", "awards", "document", "achievements", "eb1a_criterion_1"],
        eb1a_criterion=1,
    ),
    DocumentType(
        id="competition_winner",
        name_ru="Диплом победителя конкурса",
        name_en="Competition Winner Certificate",
        category=DocumentCategory.EB1A_AWARDS,
        linked_question_id="doc_awards",
        keywords_ru=["конкурс", "соревнование", "олимпиада", "первое место", "призер"],
        keywords_en=["competition", "contest", "first place", "champion", "olympiad"],
        tags=["intake", "awards", "document", "achievements", "eb1a_criterion_1"],
        eb1a_criterion=1,
    ),
    # === EB-1A CRITERION 2: MEMBERSHIP ===
    DocumentType(
        id="membership_certificate",
        name_ru="Членство в организации",
        name_en="Membership Certificate",
        category=DocumentCategory.EB1A_MEMBERSHIP,
        linked_question_id=None,
        keywords_ru=["член", "членство", "ассоциация", "общество", "федерация", "союз"],
        keywords_en=["member", "membership", "association", "society", "federation", "fellow"],
        tags=["eb1a", "membership", "document", "eb1a_criterion_2"],
        eb1a_criterion=2,
    ),
    # === EB-1A CRITERION 3: PRESS ===
    DocumentType(
        id="press_article",
        name_ru="Статья в прессе",
        name_en="Press Article",
        category=DocumentCategory.EB1A_PRESS,
        linked_question_id=None,
        keywords_ru=["статья", "интервью", "газета", "журнал", "публикация в сми", "пресса"],
        keywords_en=["article", "interview", "newspaper", "magazine", "press", "media coverage"],
        tags=["eb1a", "press", "document", "eb1a_criterion_3"],
        eb1a_criterion=3,
    ),
    # === EB-1A CRITERION 4: JUDGING ===
    DocumentType(
        id="judging_evidence",
        name_ru="Участие в жюри / Рецензирование",
        name_en="Judging/Review Evidence",
        category=DocumentCategory.EB1A_JUDGING,
        linked_question_id=None,
        keywords_ru=["жюри", "рецензент", "эксперт", "оценка", "peer review", "редколлегия"],
        keywords_en=["judge", "jury", "reviewer", "peer review", "editorial board", "referee"],
        tags=["eb1a", "judging", "document", "eb1a_criterion_4"],
        eb1a_criterion=4,
    ),
    # === EB-1A CRITERION 5: ORIGINAL CONTRIBUTION ===
    DocumentType(
        id="patent",
        name_ru="Патент",
        name_en="Patent",
        category=DocumentCategory.EB1A_CONTRIBUTION,
        linked_question_id="doc_patents",
        keywords_ru=["патент", "изобретение", "полезная модель", "авторское свидетельство"],
        keywords_en=["patent", "invention", "utility model", "intellectual property"],
        tags=["intake", "projects_research", "document", "patents", "eb1a_criterion_5"],
        eb1a_criterion=5,
    ),
    DocumentType(
        id="invention_certificate",
        name_ru="Свидетельство об изобретении",
        name_en="Invention Certificate",
        category=DocumentCategory.EB1A_CONTRIBUTION,
        linked_question_id="doc_patents",
        keywords_ru=["изобретение", "инновация", "разработка", "внедрение"],
        keywords_en=["invention", "innovation", "development", "implementation"],
        tags=["eb1a", "contribution", "document", "eb1a_criterion_5"],
        eb1a_criterion=5,
    ),
    # === EB-1A CRITERION 6: SCHOLARLY ARTICLES ===
    DocumentType(
        id="publication",
        name_ru="Научная публикация",
        name_en="Scientific Publication",
        category=DocumentCategory.EB1A_SCHOLARLY,
        linked_question_id="doc_publications",
        keywords_ru=["статья", "публикация", "журнал", "научный", "исследование", "doi"],
        keywords_en=["article", "publication", "journal", "scientific", "research", "doi", "paper"],
        tags=["intake", "projects_research", "document", "publications", "eb1a_criterion_6"],
        eb1a_criterion=6,
    ),
    DocumentType(
        id="citation_report",
        name_ru="Отчет о цитированиях",
        name_en="Citation Report",
        category=DocumentCategory.EB1A_SCHOLARLY,
        linked_question_id="doc_citations",
        keywords_ru=[
            "цитирование",
            "google scholar",
            "scopus",
            "web of science",
            "h-index",
            "индекс хирша",
        ],
        keywords_en=[
            "citation",
            "google scholar",
            "scopus",
            "web of science",
            "h-index",
            "cited by",
        ],
        tags=["intake", "projects_research", "document", "citations", "eb1a_criterion_6"],
        eb1a_criterion=6,
    ),
    # === EB-1A CRITERION 7: EXHIBITION ===
    DocumentType(
        id="exhibition_catalog",
        name_ru="Каталог выставки",
        name_en="Exhibition Catalog",
        category=DocumentCategory.EB1A_EXHIBITION,
        linked_question_id=None,
        keywords_ru=["выставка", "экспозиция", "галерея", "каталог", "музей"],
        keywords_en=["exhibition", "gallery", "museum", "catalog", "showcase"],
        tags=["eb1a", "exhibition", "document", "eb1a_criterion_7"],
        eb1a_criterion=7,
    ),
    # === EB-1A CRITERION 8: LEADERSHIP ===
    DocumentType(
        id="leadership_evidence",
        name_ru="Подтверждение руководящей роли",
        name_en="Leadership Evidence",
        category=DocumentCategory.EB1A_LEADERSHIP,
        linked_question_id=None,
        keywords_ru=[
            "директор",
            "руководитель",
            "начальник",
            "ceo",
            "cto",
            "founder",
            "основатель",
        ],
        keywords_en=["director", "manager", "head", "ceo", "cto", "founder", "lead", "chief"],
        tags=["eb1a", "leadership", "document", "eb1a_criterion_8"],
        eb1a_criterion=8,
    ),
    # === EB-1A CRITERION 9: HIGH SALARY ===
    DocumentType(
        id="salary_document",
        name_ru="Документ о зарплате",
        name_en="Salary Document",
        category=DocumentCategory.EB1A_SALARY,
        linked_question_id="doc_salary",
        keywords_ru=["зарплата", "оклад", "доход", "налоговая декларация", "справка 2-ндфл"],
        keywords_en=["salary", "income", "wage", "tax return", "pay stub", "compensation"],
        tags=["intake", "compensation", "document", "eb1a_criterion_9"],
        eb1a_criterion=9,
    ),
    DocumentType(
        id="offer_letter",
        name_ru="Офер / Предложение о работе",
        name_en="Job Offer Letter",
        category=DocumentCategory.EB1A_SALARY,
        linked_question_id="doc_salary",
        keywords_ru=["офер", "предложение о работе", "трудовой договор", "условия труда"],
        keywords_en=["offer letter", "job offer", "employment offer", "compensation package"],
        tags=["intake", "compensation", "document", "eb1a_criterion_9", "career"],
        eb1a_criterion=9,
    ),
    # === EB-1A CRITERION 10: COMMERCIAL SUCCESS ===
    DocumentType(
        id="commercial_success",
        name_ru="Коммерческий успех",
        name_en="Commercial Success Evidence",
        category=DocumentCategory.EB1A_COMMERCIAL,
        linked_question_id=None,
        keywords_ru=["продажи", "выручка", "доход", "box office", "тираж"],
        keywords_en=["sales", "revenue", "box office", "commercial", "bestseller"],
        tags=["eb1a", "commercial", "document", "eb1a_criterion_10"],
        eb1a_criterion=10,
    ),
    # === CAREER / EMPLOYMENT ===
    DocumentType(
        id="employment_contract",
        name_ru="Трудовой договор",
        name_en="Employment Contract",
        category=DocumentCategory.CAREER_EMPLOYMENT,
        linked_question_id=None,
        keywords_ru=["трудовой договор", "контракт", "работодатель", "работник", "должность"],
        keywords_en=["employment contract", "agreement", "employer", "employee", "position"],
        tags=["career", "employment", "document"],
    ),
    DocumentType(
        id="work_reference",
        name_ru="Рекомендация от работодателя",
        name_en="Employment Reference",
        category=DocumentCategory.CAREER_RECOMMENDATION,
        linked_question_id=None,
        keywords_ru=["рекомендация", "характеристика", "отзыв", "работал в должности"],
        keywords_en=["reference", "recommendation", "employed as", "worked as"],
        tags=["career", "recommendation", "document"],
    ),
    # === RECOMMENDATION LETTERS ===
    DocumentType(
        id="recommendation_letter",
        name_ru="Рекомендательное письмо",
        name_en="Recommendation Letter",
        category=DocumentCategory.RECOMMENDATION_LETTER,
        linked_question_id=None,
        keywords_ru=[
            "рекомендательное письмо",
            "рекомендую",
            "to whom it may concern",
            "подтверждаю",
            "эксперт",
        ],
        keywords_en=[
            "recommendation letter",
            "letter of recommendation",
            "to whom it may concern",
            "i recommend",
            "expert",
        ],
        tags=["recommendation", "letter", "document", "eb1a"],
    ),
]

# Create lookup dictionaries
DOCUMENT_TYPES_BY_ID: dict[str, DocumentType] = {dt.id: dt for dt in DOCUMENT_TYPES}
DOCUMENT_TYPES_BY_QUESTION_ID: dict[str, DocumentType] = {
    dt.linked_question_id: dt for dt in DOCUMENT_TYPES if dt.linked_question_id
}


@dataclass
class ClassificationResult:
    """Result of document classification."""

    document_type: DocumentType
    confidence: float  # 0.0 to 1.0
    matched_keywords: list[str]
    ocr_snippet: str  # First 500 chars of OCR text
    suggested_tags: list[str]
    eb1a_criterion: int | None


class DocumentClassifier:
    """
    Classifies documents using OCR text and optional LLM enhancement.

    Classification flow:
    1. Keyword matching against OCR text (fast, no API calls)
    2. If confidence < threshold, use LLM for better classification
    3. Return classification with confidence score
    """

    def __init__(self, llm_client: Any | None = None, confidence_threshold: float = 0.6):
        """Initialize classifier.

        Args:
            llm_client: Optional LLM client for enhanced classification
            confidence_threshold: Minimum confidence for keyword-only classification
        """
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold

    def classify_by_keywords(self, ocr_text: str) -> ClassificationResult | None:
        """
        Classify document using keyword matching only.

        Args:
            ocr_text: Extracted text from document (OCR)

        Returns:
            ClassificationResult or None if no match
        """
        if not ocr_text or len(ocr_text.strip()) < 10:
            return None

        ocr_lower = ocr_text.lower()
        best_match: DocumentType | None = None
        best_score = 0.0
        best_keywords: list[str] = []

        for doc_type in DOCUMENT_TYPES:
            matched = []
            # Check Russian keywords
            for kw in doc_type.keywords_ru:
                if kw.lower() in ocr_lower:
                    matched.append(kw)
            # Check English keywords
            for kw in doc_type.keywords_en:
                if kw.lower() in ocr_lower:
                    matched.append(kw)

            if matched:
                # Score based on number of matched keywords and their specificity
                total_keywords = len(doc_type.keywords_ru) + len(doc_type.keywords_en)
                score = len(matched) / total_keywords if total_keywords > 0 else 0

                # Boost score for more specific matches
                if len(matched) >= 3:
                    score = min(1.0, score * 1.5)

                if score > best_score:
                    best_score = score
                    best_match = doc_type
                    best_keywords = matched

        if best_match and best_score > 0.1:  # Minimum threshold for any match
            return ClassificationResult(
                document_type=best_match,
                confidence=min(1.0, best_score),
                matched_keywords=best_keywords,
                ocr_snippet=ocr_text[:500],
                suggested_tags=best_match.tags,
                eb1a_criterion=best_match.eb1a_criterion,
            )

        return None

    async def classify_with_llm(self, ocr_text: str) -> ClassificationResult | None:
        """
        Classify document using LLM for better accuracy.

        Args:
            ocr_text: Extracted text from document

        Returns:
            ClassificationResult or None
        """
        if not self.llm_client:
            return None

        # Build document type options for LLM
        options = []
        for dt in DOCUMENT_TYPES:
            options.append(f"- {dt.id}: {dt.name_ru} / {dt.name_en}")

        options_text = "\n".join(options)

        prompt = f"""Classify the following document based on its OCR text.

Available document types:
{options_text}

OCR Text (first 2000 chars):
{ocr_text[:2000]}

Respond with ONLY the document type ID (e.g., "passport", "birth_certificate", "publication").
If uncertain, respond with "other".
"""

        try:
            # Add timeout for LLM classification
            response = await asyncio.wait_for(
                self.llm_client.achat(prompt),
                timeout=LLM_CLASSIFICATION_TIMEOUT,
            )
            doc_type_id = response.strip().lower().replace('"', "").replace("'", "")

            # Find matching document type
            if doc_type_id in DOCUMENT_TYPES_BY_ID:
                doc_type = DOCUMENT_TYPES_BY_ID[doc_type_id]
                return ClassificationResult(
                    document_type=doc_type,
                    confidence=0.85,  # LLM classification confidence
                    matched_keywords=["llm_classification"],
                    ocr_snippet=ocr_text[:500],
                    suggested_tags=doc_type.tags,
                    eb1a_criterion=doc_type.eb1a_criterion,
                )
        except asyncio.TimeoutError:
            logger.warning(
                "document_classifier.llm_timeout",
                timeout_seconds=LLM_CLASSIFICATION_TIMEOUT,
            )
        except Exception as e:
            logger.warning("document_classifier.llm_failed", error=str(e))

        return None

    async def classify(self, ocr_text: str, use_llm_fallback: bool = True) -> ClassificationResult:
        """
        Classify document using keywords first, then LLM if needed.

        Args:
            ocr_text: Extracted text from document
            use_llm_fallback: Whether to use LLM if keyword confidence is low

        Returns:
            ClassificationResult (always returns something, even if "other")
        """
        # Try keyword classification first
        keyword_result = self.classify_by_keywords(ocr_text)

        if keyword_result and keyword_result.confidence >= self.confidence_threshold:
            logger.info(
                "document_classifier.keyword_match",
                doc_type=keyword_result.document_type.id,
                confidence=keyword_result.confidence,
                keywords=keyword_result.matched_keywords,
            )
            return keyword_result

        # Try LLM classification if available and needed
        if use_llm_fallback and self.llm_client:
            llm_result = await self.classify_with_llm(ocr_text)
            if llm_result:
                logger.info(
                    "document_classifier.llm_match",
                    doc_type=llm_result.document_type.id,
                    confidence=llm_result.confidence,
                )
                return llm_result

        # Return keyword result with low confidence, or "other"
        if keyword_result:
            return keyword_result

        # Fallback to "other"
        other_type = DocumentType(
            id="other",
            name_ru="Другой документ",
            name_en="Other Document",
            category=DocumentCategory.OTHER,
            linked_question_id=None,
            keywords_ru=[],
            keywords_en=[],
            tags=["document", "unclassified"],
        )

        return ClassificationResult(
            document_type=other_type,
            confidence=0.0,
            matched_keywords=[],
            ocr_snippet=ocr_text[:500] if ocr_text else "",
            suggested_tags=["document", "unclassified"],
            eb1a_criterion=None,
        )


# Global classifier instance
_classifier: DocumentClassifier | None = None


def get_document_classifier(llm_client: Any | None = None) -> DocumentClassifier:
    """Get or create global document classifier."""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier(llm_client=llm_client)
    return _classifier


def get_document_types_for_category(category: DocumentCategory) -> list[DocumentType]:
    """Get all document types for a specific category."""
    return [dt for dt in DOCUMENT_TYPES if dt.category == category]


def get_document_types_for_criterion(criterion: int) -> list[DocumentType]:
    """Get all document types for a specific EB-1A criterion."""
    return [dt for dt in DOCUMENT_TYPES if dt.eb1a_criterion == criterion]
