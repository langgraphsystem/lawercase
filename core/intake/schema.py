"""
Intake questionnaire schema with Pydantic v2 models.

Defines 11 blocks covering biographical data from childhood to current goals.
All user-facing text is in Russian.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# -------------------- PYDANTIC V2 MODELS --------------------


class QuestionType(str, Enum):
    """Type of question for validation and rendering."""

    TEXT = "text"  # Free-form text input
    YES_NO = "yes_no"  # Boolean (да/нет normalization)
    DATE = "date"  # Date in YYYY-MM-DD format
    SELECT = "select"  # Single choice from options
    LIST = "list"  # Multiple items (comma/newline separated)
    DOCUMENT = "document"  # File upload (PDF, images, documents)


class IntakeCondition(BaseModel):
    """
    Conditional rendering logic for questions.

    A question is only shown if the dependent question's answer matches expected_value.
    """

    depends_on_question_id: str = Field(description="ID of the question this depends on")
    expected_value: Any = Field(description="Required value to show this question")


class IntakeQuestion(BaseModel):
    """
    Single question in an intake block.

    All user-facing text (text_template, hint) must be in Russian.
    """

    id: str = Field(description="Unique identifier for this question")
    text_template: str = Field(description="Question text in Russian (supports .format())")
    type: QuestionType = Field(
        default=QuestionType.TEXT, description="Question type for validation"
    )
    options: list[str] | None = Field(default=None, description="Options for SELECT type")
    hint: str | None = Field(default=None, description="Help text in Russian")
    rationale: str | None = Field(
        default=None, description="Why this question matters (EB-1A context, in English for dev)"
    )
    condition: IntakeCondition | None = Field(
        default=None, description="Conditional rendering logic"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for semantic memory")

    class Config:
        use_enum_values = True


class IntakeBlock(BaseModel):
    """
    Block of related questions covering a life stage or topic.

    All user-facing text (title, description) must be in Russian.
    """

    id: str = Field(description="Unique identifier for this block")
    title: str = Field(description="Block title in Russian")
    description: str = Field(description="Short description in Russian")
    questions: list[IntakeQuestion] = Field(description="Questions in this block")

    class Config:
        use_enum_values = True


# -------------------- BLOCK DEFINITIONS --------------------


# Block 1: basic_info - Общие данные
BLOCK_BASIC_INFO = IntakeBlock(
    id="basic_info",
    title="Общая информация",
    description="Базовые данные о вас",
    questions=[
        IntakeQuestion(
            id="full_name",
            text_template="Как ваше полное имя (Имя Фамилия)?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info", "identity"],
        ),
        IntakeQuestion(
            id="date_of_birth",
            text_template="Когда вы родились? (Формат: ГГГГ-ММ-ДД)",
            type=QuestionType.DATE,
            hint="Например: 1990-05-15",
            tags=["intake", "basic_info", "timeline"],
        ),
        IntakeQuestion(
            id="place_of_birth",
            text_template="Где вы родились? (Город, страна)",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info", "location"],
        ),
        IntakeQuestion(
            id="citizenship",
            text_template="Какое у вас гражданство?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info", "identity"],
        ),
        IntakeQuestion(
            id="current_residence",
            text_template="Где вы сейчас живёте? (Город, страна)",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info", "location"],
        ),
        IntakeQuestion(
            id="main_field",
            text_template="Какова ваша основная область деятельности или экспертизы?",
            type=QuestionType.TEXT,
            hint="Например: машинное обучение, биотехнологии, финансовые технологии",
            tags=["intake", "basic_info", "career"],
        ),
        IntakeQuestion(
            id="doc_passport",
            text_template="📎 Загрузите скан/фото вашего паспорта (главная страница с фото и данными)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "basic_info", "document", "identity"],
        ),
        IntakeQuestion(
            id="doc_birth_certificate",
            text_template="📎 Загрузите свидетельство о рождении (если есть)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "basic_info", "document", "identity"],
        ),
    ],
)


# Block 2: family_childhood - Семья и раннее детство
BLOCK_FAMILY_CHILDHOOD = IntakeBlock(
    id="family_childhood",
    title="Семья и раннее детство",
    description="Информация о семье и раннем развитии",
    questions=[
        IntakeQuestion(
            id="parents_professions",
            text_template="Кем работают или работали ваши родители?",
            type=QuestionType.TEXT,
            tags=["intake", "family_childhood", "background"],
        ),
        IntakeQuestion(
            id="parents_education",
            text_template="Какое образование у ваших родителей?",
            type=QuestionType.TEXT,
            tags=["intake", "family_childhood", "background"],
        ),
        IntakeQuestion(
            id="family_attitude_education",
            text_template="Как в вашей семье относились к образованию и карьере?",
            type=QuestionType.TEXT,
            hint="Например: поощряли учёбу, ценили достижения, поддерживали интересы",
            tags=["intake", "family_childhood", "background"],
        ),
        IntakeQuestion(
            id="early_interests",
            text_template="Какие у вас были интересы и увлечения в детстве?",
            type=QuestionType.TEXT,
            tags=["intake", "family_childhood", "background"],
        ),
    ],
)


# Block 3: school - Школа
BLOCK_SCHOOL = IntakeBlock(
    id="school",
    title="Школа",
    description="Школьное образование и достижения",
    questions=[
        IntakeQuestion(
            id="schools_attended",
            text_template="В каких школах вы учились? Укажите названия, города, годы обучения.",
            type=QuestionType.TEXT,
            hint="Например: Школа №57, Москва, 2005-2016",
            tags=["intake", "school", "timeline"],
        ),
        IntakeQuestion(
            id="school_specialization",
            text_template="Была ли у вас специализация или профиль в школе? (физ-мат, гуманитарный, естественнонаучный)",
            type=QuestionType.TEXT,
            tags=["intake", "school", "background"],
        ),
        IntakeQuestion(
            id="school_strong_subjects",
            text_template="Какие предметы давались вам лучше всего? В чём вы были сильны?",
            type=QuestionType.TEXT,
            tags=["intake", "school", "background"],
        ),
        IntakeQuestion(
            id="school_olympiads",
            text_template="Участвовали ли вы в олимпиадах, конкурсах или соревнованиях? Какие были результаты?",
            type=QuestionType.TEXT,
            hint="Укажите названия олимпиад, годы, места/призы",
            tags=["intake", "school", "achievements"],
        ),
        IntakeQuestion(
            id="school_roles",
            text_template="Были ли у вас какие-то роли или позиции в школе? (староста класса, капитан команды, организатор мероприятий)",
            type=QuestionType.TEXT,
            tags=["intake", "school", "achievements"],
        ),
        IntakeQuestion(
            id="school_projects",
            text_template="Были ли у вас значимые проекты или инициативы в школе?",
            type=QuestionType.TEXT,
            tags=["intake", "school", "achievements"],
        ),
        IntakeQuestion(
            id="school_macro_context",
            text_template="В какие годы вы учились в школе, в какой стране, и какие важные экономические/социальные события происходили в это время? Как это влияло на ваши возможности?",
            type=QuestionType.TEXT,
            hint="Например: кризис, реформы образования, доступ к ресурсам, поездки",
            tags=["intake", "school", "macro_context", "timeline"],
        ),
        IntakeQuestion(
            id="school_recommenders",
            text_template="Кто из ваших учителей или школьных наставников мог бы предоставить рекомендательное письмо? Укажите имена, должности, контекст знакомства.",
            type=QuestionType.TEXT,
            hint="Например: Иванов Иван Петрович, учитель математики, знает с 2010 года",
            tags=["intake", "school", "recommender"],
        ),
    ],
)


# Block 4: university - Университет / колледж
BLOCK_UNIVERSITY = IntakeBlock(
    id="university",
    title="Университет / Колледж",
    description="Высшее образование и академические достижения",
    questions=[
        IntakeQuestion(
            id="universities_attended",
            text_template="В каких университетах или колледжах вы учились? Укажите названия, города, программы, годы обучения.",
            type=QuestionType.TEXT,
            hint="Например: МГУ, Москва, бакалавриат по прикладной математике, 2010-2014",
            tags=["intake", "university", "timeline"],
        ),
        IntakeQuestion(
            id="university_major",
            text_template="Какая была ваша специальность или направление подготовки?",
            type=QuestionType.TEXT,
            tags=["intake", "university", "background"],
        ),
        IntakeQuestion(
            id="university_research",
            text_template="Занимались ли вы научной работой или исследованиями в университете? Опишите темы и результаты.",
            type=QuestionType.TEXT,
            tags=["intake", "university", "research"],
        ),
        IntakeQuestion(
            id="university_organizations",
            text_template="Участвовали ли вы в студенческих организациях, клубах, научных кружках?",
            type=QuestionType.TEXT,
            tags=["intake", "university", "background"],
        ),
        IntakeQuestion(
            id="university_thesis",
            text_template="Какова была тема вашей дипломной работы или диссертации?",
            type=QuestionType.TEXT,
            tags=["intake", "university", "research"],
        ),
        IntakeQuestion(
            id="university_awards",
            text_template="Получали ли вы награды, стипендии или гранты во время обучения в университете?",
            type=QuestionType.TEXT,
            hint="Укажите названия, годы, организации",
            tags=["intake", "university", "achievements"],
        ),
        IntakeQuestion(
            id="university_macro_context",
            text_template="Какие важные события (экономические, социальные, политические) происходили в стране во время вашего обучения в университете? Как это влияло на ваши возможности?",
            type=QuestionType.TEXT,
            tags=["intake", "university", "macro_context", "timeline"],
        ),
        IntakeQuestion(
            id="university_recommenders",
            text_template="Кто из профессоров, научных руководителей или преподавателей мог бы предоставить рекомендательное письмо? Укажите имена, должности, контекст знакомства.",
            type=QuestionType.TEXT,
            hint="Например: Проф. Петров П.П., научный руководитель диплома, знаком с 2012 года",
            tags=["intake", "university", "recommender"],
        ),
        IntakeQuestion(
            id="doc_diploma",
            text_template="📎 Загрузите ваш диплом о высшем образовании",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "university", "document", "education"],
        ),
        IntakeQuestion(
            id="doc_transcript",
            text_template="📎 Загрузите приложение к диплому / транскрипт оценок (если есть)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "university", "document", "education"],
        ),
    ],
)


# Block 5: career - Профессиональный путь
BLOCK_CAREER = IntakeBlock(
    id="career",
    title="Профессиональный путь",
    description="История работы, должности, проекты, достижения",
    questions=[
        IntakeQuestion(
            id="career_companies",
            text_template="В каких компаниях или организациях вы работали? Укажите названия, города/страны, годы работы.",
            type=QuestionType.TEXT,
            hint="Например: Google, Цюрих, 2015-2018; Яндекс, Москва, 2013-2015",
            tags=["intake", "career", "timeline"],
        ),
        IntakeQuestion(
            id="career_positions",
            text_template="Какие должности или роли вы занимали на каждом месте работы?",
            type=QuestionType.TEXT,
            hint="Например: Software Engineer → Senior Engineer → Tech Lead",
            tags=["intake", "career", "timeline"],
        ),
        IntakeQuestion(
            id="career_responsibilities",
            text_template="Каковы были ваши основные обязанности и зоны ответственности?",
            type=QuestionType.TEXT,
            tags=["intake", "career", "background"],
        ),
        IntakeQuestion(
            id="career_key_projects",
            text_template="Какие ключевые проекты вы реализовали? Опишите масштаб, ваш вклад, результаты.",
            type=QuestionType.TEXT,
            tags=["intake", "career", "achievements"],
        ),
        IntakeQuestion(
            id="career_achievements_metrics",
            text_template="Какие у вас были измеримые достижения? (Например: увеличение метрик, рост команды, экономия ресурсов, выручка)",
            type=QuestionType.TEXT,
            hint="Постарайтесь указать конкретные цифры и результаты",
            tags=["intake", "career", "achievements"],
        ),
        IntakeQuestion(
            id="career_critical_role",
            text_template="Занимали ли вы критическую или ведущую роль в известных организациях или проектах? Опишите подробнее.",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: leading or critical role in distinguished organizations.",
            tags=["intake", "career", "achievements", "eb1a_criterion"],
        ),
        IntakeQuestion(
            id="career_high_salary",
            text_template="Ваша зарплата или компенсация значительно выше среднего по индустрии? Можете ли вы предоставить общее сравнение?",
            type=QuestionType.TEXT,
            hint="Не обязательно указывать точную сумму, можно сравнить с медианой по индустрии",
            rationale="Used to support EB-1A criterion: high salary or remuneration compared to others in the field.",
            tags=["intake", "career", "achievements", "eb1a_criterion"],
        ),
        IntakeQuestion(
            id="career_team_size",
            text_template="Управляли ли вы командой? Какого размера и с какими обязанностями?",
            type=QuestionType.TEXT,
            tags=["intake", "career", "background"],
        ),
        IntakeQuestion(
            id="career_macro_context",
            text_template="Какие важные события (экономические кризисы, бумы, реформы, санкции) происходили во время вашей карьеры? Как это влияло на ваши возможности или проекты?",
            type=QuestionType.TEXT,
            tags=["intake", "career", "macro_context", "timeline"],
        ),
        IntakeQuestion(
            id="career_recommenders",
            text_template="Кто из ваших руководителей, коллег, клиентов или партнёров мог бы предоставить рекомендательное письмо? Укажите имена, должности, контекст знакомства.",
            type=QuestionType.TEXT,
            hint="Например: Джон Смит, CTO, работали вместе 3 года",
            tags=["intake", "career", "recommender"],
        ),
    ],
)


# Block 6: projects_research - Проекты / исследования / публикации
BLOCK_PROJECTS_RESEARCH = IntakeBlock(
    id="projects_research",
    title="Проекты / Исследования / Публикации",
    description="Научная и профессиональная деятельность",
    questions=[
        IntakeQuestion(
            id="publications",
            text_template="Есть ли у вас научные публикации? Укажите количество, ведущие журналы/конференции, цитирования.",
            type=QuestionType.TEXT,
            hint="Например: 25 статей, h-index 15, главная статья в Nature с 500+ цитированиями",
            tags=["intake", "projects_research", "achievements"],
        ),
        IntakeQuestion(
            id="metrics",
            text_template="Какие у вас метрики научной деятельности? (h-index, i10-index, общее число цитирований)",
            type=QuestionType.TEXT,
            tags=["intake", "projects_research", "achievements"],
        ),
        IntakeQuestion(
            id="open_source",
            text_template="Вносили ли вы вклад в open source проекты? Какие и каков был масштаб вклада?",
            type=QuestionType.TEXT,
            hint="Например: maintainer проекта с 10k+ stars на GitHub",
            tags=["intake", "projects_research", "achievements"],
        ),
        IntakeQuestion(
            id="patents",
            text_template="Есть ли у вас патенты или изобретения? Укажите названия, годы, статусы.",
            type=QuestionType.TEXT,
            tags=["intake", "projects_research", "achievements"],
        ),
        IntakeQuestion(
            id="commercial_products",
            text_template="Создавали ли вы коммерческие продукты или сервисы? Опишите их успех (пользователи, выручка, известность).",
            type=QuestionType.TEXT,
            tags=["intake", "projects_research", "achievements"],
        ),
        IntakeQuestion(
            id="doc_publications",
            text_template="📎 Загрузите PDF ваших ключевых публикаций или статей (можно несколько файлов)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда закончите, напишите 'готово' или 'пропустить'",
            tags=["intake", "projects_research", "document", "publications"],
        ),
        IntakeQuestion(
            id="doc_patents",
            text_template="📎 Загрузите документы о патентах (если есть)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "projects_research", "document", "patents"],
        ),
    ],
)


# Block 7: awards - Награды / конкурсы / олимпиады
BLOCK_AWARDS = IntakeBlock(
    id="awards",
    title="Награды / Конкурсы / Олимпиады",
    description="Признание и достижения",
    questions=[
        IntakeQuestion(
            id="major_awards",
            text_template="Получали ли вы значимые награды или премии в вашей области? Укажите названия, годы, организации.",
            type=QuestionType.TEXT,
            hint="Например: Best Paper Award на конференции NeurIPS 2023",
            tags=["intake", "awards", "achievements"],
        ),
        IntakeQuestion(
            id="competitions",
            text_template="Участвовали ли вы в конкурсах, хакатонах, чемпионатах? Какие были результаты?",
            type=QuestionType.TEXT,
            hint="Укажите места, призы, годы",
            tags=["intake", "awards", "achievements"],
        ),
        IntakeQuestion(
            id="grants_scholarships",
            text_template="Получали ли вы гранты, стипендии или другие виды финансирования для исследований или проектов?",
            type=QuestionType.TEXT,
            hint="Например: грант NSF CAREER, стипендия Fulbright",
            tags=["intake", "awards", "achievements"],
        ),
        IntakeQuestion(
            id="doc_awards",
            text_template="📎 Загрузите документы о наградах, дипломы, сертификаты (можно несколько файлов)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда закончите, напишите 'готово' или 'пропустить'",
            tags=["intake", "awards", "document", "achievements"],
        ),
    ],
)


# Block 8: talks_public_activity - Конференции / выступления / ассоциации
BLOCK_TALKS_PUBLIC = IntakeBlock(
    id="talks_public_activity",
    title="Конференции / Выступления / Общественная деятельность",
    description="Публичная активность и признание",
    questions=[
        IntakeQuestion(
            id="conferences_talks",
            text_template="Выступали ли вы на конференциях, семинарах, митапах? Укажите названия, темы, годы.",
            type=QuestionType.TEXT,
            hint="Например: keynote speaker на конференции AI Summit 2023",
            tags=["intake", "talks_public_activity", "achievements"],
        ),
        IntakeQuestion(
            id="associations_memberships",
            text_template="Являетесь ли вы членом профессиональных ассоциаций, научных обществ, НКО?",
            type=QuestionType.TEXT,
            hint="Например: IEEE, ACM, AAAI",
            tags=["intake", "talks_public_activity", "background"],
        ),
        IntakeQuestion(
            id="expert_roles",
            text_template="Выполняли ли вы экспертные роли? (судейство на конкурсах, peer review, участие в программных комитетах конференций, grant panels)",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: judging the work of others in the field.",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion"],
        ),
        IntakeQuestion(
            id="media_press",
            text_template="Освещалась ли ваша работа в СМИ или прессе? (Интервью, статьи о вашей работе, упоминания)",
            type=QuestionType.TEXT,
            hint="Например: интервью в TechCrunch, статья в Nature News",
            tags=["intake", "talks_public_activity", "achievements"],
        ),
        IntakeQuestion(
            id="mentorship_teaching",
            text_template="Занимались ли вы менторством, преподаванием, обучением других?",
            type=QuestionType.TEXT,
            tags=["intake", "talks_public_activity", "background"],
        ),
    ],
)


# Block 9: courses_certificates - Курсы / сертификаты
BLOCK_COURSES_CERTIFICATES = IntakeBlock(
    id="courses_certificates",
    title="Курсы / Сертификаты / Дополнительное образование",
    description="Повышение квалификации и обучение",
    questions=[
        IntakeQuestion(
            id="courses_programs",
            text_template="Проходили ли вы какие-то курсы, программы повышения квалификации, bootcamps?",
            type=QuestionType.TEXT,
            hint="Укажите названия, организации, годы",
            tags=["intake", "courses_certificates", "background"],
        ),
        IntakeQuestion(
            id="certifications_licenses",
            text_template="Есть ли у вас профессиональные сертификаты или лицензии?",
            type=QuestionType.TEXT,
            hint="Например: AWS Certified Solutions Architect, CFA, PMP",
            tags=["intake", "courses_certificates", "background"],
        ),
    ],
)


# Block 10: recommenders - Потенциальные рекомендатели
BLOCK_RECOMMENDERS = IntakeBlock(
    id="recommenders",
    title="Потенциальные рекомендатели",
    description="Люди, которые могут предоставить рекомендации",
    questions=[
        IntakeQuestion(
            id="recommenders_summary",
            text_template="Кто из всех упомянутых людей (учителя, профессора, руководители, коллеги) мог бы написать наиболее сильные рекомендательные письма?",
            type=QuestionType.TEXT,
            hint="Перечислите 5-10 человек с указанием их связи с вами",
            tags=["intake", "recommenders", "background"],
        ),
        IntakeQuestion(
            id="recommenders_priority",
            text_template="Кого из них вы бы выделили как приоритетных кандидатов для писем? (Обычно нужно 3-5 писем)",
            type=QuestionType.TEXT,
            tags=["intake", "recommenders", "background"],
        ),
    ],
)


# Block 11: goals_usa - Личные мотивы и планы в США
BLOCK_GOALS_USA = IntakeBlock(
    id="goals_usa",
    title="Цели и планы в США",
    description="Ваши мотивы и долгосрочные планы",
    questions=[
        IntakeQuestion(
            id="motivation_usa",
            text_template="Почему вы хотите переехать в США? Какова ваша мотивация?",
            type=QuestionType.TEXT,
            tags=["intake", "goals_usa", "background"],
        ),
        IntakeQuestion(
            id="professional_plans_usa",
            text_template="Какие у вас профессиональные планы в США? (Работа в компании, исследования, преподавание, стартап)",
            type=QuestionType.TEXT,
            tags=["intake", "goals_usa", "background"],
        ),
        IntakeQuestion(
            id="longterm_goals",
            text_template="Каковы ваши долгосрочные цели и амбиции на ближайшие 5-10 лет?",
            type=QuestionType.TEXT,
            tags=["intake", "goals_usa", "background"],
        ),
    ],
)


# -------------------- REGISTRIES --------------------


INTAKE_BLOCKS: list[IntakeBlock] = [
    BLOCK_BASIC_INFO,
    BLOCK_FAMILY_CHILDHOOD,
    BLOCK_SCHOOL,
    BLOCK_UNIVERSITY,
    BLOCK_CAREER,
    BLOCK_PROJECTS_RESEARCH,
    BLOCK_AWARDS,
    BLOCK_TALKS_PUBLIC,
    BLOCK_COURSES_CERTIFICATES,
    BLOCK_RECOMMENDERS,
    BLOCK_GOALS_USA,
]

BLOCKS_BY_ID: dict[str, IntakeBlock] = {block.id: block for block in INTAKE_BLOCKS}
