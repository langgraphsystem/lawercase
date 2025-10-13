"""
EB-1A Document Models and Templates

Типы документов для EB-1A петиции:
1. Recommendation Letters (Рекомендательные письма)
2. Evidence Letters (Письма-доказательства)
3. Cover Letter (Сопроводительное письмо)
4. Form I-140 (Иммиграционная форма)
5. Publications List (Список публикаций)
6. Awards Documentation (Документация наград)
7. Media Coverage (Покрытие в СМИ)
8. Employment Verification (Подтверждение работы)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .eb1_models import EB1Criterion


class EB1DocumentType(str, Enum):
    """Типы документов для EB-1A"""

    # Основные документы
    FORM_I140 = "form_i140"  # Иммиграционная форма I-140
    COVER_LETTER = "cover_letter"  # Сопроводительное письмо
    RECOMMENDATION_LETTER = "recommendation_letter"  # Рекомендательное письмо

    # Доказательства по критериям
    AWARDS_DOCUMENTATION = "awards_documentation"  # Документация наград
    MEMBERSHIP_PROOF = "membership_proof"  # Доказательство членства
    PRESS_COVERAGE = "press_coverage"  # Покрытие в прессе
    JUDGING_EVIDENCE = "judging_evidence"  # Доказательства судейства
    CONTRIBUTION_LETTER = "contribution_letter"  # Письмо о вкладе
    PUBLICATIONS_LIST = "publications_list"  # Список публикаций
    EXHIBITION_CATALOG = "exhibition_catalog"  # Каталог выставки
    LEADERSHIP_VERIFICATION = "leadership_verification"  # Подтверждение лидерства
    SALARY_VERIFICATION = "salary_verification"  # Подтверждение зарплаты
    COMMERCIAL_SUCCESS = "commercial_success"  # Коммерческий успех

    # Вспомогательные документы
    CV_RESUME = "cv_resume"  # Резюме
    EMPLOYMENT_LETTER = "employment_letter"  # Письмо от работодателя
    EXPERT_OPINION = "expert_opinion"  # Экспертное мнение
    CITATION_REPORT = "citation_report"  # Отчет о цитированиях


class EB1DocumentStatus(str, Enum):
    """Статусы документов"""

    DRAFT = "draft"  # Черновик
    PENDING_REVIEW = "pending_review"  # Ожидает проверки
    APPROVED = "approved"  # Одобрен
    NEEDS_REVISION = "needs_revision"  # Требует правок
    FINALIZED = "finalized"  # Финализирован


class RecommendationLetterData(BaseModel):
    """Данные для генерации рекомендательного письма"""

    # Информация о рекомендателе
    recommender_name: str = Field(..., description="Имя рекомендателя")
    recommender_title: str = Field(..., description="Должность рекомендателя")
    recommender_organization: str = Field(..., description="Организация рекомендателя")
    recommender_credentials: str = Field(..., description="Регалии рекомендателя")
    recommender_relationship: str = Field(
        ..., description="Отношения с кандидатом (коллега, научный руководитель, и т.д.)"
    )
    years_known: int = Field(..., description="Сколько лет знает кандидата")

    # Информация о кандидате
    candidate_name: str = Field(..., description="Имя кандидата")
    candidate_field: str = Field(..., description="Область деятельности кандидата")

    # Критерии, которые письмо должно подтверждать
    supporting_criteria: list[EB1Criterion] = Field(
        ..., description="Критерии EB-1A, которые подтверждает это письмо"
    )

    # Конкретные достижения для упоминания
    specific_achievements: list[str] = Field(
        default_factory=list, description="Конкретные достижения для упоминания"
    )

    # Ключевые слова для каждого критерия (важно для USCIS!)
    keywords_for_criteria: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Ключевые слова для каждого критерия (например, 'extraordinary', 'sustained acclaim')",
    )

    # Примеры работы вместе
    collaboration_examples: list[str] = Field(
        default_factory=list, description="Примеры совместной работы"
    )

    # Влияние работы кандидата
    impact_statements: list[str] = Field(
        default_factory=list, description="Утверждения о влиянии работы кандидата"
    )

    # Дополнительные детали
    tone: str = Field(
        default="professional", description="Тон письма: professional/academic/personal"
    )


class UploadedDocument(BaseModel):
    """Загруженный документ пользователя (PDF, изображение)"""

    document_id: str = Field(..., description="ID документа")
    file_path: str = Field(..., description="Путь к файлу")
    file_type: str = Field(..., description="Тип файла (pdf, png, jpg)")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Извлеченные данные (после OCR)
    extracted_text: str | None = Field(default=None, description="Извлеченный текст")
    extracted_data: dict[str, Any] | None = Field(
        default=None, description="Структурированные данные"
    )

    # Классификация документа
    detected_type: EB1DocumentType | None = Field(default=None, description="Определенный тип")
    detected_criteria: list[EB1Criterion] = Field(
        default_factory=list, description="Определенные критерии"
    )

    # Метаданные
    language: str = Field(default="en", description="Язык документа")
    confidence_score: float = Field(default=0.0, description="Уверенность в извлечении")


class GeneratedDocument(BaseModel):
    """Сгенерированный документ"""

    document_id: str = Field(..., description="ID документа")
    petition_id: str = Field(..., description="ID петиции")
    document_type: EB1DocumentType = Field(..., description="Тип документа")
    status: EB1DocumentStatus = Field(default=EB1DocumentStatus.DRAFT)

    # Содержимое
    content: str = Field(..., description="Текстовое содержимое документа")
    formatted_content: str | None = Field(
        default=None, description="Форматированное содержимое (HTML/Markdown)"
    )

    # Критерии, которые подтверждает документ
    supporting_criteria: list[EB1Criterion] = Field(
        default_factory=list, description="Подтверждаемые критерии"
    )

    # Метаданные генерации
    template_used: str | None = Field(default=None, description="Использованный шаблон")
    generation_prompt: str | None = Field(default=None, description="Промпт для генерации")
    llm_model: str = Field(default="claude-3-5-sonnet", description="Использованная LLM")

    # Версионирование
    version: int = Field(default=1, description="Версия документа")
    revision_notes: list[str] = Field(default_factory=list, description="Заметки о правках")

    # Временные метки
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    finalized_at: datetime | None = Field(default=None)


# ========== ШАБЛОНЫ И КЛЮЧЕВЫЕ СЛОВА ==========

# Ключевые фразы USCIS для каждого критерия (важно для одобрения!)
USCIS_KEYWORDS_BY_CRITERION = {
    EB1Criterion.AWARDS: [
        "nationally recognized",
        "internationally recognized",
        "prestigious award",
        "outstanding achievement",
        "excellence in the field",
        "significant recognition",
    ],
    EB1Criterion.MEMBERSHIP: [
        "exclusive membership",
        "outstanding achievements required",
        "judged by experts",
        "selective association",
        "peer-reviewed admission",
    ],
    EB1Criterion.PRESS: [
        "major media",
        "professional publications",
        "widespread recognition",
        "featured in",
        "significant press coverage",
    ],
    EB1Criterion.JUDGING: [
        "peer reviewer",
        "evaluation of work",
        "manuscript reviewer",
        "grant reviewer",
        "expert judge",
        "critical evaluation",
    ],
    EB1Criterion.CONTRIBUTION: [
        "original contribution",
        "major significance",
        "groundbreaking work",
        "innovative approach",
        "paradigm shift",
        "substantial impact",
        "widely adopted",
    ],
    EB1Criterion.SCHOLARLY: [
        "peer-reviewed publications",
        "scholarly articles",
        "highly cited",
        "influential research",
        "seminal work",
    ],
    EB1Criterion.EXHIBITION: [
        "artistic exhibition",
        "showcase of work",
        "public display",
        "gallery presentation",
    ],
    EB1Criterion.LEADERSHIP: [
        "critical role",
        "leading position",
        "distinguished organization",
        "executive capacity",
        "pivotal contribution",
    ],
    EB1Criterion.SALARY: [
        "high remuneration",
        "top percentile",
        "substantially higher",
        "commanding salary",
        "premium compensation",
    ],
    EB1Criterion.COMMERCIAL: [
        "commercial success",
        "box office",
        "record sales",
        "financial achievement",
    ],
}


# Шаблон рекомендательного письма
RECOMMENDATION_LETTER_TEMPLATE = """
[Letterhead of Recommender's Organization]

{date}

U.S. Citizenship and Immigration Services
{uscis_office_address}

RE: I-140 Petition for {candidate_name} - Letter of Recommendation

Dear USCIS Officer,

I am writing this letter in strong support of the I-140 immigrant petition for {candidate_name},
who is seeking classification under the EB-1A category for individuals with extraordinary ability
in {field_of_expertise}.

ABOUT THE RECOMMENDER:
I am {recommender_name}, {recommender_title} at {recommender_organization}. {recommender_credentials}
I have known {candidate_name} for {years_known} years in my capacity as {relationship}.

{criterion_section_1}

{criterion_section_2}

{criterion_section_3}

IMPACT AND RECOGNITION:
{impact_statements}

CONCLUSION:
In my professional opinion, {candidate_name} has demonstrated sustained national and international
acclaim and recognition for achievements in {field_of_expertise}. The contributions made by
{candidate_name} are of major significance to the field and have been widely recognized by peers
and experts.

I strongly recommend approval of this petition. {candidate_name} clearly meets the criteria for
classification as an individual with extraordinary ability.

If you require any additional information, please do not hesitate to contact me.

Sincerely,

{recommender_name}
{recommender_title}
{recommender_organization}
{recommender_contact}
"""


# Шаблон Cover Letter для петиции
COVER_LETTER_TEMPLATE = """
[Petitioner's Letterhead]

{date}

U.S. Citizenship and Immigration Services
{uscis_service_center}

RE: Form I-140 Immigrant Petition for Alien Worker
    Petitioner: {petitioner_name}
    Beneficiary: {candidate_name}
    Classification: EB-1A - Alien of Extraordinary Ability

Dear USCIS Officer,

INTRODUCTION
{petitioner_name} hereby submits this Form I-140, Immigrant Petition for Alien Worker, on behalf
of {candidate_name}, seeking classification as an individual with extraordinary ability in
{field_of_expertise} under Section 203(b)(1)(A) of the Immigration and Nationality Act.

OVERVIEW OF BENEFICIARY'S QUALIFICATIONS
{candidate_name} is an internationally recognized expert in {field_of_expertise} with over
{years_of_experience} years of experience. The beneficiary has made original contributions of
major significance to the field and has received sustained national and international acclaim.

EVIDENCE OF EXTRAORDINARY ABILITY
This petition demonstrates that {candidate_name} meets at least three of the regulatory criteria
set forth in 8 CFR 204.5(h)(3). Specifically, the evidence submitted proves:

{criteria_list}

ORGANIZATION OF SUPPORTING DOCUMENTS
This petition includes the following exhibits:

{exhibit_list}

CONCLUSION
Based on the overwhelming evidence presented, it is clear that {candidate_name} possesses
extraordinary ability in {field_of_expertise} and has risen to the very top of the field.
We respectfully request that USCIS approve this petition.

If you have any questions or require additional information, please contact the undersigned.

Respectfully submitted,

{petitioner_signature}
{petitioner_name}
{petitioner_title}
"""


# Структура для каждого критерия в рекомендательном письме
CRITERION_SECTION_TEMPLATES = {
    EB1Criterion.AWARDS: """
RECOGNITION THROUGH AWARDS ({criterion_name}):
{candidate_name} has received numerous nationally and internationally recognized awards for
outstanding achievements in {field}. Most notably, {specific_awards}. These prestigious awards
are given only to individuals who have demonstrated excellence in the field and are highly
competitive. The receipt of these honors confirms {candidate_name}'s extraordinary ability
and sustained acclaim.
""",
    EB1Criterion.MEMBERSHIP: """
MEMBERSHIP IN DISTINGUISHED ASSOCIATIONS ({criterion_name}):
{candidate_name} holds membership in highly selective professional associations that require
outstanding achievements as judged by recognized experts. These include {memberships}.
Admission to these organizations is granted only to individuals who have demonstrated exceptional
accomplishments and are recognized by their peers as leaders in the field.
""",
    EB1Criterion.PRESS: """
PUBLISHED MATERIAL IN PROFESSIONAL OR MAJOR TRADE PUBLICATIONS ({criterion_name}):
{candidate_name}'s work has been featured extensively in major media and professional publications,
demonstrating widespread recognition. Notable coverage includes {press_examples}. This significant
press coverage in respected outlets confirms the impact and importance of {candidate_name}'s
contributions to the field.
""",
    EB1Criterion.JUDGING: """
PARTICIPATION AS A JUDGE OF THE WORK OF OTHERS ({criterion_name}):
{candidate_name} has served as a peer reviewer and judge of the work of others in the field,
which is a clear indication of expert status. Specifically, {candidate_name} has {judging_examples}.
This critical evaluation role is entrusted only to recognized experts and demonstrates
{candidate_name}'s standing in the professional community.
""",
    EB1Criterion.CONTRIBUTION: """
ORIGINAL CONTRIBUTIONS OF MAJOR SIGNIFICANCE ({criterion_name}):
{candidate_name} has made original contributions of major significance to the field of {field}.
Most notably, {contribution_details}. This groundbreaking work has been widely adopted and has
had a substantial impact on the field. The innovative nature and significance of these contributions
demonstrate extraordinary ability.
""",
    EB1Criterion.SCHOLARLY: """
SCHOLARLY ARTICLES AND PUBLICATIONS ({criterion_name}):
{candidate_name} is the author of numerous scholarly articles published in peer-reviewed journals
and presented at professional conferences. With {publication_count} publications and over
{citation_count} citations, {candidate_name}'s research has been highly influential. Key publications
include {key_publications}. The high citation rate and publication in top-tier venues demonstrate
the impact and recognition of {candidate_name}'s scholarly work.
""",
    EB1Criterion.LEADERSHIP: """
LEADERSHIP ROLE IN DISTINGUISHED ORGANIZATIONS ({criterion_name}):
{candidate_name} has played a critical and leading role in organizations with distinguished
reputations. Specifically, {leadership_roles}. In these positions, {candidate_name} has made
pivotal contributions to the organization's mission and has been instrumental in {achievements}.
This leadership role in respected organizations evidences extraordinary ability.
""",
    EB1Criterion.SALARY: """
HIGH REMUNERATION ({criterion_name}):
{candidate_name} commands a salary that is substantially higher than others in the field.
With an annual compensation of ${salary_amount}, {candidate_name} is in the top percentile
of professionals in {field}. This high remuneration, which significantly exceeds the national
average for the field, reflects the extraordinary value and recognition of {candidate_name}'s abilities.
""",
}
