"""
Intake questionnaire schema with Pydantic v2 models.

Defines 11 blocks covering biographical data from childhood to current goals.
All user-facing text is in Russian.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(use_enum_values=True)


class IntakeBlock(BaseModel):
    """
    Block of related questions covering a life stage or topic.

    All user-facing text (title, description) must be in Russian.
    """

    id: str = Field(description="Unique identifier for this block")
    title: str = Field(description="Block title in Russian")
    description: str = Field(description="Short description in Russian")
    questions: list[IntakeQuestion] = Field(description="Questions in this block")

    model_config = ConfigDict(use_enum_values=True)


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
        IntakeQuestion(
            id="doc_school_certificate",
            text_template="📎 Загрузите аттестат/свидетельство об окончании школы",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "school", "document", "education"],
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
            text_template="📎 Загрузите дипломы о высшем образовании (бакалавр, магистр, PhD - все учебные заведения)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда загрузите все дипломы, напишите 'готово' или 'пропустить'",
            tags=["intake", "university", "document", "education"],
        ),
        IntakeQuestion(
            id="doc_transcript",
            text_template="📎 Загрузите приложения к дипломам / транскрипты оценок (все учебные заведения)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда загрузите все транскрипты, напишите 'готово' или 'пропустить'",
            tags=["intake", "university", "document", "education"],
        ),
    ],
)


# Block 5: career - Профессиональный путь
# NOTE: This block triggers detailed company-by-company career intake (career_intake.py)
# The single placeholder question below is only used if detailed intake fails to import
BLOCK_CAREER = IntakeBlock(
    id="career",
    title="Профессиональный путь",
    description="Детальный опрос по каждому месту работы: компании, должности, проекты, достижения, рекомендатели",
    questions=[
        # Placeholder - triggers detailed career intake at step 0
        # See intake_handlers.py:_start_detailed_career_intake()
        IntakeQuestion(
            id="career_detailed_trigger",
            text_template="[Этот блок использует детальный опрос по карьере]",
            type=QuestionType.TEXT,
            hint="Если вы видите это сообщение, произошла ошибка. Используйте /career_start",
            tags=["intake", "career", "system"],
        ),
    ],
)


# Block 6: projects_research - Проекты / исследования / публикации
# EB-1A Criteria 5 (Original Contributions) and 6 (Scholarly Articles)
BLOCK_PROJECTS_RESEARCH = IntakeBlock(
    id="projects_research",
    title="Проекты / Исследования / Публикации",
    description="Научная и профессиональная деятельность (EB-1A Criteria 5, 6)",
    questions=[
        # Criterion 6: Scholarly Articles
        IntakeQuestion(
            id="publications",
            text_template="Есть ли у вас научные публикации? Укажите количество, ведущие журналы/конференции, цитирования.",
            type=QuestionType.TEXT,
            hint="Например: 25 статей, h-index 15, главная статья в Nature с 500+ цитированиями",
            rationale="EB-1A Criterion 6: Authorship of scholarly articles",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_6"],
        ),
        IntakeQuestion(
            id="journal_quality",
            text_template="В каких журналах/конференциях опубликованы ваши работы? Укажите impact factor или ранг.",
            type=QuestionType.TEXT,
            hint="Например: Nature (IF 49.9), CVPR (top-tier AI conference), IEEE TPAMI (top 1% journal)",
            rationale="Quality of venues demonstrates scholarly standing",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_6"],
        ),
        IntakeQuestion(
            id="metrics",
            text_template="Какие у вас метрики научной деятельности? (h-index, i10-index, общее число цитирований)",
            type=QuestionType.TEXT,
            hint="Укажите источник: Google Scholar, Scopus, Web of Science",
            rationale="Citation metrics demonstrate impact and recognition",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_6"],
        ),
        IntakeQuestion(
            id="authorship_role",
            text_template="В каких публикациях вы были первым автором или corresponding author?",
            type=QuestionType.TEXT,
            hint="Первое авторство показывает лидирующую роль в исследовании",
            rationale="First/corresponding authorship shows leadership in research",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_6"],
        ),
        # Criterion 5: Original Contributions
        IntakeQuestion(
            id="original_contributions",
            text_template="Какие ОРИГИНАЛЬНЫЕ вклады вы сделали в вашу область? (новые методы, алгоритмы, теории)",
            type=QuestionType.TEXT,
            hint="Например: создал новый алгоритм X, который стал стандартом в индустрии",
            rationale="EB-1A Criterion 5: Original contributions of major significance",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="contribution_adoption",
            text_template="Кто использует ваши разработки? (компании, исследователи, организации)",
            type=QuestionType.TEXT,
            hint="Например: мой алгоритм используется Google, Microsoft; моя библиотека имеет 50K downloads/месяц",
            rationale="Adoption by others proves major significance of contributions",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="contribution_impact",
            text_template="Какое измеримое влияние оказали ваши оригинальные вклады?",
            type=QuestionType.TEXT,
            hint="Экономия $X млн, улучшение точности на Y%, ускорение процесса в Z раз",
            rationale="Measurable impact strengthens original contributions claim",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="open_source",
            text_template="Вносили ли вы вклад в open source проекты? Какие и каков был масштаб вклада?",
            type=QuestionType.TEXT,
            hint="Например: maintainer проекта с 10k+ stars на GitHub, core contributor в TensorFlow",
            rationale="Open source contributions can demonstrate major significance",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="patents",
            text_template="Есть ли у вас патенты или изобретения? Укажите названия, годы, статусы.",
            type=QuestionType.TEXT,
            hint="Granted патенты сильнее pending; укажите patent numbers",
            rationale="Patents demonstrate original, recognized contributions",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="patent_citations",
            text_template="Цитируются ли ваши патенты в других патентах? Лицензируются ли они?",
            type=QuestionType.TEXT,
            hint="Patent citations показывают влияние на технологическое развитие",
            rationale="Patent citations/licensing demonstrate commercial significance",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="commercial_products",
            text_template="Создавали ли вы коммерческие продукты или сервисы? Опишите их успех.",
            type=QuestionType.TEXT,
            hint="Пользователи, выручка, market share, известность в индустрии",
            rationale="Commercial success demonstrates practical significance of contributions",
            tags=["intake", "projects_research", "achievements", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="doc_publications",
            text_template="📎 Загрузите PDF ваших ключевых публикаций или статей (можно несколько файлов)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда закончите, напишите 'готово' или 'пропустить'",
            tags=["intake", "projects_research", "document", "publications", "eb1a_criterion_6"],
        ),
        IntakeQuestion(
            id="doc_patents",
            text_template="📎 Загрузите документы о патентах (если есть)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл PDF или фото. Можно пропустить, отправив 'пропустить'",
            tags=["intake", "projects_research", "document", "patents", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="doc_citations",
            text_template="📎 Загрузите скриншот профиля Google Scholar или отчёт о цитированиях",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файл или 'пропустить'",
            tags=["intake", "projects_research", "document", "citations", "eb1a_criterion_6"],
        ),
    ],
)


# Block 7: awards - Награды / конкурсы / олимпиады
# EB-1A Criterion 1: Awards for excellence
BLOCK_AWARDS = IntakeBlock(
    id="awards",
    title="Награды / Конкурсы / Олимпиады",
    description="Признание и достижения (EB-1A Criterion 1: Awards)",
    questions=[
        IntakeQuestion(
            id="major_awards",
            text_template="Получали ли вы значимые награды или премии в вашей области? Укажите названия, годы, организации.",
            type=QuestionType.TEXT,
            hint="Например: Best Paper Award на конференции NeurIPS 2023",
            rationale="EB-1A Criterion 1: Awards for excellence in the field",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="award_level",
            text_template="На каком уровне были эти награды? (международный, национальный, региональный, корпоративный)",
            type=QuestionType.TEXT,
            hint="USCIS особенно ценит национальные и международные награды",
            rationale="Awards must be nationally or internationally recognized",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="award_criteria",
            text_template="Какими были критерии отбора для этих наград? Кто принимал решение о награждении?",
            type=QuestionType.TEXT,
            hint="Например: отбор жюри из 50 экспертов по научной значимости",
            rationale="USCIS checks that awards recognize excellence, not just participation",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="award_selectivity",
            text_template="Сколько человек претендовало на награду и сколько получили? (приблизительно)",
            type=QuestionType.TEXT,
            hint="Например: из 500 заявок выбрали 3 лауреата",
            rationale="Selectivity demonstrates the prestige of the award",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="competitions",
            text_template="Участвовали ли вы в конкурсах, хакатонах, чемпионатах? Какие были результаты?",
            type=QuestionType.TEXT,
            hint="Укажите места, призы, годы",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="grants_scholarships",
            text_template="Получали ли вы гранты, стипендии или другие виды финансирования для исследований или проектов?",
            type=QuestionType.TEXT,
            hint="Например: грант NSF CAREER, стипендия Fulbright. Укажите сумму, если это уместно.",
            rationale="Competitive grants can support Criterion 1 (awards) or 5 (contributions)",
            tags=["intake", "awards", "achievements", "eb1a_criterion_1"],
        ),
        IntakeQuestion(
            id="doc_awards",
            text_template="📎 Загрузите документы о наградах, дипломы, сертификаты (можно несколько файлов)",
            type=QuestionType.DOCUMENT,
            hint="Отправляйте по одному файлу. Когда закончите, напишите 'готово' или 'пропустить'",
            tags=["intake", "awards", "document", "achievements", "eb1a_criterion_1"],
        ),
    ],
)


# Block 8: talks_public_activity - Конференции / выступления / ассоциации
# EB-1A Criteria 2 (Membership), 3 (Published Material), 4 (Judging)
BLOCK_TALKS_PUBLIC = IntakeBlock(
    id="talks_public_activity",
    title="Конференции / Выступления / Общественная деятельность",
    description="Публичная активность, членство и признание (EB-1A Criteria 2, 3, 4)",
    questions=[
        IntakeQuestion(
            id="conferences_talks",
            text_template="Выступали ли вы на конференциях, семинарах, митапах? Укажите названия, темы, годы.",
            type=QuestionType.TEXT,
            hint="Например: keynote speaker на конференции AI Summit 2023",
            tags=["intake", "talks_public_activity", "achievements"],
        ),
        # Criterion 2: Membership
        IntakeQuestion(
            id="associations_memberships",
            text_template="Являетесь ли вы членом профессиональных ассоциаций, научных обществ, НКО?",
            type=QuestionType.TEXT,
            hint="Например: IEEE, ACM, AAAI, Fellow статусы",
            rationale="EB-1A Criterion 2: Membership in associations requiring outstanding achievements",
            tags=["intake", "talks_public_activity", "background", "eb1a_criterion_2"],
        ),
        IntakeQuestion(
            id="membership_requirements",
            text_template="Какие требования для вступления в эти организации? Требуется ли выдающееся достижение или рекомендации?",
            type=QuestionType.TEXT,
            hint="Например: для IEEE Fellow нужны рекомендации от 5 Fellows + значительный вклад",
            rationale="USCIS requires proof that membership requires outstanding achievements, not just payment",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_2"],
        ),
        IntakeQuestion(
            id="membership_selectivity",
            text_template="Какой процент специалистов в вашей области имеет такое членство? Сколько членов в организации?",
            type=QuestionType.TEXT,
            hint="Например: IEEE Fellows составляют менее 0.1% членов IEEE",
            rationale="Demonstrates exclusivity and prestige of membership",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_2"],
        ),
        # Criterion 4: Judging
        IntakeQuestion(
            id="expert_roles",
            text_template="Выполняли ли вы экспертные роли? (судейство на конкурсах, peer review, участие в программных комитетах конференций, grant panels)",
            type=QuestionType.TEXT,
            rationale="EB-1A Criterion 4: Participation as a judge of the work of others",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_4"],
        ),
        IntakeQuestion(
            id="judging_venues",
            text_template="В каких конкретно журналах, конференциях или организациях вы выступали рецензентом/судьёй?",
            type=QuestionType.TEXT,
            hint="Укажите названия: Nature, Science, NeurIPS, CVPR и т.д.",
            rationale="Specific venues demonstrate expertise and recognition in the field",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_4"],
        ),
        IntakeQuestion(
            id="judging_frequency",
            text_template="Как часто вас приглашают для рецензирования/судейства? Сколько работ вы рецензировали?",
            type=QuestionType.TEXT,
            hint="Например: 50+ рецензий для NeurIPS за 5 лет",
            rationale="Frequency shows sustained recognition as an expert",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_4"],
        ),
        IntakeQuestion(
            id="judging_invitation",
            text_template="Как вас приглашали для судейства? По рекомендации, по репутации, на основании публикаций?",
            type=QuestionType.TEXT,
            hint="Важно показать, что приглашение основано на вашей экспертизе",
            rationale="Shows recognition of expertise by others in the field",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_4"],
        ),
        # Criterion 3: Published material about the applicant
        IntakeQuestion(
            id="media_press",
            text_template="Писали ли о вас или вашей работе в СМИ, прессе, профессиональных изданиях?",
            type=QuestionType.TEXT,
            hint="Например: интервью в TechCrunch, статья о вас в Nature News, Forbes 30 Under 30",
            rationale="EB-1A Criterion 3: Published material about the alien in professional publications",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_3"],
        ),
        IntakeQuestion(
            id="media_about_you",
            text_template="Были ли публикации именно О ВАС (не ваши статьи)? Укажите издание, заголовок, дату.",
            type=QuestionType.TEXT,
            hint="Важно: статьи, где ВЫ - главный герой, а не просто упоминание",
            rationale="USCIS requires that the material is ABOUT the alien, not just authored by them",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_3"],
        ),
        IntakeQuestion(
            id="media_circulation",
            text_template="Какой тираж или охват у этих изданий? Являются ли они major trade publications или major media?",
            type=QuestionType.TEXT,
            hint="Например: Forbes (8M читателей), отраслевой журнал с 50K подписчиков",
            rationale="USCIS requires publications to be major trade or professional publications",
            tags=["intake", "talks_public_activity", "achievements", "eb1a_criterion_3"],
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


# Block 10/11: recommenders - Потенциальные рекомендатели
# Strong recommendation letters are crucial for EB-1A
BLOCK_RECOMMENDERS = IntakeBlock(
    id="recommenders",
    title="Потенциальные рекомендатели",
    description="Люди, которые могут предоставить рекомендации (критически важно для EB-1A)",
    questions=[
        IntakeQuestion(
            id="recommenders_summary",
            text_template="Кто из всех упомянутых людей (учителя, профессора, руководители, коллеги) мог бы написать наиболее сильные рекомендательные письма?",
            type=QuestionType.TEXT,
            hint="Перечислите 5-10 человек с указанием их связи с вами",
            rationale="Letters should come from experts who can speak to your extraordinary ability",
            tags=["intake", "recommenders", "background"],
        ),
        IntakeQuestion(
            id="independent_recommenders",
            text_template="Есть ли среди них НЕЗАВИСИМЫЕ эксперты, которые знают вас только по работе/репутации (не бывшие руководители)?",
            type=QuestionType.TEXT,
            hint="USCIS ценит письма от независимых экспертов выше, чем от руководителей",
            rationale="Independent expert letters carry more weight than those from supervisors",
            tags=["intake", "recommenders", "eb1a_evidence"],
        ),
        IntakeQuestion(
            id="recommender_credentials",
            text_template="Какова квалификация ваших рекомендателей? (должности, звания, достижения)",
            type=QuestionType.TEXT,
            hint="Например: профессор MIT, Fellow IEEE, автор 200+ публикаций, VP в Google",
            rationale="Recommender credentials add credibility to their assessment",
            tags=["intake", "recommenders", "eb1a_evidence"],
        ),
        IntakeQuestion(
            id="recommender_expertise",
            text_template="Являются ли ваши рекомендатели признанными экспертами в вашей узкой области?",
            type=QuestionType.TEXT,
            hint="Эксперт в той же области может лучше оценить ваш вклад",
            rationale="Field experts can best evaluate extraordinary ability claims",
            tags=["intake", "recommenders", "eb1a_evidence"],
        ),
        IntakeQuestion(
            id="recommenders_priority",
            text_template="Кого из них вы бы выделили как приоритетных кандидатов для писем? (Обычно нужно 5-7 писем)",
            type=QuestionType.TEXT,
            hint="Идеальный микс: 2-3 независимых эксперта + 2-3 бывших руководителя/коллеги",
            rationale="Mix of independent experts and collaborators strengthens the case",
            tags=["intake", "recommenders", "background"],
        ),
        IntakeQuestion(
            id="recommender_international",
            text_template="Есть ли среди рекомендателей люди из разных стран или международных организаций?",
            type=QuestionType.TEXT,
            hint="Международные рекомендатели подтверждают международное признание",
            rationale="International recommenders support international acclaim claim",
            tags=["intake", "recommenders", "eb1a_evidence"],
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


# Block 12: compensation - Зарплата и компенсация
# EB-1A Criterion 9: High salary relative to others in the field
BLOCK_COMPENSATION = IntakeBlock(
    id="compensation",
    title="Зарплата и компенсация",
    description="Информация о доходах (EB-1A Criterion 9: High Salary)",
    questions=[
        IntakeQuestion(
            id="current_salary",
            text_template="Какова ваша текущая годовая зарплата (gross, до налогов)?",
            type=QuestionType.TEXT,
            hint="Укажите валюту. Например: $180,000 USD или 15,000,000 RUB",
            rationale="EB-1A Criterion 9: Commanding a high salary relative to others in the field",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="total_compensation",
            text_template="Какова ваша полная компенсация включая бонусы, акции, опционы?",
            type=QuestionType.TEXT,
            hint="Например: base $150K + bonus $30K + RSU $50K = $230K total",
            rationale="Total compensation may be more impressive than base salary alone",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="salary_history",
            text_template="Как менялась ваша зарплата за последние 5 лет? Укажите ключевые цифры.",
            type=QuestionType.TEXT,
            hint="Например: 2020: $100K → 2022: $150K → 2024: $200K",
            rationale="Salary growth trajectory shows increasing recognition",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="salary_comparison",
            text_template="Как ваша зарплата соотносится со средней в вашей области и регионе?",
            type=QuestionType.TEXT,
            hint="Например: средняя для Senior ML Engineer в Москве $80K, у меня $150K (187%)",
            rationale="USCIS requires comparison to demonstrate salary is HIGH relative to others",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="salary_percentile",
            text_template="В каком процентиле по зарплате вы находитесь в вашей профессии? (если знаете)",
            type=QuestionType.TEXT,
            hint="Например: top 5%, top 10%. Можно использовать данные Glassdoor, Levels.fyi",
            rationale="Percentile data strengthens the high salary claim",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="special_offers",
            text_template="Получали ли вы особые предложения о работе с высокой компенсацией? (signing bonus, relocation, etc.)",
            type=QuestionType.TEXT,
            hint="Например: signing bonus $50K, relocation package $30K",
            rationale="Special recruitment efforts show market demand for your skills",
            tags=["intake", "compensation", "eb1a_criterion_9"],
        ),
        IntakeQuestion(
            id="doc_salary",
            text_template="📎 Загрузите документы о зарплате (tax returns, offer letters, pay stubs)",
            type=QuestionType.DOCUMENT,
            hint="Отправьте файлы по одному. Напишите 'готово' когда закончите или 'пропустить'",
            tags=["intake", "compensation", "document", "eb1a_criterion_9"],
        ),
    ],
)


# Block 13: final_merits - Итоговая оценка (Final Merits Determination)
# Questions for the second prong of EB-1A adjudication
BLOCK_FINAL_MERITS = IntakeBlock(
    id="final_merits",
    title="Итоговая оценка достижений",
    description="Вопросы для Final Merits Determination (второй этап оценки EB-1A)",
    questions=[
        IntakeQuestion(
            id="sustained_acclaim",
            text_template="Можете ли вы показать ПОСТОЯННОЕ признание на протяжении нескольких лет (не разовое достижение)?",
            type=QuestionType.TEXT,
            hint="Например: награды каждый год, постоянные приглашения как эксперта, растущие цитирования",
            rationale="Final merits requires evidence of SUSTAINED national/international acclaim",
            tags=["intake", "final_merits", "eb1a_final_merits"],
        ),
        IntakeQuestion(
            id="recognition_scope",
            text_template="На каком уровне вас признают в вашей области: локальный, национальный, международный?",
            type=QuestionType.TEXT,
            hint="Приведите примеры: приглашения из других стран, международные награды, глобальные публикации",
            rationale="EB-1A requires national or international acclaim, not just local recognition",
            tags=["intake", "final_merits", "eb1a_final_merits"],
        ),
        IntakeQuestion(
            id="top_percentage",
            text_template="Считаете ли вы себя в числе лучших специалистов в вашей узкой области? Почему?",
            type=QuestionType.TEXT,
            hint="EB-1A требует доказательства, что вы в 'small percentage at the very top'",
            rationale="Must demonstrate being among the small percentage at the very top of the field",
            tags=["intake", "final_merits", "eb1a_final_merits"],
        ),
        IntakeQuestion(
            id="unique_contributions",
            text_template="Какие УНИКАЛЬНЫЕ вклады вы сделали, которых не сделал никто другой в вашей области?",
            type=QuestionType.TEXT,
            hint="Первый в мире, создатель нового метода/подхода, пионер направления",
            rationale="Original contributions of major significance demonstrate extraordinary ability",
            tags=["intake", "final_merits", "eb1a_final_merits", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="industry_impact",
            text_template="Как ваша работа повлияла на индустрию или научное сообщество? Кто использует ваши разработки?",
            type=QuestionType.TEXT,
            hint="Например: мой алгоритм используется в TensorFlow, мою методологию цитируют 500+ работ",
            rationale="Impact demonstrates that contributions are of MAJOR significance",
            tags=["intake", "final_merits", "eb1a_final_merits", "eb1a_criterion_5"],
        ),
        IntakeQuestion(
            id="peer_recognition",
            text_template="Как вас воспринимают коллеги и эксперты в вашей области? Есть ли цитаты, отзывы?",
            type=QuestionType.TEXT,
            hint="Например: 'ведущий эксперт', приглашения написать главы в учебники, отзывы коллег",
            rationale="Peer recognition is strong evidence of standing in the field",
            tags=["intake", "final_merits", "eb1a_final_merits"],
        ),
        IntakeQuestion(
            id="benefit_to_us",
            text_template="Как ваша работа в США будет выгодна для страны? (национальный интерес)",
            type=QuestionType.TEXT,
            hint="Продвижение науки, создание рабочих мест, экономический вклад, обучение следующего поколения",
            rationale="EB-1A also considers prospective national benefit",
            tags=["intake", "final_merits", "eb1a_final_merits"],
        ),
    ],
)


# -------------------- REGISTRIES --------------------


INTAKE_BLOCKS: list[IntakeBlock] = [
    BLOCK_BASIC_INFO,  # 1. Basic info
    BLOCK_FAMILY_CHILDHOOD,  # 2. Family/childhood
    BLOCK_SCHOOL,  # 3. School
    BLOCK_UNIVERSITY,  # 4. University
    BLOCK_CAREER,  # 5. Career (triggers detailed career_intake)
    BLOCK_PROJECTS_RESEARCH,  # 6. Projects/research (Criterion 5, 6)
    BLOCK_AWARDS,  # 7. Awards (Criterion 1)
    BLOCK_TALKS_PUBLIC,  # 8. Public activity (Criteria 2, 3, 4)
    BLOCK_COURSES_CERTIFICATES,  # 9. Courses/certificates
    BLOCK_COMPENSATION,  # 10. Salary (Criterion 9) - NEW
    BLOCK_RECOMMENDERS,  # 11. Recommenders
    BLOCK_GOALS_USA,  # 12. Goals in USA
    BLOCK_FINAL_MERITS,  # 13. Final Merits Determination - NEW
]

BLOCKS_BY_ID: dict[str, IntakeBlock] = {block.id: block for block in INTAKE_BLOCKS}
