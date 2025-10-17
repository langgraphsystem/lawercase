"""
WriterAgent - Генерация документов и писем.

Обеспечивает:
- Template-based генерацию документов
- Multi-language support
- PDF generation functionality
- Approval workflow integration
- Style recommendations
- Document versioning
- Few-shot learning для юридических секций
- Библиотека примеров и паттернов
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent


class _WriterBaseModel(BaseModel):
    """Base class to keep dumps JSON-friendly for enums/datetimes."""

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        return super().model_dump(*args, **kwargs)


class DocumentType(str, Enum):
    """Типы документов"""

    LETTER = "letter"
    CONTRACT = "contract"
    MOTION = "motion"
    BRIEF = "brief"
    MEMO = "memo"
    REPORT = "report"
    EMAIL = "email"
    NOTICE = "notice"
    PETITION = "petition"
    RESPONSE = "response"


class DocumentFormat(str, Enum):
    """Форматы документов"""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class Language(str, Enum):
    """Поддерживаемые языки"""

    ENGLISH = "en"
    RUSSIAN = "ru"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"


class ToneStyle(str, Enum):
    """Стили тона документа"""

    FORMAL = "formal"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    PERSUASIVE = "persuasive"
    DIPLOMATIC = "diplomatic"
    ASSERTIVE = "assertive"


class DocumentTemplate(_WriterBaseModel):
    """Модель шаблона документа"""

    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название шаблона")
    document_type: DocumentType = Field(..., description="Тип документа")
    language: Language = Field(..., description="Язык шаблона")
    template_content: str = Field(..., description="Содержимое шаблона")
    variables: list[str] = Field(default_factory=list, description="Переменные шаблона")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные шаблона")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, description="Версия шаблона")


class DocumentRequest(_WriterBaseModel):
    """Запрос на генерацию документа"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: DocumentType = Field(..., description="Тип документа")
    template_id: str | None = Field(None, description="ID шаблона")
    content_data: dict[str, Any] = Field(..., description="Данные для генерации")
    format: DocumentFormat = Field(default=DocumentFormat.MARKDOWN, description="Формат вывода")
    language: Language = Field(default=Language.ENGLISH, description="Язык документа")
    tone: ToneStyle = Field(default=ToneStyle.PROFESSIONAL, description="Стиль тона")
    case_id: str | None = Field(None, description="Связанное дело")
    approval_required: bool = Field(default=False, description="Требуется ли одобрение")
    custom_instructions: str | None = Field(None, description="Дополнительные инструкции")

    @field_validator("content_data")
    @classmethod
    def _validate_content(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("content_data cannot be empty")
        return value


class GeneratedDocument(_WriterBaseModel):
    """Сгенерированный документ"""

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(..., description="ID запроса")
    title: str = Field(..., description="Заголовок документа")
    content: str = Field(..., description="Содержимое документа")
    format: DocumentFormat = Field(..., description="Формат документа")
    language: Language = Field(..., description="Язык документа")
    document_type: DocumentType = Field(..., description="Тип документа")
    template_used: str | None = Field(None, description="Использованный шаблон")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные документа")
    file_path: str | None = Field(None, description="Путь к файлу")
    file_size: int | None = Field(None, description="Размер файла")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: str = Field(..., description="ID пользователя")
    approval_status: str = Field(default="pending", description="Статус одобрения")
    version: int = Field(default=1, description="Версия документа")


class ApprovalWorkflow(_WriterBaseModel):
    """Workflow одобрения документа"""

    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    approver_id: str = Field(..., description="ID одобряющего")
    status: str = Field(default="pending", description="Статус одобрения")
    comments: list[str] = Field(default_factory=list, description="Комментарии")
    approval_date: datetime | None = Field(None, description="Дата одобрения")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# === Few-Shot Learning Models ===


class FewShotExample(_WriterBaseModel):
    """
    Пример для few-shot learning.

    Содержит реальный успешный пример написания секции для обучения LLM.
    """

    example_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_type: str = Field(..., description="Тип секции (awards, press, judging)")
    criterion_name: str = Field(..., description="Название критерия")
    input_data: dict[str, Any] = Field(..., description="Входные данные (evidence, context)")
    generated_content: str = Field(..., description="Сгенерированный контент")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Оценка качества (0-1)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные примера")
    tags: list[str] = Field(default_factory=list, description="Теги для фильтрации")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = Field(default=0, description="Сколько раз использовался")


class SectionPattern(_WriterBaseModel):
    """
    Переиспользуемый паттерн для написания секций.

    Содержит структурные элементы и фразы для разных типов аргументации.
    """

    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = Field(
        ..., description="Тип паттерна (opening, evidence_analysis, conclusion)"
    )
    section_types: list[str] = Field(..., description="Применимые типы секций")
    template_structure: str = Field(..., description="Шаблон структуры")
    example_phrases: list[str] = Field(default_factory=list, description="Примеры фраз")
    legal_language_hints: list[str] = Field(default_factory=list, description="Юридические фразы")
    variables: list[str] = Field(default_factory=list, description="Переменные для подстановки")
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedSection(_WriterBaseModel):
    """
    Результат генерации секции с few-shot learning.
    """

    section_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_type: str = Field(..., description="Тип секции")
    title: str = Field(..., description="Заголовок секции")
    content: str = Field(..., description="Содержимое секции")
    evidence_used: list[str] = Field(
        default_factory=list, description="Использованные доказательства"
    )
    examples_used: list[str] = Field(default_factory=list, description="ID использованных примеров")
    patterns_applied: list[str] = Field(default_factory=list, description="Применённые паттерны")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    word_count: int = Field(default=0)
    suggestions: list[str] = Field(default_factory=list, description="Предложения по улучшению")
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class WriterError(Exception):
    """Исключение для ошибок WriterAgent"""


class TemplateError(Exception):
    """Исключение для ошибок шаблонов"""


# === Few-Shot Learning Libraries ===


class ExampleLibrary:
    """
    Библиотека примеров для few-shot learning.

    Управляет хранением и извлечением успешных примеров написания секций.
    Поддерживает фильтрацию по типу секции, качеству и тегам.
    """

    def __init__(self):
        """Инициализация библиотеки примеров."""
        self._examples: dict[str, FewShotExample] = {}
        self._examples_by_type: dict[str, list[str]] = {}
        self._load_default_examples()

    async def get_examples(
        self,
        section_type: str,
        limit: int = 3,
        min_quality: float = 0.7,
        tags: list[str] | None = None,
    ) -> list[FewShotExample]:
        """
        Получить примеры для указанного типа секции.

        Args:
            section_type: Тип секции (awards, press, judging, etc.)
            limit: Максимальное количество примеров
            min_quality: Минимальная оценка качества
            tags: Дополнительные теги для фильтрации

        Returns:
            List[FewShotExample]: Отфильтрованные и отсортированные примеры
        """
        # Получаем ID примеров для типа секции
        example_ids = self._examples_by_type.get(section_type, [])

        # Фильтруем и сортируем
        examples = []
        for example_id in example_ids:
            example = self._examples.get(example_id)
            if not example:
                continue

            # Фильтр по качеству
            if example.quality_score < min_quality:
                continue

            # Фильтр по тегам
            if tags and not any(tag in example.tags for tag in tags):
                continue

            examples.append(example)

        # Сортировка по качеству и частоте использования
        examples.sort(key=lambda e: (e.quality_score, -e.usage_count), reverse=True)

        # Возвращаем топ-N примеров
        selected = examples[:limit]

        # Обновляем счётчик использования
        for example in selected:
            example.usage_count += 1

        return selected

    async def add_example(self, example: FewShotExample) -> str:
        """
        Добавить новый пример в библиотеку.

        Args:
            example: Пример для добавления

        Returns:
            str: ID добавленного примера
        """
        self._examples[example.example_id] = example

        # Индексируем по типу
        if example.section_type not in self._examples_by_type:
            self._examples_by_type[example.section_type] = []
        self._examples_by_type[example.section_type].append(example.example_id)

        return example.example_id

    async def remove_example(self, example_id: str) -> bool:
        """Удалить пример из библиотеки."""
        if example_id not in self._examples:
            return False

        example = self._examples[example_id]
        del self._examples[example_id]

        # Удаляем из индекса
        if example.section_type in self._examples_by_type:
            try:
                self._examples_by_type[example.section_type].remove(example_id)
            except ValueError:
                pass

        return True

    async def get_example_stats(self) -> dict[str, Any]:
        """Получить статистику библиотеки."""
        return {
            "total_examples": len(self._examples),
            "examples_by_type": {
                section_type: len(ids) for section_type, ids in self._examples_by_type.items()
            },
            "average_quality": sum(e.quality_score for e in self._examples.values())
            / max(len(self._examples), 1),
            "most_used": sorted(self._examples.values(), key=lambda e: e.usage_count, reverse=True)[
                :5
            ],
        }

    def _load_default_examples(self) -> None:
        """Загрузить примеры по умолчанию."""
        # Пример для Awards секции
        awards_example = FewShotExample(
            section_type="awards",
            criterion_name="Awards and Prizes",
            input_data={
                "beneficiary": "Dr. Jane Smith",
                "field": "Artificial Intelligence",
                "awards": [
                    {
                        "title": "Best Paper Award",
                        "organization": "IEEE International Conference",
                        "date": "2023",
                    }
                ],
            },
            generated_content="""**Awards and Prizes**

Dr. Smith has received the prestigious Best Paper Award from the IEEE International Conference, \
demonstrating recognition by leading experts in Artificial Intelligence. This award, selected from \
over 1,000 submissions through rigorous peer review, establishes Dr. Smith's exceptional \
contributions to the field.

The competitive selection process and international recognition satisfy the regulatory requirements \
of 8 CFR § 204.5(h)(3)(i), establishing nationally and internationally recognized excellence.""",
            quality_score=0.9,
            tags=["awards", "peer-reviewed", "international"],
        )

        # Пример для Press секции
        press_example = FewShotExample(
            section_type="press",
            criterion_name="Published Material About Beneficiary",
            input_data={
                "beneficiary": "Dr. John Doe",
                "field": "Quantum Computing",
                "articles": [
                    {
                        "title": "Breakthrough in Quantum Computing",
                        "publication": "Scientific American",
                        "date": "2023",
                    }
                ],
            },
            generated_content="""**Published Material About Beneficiary**

Dr. Doe has been featured in Scientific American, a major publication with international \
circulation exceeding 500,000 readers. The article, written by independent science journalist \
Sarah Johnson, focuses specifically on Dr. Doe's groundbreaking research in quantum computing.

This third-party recognition in a major media outlet demonstrates widespread acclaim and satisfies \
8 CFR § 204.5(h)(3)(iii). Per *Grimson v. INS*, published material about the beneficiary in \
professional or major trade publications is strong evidence of extraordinary ability.""",
            quality_score=0.85,
            tags=["press", "major_media", "third_party"],
        )

        # Пример для Judging секции
        judging_example = FewShotExample(
            section_type="judging",
            criterion_name="Participation as Judge",
            input_data={
                "beneficiary": "Prof. Maria Garcia",
                "field": "Robotics",
                "judging_roles": [
                    {
                        "role": "Program Committee Member",
                        "organization": "ICRA 2023",
                        "responsibility": "Peer review of 50+ submissions",
                    }
                ],
            },
            generated_content="""**Participation as Judge**

Prof. Garcia has served as a Program Committee Member for ICRA 2023, one of the premier \
conferences in Robotics. In this capacity, Prof. Garcia evaluated over 50 research submissions \
through rigorous peer review, making acceptance recommendations that shaped the conference program.

This judging role demonstrates that Prof. Garcia is recognized by peers as having the expertise \
to evaluate the work of others in Robotics. Per 8 CFR § 204.5(h)(3)(iv), participation as a \
judge of the work of others in the field is evidence of extraordinary ability.""",
            quality_score=0.88,
            tags=["judging", "peer_review", "conference"],
        )

        # Добавляем примеры синхронно при инициализации
        for example in [awards_example, press_example, judging_example]:
            self._examples[example.example_id] = example
            if example.section_type not in self._examples_by_type:
                self._examples_by_type[example.section_type] = []
            self._examples_by_type[example.section_type].append(example.example_id)


class SectionPatternLibrary:
    """
    Библиотека структурных паттернов для написания секций.

    Содержит переиспользуемые шаблоны структуры, фразы и
    юридические формулировки для разных типов аргументации.
    """

    def __init__(self):
        """Инициализация библиотеки паттернов."""
        self._patterns: dict[str, SectionPattern] = {}
        self._patterns_by_type: dict[str, list[str]] = {}
        self._load_default_patterns()

    async def get_patterns(
        self,
        section_type: str,
        pattern_types: list[str] | None = None,
    ) -> list[SectionPattern]:
        """
        Получить паттерны для типа секции.

        Args:
            section_type: Тип секции
            pattern_types: Типы паттернов (opening, analysis, conclusion)

        Returns:
            List[SectionPattern]: Подходящие паттерны
        """
        all_patterns = []

        for pattern in self._patterns.values():
            # Проверяем применимость к типу секции
            if section_type not in pattern.section_types:
                continue

            # Фильтр по типам паттернов
            if pattern_types and pattern.pattern_type not in pattern_types:
                continue

            all_patterns.append(pattern)

        return all_patterns

    async def add_pattern(self, pattern: SectionPattern) -> str:
        """Добавить паттерн в библиотеку."""
        self._patterns[pattern.pattern_id] = pattern

        # Индексируем по типам секций
        for section_type in pattern.section_types:
            if section_type not in self._patterns_by_type:
                self._patterns_by_type[section_type] = []
            self._patterns_by_type[section_type].append(pattern.pattern_id)

        return pattern.pattern_id

    def _load_default_patterns(self) -> None:
        """Загрузить паттерны по умолчанию."""
        # Паттерн вступления
        opening_pattern = SectionPattern(
            pattern_type="opening",
            section_types=["awards", "press", "judging", "membership", "contributions"],
            template_structure="""{beneficiary} has {achievement_summary} in {field}. \
This {evidence_type} demonstrates {quality_descriptor} and satisfies the regulatory \
requirements of 8 CFR § {regulation_code}.""",
            example_phrases=[
                "has received {count} nationally and internationally recognized awards",
                "has been featured in {count} professional publications and major media outlets",
                "has served as a judge for {count} prestigious conferences and journals",
            ],
            legal_language_hints=[
                "satisfies the regulatory requirements",
                "meets the plain language of the criterion",
                "demonstrates extraordinary ability",
                "establishes sustained national and international acclaim",
            ],
            variables=[
                "beneficiary",
                "achievement_summary",
                "field",
                "evidence_type",
                "quality_descriptor",
            ],
        )

        # Паттерн анализа доказательств
        evidence_analysis_pattern = SectionPattern(
            pattern_type="evidence_analysis",
            section_types=["awards", "press", "judging", "contributions"],
            template_structure="""**{evidence_title}** ({date})

**{descriptor_1}:** {value_1}

**{descriptor_2}:** {value_2}

**Significance:** {significance_explanation}

**Evidence:** {exhibit_reference}""",
            example_phrases=[
                "demonstrates recognition by leading experts",
                "selected through rigorous peer review",
                "establishes exceptional contributions to the field",
                "provides independent third-party validation",
            ],
            legal_language_hints=[
                "competitive selection process",
                "independent third-party recognition",
                "peer and expert validation",
                "sustained excellence and acclaim",
            ],
            variables=[
                "evidence_title",
                "date",
                "descriptor_1",
                "value_1",
                "significance_explanation",
            ],
        )

        # Паттерн заключения
        conclusion_pattern = SectionPattern(
            pattern_type="conclusion",
            section_types=["awards", "press", "judging", "membership", "contributions"],
            template_structure="""**Conclusion**

The {evidence_summary} clearly establishes {possessive} {quality_statement} in {field}. \
{supporting_statement}

Per *{case_citation}*, {legal_standard}. The {evidence_characteristics} meet these standards \
and demonstrate extraordinary ability.""",
            example_phrases=[
                "quality, prestige, and competitive nature of these awards",
                "extensive coverage in professional publications and major media",
                "distinguished judging roles and peer review responsibilities",
            ],
            legal_language_hints=[
                "satisfies the regulatory requirements of 8 CFR",
                "meets the plain language of the criterion",
                "establishes sustained national and international acclaim",
                "demonstrates extraordinary ability in the field",
            ],
            variables=["evidence_summary", "possessive", "quality_statement", "case_citation"],
        )

        # Паттерн сравнительного анализа
        comparative_pattern = SectionPattern(
            pattern_type="comparative_analysis",
            section_types=["awards", "press", "contributions"],
            template_structure="""**Comparative Analysis**

{possessive} {count} {evidence_type} place {last_name} among the top echelon of professionals \
in {field}. Industry data indicates that fewer than {percentage}% of practitioners in {field} \
achieve {achievement_descriptor}.

The diversity and {quality_descriptor} demonstrate sustained excellence across multiple dimensions \
of {field}, distinguishing {last_name} from peers who may have achieved recognition in only \
limited areas.""",
            example_phrases=[
                "place among the top echelon of professionals",
                "fewer than 5% of practitioners achieve",
                "demonstrate sustained excellence across multiple dimensions",
                "distinguishing from peers",
            ],
            legal_language_hints=[
                "top percentage of the field",
                "sustained excellence",
                "distinguished from ordinary practitioners",
            ],
            variables=["possessive", "count", "evidence_type", "percentage", "quality_descriptor"],
        )

        # Добавляем паттерны
        for pattern in [
            opening_pattern,
            evidence_analysis_pattern,
            conclusion_pattern,
            comparative_pattern,
        ]:
            self._patterns[pattern.pattern_id] = pattern
            for section_type in pattern.section_types:
                if section_type not in self._patterns_by_type:
                    self._patterns_by_type[section_type] = []
                self._patterns_by_type[section_type].append(pattern.pattern_id)


class WriterAgent:
    """
    Агент для генерации документов и писем.

    Основные функции:
    - Template-based генерация документов
    - Multi-language support
    - PDF и DOCX generation
    - Approval workflow integration
    - Style recommendations и customization
    - Document versioning и tracking
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Инициализация WriterAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилища
        self._templates: dict[str, DocumentTemplate] = {}
        self._documents: dict[str, GeneratedDocument] = {}
        self._approval_workflows: dict[str, ApprovalWorkflow] = {}

        # НОВОЕ: Few-shot learning библиотеки
        self._example_library = ExampleLibrary()
        self._section_patterns = SectionPatternLibrary()
        self._generated_sections: dict[str, GeneratedSection] = {}

        # Инициализация базовых шаблонов
        self._load_default_templates()

        # Статистика
        self._generation_stats: dict[str, int] = {}

    async def agenerate_letter(self, request: DocumentRequest, user_id: str) -> GeneratedDocument:
        """
        Генерация письма с template support.

        Args:
            request: Запрос на генерацию
            user_id: ID пользователя

        Returns:
            GeneratedDocument: Сгенерированное письмо

        Raises:
            WriterError: При ошибках генерации
            TemplateError: При ошибках шаблона
        """
        try:
            # Получение или создание шаблона
            template = await self._get_or_create_template(request)

            # Генерация содержимого
            content = await self._generate_content(request, template, user_id)

            # Создание документа
            document = GeneratedDocument(
                request_id=request.request_id,
                title=self._generate_title(request),
                content=content,
                format=request.format,
                language=request.language,
                document_type=request.document_type,
                template_used=template.template_id,
                generated_by=user_id,
                approval_status="approved" if not request.approval_required else "pending",
            )

            # Сохранение документа
            self._documents[document.document_id] = document

            # Создание workflow одобрения если необходимо
            if request.approval_required:
                await self._create_approval_workflow(document, user_id)

            # Конвертация в требуемый формат
            if request.format != DocumentFormat.MARKDOWN:
                await self._convert_document_format(document, request.format)

            # Audit log
            await self._log_document_generation(request, document, user_id)

            # Обновление статистики
            self._update_stats(request.document_type)

            return document

        except Exception as e:
            await self._log_generation_error(request, user_id, e)
            raise WriterError(f"Failed to generate letter: {e!s}")

    async def agenerate_document_pdf(self, document_id: str, user_id: str) -> str:
        """
        Генерация PDF версии документа.

        Args:
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            str: Путь к PDF файлу

        Raises:
            WriterError: При ошибках генерации PDF
        """
        try:
            # Получение документа
            document = self._documents.get(document_id)
            if not document:
                raise WriterError(f"Document {document_id} not found")

            # Генерация PDF (заглушка - в реальности использовать библиотеку типа reportlab)
            pdf_path = await self._generate_pdf(document)

            # Обновление документа
            document.file_path = pdf_path
            document.format = DocumentFormat.PDF

            # Audit log
            await self._log_pdf_generation(document, user_id)

            return pdf_path

        except Exception as e:
            await self._log_generation_error(None, user_id, e)
            raise WriterError(f"Failed to generate PDF: {e!s}")

    async def aget_document(self, document_id: str, user_id: str) -> GeneratedDocument:
        """
        Получение документа по ID.

        Args:
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            GeneratedDocument: Документ

        Raises:
            WriterError: Если документ не найден
        """
        document = self._documents.get(document_id)
        if not document:
            raise WriterError(f"Document {document_id} not found")

        # Audit log
        await self._log_document_access(document, user_id)

        return document

    async def arequest_approval(
        self, document_id: str, approver_id: str, user_id: str, comments: str | None = None
    ) -> ApprovalWorkflow:
        """
        Создать запрос на одобрение документа (workflow со статусом pending).

        Args:
            document_id: ID документа для одобрения
            approver_id: ID одобряющего
            user_id: Инициатор запроса (для аудита)
            comments: Необязательные комментарии

        Returns:
            ApprovalWorkflow: Созданный workflow одобрения
        """
        document = self._documents.get(document_id)
        if not document:
            raise WriterError(f"Document {document_id} not found")

        # Если workflow уже существует — возвращаем его
        for wf in self._approval_workflows.values():
            if wf.document_id == document_id and wf.status in {"pending", "approved"}:
                return wf

        workflow = ApprovalWorkflow(
            document_id=document_id,
            approver_id=approver_id,
            status="pending",
            comments=[comments] if comments else [],
        )
        self._approval_workflows[workflow.workflow_id] = workflow

        # Обновляем документ
        document.approval_status = "pending"

        # Audit log
        await self._log_audit_event(
            user_id=user_id,
            action="approval_requested",
            payload={
                "document_id": document_id,
                "workflow_id": workflow.workflow_id,
                "approver_id": approver_id,
            },
        )

        return workflow

    async def asearch_documents(
        self, filters: dict[str, Any], user_id: str
    ) -> list[GeneratedDocument]:
        """
        Поиск документов по фильтрам.

        Args:
            filters: Фильтры поиска
            user_id: ID пользователя

        Returns:
            List[GeneratedDocument]: Найденные документы
        """
        results = []

        for document in self._documents.values():
            if self._matches_filters(document, filters):
                results.append(document)

        # Сортировка по дате создания
        results.sort(key=lambda x: x.generated_at, reverse=True)

        # Audit log
        await self._log_document_search(filters, len(results), user_id)

        return results

    async def acreate_template(
        self, template_data: dict[str, Any], user_id: str
    ) -> DocumentTemplate:
        """
        Создание нового шаблона документа.

        Args:
            template_data: Данные шаблона
            user_id: ID пользователя

        Returns:
            DocumentTemplate: Созданный шаблон
        """
        try:
            template = DocumentTemplate(**template_data)

            # Валидация шаблона
            await self._validate_template(template)

            # Сохранение шаблона
            self._templates[template.template_id] = template

            # Audit log
            await self._log_template_creation(template, user_id)

            return template

        except Exception as e:
            await self._log_template_error(template_data, user_id, e)
            raise TemplateError(f"Failed to create template: {e!s}")

    async def aapprove_document(
        self, document_id: str, approver_id: str, comments: str | None = None
    ) -> ApprovalWorkflow:
        """
        Одобрение документа.

        Args:
            document_id: ID документа
            approver_id: ID одобряющего
            comments: Комментарии

        Returns:
            ApprovalWorkflow: Workflow одобрения
        """
        document = self._documents.get(document_id)
        if not document:
            raise WriterError(f"Document {document_id} not found")

        # Поиск workflow одобрения
        workflow = None
        for wf in self._approval_workflows.values():
            if wf.document_id == document_id:
                workflow = wf
                break

        if not workflow:
            raise WriterError(f"Approval workflow for document {document_id} not found")

        # Обновление статуса
        workflow.status = "approved"
        workflow.approval_date = datetime.utcnow()
        if comments:
            workflow.comments.append(comments)

        # Обновление документа
        document.approval_status = "approved"

        # Audit log
        await self._log_document_approval(document, workflow, approver_id)

        return workflow

    async def _get_or_create_template(self, request: DocumentRequest) -> DocumentTemplate:
        """Получение или создание шаблона"""
        if request.template_id:
            template = self._templates.get(request.template_id)
            if template:
                return template

        # Поиск подходящего шаблона
        for template in self._templates.values():
            if (
                template.document_type == request.document_type
                and template.language == request.language
            ):
                return template

        # Создание шаблона по умолчанию
        return await self._create_default_template(request)

    async def _generate_content(
        self, request: DocumentRequest, template: DocumentTemplate, user_id: str
    ) -> str:
        """Генерация содержимого документа"""

        # Замена переменных в шаблоне
        content = template.template_content

        # Обработка переменных
        for var in template.variables:
            value = request.content_data.get(var, f"[{var}]")
            content = content.replace(f"{{{var}}}", str(value))

        # Применение стиля тона
        content = await self._apply_tone_style(content, request.tone, request.language)

        # Добавление кастомных инструкций
        if request.custom_instructions:
            content = await self._apply_custom_instructions(content, request.custom_instructions)

        return content

    async def _apply_tone_style(self, content: str, tone: ToneStyle, language: Language) -> str:
        """Применение стиля тона к содержимому"""

        # Словари стилевых модификаций
        tone_modifications = {
            ToneStyle.FORMAL: {
                Language.ENGLISH: {
                    "Dear": "Dear",
                    "Thank you": "I would like to express my gratitude",
                    "Please": "I would kindly request",
                },
                Language.RUSSIAN: {
                    "Уважаемый": "Глубокоуважаемый",
                    "Спасибо": "Выражаю благодарность",
                    "Пожалуйста": "Прошу Вас",
                },
            },
            ToneStyle.CASUAL: {
                Language.ENGLISH: {
                    "Dear": "Hi",
                    "I would like to express": "Thanks for",
                    "I would kindly request": "Could you please",
                },
                Language.RUSSIAN: {
                    "Уважаемый": "Привет",
                    "Выражаю благодарность": "Спасибо",
                    "Прошу Вас": "Можешь",
                },
            },
        }

        modifications = tone_modifications.get(tone, {}).get(language, {})

        for original, replacement in modifications.items():
            content = content.replace(original, replacement)

        return content

    async def _apply_custom_instructions(self, content: str, instructions: str) -> str:
        """Применение кастомных инструкций"""
        # Простая реализация - добавление в конец
        return f"{content}\n\n[Custom Instructions: {instructions}]"

    async def _create_default_template(self, request: DocumentRequest) -> DocumentTemplate:
        """Создание шаблона по умолчанию"""

        default_templates = {
            DocumentType.LETTER: {
                Language.ENGLISH: """
Dear {recipient},

{content}

{closing}

Best regards,
{sender}
                """.strip(),
                Language.RUSSIAN: """
Уважаемый {recipient},

{content}

{closing}

С уважением,
{sender}
                """.strip(),
            },
            DocumentType.EMAIL: {
                Language.ENGLISH: """
Subject: {subject}

Dear {recipient},

{content}

Best regards,
{sender}
                """.strip(),
                Language.RUSSIAN: """
Тема: {subject}

Уважаемый {recipient},

{content}

С уважением,
{sender}
                """.strip(),
            },
        }

        template_content = default_templates.get(request.document_type, {}).get(
            request.language, "Default template for {document_type} in {language}\n\n{content}"
        )

        template = DocumentTemplate(
            name=f"Default {request.document_type.value} Template ({request.language.value})",
            document_type=request.document_type,
            language=request.language,
            template_content=template_content,
            variables=["recipient", "content", "closing", "sender", "subject"],
        )

        # Сохранение шаблона
        self._templates[template.template_id] = template

        return template

    async def _convert_document_format(
        self, document: GeneratedDocument, target_format: DocumentFormat
    ) -> None:
        """Конвертация документа в другой формат"""

        if target_format == DocumentFormat.HTML:
            # Конвертация Markdown -> HTML
            document.content = self._markdown_to_html(document.content)

        elif target_format == DocumentFormat.PDF:
            # Генерация PDF файла
            pdf_path = await self._generate_pdf(document)
            document.file_path = pdf_path

        elif target_format == DocumentFormat.TXT:
            # Конвертация в простой текст
            document.content = self._strip_markdown(document.content)

        document.format = target_format

    def _markdown_to_html(self, markdown_content: str) -> str:
        """Конвертация Markdown в HTML"""
        # Упрощенная конвертация
        html = markdown_content
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("*", "<em>").replace("*", "</em>")
        html = html.replace("\n\n", "</p><p>")
        html = f"<p>{html}</p>"
        return html

    def _strip_markdown(self, markdown_content: str) -> str:
        """Удаление Markdown разметки"""
        content = markdown_content
        content = content.replace("**", "")
        content = content.replace("*", "")
        content = content.replace("#", "")
        return content

    async def _generate_pdf(self, document: GeneratedDocument) -> str:
        """Генерация PDF файла"""
        # Заглушка для PDF генерации
        # В реальности использовать библиотеку типа reportlab или weasyprint

        pdf_path = f"documents/{document.document_id}.pdf"

        # Имитация создания PDF
        Path("documents").mkdir(exist_ok=True)
        with open(pdf_path, "w") as f:
            f.write(f"PDF content for document {document.document_id}\n")
            f.write(f"Title: {document.title}\n")
            f.write(f"Content: {document.content}\n")

        # Обновление размера файла
        document.file_size = len(document.content.encode("utf-8"))

        return pdf_path

    def _generate_title(self, request: DocumentRequest) -> str:
        """Генерация заголовка документа"""
        title_data = request.content_data.get("title")
        if title_data:
            return title_data

        subject = request.content_data.get("subject")
        if subject:
            return subject

        return f"{request.document_type.value.title()} - {datetime.now().strftime('%Y-%m-%d')}"

    async def _create_approval_workflow(self, document: GeneratedDocument, user_id: str) -> None:
        """Создание workflow одобрения"""
        workflow = ApprovalWorkflow(
            document_id=document.document_id,
            approver_id=user_id,  # В реальности получать из бизнес-логики
        )

        self._approval_workflows[workflow.workflow_id] = workflow

    def _matches_filters(self, document: GeneratedDocument, filters: dict[str, Any]) -> bool:
        """Проверка соответствия документа фильтрам"""
        for key, value in filters.items():
            if (key == "document_type" and document.document_type != value) or (
                key == "language" and document.language != value
            ):
                return False
            if (
                (key == "generated_by" and document.generated_by != value)
                or (key == "case_id" and document.metadata.get("case_id") != value)
                or (key == "approval_status" and document.approval_status != value)
            ):
                return False

        return True

    async def _validate_template(self, template: DocumentTemplate) -> None:
        """Валидация шаблона"""
        if not template.template_content.strip():
            raise TemplateError("Template content cannot be empty")

        # Проверка переменных
        content = template.template_content
        for var in template.variables:
            if f"{{{var}}}" not in content:
                raise TemplateError(f"Variable {var} not found in template content")

    def _load_default_templates(self) -> None:
        """Инициализация базовых шаблонов"""
        # Создание базовых шаблонов для разных типов документов
        default_templates = [
            {
                "name": "Standard Business Letter (English)",
                "document_type": DocumentType.LETTER,
                "language": Language.ENGLISH,
                "template_content": """
Date: {date}

{recipient_address}

Dear {recipient_name},

{content}

{closing_phrase}

Sincerely,

{sender_name}
{sender_title}
{sender_contact}
                """.strip(),
                "variables": [
                    "date",
                    "recipient_address",
                    "recipient_name",
                    "content",
                    "closing_phrase",
                    "sender_name",
                    "sender_title",
                    "sender_contact",
                ],
            },
            {
                "name": "Деловое письмо (Русский)",
                "document_type": DocumentType.LETTER,
                "language": Language.RUSSIAN,
                "template_content": """
Дата: {date}

{recipient_address}

Уважаемый(ая) {recipient_name},

{content}

{closing_phrase}

С уважением,

{sender_name}
{sender_title}
{sender_contact}
                """.strip(),
                "variables": [
                    "date",
                    "recipient_address",
                    "recipient_name",
                    "content",
                    "closing_phrase",
                    "sender_name",
                    "sender_title",
                    "sender_contact",
                ],
            },
        ]

        for template_data in default_templates:
            try:
                template = DocumentTemplate(**template_data)
                self._templates[template.template_id] = template
            except (ValidationError, KeyError, TypeError) as e:
                # Log template initialization errors but continue
                print(f"Warning: Failed to initialize template: {e}")

    def _update_stats(self, document_type: DocumentType) -> None:
        """Обновление статистики генерации"""
        key = document_type.value
        self._generation_stats[key] = self._generation_stats.get(key, 0) + 1

    async def _log_document_generation(
        self, request: DocumentRequest, document: GeneratedDocument, user_id: str
    ) -> None:
        """Логирование генерации документа"""
        await self._log_audit_event(
            user_id=user_id,
            action="document_generated",
            payload={
                "document_id": document.document_id,
                "document_type": request.document_type.value,
                "language": request.language.value,
                "format": request.format.value,
                "case_id": request.case_id,
            },
        )

    async def _log_pdf_generation(self, document: GeneratedDocument, user_id: str) -> None:
        """Логирование генерации PDF"""
        await self._log_audit_event(
            user_id=user_id,
            action="pdf_generated",
            payload={
                "document_id": document.document_id,
                "file_path": document.file_path,
                "file_size": document.file_size,
            },
        )

    async def _log_document_access(self, document: GeneratedDocument, user_id: str) -> None:
        """Логирование доступа к документу"""
        await self._log_audit_event(
            user_id=user_id,
            action="document_accessed",
            payload={
                "document_id": document.document_id,
                "document_type": document.document_type.value,
            },
        )

    async def _log_document_search(self, filters: dict[str, Any], count: int, user_id: str) -> None:
        """Логирование поиска документов"""
        await self._log_audit_event(
            user_id=user_id,
            action="documents_searched",
            payload={"filters": filters, "results_count": count},
        )

    async def _log_template_creation(self, template: DocumentTemplate, user_id: str) -> None:
        """Логирование создания шаблона"""
        await self._log_audit_event(
            user_id=user_id,
            action="template_created",
            payload={
                "template_id": template.template_id,
                "template_name": template.name,
                "document_type": template.document_type.value,
                "language": template.language.value,
            },
        )

    async def _log_document_approval(
        self, document: GeneratedDocument, workflow: ApprovalWorkflow, approver_id: str
    ) -> None:
        """Логирование одобрения документа"""
        await self._log_audit_event(
            user_id=approver_id,
            action="document_approved",
            payload={
                "document_id": document.document_id,
                "workflow_id": workflow.workflow_id,
                "approval_date": (
                    workflow.approval_date.isoformat() if workflow.approval_date else None
                ),
            },
        )

    async def _log_generation_error(
        self, request: DocumentRequest | None, user_id: str, error: Exception
    ) -> None:
        """Логирование ошибки генерации"""
        await self._log_audit_event(
            user_id=user_id,
            action="generation_error",
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "request": request.model_dump() if request else None,
            },
        )

    async def _log_template_error(
        self, template_data: dict[str, Any], user_id: str, error: Exception
    ) -> None:
        """Логирование ошибки шаблона"""
        await self._log_audit_event(
            user_id=user_id,
            action="template_error",
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "template_data": template_data,
            },
        )

    async def _log_audit_event(self, user_id: str, action: str, payload: dict[str, Any]) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"writer_agent_{user_id}",
            source="writer_agent",
            action=action,
            payload=payload,
            tags=["writer_agent", "document_generation"],
        )

        await self.memory.alog_audit(event)

    async def get_stats(self) -> dict[str, Any]:
        """Получение статистики WriterAgent"""
        return {
            "generation_stats": self._generation_stats.copy(),
            "total_documents": len(self._documents),
            "total_templates": len(self._templates),
            "pending_approvals": len(
                [wf for wf in self._approval_workflows.values() if wf.status == "pending"]
            ),
            "total_sections_generated": len(self._generated_sections),
            "example_library_stats": await self._example_library.get_example_stats(),
        }

    # === Few-Shot Learning Methods ===

    async def agenerate_legal_section(
        self,
        section_type: str,
        client_data: dict[str, Any],
        examples: list[str] | None = None,
        use_patterns: bool = True,
        user_id: str = "system",
    ) -> GeneratedSection:
        """
        Генерация юридической секции с few-shot learning.

        Использует библиотеку примеров и паттернов для создания
        высококачественного контента для EB-1A петиций.

        Args:
            section_type: Тип секции (awards, press, judging, etc.)
            client_data: Данные клиента включая evidence, beneficiary info
            examples: Опциональные ID конкретных примеров для использования
            use_patterns: Использовать ли структурные паттерны
            user_id: ID пользователя для аудита

        Returns:
            GeneratedSection: Сгенерированная секция с метаданными

        Example:
            >>> client_data = {
            ...     "beneficiary_name": "Dr. Jane Smith",
            ...     "field": "Machine Learning",
            ...     "evidence": [
            ...         {"title": "Best Paper Award", "description": "..."},
            ...         {"title": "Outstanding Researcher Award", "description": "..."}
            ...     ]
            ... }
            >>> section = await writer.agenerate_legal_section(
            ...     section_type="awards",
            ...     client_data=client_data
            ... )
            >>> print(section.content)
        """
        try:
            # 1. Получаем примеры из библиотеки
            few_shot_examples = await self._get_few_shot_examples(section_type, examples)

            # 2. Получаем структурные паттерны
            patterns = []
            if use_patterns:
                patterns = await self._section_patterns.get_patterns(section_type)

            # 3. Строим контекст с примерами
            context = await self._build_few_shot_context(
                section_type, client_data, few_shot_examples, patterns
            )

            # 4. Генерация с использованием паттернов
            section = await self._generate_with_patterns(context, section_type, client_data)

            # 5. Сохраняем сгенерированную секцию
            self._generated_sections[section.section_id] = section

            # 6. Audit log
            await self._log_section_generation(section, user_id)

            return section

        except Exception as e:
            await self._log_audit_event(
                user_id=user_id,
                action="section_generation_error",
                payload={
                    "section_type": section_type,
                    "error": str(e),
                },
            )
            raise WriterError(f"Failed to generate legal section: {e!s}")

    async def _get_few_shot_examples(
        self, section_type: str, example_ids: list[str] | None
    ) -> list[FewShotExample]:
        """
        Получить few-shot примеры для секции.

        Args:
            section_type: Тип секции
            example_ids: Конкретные ID примеров (опционально)

        Returns:
            List[FewShotExample]: Выбранные примеры
        """
        if example_ids:
            # Используем конкретные примеры
            examples = []
            for example_id in example_ids:
                example = self._example_library._examples.get(example_id)
                if example and example.section_type == section_type:
                    examples.append(example)
            return examples

        # Автоматический выбор лучших примеров
        return await self._example_library.get_examples(
            section_type=section_type,
            limit=3,
            min_quality=0.75,
        )

    async def _build_few_shot_context(
        self,
        section_type: str,
        client_data: dict[str, Any],
        examples: list[FewShotExample],
        patterns: list[SectionPattern],
    ) -> dict[str, Any]:
        """
        Построить контекст для генерации с few-shot примерами.

        Args:
            section_type: Тип секции
            client_data: Данные клиента
            examples: Few-shot примеры
            patterns: Структурные паттерны

        Returns:
            dict: Контекст для генерации
        """
        # Извлекаем данные клиента
        beneficiary = client_data.get("beneficiary_name", "The beneficiary")
        field = client_data.get("field", "their field of expertise")
        evidence = client_data.get("evidence", [])

        # Формируем контекст с примерами
        context = {
            "section_type": section_type,
            "beneficiary": beneficiary,
            "field": field,
            "evidence": evidence,
            "evidence_count": len(evidence),
            "examples": [],
            "patterns": [],
            "instructions": self._get_section_instructions(section_type),
        }

        # Добавляем few-shot примеры
        for example in examples:
            context["examples"].append(
                {
                    "input": example.input_data,
                    "output": example.generated_content,
                    "quality": example.quality_score,
                    "criterion": example.criterion_name,
                }
            )

        # Добавляем структурные паттерны
        for pattern in patterns:
            context["patterns"].append(
                {
                    "type": pattern.pattern_type,
                    "structure": pattern.template_structure,
                    "phrases": pattern.example_phrases,
                    "legal_hints": pattern.legal_language_hints,
                    "variables": pattern.variables,
                }
            )

        return context

    async def _generate_with_patterns(
        self, context: dict[str, Any], section_type: str, client_data: dict[str, Any]
    ) -> GeneratedSection:
        """
        Генерация секции с применением паттернов.

        Использует LLM для создания контента на основе контекста,
        примеров и структурных паттернов.

        Args:
            context: Контекст с примерами и паттернами
            section_type: Тип секции
            client_data: Данные клиента

        Returns:
            GeneratedSection: Сгенерированная секция
        """
        # Формируем промпт для LLM с few-shot примерами
        prompt = self._build_generation_prompt(context)

        # ПРИМЕЧАНИЕ: В реальной реализации здесь был бы вызов LLM
        # Для демонстрации создаём контент на основе паттернов
        content = await self._simulate_llm_generation(context, client_data)

        # Извлекаем использованные ресурсы
        examples_used = [str(ex["quality"]) for ex in context["examples"]]
        patterns_applied = [p["type"] for p in context["patterns"]]

        # Оцениваем качество
        confidence_score = self._calculate_section_confidence(content, context)
        suggestions = self._generate_section_suggestions(content, context)

        # Создаём секцию
        section = GeneratedSection(
            section_type=section_type,
            title=self._get_section_title(section_type),
            content=content,
            evidence_used=[str(i) for i in range(len(context.get("evidence", [])))],
            examples_used=examples_used,
            patterns_applied=patterns_applied,
            confidence_score=confidence_score,
            word_count=len(content.split()),
            suggestions=suggestions,
            metadata={
                "beneficiary": context.get("beneficiary"),
                "field": context.get("field"),
                "example_count": len(context["examples"]),
                "pattern_count": len(context["patterns"]),
            },
        )

        return section

    def _build_generation_prompt(self, context: dict[str, Any]) -> str:
        """
        Построить промпт для LLM с few-shot примерами.

        Args:
            context: Контекст генерации

        Returns:
            str: Промпт для LLM
        """
        prompt_parts = [
            f"Generate a {context['section_type']} section for an EB-1A petition.",
            f"\nBeneficiary: {context['beneficiary']}",
            f"Field: {context['field']}",
            f"Evidence Count: {context['evidence_count']}",
            f"\nInstructions:\n{context['instructions']}",
        ]

        # Добавляем few-shot примеры
        if context["examples"]:
            prompt_parts.append("\n\n=== EXAMPLES OF HIGH-QUALITY SECTIONS ===\n")
            for i, example in enumerate(context["examples"], 1):
                prompt_parts.append(f"\nExample {i} (Quality: {example['quality']:.2f}):")
                prompt_parts.append(f"Input: {json.dumps(example['input'], indent=2)}")
                prompt_parts.append(f"Output:\n{example['output']}\n")

        # Добавляем структурные паттерны
        if context["patterns"]:
            prompt_parts.append("\n\n=== STRUCTURAL PATTERNS TO FOLLOW ===\n")
            for pattern in context["patterns"]:
                prompt_parts.append(f"\n{pattern['type'].upper()} Pattern:")
                prompt_parts.append(f"Structure: {pattern['structure']}")
                prompt_parts.append(f"Example Phrases: {', '.join(pattern['phrases'][:3])}")
                prompt_parts.append(f"Legal Language: {', '.join(pattern['legal_hints'][:3])}")

        # Добавляем входные данные клиента
        prompt_parts.append("\n\n=== CLIENT DATA ===\n")
        prompt_parts.append(f"Evidence Items: {len(context['evidence'])}")
        for i, evidence_item in enumerate(context.get("evidence", [])[:5], 1):
            prompt_parts.append(f"\n{i}. {evidence_item}")

        prompt_parts.append(
            "\n\nNow generate a high-quality section following the examples and patterns above:"
        )

        return "\n".join(prompt_parts)

    async def _simulate_llm_generation(
        self, context: dict[str, Any], client_data: dict[str, Any]
    ) -> str:
        """
        Симуляция генерации LLM (заглушка).

        В реальной реализации здесь был бы вызов LLM API.
        Для демонстрации создаём контент на основе паттернов.

        Args:
            context: Контекст генерации
            client_data: Данные клиента

        Returns:
            str: Сгенерированный контент
        """
        section_type = context["section_type"]
        beneficiary = context.get("beneficiary", "The Beneficiary")
        field = context.get("field", "their field")
        evidence = context.get("evidence", [])

        # Используем паттерны из контекста
        opening_pattern = next(
            (p for p in context.get("patterns", []) if p["type"] == "opening"), None
        )

        conclusion_pattern = next(
            (p for p in context.get("patterns", []) if p["type"] == "conclusion"), None
        )

        # Генерируем контент на основе паттернов
        content_parts = []

        # Заголовок
        title = self._get_section_title(section_type)
        content_parts.append(f"**{title}**\n")

        # Вступление
        if opening_pattern:
            content_parts.append(
                f"{beneficiary} has demonstrated exceptional achievements in {field}. "
                f"This evidence establishes sustained national and international acclaim "
                f"and satisfies the regulatory requirements.\n"
            )

        # Список доказательств
        content_parts.append("\n**Evidence:**\n")
        for i, ev in enumerate(evidence[:5], 1):
            if isinstance(ev, dict):
                title_str = ev.get("title", f"Evidence {i}")
                desc = ev.get("description", "")
                content_parts.append(f"\n{i}. **{title_str}**\n   {desc[:200]}...\n")
            else:
                content_parts.append(f"\n{i}. {ev}\n")

        # Заключение
        if conclusion_pattern:
            content_parts.append(
                f"\n**Conclusion**\n\n"
                f"The evidence clearly establishes {beneficiary}'s extraordinary ability in {field}. "
                f"Per *Kazarian v. USCIS*, this meets the plain language of the criterion and "
                f"demonstrates the required level of acclaim.\n"
            )

        return "".join(content_parts)

    def _get_section_instructions(self, section_type: str) -> str:
        """Получить инструкции для типа секции."""
        instructions = {
            "awards": "Focus on prestige, competitive selection, and national/international recognition. "
            "Cite 8 CFR § 204.5(h)(3)(i) and emphasize excellence over participation.",
            "press": "Emphasize major publication outlets, independent third-party authorship, and focus "
            "on beneficiary's achievements. Cite 8 CFR § 204.5(h)(3)(iii).",
            "judging": "Highlight peer recognition, expert evaluation responsibilities, and reputation. "
            "Cite 8 CFR § 204.5(h)(3)(iv).",
            "membership": "Focus on selective membership, distinguished requirements, and professional standing. "
            "Cite 8 CFR § 204.5(h)(3)(ii).",
            "contributions": "Emphasize original contributions, major significance, and impact on the field. "
            "Cite 8 CFR § 204.5(h)(3)(v).",
        }
        return instructions.get(
            section_type, "Generate professional, legally sound content with regulatory citations."
        )

    def _get_section_title(self, section_type: str) -> str:
        """Получить заголовок для типа секции."""
        titles = {
            "awards": "Awards and Prizes for Excellence",
            "press": "Published Material About Beneficiary",
            "judging": "Participation as Judge of Others' Work",
            "membership": "Membership in Distinguished Organizations",
            "contributions": "Original Contributions of Major Significance",
        }
        return titles.get(section_type, f"{section_type.title()} Section")

    def _calculate_section_confidence(self, content: str, context: dict[str, Any]) -> float:
        """
        Рассчитать уровень уверенности в качестве секции.

        Args:
            content: Сгенерированный контент
            context: Контекст генерации

        Returns:
            float: Оценка уверенности (0.0-1.0)
        """
        score = 0.5  # Базовый уровень

        # Бонус за использование примеров
        if context.get("examples"):
            score += min(0.2, len(context["examples"]) * 0.07)

        # Бонус за использование паттернов
        if context.get("patterns"):
            score += min(0.15, len(context["patterns"]) * 0.05)

        # Бонус за длину контента
        word_count = len(content.split())
        if 300 <= word_count <= 800:
            score += 0.1
        elif 200 <= word_count <= 1000:
            score += 0.05

        # Бонус за юридические фразы
        legal_phrases = ["8 CFR", "Kazarian", "regulatory requirements", "extraordinary ability"]
        found_phrases = sum(1 for phrase in legal_phrases if phrase in content)
        score += min(0.15, found_phrases * 0.04)

        return min(1.0, score)

    def _generate_section_suggestions(self, content: str, context: dict[str, Any]) -> list[str]:
        """
        Генерация предложений по улучшению секции.

        Args:
            content: Сгенерированный контент
            context: Контекст генерации

        Returns:
            list[str]: Список предложений
        """
        suggestions = []

        word_count = len(content.split())
        if word_count < 200:
            suggestions.append("Consider expanding with more detailed evidence analysis")

        if word_count > 900:
            suggestions.append("Consider condensing to focus on strongest evidence")

        evidence_count = len(context.get("evidence", []))
        if evidence_count < 3:
            suggestions.append("Add more evidence items for stronger support (3-5 recommended)")

        if "8 CFR" not in content:
            suggestions.append("Include regulatory citation (8 CFR §)")

        if "Kazarian" not in content and context["section_type"] in ["awards", "press"]:
            suggestions.append("Consider citing Kazarian v. USCIS for legal support")

        if not any(
            word in content.lower() for word in ["extraordinary", "exceptional", "outstanding"]
        ):
            suggestions.append("Strengthen language emphasizing extraordinary ability")

        return suggestions[:5]

    async def _log_section_generation(self, section: GeneratedSection, user_id: str) -> None:
        """Логирование генерации секции."""
        await self._log_audit_event(
            user_id=user_id,
            action="legal_section_generated",
            payload={
                "section_id": section.section_id,
                "section_type": section.section_type,
                "word_count": section.word_count,
                "confidence_score": section.confidence_score,
                "examples_used": len(section.examples_used),
                "patterns_applied": len(section.patterns_applied),
            },
        )

    # === Example Library Management ===

    async def aadd_example(self, example_data: dict[str, Any], user_id: str) -> str:
        """
        Добавить новый пример в библиотеку.

        Args:
            example_data: Данные примера
            user_id: ID пользователя

        Returns:
            str: ID добавленного примера
        """
        example = FewShotExample(**example_data)
        example_id = await self._example_library.add_example(example)

        await self._log_audit_event(
            user_id=user_id,
            action="example_added",
            payload={"example_id": example_id, "section_type": example.section_type},
        )

        return example_id

    async def aget_section(self, section_id: str) -> GeneratedSection:
        """Получить сгенерированную секцию по ID."""
        section = self._generated_sections.get(section_id)
        if not section:
            raise WriterError(f"Section {section_id} not found")
        return section
