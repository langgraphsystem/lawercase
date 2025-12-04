"""
Dynamic career intake module for detailed company-by-company questioning.

Collects comprehensive career information for each employer:
- Company details and industry
- Positions and responsibilities
- Projects and achievements
- Colleagues and recommenders
- Evidence and documentation

Uses LLM to generate contextual follow-up questions based on:
- Company type (private/government/NGO)
- Industry sector
- User's role and responsibilities
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CompanyType(str, Enum):
    """Type of organization."""

    PRIVATE = "private"  # Частная компания
    GOVERNMENT = "government"  # Государственная служба
    NGO = "ngo"  # НКО / общественная организация
    STARTUP = "startup"  # Стартап
    ACADEMIC = "academic"  # Академическая / научная организация
    INTERNATIONAL = "international"  # Международная организация
    OTHER = "other"


class PositionEntry(BaseModel):
    """Single position held at a company."""

    title: str = Field(description="Название должности")
    start_date: str | None = Field(default=None, description="Дата начала (ГГГГ-ММ)")
    end_date: str | None = Field(default=None, description="Дата окончания (ГГГГ-ММ или 'по н.в.')")
    responsibilities: list[str] = Field(default_factory=list, description="Обязанности")
    achievements: list[str] = Field(default_factory=list, description="Достижения на этой позиции")


class ProjectEntry(BaseModel):
    """Project or significant work at a company."""

    name: str = Field(description="Название проекта/работы")
    description: str = Field(description="Описание проекта")
    role: str = Field(description="Роль пользователя в проекте")
    impact: str | None = Field(default=None, description="Влияние/результат проекта")
    colleagues: list[str] = Field(default_factory=list, description="Коллеги по проекту")
    evidence: list[str] = Field(
        default_factory=list, description="Доказательства (документы, ссылки)"
    )


class AchievementEntry(BaseModel):
    """Significant achievement at a company."""

    description: str = Field(description="Описание достижения")
    category: str = Field(
        description="Категория: profit/efficiency/legislation/award/innovation/other"
    )
    impact: str | None = Field(default=None, description="Измеримое влияние")
    evidence: list[str] = Field(default_factory=list, description="Доказательства")
    date: str | None = Field(default=None, description="Дата достижения")


class RecommenderEntry(BaseModel):
    """Potential recommender from a company."""

    name: str = Field(description="ФИО")
    position: str = Field(description="Должность")
    relationship: str = Field(description="Как знакомы (руководитель, коллега, клиент)")
    context: str = Field(description="Контекст совместной работы")
    contact: str | None = Field(default=None, description="Контактные данные (если есть)")
    can_confirm: list[str] = Field(
        default_factory=list, description="Что может подтвердить этот человек"
    )


class CareerEntry(BaseModel):
    """Complete information about one employer/company."""

    # Basic company info
    company_name: str = Field(description="Название компании/организации")
    company_type: CompanyType = Field(default=CompanyType.PRIVATE, description="Тип организации")
    company_industry: str = Field(description="Сфера деятельности компании")
    company_description: str | None = Field(default=None, description="Краткое описание компании")
    company_size: str | None = Field(
        default=None, description="Размер компании (кол-во сотрудников)"
    )
    company_location: str = Field(description="Город, страна")

    # Employment period
    start_date: str = Field(description="Дата начала работы (ГГГГ-ММ)")
    end_date: str | None = Field(
        default=None, description="Дата окончания (ГГГГ-ММ или None если текущая)"
    )
    is_current: bool = Field(default=False, description="Текущее место работы")

    # Positions (can be multiple if promoted)
    positions: list[PositionEntry] = Field(
        default_factory=list, description="Должности в этой компании"
    )

    # Projects and work
    projects: list[ProjectEntry] = Field(
        default_factory=list, description="Проекты и значимые работы"
    )

    # Achievements
    achievements: list[AchievementEntry] = Field(
        default_factory=list, description="Достижения в этой компании"
    )

    # Recommenders
    recommenders: list[RecommenderEntry] = Field(
        default_factory=list, description="Потенциальные рекомендатели"
    )

    # Government-specific (if applicable)
    government_level: str | None = Field(
        default=None, description="Уровень (федеральный, региональный, муниципальный)"
    )
    legislation_involvement: list[str] = Field(
        default_factory=list, description="Участие в разработке законодательства"
    )

    # Evidence
    documents: list[str] = Field(
        default_factory=list, description="Загруженные документы (file_ids)"
    )

    # Metadata
    eb1a_relevance: list[str] = Field(
        default_factory=list, description="Релевантные критерии EB-1A"
    )


class CareerIntakeState(BaseModel):
    """State for career intake conversation."""

    user_id: str
    case_id: str

    # Total companies count
    total_companies: int = Field(default=0, description="Общее количество мест работы")

    # Current company being discussed
    current_company_index: int = Field(default=0, description="Индекс текущей компании (0-based)")

    # All collected career entries
    career_entries: list[CareerEntry] = Field(
        default_factory=list, description="Собранная информация о компаниях"
    )

    # Current entry being built (before it's finalized)
    current_entry: dict[str, Any] = Field(
        default_factory=dict, description="Текущая запись в процессе заполнения"
    )

    # Current phase within company intake
    current_phase: str = Field(
        default="company_basics",
        description="Текущая фаза: company_basics, positions, projects, achievements, recommenders, evidence",
    )

    # Generated follow-up questions queue
    pending_questions: list[str] = Field(
        default_factory=list, description="Очередь сгенерированных вопросов"
    )

    # Completed
    is_complete: bool = Field(default=False, description="Завершён ли опрос по карьере")


# Base questions for each phase (before dynamic generation)
CAREER_PHASE_QUESTIONS = {
    "company_count": [
        {
            "id": "total_companies",
            "text": "Сколько компаний/организаций было в вашей карьере? (Начиная с первой работы)",
            "hint": "Укажите число. Мы пройдём по каждой компании отдельно.",
            "type": "number",
        }
    ],
    "company_basics": [
        {
            "id": "company_name",
            "text": "Название компании/организации #{index}:",
            "hint": "Полное официальное название",
            "type": "text",
        },
        {
            "id": "company_type",
            "text": "Тип организации:",
            "options": [
                "Частная компания",
                "Государственная служба",
                "НКО / общественная организация",
                "Стартап",
                "Академическая / научная организация",
                "Международная организация",
                "Другое",
            ],
            "type": "select",
        },
        {
            "id": "company_industry",
            "text": "Сфера деятельности компании:",
            "hint": "Например: IT, финансы, здравоохранение, юриспруденция, госуправление",
            "type": "text",
        },
        {
            "id": "company_description",
            "text": "Кратко опишите, чем занимается эта компания:",
            "hint": "2-3 предложения о деятельности компании",
            "type": "text",
        },
        {
            "id": "company_location",
            "text": "Где расположена компания? (Город, страна)",
            "type": "text",
        },
        {
            "id": "employment_period",
            "text": "Когда вы там работали? (с - по)",
            "hint": "Например: 2015-03 - 2018-06 или 2020-01 - по настоящее время",
            "type": "text",
        },
    ],
    "positions": [
        {
            "id": "positions_list",
            "text": "Какие должности вы занимали в {company_name}?",
            "hint": "Перечислите все должности, если были повышения. Например: Junior Developer (2015-2016), Senior Developer (2016-2018)",
            "type": "text",
        },
        {
            "id": "main_responsibilities",
            "text": "Опишите ваши основные обязанности на последней должности:",
            "hint": "Перечислите 3-5 ключевых обязанностей",
            "type": "text",
        },
        {
            "id": "team_management",
            "text": "Руководили ли вы командой или подразделением?",
            "hint": "Если да, укажите размер команды и зону ответственности",
            "type": "text",
        },
    ],
    "projects": [
        {
            "id": "has_projects",
            "text": "Были ли значимые проекты или инициативы, в которых вы участвовали в {company_name}?",
            "type": "yes_no",
        },
        {
            "id": "project_name",
            "text": "Название проекта/инициативы:",
            "type": "text",
            "condition": {"depends_on": "has_projects", "value": True},
        },
        {
            "id": "project_description",
            "text": "Опишите проект и вашу роль в нём:",
            "hint": "Что это был за проект? Какой была ваша роль? Каков результат?",
            "type": "text",
            "condition": {"depends_on": "has_projects", "value": True},
        },
        {
            "id": "project_impact",
            "text": "Какое влияние оказал этот проект?",
            "hint": "Измеримые результаты: экономия, прибыль, улучшение показателей, охват пользователей",
            "type": "text",
            "condition": {"depends_on": "has_projects", "value": True},
        },
        {
            "id": "more_projects",
            "text": "Есть ли ещё проекты, которые стоит упомянуть?",
            "type": "yes_no",
            "condition": {"depends_on": "has_projects", "value": True},
        },
    ],
    "achievements": [
        {
            "id": "significant_achievements",
            "text": "Какие значимые достижения были у вас в {company_name}?",
            "hint": "Например: повышение прибыли, оптимизация процессов, награды, признание, инновации",
            "type": "text",
        },
        {
            "id": "measurable_impact",
            "text": "Можете ли вы указать измеримые результаты?",
            "hint": "Цифры, проценты, суммы. Например: 'увеличил продажи на 30%', 'сэкономил $500K'",
            "type": "text",
        },
        {
            "id": "awards_recognition",
            "text": "Получали ли вы награды или признание в этой компании?",
            "hint": "Премии, благодарности, звания 'лучший сотрудник' и т.д.",
            "type": "text",
        },
    ],
    "achievements_government": [
        {
            "id": "legislation_work",
            "text": "Участвовали ли вы в разработке законодательства или нормативных актов?",
            "type": "yes_no",
        },
        {
            "id": "legislation_details",
            "text": "Опишите вашу роль в разработке законодательства:",
            "hint": "Какие законы/акты? Какова была ваша роль? Какой результат?",
            "type": "text",
            "condition": {"depends_on": "legislation_work", "value": True},
        },
        {
            "id": "legislation_impact",
            "text": "Какое влияние оказали эти изменения?",
            "hint": "На кого повлияло? Какой масштаб? Есть ли публикации/ссылки?",
            "type": "text",
            "condition": {"depends_on": "legislation_work", "value": True},
        },
        {
            "id": "policy_decisions",
            "text": "Принимали ли вы значимые решения, влияющие на политику или практику?",
            "type": "text",
        },
    ],
    "recommenders": [
        {
            "id": "has_recommenders",
            "text": "Есть ли люди из {company_name}, которые могли бы дать вам рекомендацию?",
            "hint": "Руководители, коллеги, клиенты, партнёры",
            "type": "yes_no",
        },
        {
            "id": "recommender_name",
            "text": "ФИО рекомендателя:",
            "type": "text",
            "condition": {"depends_on": "has_recommenders", "value": True},
        },
        {
            "id": "recommender_position",
            "text": "Должность этого человека:",
            "type": "text",
            "condition": {"depends_on": "has_recommenders", "value": True},
        },
        {
            "id": "recommender_relationship",
            "text": "Как вы работали вместе?",
            "hint": "Например: был моим руководителем, работали над проектом X, он был клиентом",
            "type": "text",
            "condition": {"depends_on": "has_recommenders", "value": True},
        },
        {
            "id": "recommender_confirm",
            "text": "Что этот человек может подтвердить о вашей работе?",
            "hint": "Какие достижения, навыки или качества он может описать?",
            "type": "text",
            "condition": {"depends_on": "has_recommenders", "value": True},
        },
        {
            "id": "more_recommenders",
            "text": "Есть ли ещё рекомендатели из этой компании?",
            "type": "yes_no",
            "condition": {"depends_on": "has_recommenders", "value": True},
        },
    ],
    "evidence": [
        {
            "id": "has_evidence",
            "text": "Есть ли у вас документы, подтверждающие вашу работу в {company_name}?",
            "hint": "Трудовая книжка, контракты, рекомендательные письма, грамоты, публикации",
            "type": "yes_no",
        },
        {
            "id": "upload_evidence",
            "text": "📎 Загрузите документы по работе в {company_name}:",
            "hint": "Отправьте файлы по одному. Напишите 'готово' когда закончите.",
            "type": "document",
            "condition": {"depends_on": "has_evidence", "value": True},
        },
    ],
    "company_summary": [
        {
            "id": "anything_else",
            "text": "Есть ли что-то ещё важное о вашей работе в {company_name}, что мы не обсудили?",
            "hint": "Особые обстоятельства, уникальные возможности, важный контекст",
            "type": "text",
        },
    ],
}


# LLM prompt template for generating follow-up questions
FOLLOWUP_QUESTION_PROMPT = """
Ты помогаешь собирать информацию для иммиграционной петиции EB-1A (Extraordinary Ability).

