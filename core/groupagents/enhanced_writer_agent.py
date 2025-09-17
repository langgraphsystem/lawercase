"""
Enhanced WriterAgent - Генерация документов с интеграцией LLM Router и RAG.

Обеспечивает улучшенную генерацию документов с:
- Интеграция с LLM Router для качественной генерации
- RAG поиск для автоматического включения релевантной информации
- Интеллектуальный выбор стиля и тона
- Автоматическая проверка качества документов
- Контекстно-зависимая генерация
- Многоязычная поддержка с AI переводом
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Импорты новой архитектуры
from ..llm_router import LLMRouter, LLMRequest, ModelType, Priority, create_llm_router
from ..simple_embedder import SimpleEmbedder, create_simple_embedder
from ..basic_rag import BasicRAG, RAGQuery, SearchType, create_basic_rag

# Импорты из writer_agent для совместимости
from .writer_agent import DocumentType, DocumentFormat, Language


class DocumentGenerationRequest(BaseModel):
    """Запрос на генерацию документа"""
    document_type: DocumentType = Field(..., description="Тип документа")
    title: str = Field(..., description="Заголовок документа")
    content_data: Dict[str, Any] = Field(..., description="Данные для генерации")
    style: str = Field(default="formal", description="Стиль документа")
    language: Language = Field(default=Language.RUSSIAN, description="Язык документа")
    format: DocumentFormat = Field(default=DocumentFormat.TXT, description="Формат документа")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст генерации")
    priority: str = Field(default="normal", description="Приоритет генерации")
    use_rag: bool = Field(default=True, description="Использовать RAG для поиска информации")
    max_length: int = Field(default=2000, description="Максимальная длина документа")


class DocumentGenerationResult(BaseModel):
    """Результат генерации документа"""
    document_id: str = Field(..., description="ID документа")
    title: str = Field(..., description="Заголовок")
    content: str = Field(..., description="Содержимое документа")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")
    quality_score: float = Field(..., description="Оценка качества")
    suggestions: List[str] = Field(default_factory=list, description="Предложения по улучшению")
    sources: List[str] = Field(default_factory=list, description="Источники информации")
    generation_time: float = Field(..., description="Время генерации")
    word_count: int = Field(..., description="Количество слов")
    success: bool = Field(default=True, description="Успешность генерации")
    error: Optional[str] = Field(default=None, description="Ошибка если есть")


class DocumentTemplate(BaseModel):
    """Шаблон документа"""
    template_id: str = Field(..., description="ID шаблона")
    name: str = Field(..., description="Название шаблона")
    document_type: DocumentType = Field(..., description="Тип документа")
    template_content: str = Field(..., description="Содержимое шаблона")
    variables: List[str] = Field(default_factory=list, description="Переменные шаблона")
    style: str = Field(..., description="Стиль шаблона")
    language: Language = Field(..., description="Язык шаблона")


class DocumentQuality(BaseModel):
    """Оценка качества документа"""
    overall_score: float = Field(..., description="Общая оценка")
    grammar_score: float = Field(..., description="Грамматика")
    style_score: float = Field(..., description="Стиль")
    completeness_score: float = Field(..., description="Полнота")
    clarity_score: float = Field(..., description="Ясность")
    issues: List[str] = Field(default_factory=list, description="Выявленные проблемы")
    suggestions: List[str] = Field(default_factory=list, description="Рекомендации")


class EnhancedWriterAgent:
    """
    Улучшенный агент для генерации документов с AI интеграцией.

    Включает:
    - Все функции базового WriterAgent
    - LLM Router для высококачественной генерации
    - RAG поиск для автоматического включения информации
    - AI-powered проверка качества
    - Интеллектуальный выбор стиля
    - Контекстно-зависимая генерация
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        embedder: Optional[SimpleEmbedder] = None,
        rag_system: Optional[BasicRAG] = None,
        memory_manager=None
    ):
        self.llm_router = llm_router
        self.embedder = embedder
        self.rag_system = rag_system
        self.memory_manager = memory_manager

        # Хранилище документов и шаблонов
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, DocumentTemplate] = {}

        # Инициализируем базовые шаблоны
        self._init_default_templates()

        # Статистика
        self.stats = {
            "documents_generated": 0,
            "templates_used": 0,
            "rag_searches_performed": 0,
            "quality_checks_performed": 0,
            "average_quality_score": 0.0
        }

    async def initialize(self) -> None:
        """Инициализация агента с AI компонентами"""
        try:
            # Создаем AI компоненты если не переданы
            if not self.llm_router:
                self.llm_router = await create_llm_router({
                    "providers": {
                        "openai": {"enabled": True},
                        "gemini": {"enabled": True},
                        "mock": {"enabled": True}
                    }
                })

            if not self.embedder:
                self.embedder = await create_simple_embedder({
                    "providers": {
                        "openai": {"enabled": True},
                        "gemini": {"enabled": True},
                        "mock": {"enabled": True}
                    }
                })

            if not self.rag_system:
                self.rag_system = await create_basic_rag(self.embedder, self.llm_router)

            # Индексируем шаблоны в RAG
            await self._index_templates_in_rag()

            print("✅ EnhancedWriterAgent инициализирован с AI компонентами")

        except Exception as e:
            print(f"⚠️ Ошибка инициализации AI компонентов: {e}")

    # Основные методы генерации

    async def generate_document(self, request: DocumentGenerationRequest) -> DocumentGenerationResult:
        """Генерация документа с AI улучшениями"""
        start_time = datetime.utcnow()

        try:
            document_id = str(uuid.uuid4())

            # 1. Поиск релевантной информации через RAG
            context_info = ""
            sources = []
            if request.use_rag and self.rag_system:
                context_info, sources = await self._gather_context_from_rag(request)

            # 2. Выбор или создание промпта
            generation_prompt = await self._create_generation_prompt(request, context_info)

            # 3. Генерация контента через LLM Router
            content = await self._generate_content_with_llm(generation_prompt, request)

            # 4. Постобработка и улучшение
            processed_content = await self._post_process_content(content, request)

            # 5. Оценка качества
            quality_assessment = await self._assess_document_quality(processed_content, request)

            # 6. Создание финального документа
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            word_count = len(processed_content.split())

            # Сохраняем документ
            document_data = {
                "id": document_id,
                "title": request.title,
                "content": processed_content,
                "type": request.document_type,
                "format": request.format,
                "language": request.language,
                "style": request.style,
                "created_at": datetime.utcnow(),
                "metadata": {
                    **request.content_data,
                    "generation_method": "ai_enhanced",
                    "sources": sources,
                    "quality_score": quality_assessment.overall_score
                }
            }

            self.documents[document_id] = document_data
            self.stats["documents_generated"] += 1

            if sources:
                self.stats["rag_searches_performed"] += 1

            return DocumentGenerationResult(
                document_id=document_id,
                title=request.title,
                content=processed_content,
                metadata=document_data["metadata"],
                quality_score=quality_assessment.overall_score,
                suggestions=quality_assessment.suggestions,
                sources=sources,
                generation_time=generation_time,
                word_count=word_count,
                success=True
            )

        except Exception as e:
            return DocumentGenerationResult(
                document_id="",
                title=request.title,
                content="",
                metadata={},
                quality_score=0.0,
                generation_time=0.0,
                word_count=0,
                success=False,
                error=str(e)
            )

    async def improve_document(self, document_id: str, improvement_request: str) -> DocumentGenerationResult:
        """Улучшение существующего документа"""
        try:
            document = self.documents.get(document_id)
            if not document:
                raise ValueError(f"Документ {document_id} не найден")

            if not self.llm_router:
                return self._mock_improve_document(document, improvement_request)

            # Создаем промпт для улучшения
            improve_prompt = f"""
            Улучши следующий документ согласно запросу:

            Исходный документ:
            Заголовок: {document['title']}
            Содержимое: {document['content']}

            Запрос на улучшение: {improvement_request}

            Предоставь улучшенную версию документа, сохраняя его основную структуру и стиль.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты опытный редактор документов. Улучшай тексты сохраняя их стиль."},
                    {"role": "user", "content": improve_prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=2000
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                # Оцениваем качество улучшенного документа
                quality = await self._assess_document_quality(response.content, None)

                # Создаем новую версию документа
                new_document_id = str(uuid.uuid4())
                improved_document = {
                    **document,
                    "id": new_document_id,
                    "content": response.content,
                    "updated_at": datetime.utcnow(),
                    "metadata": {
                        **document["metadata"],
                        "improved_from": document_id,
                        "improvement_request": improvement_request,
                        "quality_score": quality.overall_score
                    }
                }

                self.documents[new_document_id] = improved_document

                return DocumentGenerationResult(
                    document_id=new_document_id,
                    title=document["title"],
                    content=response.content,
                    metadata=improved_document["metadata"],
                    quality_score=quality.overall_score,
                    suggestions=quality.suggestions,
                    sources=[],
                    generation_time=response.latency,
                    word_count=len(response.content.split()),
                    success=True
                )

        except Exception as e:
            return DocumentGenerationResult(
                document_id="",
                title="",
                content="",
                metadata={},
                quality_score=0.0,
                generation_time=0.0,
                word_count=0,
                success=False,
                error=str(e)
            )

    async def generate_from_template(self, template_id: str, variables: Dict[str, Any]) -> DocumentGenerationResult:
        """Генерация документа на основе шаблона"""
        try:
            template = self.templates.get(template_id)
            if not template:
                raise ValueError(f"Шаблон {template_id} не найден")

            # Создаем запрос на генерацию на основе шаблона
            request = DocumentGenerationRequest(
                document_type=template.document_type,
                title=variables.get("title", f"Документ по шаблону {template.name}"),
                content_data=variables,
                style=template.style,
                language=template.language
            )

            # Генерируем документ с учетом шаблона
            result = await self.generate_document(request)

            if result.success:
                # Добавляем информацию о шаблоне
                result.metadata["template_id"] = template_id
                result.metadata["template_name"] = template.name
                self.stats["templates_used"] += 1

            return result

        except Exception as e:
            return DocumentGenerationResult(
                document_id="",
                title="",
                content="",
                metadata={},
                quality_score=0.0,
                generation_time=0.0,
                word_count=0,
                success=False,
                error=str(e)
            )

    async def translate_document(self, document_id: str, target_language: Language) -> DocumentGenerationResult:
        """Перевод документа на другой язык"""
        try:
            document = self.documents.get(document_id)
            if not document:
                raise ValueError(f"Документ {document_id} не найден")

            if not self.llm_router:
                return self._mock_translate_document(document, target_language)

            # Создаем промпт для перевода
            translate_prompt = f"""
            Переведи следующий документ на {target_language}:

            Заголовок: {document['title']}
            Содержимое: {document['content']}

            Сохрани структуру, стиль и формальность оригинального документа.
            Предоставь только переведенный текст без дополнительных комментариев.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты профессиональный переводчик юридических документов."},
                    {"role": "user", "content": translate_prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=2000
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                # Создаем переведенный документ
                translated_id = str(uuid.uuid4())
                translated_document = {
                    **document,
                    "id": translated_id,
                    "content": response.content,
                    "language": target_language,
                    "created_at": datetime.utcnow(),
                    "metadata": {
                        **document["metadata"],
                        "translated_from": document_id,
                        "original_language": document["language"],
                        "translation_method": "ai_llm"
                    }
                }

                self.documents[translated_id] = translated_document

                return DocumentGenerationResult(
                    document_id=translated_id,
                    title=document["title"],
                    content=response.content,
                    metadata=translated_document["metadata"],
                    quality_score=0.85,  # Предполагаем хорошее качество перевода
                    suggestions=[],
                    sources=[],
                    generation_time=response.latency,
                    word_count=len(response.content.split()),
                    success=True
                )

        except Exception as e:
            return DocumentGenerationResult(
                document_id="",
                title="",
                content="",
                metadata={},
                quality_score=0.0,
                generation_time=0.0,
                word_count=0,
                success=False,
                error=str(e)
            )

    # Вспомогательные методы

    async def _gather_context_from_rag(self, request: DocumentGenerationRequest) -> tuple[str, List[str]]:
        """Сбор контекстной информации через RAG"""
        try:
            if not self.rag_system:
                return "", []

            # Формируем поисковый запрос
            search_query = f"{request.title} {request.document_type} {' '.join(str(v) for v in request.content_data.values())}"

            # Выполняем поиск
            rag_response = await self.rag_system.search(
                search_query,
                max_results=3,
                search_type="semantic"
            )

            if rag_response.success and rag_response.sources:
                context_parts = []
                sources = []

                for source in rag_response.sources:
                    context_parts.append(source.chunk.content)
                    sources.append(source.chunk.metadata.get("title", "Unknown source"))

                context_info = "\n\n".join(context_parts)
                return context_info, sources

        except Exception as e:
            print(f"Ошибка RAG поиска: {e}")

        return "", []

    async def _create_generation_prompt(self, request: DocumentGenerationRequest, context_info: str) -> str:
        """Создание промпта для генерации документа"""
        # Базовый промпт в зависимости от типа документа
        type_prompts = {
            DocumentType.LETTER: "Создай официальное письмо",
            DocumentType.CONTRACT: "Составь договор",
            DocumentType.MOTION: "Подготовь ходатайство",
            DocumentType.BRIEF: "Напиши краткую справку",
            DocumentType.MEMO: "Создай служебную записку",
            DocumentType.REPORT: "Составь отчет",
            DocumentType.EMAIL: "Напиши деловое электронное письмо",
            DocumentType.NOTICE: "Подготовь уведомление"
        }

        base_prompt = type_prompts.get(request.document_type, "Создай документ")

        prompt_parts = [
            f"{base_prompt} со следующими параметрами:",
            f"Заголовок: {request.title}",
            f"Стиль: {request.style}",
            f"Язык: {request.language}",
            f"Максимальная длина: {request.max_length} слов",
            ""
        ]

        # Добавляем данные для генерации
        if request.content_data:
            prompt_parts.append("Используй следующую информацию:")
            for key, value in request.content_data.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")

        # Добавляем контекст из RAG
        if context_info:
            prompt_parts.extend([
                "Релевантная информация из базы знаний:",
                context_info,
                ""
            ])

        # Добавляем специфичные инструкции
        prompt_parts.extend([
            "Требования:",
            "- Используй профессиональный юридический язык",
            "- Структурируй документ логично",
            "- Включи все необходимые разделы",
            "- Убедись в грамматической правильности",
            "- Следуй указанному стилю"
        ])

        return "\n".join(prompt_parts)

    async def _generate_content_with_llm(self, prompt: str, request: DocumentGenerationRequest) -> str:
        """Генерация контента через LLM Router"""
        try:
            if not self.llm_router:
                return self._generate_mock_content(request)

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты опытный юридический писатель и документооборотчик."},
                    {"role": "user", "content": prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=min(request.max_length * 2, 2000),  # Даем запас для генерации
                priority=Priority.HIGH if request.priority == "high" else Priority.NORMAL
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                return response.content
            else:
                return self._generate_mock_content(request)

        except Exception as e:
            print(f"Ошибка генерации через LLM: {e}")
            return self._generate_mock_content(request)

    async def _post_process_content(self, content: str, request: DocumentGenerationRequest) -> str:
        """Постобработка сгенерированного контента"""
        try:
            # Базовая обработка - удаление лишних пробелов, форматирование
            processed = content.strip()

            # Ограничение по длине если необходимо
            words = processed.split()
            if len(words) > request.max_length:
                processed = " ".join(words[:request.max_length]) + "..."

            # Дополнительная обработка в зависимости от типа документа
            if request.document_type == DocumentType.LETTER:
                processed = self._format_as_letter(processed, request.content_data)
            elif request.document_type == DocumentType.CONTRACT:
                processed = self._format_as_contract(processed)

            return processed

        except Exception:
            return content

    async def _assess_document_quality(self, content: str, request: Optional[DocumentGenerationRequest]) -> DocumentQuality:
        """Оценка качества документа"""
        try:
            if self.llm_router and request:
                return await self._ai_assess_quality(content, request)
            else:
                return self._basic_assess_quality(content)

        except Exception:
            return self._basic_assess_quality(content)

    async def _ai_assess_quality(self, content: str, request: DocumentGenerationRequest) -> DocumentQuality:
        """AI оценка качества документа"""
        try:
            quality_prompt = f"""
            Оцени качество следующего документа по критериям:
            1. Грамматика и орфография (0-1)
            2. Стиль и тон (0-1)
            3. Полнота информации (0-1)
            4. Ясность изложения (0-1)

            Документ:
            {content}

            Тип документа: {request.document_type}
            Требуемый стиль: {request.style}

            Ответь в формате JSON с оценками и списком проблем/рекомендаций.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты эксперт по качеству юридических документов."},
                    {"role": "user", "content": quality_prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=500
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                try:
                    quality_data = json.loads(response.content)

                    grammar = quality_data.get("grammar", 0.8)
                    style = quality_data.get("style", 0.8)
                    completeness = quality_data.get("completeness", 0.8)
                    clarity = quality_data.get("clarity", 0.8)

                    overall = (grammar + style + completeness + clarity) / 4

                    self.stats["quality_checks_performed"] += 1

                    return DocumentQuality(
                        overall_score=overall,
                        grammar_score=grammar,
                        style_score=style,
                        completeness_score=completeness,
                        clarity_score=clarity,
                        issues=quality_data.get("issues", []),
                        suggestions=quality_data.get("suggestions", [])
                    )

                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return self._basic_assess_quality(content)

    def _basic_assess_quality(self, content: str) -> DocumentQuality:
        """Базовая оценка качества документа"""
        # Простые эвристики для оценки
        word_count = len(content.split())

        # Grammar score - базовая проверка
        grammar_score = 0.9 if word_count > 10 else 0.5

        # Style score - проверка формальности
        formal_words = ["согласно", "таким образом", "в соответствии", "настоящим"]
        style_score = min(1.0, sum(1 for word in formal_words if word in content.lower()) * 0.2 + 0.6)

        # Completeness - по длине
        completeness_score = min(1.0, word_count / 100)

        # Clarity - простая проверка
        clarity_score = 0.8 if len(content.split('.')) > 1 else 0.6

        overall = (grammar_score + style_score + completeness_score + clarity_score) / 4

        return DocumentQuality(
            overall_score=overall,
            grammar_score=grammar_score,
            style_score=style_score,
            completeness_score=completeness_score,
            clarity_score=clarity_score,
            issues=[],
            suggestions=["Рекомендуется профессиональный обзор документа"]
        )

    def _init_default_templates(self) -> None:
        """Инициализация базовых шаблонов"""
        # Шаблон письма
        letter_template = DocumentTemplate(
            template_id="letter_formal",
            name="Официальное письмо",
            document_type=DocumentType.LETTER,
            template_content="""
            Кому: {recipient}
            От: {sender}
            Дата: {date}
            Тема: {subject}

            Уважаемый(ая) {recipient_name},

            {main_content}

            С уважением,
            {sender_name}
            {sender_title}
            """,
            variables=["recipient", "sender", "date", "subject", "recipient_name", "main_content", "sender_name", "sender_title"],
            style="formal",
            language=Language.RUSSIAN
        )

        # Шаблон договора
        contract_template = DocumentTemplate(
            template_id="contract_service",
            name="Договор оказания услуг",
            document_type=DocumentType.CONTRACT,
            template_content="""
            ДОГОВОР ОКАЗАНИЯ УСЛУГ

            Заказчик: {client_name}
            Исполнитель: {provider_name}
            Предмет договора: {service_description}
            Стоимость: {price}
            Срок выполнения: {deadline}

            {additional_terms}
            """,
            variables=["client_name", "provider_name", "service_description", "price", "deadline", "additional_terms"],
            style="formal",
            language=Language.RUSSIAN
        )

        self.templates["letter_formal"] = letter_template
        self.templates["contract_service"] = contract_template

    async def _index_templates_in_rag(self) -> None:
        """Индексация шаблонов в RAG системе"""
        try:
            if not self.rag_system:
                return

            for template in self.templates.values():
                await self.rag_system.add_document(
                    title=f"Шаблон: {template.name}",
                    content=f"Тип: {template.document_type}, Содержимое: {template.template_content}",
                    metadata={
                        "template_id": template.template_id,
                        "document_type": template.document_type,
                        "style": template.style,
                        "language": template.language
                    }
                )

        except Exception as e:
            print(f"Ошибка индексации шаблонов: {e}")

    # Mock методы для работы без AI

    def _generate_mock_content(self, request: DocumentGenerationRequest) -> str:
        """Mock генерация контента"""
        type_content = {
            DocumentType.LETTER: f"Уважаемые {request.content_data.get('recipient', 'коллеги')},\n\nНастоящим сообщаем о {request.title}.\n\nС уважением,\n{request.content_data.get('sender', 'Отправитель')}",
            DocumentType.CONTRACT: f"ДОГОВОР\n\n1. Предмет договора: {request.title}\n2. Стороны: {request.content_data.get('parties', 'Стороны договора')}\n3. Условия выполнения...",
            DocumentType.MEMO: f"СЛУЖЕБНАЯ ЗАПИСКА\n\nТема: {request.title}\n\n{request.content_data.get('content', 'Содержание служебной записки')}"
        }

        return type_content.get(request.document_type, f"Документ на тему: {request.title}\n\n{request.content_data}")

    def _mock_improve_document(self, document: Dict[str, Any], improvement_request: str) -> DocumentGenerationResult:
        """Mock улучшение документа"""
        improved_content = f"{document['content']}\n\n[УЛУЧШЕНО: {improvement_request}]"

        return DocumentGenerationResult(
            document_id=str(uuid.uuid4()),
            title=document["title"],
            content=improved_content,
            metadata={"mock_improvement": True},
            quality_score=0.85,
            suggestions=["Mock улучшение выполнено"],
            sources=[],
            generation_time=0.1,
            word_count=len(improved_content.split()),
            success=True
        )

    def _mock_translate_document(self, document: Dict[str, Any], target_language: Language) -> DocumentGenerationResult:
        """Mock перевод документа"""
        translated_content = f"[ПЕРЕВЕДЕНО НА {target_language}] {document['content']}"

        return DocumentGenerationResult(
            document_id=str(uuid.uuid4()),
            title=document["title"],
            content=translated_content,
            metadata={"mock_translation": True},
            quality_score=0.8,
            suggestions=[],
            sources=[],
            generation_time=0.1,
            word_count=len(translated_content.split()),
            success=True
        )

    def _format_as_letter(self, content: str, data: Dict[str, Any]) -> str:
        """Форматирование как письмо"""
        if not content.startswith("Уважаемый"):
            recipient = data.get("recipient", "Уважаемые коллеги")
            content = f"Уважаемый(ая) {recipient},\n\n{content}"

        if not content.endswith("С уважением"):
            sender = data.get("sender", "Отправитель")
            content += f"\n\nС уважением,\n{sender}"

        return content

    def _format_as_contract(self, content: str) -> str:
        """Форматирование как договор"""
        if not content.upper().startswith("ДОГОВОР"):
            content = f"ДОГОВОР\n\n{content}"
        return content

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Получение документа по ID"""
        return self.documents.get(document_id)

    def list_documents(self, document_type: Optional[DocumentType] = None) -> List[Dict[str, Any]]:
        """Список документов с фильтрацией по типу"""
        documents = list(self.documents.values())

        if document_type:
            documents = [doc for doc in documents if doc.get("type") == document_type]

        return documents

    def get_templates(self) -> List[DocumentTemplate]:
        """Получение списка шаблонов"""
        return list(self.templates.values())

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики агента"""
        return {
            **self.stats,
            "ai_components": {
                "llm_router": self.llm_router is not None,
                "embedder": self.embedder is not None,
                "rag_system": self.rag_system is not None
            },
            "total_documents": len(self.documents),
            "total_templates": len(self.templates)
        }


# Factory функция
async def create_enhanced_writer_agent(
    llm_router: Optional[LLMRouter] = None,
    embedder: Optional[SimpleEmbedder] = None,
    rag_system: Optional[BasicRAG] = None,
    memory_manager=None
) -> EnhancedWriterAgent:
    """Создание улучшенного агента генерации документов"""
    agent = EnhancedWriterAgent(llm_router, embedder, rag_system, memory_manager)
    await agent.initialize()
    return agent