"""
EB-1A Petition Models - Employment-Based First Preference (Extraordinary Ability)

Реализует 10 критериев USCIS для EB-1A визовых петиций согласно
8 CFR 204.5(h)(3). Необходимо соответствовать минимум 3 из 10 критериев.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EB1Criterion(str, Enum):
    """10 критериев USCIS для EB-1A (8 CFR 204.5(h)(3))"""

    # Критерий 1: Национальные/международные премии
    AWARDS = "awards"
    # Критерий 2: Членство в ассоциациях
    MEMBERSHIP = "membership"
    # Критерий 3: Публикации о вас в СМИ
    PRESS = "press"
    # Критерий 4: Судейство работ других
    JUDGING = "judging"
    # Критерий 5: Оригинальный вклад в области
    CONTRIBUTION = "contribution"
    # Критерий 6: Научные публикации
    SCHOLARLY = "scholarly"
    # Критерий 7: Выставки/показы работ
    EXHIBITION = "exhibition"
    # Критерий 8: Лидерская роль в организации
    LEADERSHIP = "leadership"
    # Критерий 9: Высокая зарплата
    SALARY = "salary"
    # Критерий 10: Коммерческий успех в искусстве
    COMMERCIAL = "commercial"


class EB1CriterionEvidence(BaseModel):
    """Доказательства для одного критерия"""

    criterion: EB1Criterion = Field(..., description="Тип критерия")
    met: bool = Field(default=False, description="Соответствует ли критерий")
    evidence_count: int = Field(default=0, description="Количество доказательств")
    evidence_items: list[dict[str, Any]] = Field(
        default_factory=list, description="Список доказательств"
    )
    description: str = Field(default="", description="Описание доказательств")
    strength_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Сила доказательств (0-1)"
    )
    notes: str = Field(default="", description="Заметки и рекомендации")


class EB1QuestionnaireStep(str, Enum):
    """Этапы опросника EB-1A"""

    PERSONAL_INFO = "personal_info"
    FIELD_OF_EXPERTISE = "field_of_expertise"
    CRITERION_AWARDS = "criterion_awards"
    CRITERION_MEMBERSHIP = "criterion_membership"
    CRITERION_PRESS = "criterion_press"
    CRITERION_JUDGING = "criterion_judging"
    CRITERION_CONTRIBUTION = "criterion_contribution"
    CRITERION_SCHOLARLY = "criterion_scholarly"
    CRITERION_EXHIBITION = "criterion_exhibition"
    CRITERION_LEADERSHIP = "criterion_leadership"
    CRITERION_SALARY = "criterion_salary"
    CRITERION_COMMERCIAL = "criterion_commercial"
    REVIEW_SUMMARY = "review_summary"
    DOCUMENT_GENERATION = "document_generation"
    COMPLETED = "completed"


class EB1PetitionStatus(str, Enum):
    """Статусы петиции EB-1A"""

    DRAFT = "draft"
    DATA_COLLECTION = "data_collection"
    CRITERIA_REVIEW = "criteria_review"
    DOCUMENT_PREPARATION = "document_preparation"
    READY_FOR_FILING = "ready_for_filing"
    FILED = "filed"
    APPROVED = "approved"
    DENIED = "denied"
    RFE_RECEIVED = "rfe_received"  # Request for Evidence


class EB1PersonalInfo(BaseModel):
    """Персональная информация петиционера"""

    full_name: str = Field(..., description="Полное имя")
    email: str = Field(..., description="Email")
    phone: str | None = Field(default=None, description="Телефон")
    current_country: str = Field(..., description="Текущая страна проживания")
    date_of_birth: str | None = Field(default=None, description="Дата рождения")
    passport_number: str | None = Field(default=None, description="Номер паспорта")
    current_visa_status: str | None = Field(default=None, description="Текущий визовый статус")


class EB1FieldOfExpertise(BaseModel):
    """Информация об области экспертизы"""

    field: str = Field(..., description="Область деятельности")
    subfield: str | None = Field(default=None, description="Подобласть")
    years_of_experience: int = Field(..., ge=0, description="Лет опыта")
    current_position: str = Field(..., description="Текущая должность")
    current_employer: str | None = Field(default=None, description="Текущий работодатель")
    education_level: str = Field(..., description="Уровень образования")
    major_achievements: list[str] = Field(default_factory=list, description="Основные достижения")


class EB1PetitionData(BaseModel):
    """Данные петиции EB-1A"""

    petition_id: str = Field(..., description="ID петиции")
    user_id: str = Field(..., description="ID пользователя")
    status: EB1PetitionStatus = Field(default=EB1PetitionStatus.DRAFT, description="Статус петиции")
    current_step: EB1QuestionnaireStep = Field(
        default=EB1QuestionnaireStep.PERSONAL_INFO, description="Текущий этап"
    )

    # Персональная информация
    personal_info: EB1PersonalInfo | None = Field(default=None)
    field_of_expertise: EB1FieldOfExpertise | None = Field(default=None)

    # Доказательства по критериям
    criteria_evidence: dict[str, EB1CriterionEvidence] = Field(
        default_factory=dict, description="Доказательства по критериям"
    )

    # Метаданные
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(default=None)

    # Результаты анализа
    criteria_met_count: int = Field(default=0, description="Количество соответствующих критериев")
    eligibility_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Общая оценка соответствия"
    )
    recommendation: str = Field(default="", description="Рекомендация по петиции")

    # Сгенерированные документы
    generated_documents: list[str] = Field(
        default_factory=list, description="ID сгенерированных документов"
    )


class EB1Question(BaseModel):
    """Вопрос в опроснике"""

    question_id: str = Field(..., description="ID вопроса")
    step: EB1QuestionnaireStep = Field(..., description="Этап опросника")
    criterion: EB1Criterion | None = Field(default=None, description="Связанный критерий")
    question_text: str = Field(..., description="Текст вопроса")
    question_type: str = Field(..., description="Тип вопроса: yes_no, text, number, list, date")
    required: bool = Field(default=True, description="Обязательный вопрос")
    help_text: str = Field(default="", description="Подсказка")
    validation_rules: dict[str, Any] = Field(default_factory=dict, description="Правила валидации")


class EB1Answer(BaseModel):
    """Ответ на вопрос"""

    question_id: str = Field(..., description="ID вопроса")
    answer: Any = Field(..., description="Ответ")
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str = Field(default="", description="Заметки")


class EB1ConversationState(BaseModel):
    """Состояние диалога с пользователем"""

    petition_id: str = Field(..., description="ID петиции")
    current_step: EB1QuestionnaireStep = Field(
        default=EB1QuestionnaireStep.PERSONAL_INFO, description="Текущий этап"
    )
    current_question_id: str | None = Field(default=None, description="Текущий вопрос")
    answers: dict[str, EB1Answer] = Field(default_factory=dict, description="Ответы пользователя")
    completed_steps: list[EB1QuestionnaireStep] = Field(
        default_factory=list, description="Завершенные этапы"
    )
    awaiting_input: bool = Field(default=False, description="Ожидает ввода от пользователя")
    last_bot_message: str = Field(default="", description="Последнее сообщение бота")


# Определение вопросов для каждого критерия
EB1_QUESTIONNAIRE_TEMPLATES = {
    EB1QuestionnaireStep.PERSONAL_INFO: [
        EB1Question(
            question_id="personal_full_name",
            step=EB1QuestionnaireStep.PERSONAL_INFO,
            question_text="Как ваше полное имя (как в паспорте)?",
            question_type="text",
            required=True,
        ),
        EB1Question(
            question_id="personal_email",
            step=EB1QuestionnaireStep.PERSONAL_INFO,
            question_text="Ваш email адрес?",
            question_type="text",
            required=True,
            validation_rules={"format": "email"},
        ),
        EB1Question(
            question_id="personal_country",
            step=EB1QuestionnaireStep.PERSONAL_INFO,
            question_text="В какой стране вы сейчас находитесь?",
            question_type="text",
            required=True,
        ),
        EB1Question(
            question_id="personal_visa_status",
            step=EB1QuestionnaireStep.PERSONAL_INFO,
            question_text="Какой у вас текущий визовый статус в США (если есть)?",
            question_type="text",
            required=False,
            help_text="Например: H-1B, F-1, O-1, или 'Нет визы'",
        ),
    ],
    EB1QuestionnaireStep.FIELD_OF_EXPERTISE: [
        EB1Question(
            question_id="field_main",
            step=EB1QuestionnaireStep.FIELD_OF_EXPERTISE,
            question_text="В какой области вы работаете?",
            question_type="text",
            required=True,
            help_text="Например: Искусственный интеллект, Медицина, Искусство, Бизнес",
        ),
        EB1Question(
            question_id="field_years",
            step=EB1QuestionnaireStep.FIELD_OF_EXPERTISE,
            question_text="Сколько лет вы работаете в этой области?",
            question_type="number",
            required=True,
            validation_rules={"min": 0, "max": 100},
        ),
        EB1Question(
            question_id="field_position",
            step=EB1QuestionnaireStep.FIELD_OF_EXPERTISE,
            question_text="Какая у вас текущая должность?",
            question_type="text",
            required=True,
        ),
        EB1Question(
            question_id="field_education",
            step=EB1QuestionnaireStep.FIELD_OF_EXPERTISE,
            question_text="Какое у вас образование?",
            question_type="text",
            required=True,
            help_text="Например: PhD, Master's, Bachelor's",
        ),
    ],
    EB1QuestionnaireStep.CRITERION_AWARDS: [
        EB1Question(
            question_id="awards_has",
            step=EB1QuestionnaireStep.CRITERION_AWARDS,
            criterion=EB1Criterion.AWARDS,
            question_text="Получали ли вы национальные или международные премии/награды за выдающиеся достижения?",
            question_type="yes_no",
            required=True,
        ),
        EB1Question(
            question_id="awards_list",
            step=EB1QuestionnaireStep.CRITERION_AWARDS,
            criterion=EB1Criterion.AWARDS,
            question_text="Перечислите награды с описанием (название, год, кем вручена, значимость):",
            question_type="list",
            required=False,
            help_text="Каждая награда на новой строке или отдельным сообщением",
        ),
    ],
    EB1QuestionnaireStep.CRITERION_MEMBERSHIP: [
        EB1Question(
            question_id="membership_has",
            step=EB1QuestionnaireStep.CRITERION_MEMBERSHIP,
            criterion=EB1Criterion.MEMBERSHIP,
            question_text="Являетесь ли вы членом ассоциаций, требующих выдающихся достижений для вступления?",
            question_type="yes_no",
            required=True,
            help_text="Ассоциация должна требовать выдающихся достижений, оцененных экспертами",
        ),
        EB1Question(
            question_id="membership_list",
            step=EB1QuestionnaireStep.CRITERION_MEMBERSHIP,
            criterion=EB1Criterion.MEMBERSHIP,
            question_text="Перечислите ассоциации и требования для вступления:",
            question_type="list",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_PRESS: [
        EB1Question(
            question_id="press_has",
            step=EB1QuestionnaireStep.CRITERION_PRESS,
            criterion=EB1Criterion.PRESS,
            question_text="Были ли о вас публикации в профессиональных изданиях или крупных СМИ?",
            question_type="yes_no",
            required=True,
        ),
        EB1Question(
            question_id="press_list",
            step=EB1QuestionnaireStep.CRITERION_PRESS,
            criterion=EB1Criterion.PRESS,
            question_text="Перечислите публикации (название издания, дата, тема статьи):",
            question_type="list",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_JUDGING: [
        EB1Question(
            question_id="judging_has",
            step=EB1QuestionnaireStep.CRITERION_JUDGING,
            criterion=EB1Criterion.JUDGING,
            question_text="Выступали ли вы судьей/рецензентом работ других в вашей области?",
            question_type="yes_no",
            required=True,
            help_text="Например: рецензирование статей, оценка грантов, судейство конкурсов",
        ),
        EB1Question(
            question_id="judging_list",
            step=EB1QuestionnaireStep.CRITERION_JUDGING,
            criterion=EB1Criterion.JUDGING,
            question_text="Опишите вашу судейскую деятельность:",
            question_type="list",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_CONTRIBUTION: [
        EB1Question(
            question_id="contribution_has",
            step=EB1QuestionnaireStep.CRITERION_CONTRIBUTION,
            criterion=EB1Criterion.CONTRIBUTION,
            question_text="Внесли ли вы оригинальный вклад большой важности в вашу область?",
            question_type="yes_no",
            required=True,
            help_text="Например: изобретения, методологии, технологии, патенты",
        ),
        EB1Question(
            question_id="contribution_list",
            step=EB1QuestionnaireStep.CRITERION_CONTRIBUTION,
            criterion=EB1Criterion.CONTRIBUTION,
            question_text="Опишите ваш оригинальный вклад и его влияние на область:",
            question_type="list",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_SCHOLARLY: [
        EB1Question(
            question_id="scholarly_has",
            step=EB1QuestionnaireStep.CRITERION_SCHOLARLY,
            criterion=EB1Criterion.SCHOLARLY,
            question_text="Публиковали ли вы научные статьи в профессиональных изданиях?",
            question_type="yes_no",
            required=True,
        ),
        EB1Question(
            question_id="scholarly_count",
            step=EB1QuestionnaireStep.CRITERION_SCHOLARLY,
            criterion=EB1Criterion.SCHOLARLY,
            question_text="Сколько у вас научных публикаций?",
            question_type="number",
            required=False,
        ),
        EB1Question(
            question_id="scholarly_citations",
            step=EB1QuestionnaireStep.CRITERION_SCHOLARLY,
            criterion=EB1Criterion.SCHOLARLY,
            question_text="Сколько цитирований ваших работ (по Google Scholar)?",
            question_type="number",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_EXHIBITION: [
        EB1Question(
            question_id="exhibition_has",
            step=EB1QuestionnaireStep.CRITERION_EXHIBITION,
            criterion=EB1Criterion.EXHIBITION,
            question_text="Были ли ваши работы выставлены/показаны на выставках или шоу?",
            question_type="yes_no",
            required=True,
            help_text="Применимо для искусства, архитектуры, дизайна",
        ),
    ],
    EB1QuestionnaireStep.CRITERION_LEADERSHIP: [
        EB1Question(
            question_id="leadership_has",
            step=EB1QuestionnaireStep.CRITERION_LEADERSHIP,
            criterion=EB1Criterion.LEADERSHIP,
            question_text="Занимали ли вы лидерскую или критически важную роль в организациях с выдающейся репутацией?",
            question_type="yes_no",
            required=True,
        ),
        EB1Question(
            question_id="leadership_list",
            step=EB1QuestionnaireStep.CRITERION_LEADERSHIP,
            criterion=EB1Criterion.LEADERSHIP,
            question_text="Опишите ваши лидерские роли:",
            question_type="list",
            required=False,
        ),
    ],
    EB1QuestionnaireStep.CRITERION_SALARY: [
        EB1Question(
            question_id="salary_has",
            step=EB1QuestionnaireStep.CRITERION_SALARY,
            criterion=EB1Criterion.SALARY,
            question_text="Получаете ли вы значительно более высокую зарплату по сравнению с коллегами?",
            question_type="yes_no",
            required=True,
        ),
        EB1Question(
            question_id="salary_amount",
            step=EB1QuestionnaireStep.CRITERION_SALARY,
            criterion=EB1Criterion.SALARY,
            question_text="Какая у вас годовая зарплата (USD)?",
            question_type="number",
            required=False,
            help_text="Необходимо быть в топ 10% для вашей области",
        ),
    ],
    EB1QuestionnaireStep.CRITERION_COMMERCIAL: [
        EB1Question(
            question_id="commercial_has",
            step=EB1QuestionnaireStep.CRITERION_COMMERCIAL,
            criterion=EB1Criterion.COMMERCIAL,
            question_text="Достигли ли вы коммерческого успеха в исполнительском искусстве?",
            question_type="yes_no",
            required=True,
            help_text="Применимо для актеров, музыкантов, спортсменов",
        ),
    ],
}