Пользователь работал в компании:
- Название: {company_name}
- Тип: {company_type}
- Сфера: {company_industry}
- Должность: {position}
- Обязанности: {responsibilities}

Уже собранная информация:
{collected_info}

Критерии EB-1A, которые мы пытаемся подтвердить:
1. Награды за выдающиеся достижения
2. Членство в организациях, требующих выдающихся достижений
3. Публикации о заявителе в профессиональных СМИ
4. Участие в качестве судьи работ других
5. Оригинальные научные/творческие/деловые вклады
6. Авторство научных статей
7. Выставки или демонстрации работ
8. Ведущая/критическая роль в организациях
9. Высокая зарплата по сравнению с другими в области
10. Коммерческий успех в исполнительском искусстве

На основе контекста, сгенерируй 2-3 уточняющих вопроса, которые помогут:
1. Выявить достижения, релевантные критериям EB-1A
2. Получить измеримые результаты и доказательства
3. Найти потенциальных рекомендателей

Формат ответа - JSON список:
[
  {{"question": "текст вопроса", "hint": "подсказка", "eb1a_criterion": "какой критерий поможет закрыть"}}
]
"""


def get_phase_questions(
    phase: str,
    company_name: str | None = None,
    company_index: int = 1,
) -> list[dict]:
    """Get questions for a specific phase, with variable substitution."""
    questions = CAREER_PHASE_QUESTIONS.get(phase, [])
    result = []

    for q in questions:
        question = q.copy()
        # Substitute variables
        if company_name:
            question["text"] = question["text"].replace("{company_name}", company_name)
        question["text"] = question["text"].replace("{index}", str(company_index))
        if "hint" in question and question["hint"]:
            question["hint"] = question["hint"].replace("{company_name}", company_name or "")
        result.append(question)

    return result


def get_next_phase(current_phase: str, company_type: CompanyType) -> str | None:
    """Get the next phase in the career intake flow."""
    phase_order = [
        "company_basics",
        "positions",
        "projects",
        "achievements",
    ]

    # Add government-specific phase if applicable
    if company_type == CompanyType.GOVERNMENT:
        phase_order.append("achievements_government")

    phase_order.extend(
        [
            "recommenders",
            "evidence",
            "company_summary",
        ]
    )

    try:
        current_index = phase_order.index(current_phase)
        if current_index + 1 < len(phase_order):
            return phase_order[current_index + 1]
    except ValueError:
        pass

    return None


def map_company_type(text: str) -> CompanyType:
    """Map user text input to CompanyType enum."""
    text_lower = text.lower()

    if "государств" in text_lower or "госслужб" in text_lower:
        return CompanyType.GOVERNMENT
    if "нко" in text_lower or "некоммерч" in text_lower or "общественн" in text_lower:
        return CompanyType.NGO
    if "стартап" in text_lower or "startup" in text_lower:
        return CompanyType.STARTUP
    if "академич" in text_lower or "научн" in text_lower or "университет" in text_lower:
        return CompanyType.ACADEMIC
    if "международн" in text_lower or "internat" in text_lower:
        return CompanyType.INTERNATIONAL
    if "частн" in text_lower or "private" in text_lower or "компани" in text_lower:
        return CompanyType.PRIVATE

    return CompanyType.OTHER
