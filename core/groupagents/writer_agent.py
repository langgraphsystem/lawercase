"""
WriterAgent - Генерация документов и писем.

Обеспечивает:
- Template-based генерацию документов
- Multi-language support
- PDF generation functionality
- Approval workflow integration
- Style recommendations
- Document versioning
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

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


class WriterError(Exception):
    """Исключение для ошибок WriterAgent"""

    pass


class TemplateError(Exception):
    """Исключение для ошибок шаблонов"""

    pass


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
            if key == "document_type" and document.document_type != value:
                return False
            elif key == "language" and document.language != value:
                return False
            elif key == "generated_by" and document.generated_by != value:
                return False
            elif key == "case_id" and document.metadata.get("case_id") != value:
                return False
            elif key == "approval_status" and document.approval_status != value:
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
            except Exception:
                pass  # Ignore initialization errors

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
        }
