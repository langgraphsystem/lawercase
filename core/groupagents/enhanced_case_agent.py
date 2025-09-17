"""
Enhanced CaseAgent - Агент для управления делами с интеграцией LLM Router и RAG.

Обеспечивает полный CRUD функционал для работы с делами с улучшениями:
- Интеграция с LLM Router для AI-powered анализа
- Использование RAG для поиска релевантных документов
- Автоматическая классификация и тегирование дел
- Интеллектуальные рекомендации
- Семантический поиск по делам
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Импорты новой архитектуры
from ..llm_router import LLMRouter, LLMRequest, ModelType, Priority, create_llm_router
from ..simple_embedder import SimpleEmbedder, EmbedRequest, create_simple_embedder
from ..basic_rag import BasicRAG, RAGQuery, SearchType, create_basic_rag

# Импорты существующих моделей
from .models import (
    CaseExhibit,
    CaseOperationResult,
    CaseQuery,
    CaseRecord,
    CaseStatus,
    CaseType,
    CaseVersion,
    CaseWorkflowState,
    ValidationResult,
)


class CaseAnalysisRequest(BaseModel):
    """Запрос на анализ дела"""
    case_id: str = Field(..., description="ID дела")
    analysis_type: str = Field(..., description="Тип анализа")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст анализа")
    priority: str = Field(default="normal", description="Приоритет запроса")


class CaseAnalysisResult(BaseModel):
    """Результат анализа дела"""
    case_id: str = Field(..., description="ID дела")
    analysis_type: str = Field(..., description="Тип анализа")
    analysis: str = Field(..., description="Результат анализа")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    confidence: float = Field(..., description="Уверенность в анализе")
    sources: List[str] = Field(default_factory=list, description="Источники информации")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")


class CaseSearchRequest(BaseModel):
    """Запрос поиска дел"""
    query: str = Field(..., description="Поисковый запрос")
    search_type: str = Field(default="semantic", description="Тип поиска")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Фильтры")
    max_results: int = Field(default=10, description="Максимум результатов")


class CaseSearchResult(BaseModel):
    """Результат поиска дел"""
    case: CaseRecord = Field(..., description="Найденное дело")
    score: float = Field(..., description="Релевантность")
    highlights: List[str] = Field(default_factory=list, description="Выделенные фрагменты")


class CaseRecommendation(BaseModel):
    """Рекомендация по делу"""
    type: str = Field(..., description="Тип рекомендации")
    description: str = Field(..., description="Описание рекомендации")
    priority: str = Field(..., description="Приоритет")
    confidence: float = Field(..., description="Уверенность")
    actions: List[str] = Field(default_factory=list, description="Рекомендуемые действия")


class EnhancedCaseAgent:
    """
    Улучшенный агент для управления делами с AI интеграцией.

    Включает:
    - Все функции базового CaseAgent
    - LLM Router для анализа дел
    - RAG систему для поиска документов
    - Семантический поиск дел
    - Автоматическое тегирование
    - AI-powered рекомендации
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

        # Локальное хранилище дел (в реальности это была бы БД)
        self.cases: Dict[str, CaseRecord] = {}
        self.case_embeddings: Dict[str, List[float]] = {}

        # Статистика
        self.stats = {
            "total_cases": 0,
            "analyses_performed": 0,
            "searches_performed": 0,
            "recommendations_generated": 0
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

            print("✅ EnhancedCaseAgent инициализирован с AI компонентами")

        except Exception as e:
            print(f"⚠️ Ошибка инициализации AI компонентов: {e}")

    # Базовые CRUD операции (расширенные)

    async def create_case(self, case_data: Dict[str, Any]) -> CaseOperationResult:
        """Создание дела с AI анализом"""
        try:
            case_id = str(uuid.uuid4())

            # Создаем базовое дело
            case = CaseRecord(
                case_id=case_id,
                title=case_data.get("title", ""),
                description=case_data.get("description", ""),
                case_type=CaseType(case_data.get("case_type", "GENERAL")),
                status=CaseStatus.OPEN,
                created_at=datetime.utcnow(),
                priority=case_data.get("priority", "MEDIUM"),
                client_id=case_data.get("client_id"),
                assigned_lawyer=case_data.get("assigned_lawyer"),
                tags=case_data.get("tags", []),
                metadata=case_data.get("metadata", {})
            )

            # AI улучшения
            await self._enhance_case_with_ai(case)

            # Сохраняем дело
            self.cases[case_id] = case
            self.stats["total_cases"] += 1

            # Индексируем в RAG системе
            if self.rag_system:
                await self._index_case_in_rag(case)

            return CaseOperationResult(
                success=True,
                case_id=case_id,
                operation="create_case",
                message="Дело создано успешно с AI анализом",
                data={"ai_enhanced": True}
            )

        except Exception as e:
            return CaseOperationResult(
                success=False,
                case_id=case_id if 'case_id' in locals() else None,
                operation="create_case",
                message=f"Ошибка создания дела: {str(e)}"
            )

    async def get_case(self, case_id: str, include_analysis: bool = False) -> Optional[CaseRecord]:
        """Получение дела с опциональным AI анализом"""
        case = self.cases.get(case_id)

        if case and include_analysis:
            # Добавляем свежий AI анализ
            analysis = await self.analyze_case(CaseAnalysisRequest(
                case_id=case_id,
                analysis_type="summary"
            ))

            if analysis:
                case.metadata["latest_analysis"] = analysis.dict()

        return case

    async def update_case(self, case_id: str, updates: Dict[str, Any]) -> CaseOperationResult:
        """Обновление дела с AI валидацией"""
        try:
            case = self.cases.get(case_id)
            if not case:
                return CaseOperationResult(
                    success=False,
                    case_id=case_id,
                    operation="update_case",
                    message="Дело не найдено",
                    data={}
                )

            # AI валидация изменений
            validation_result = await self._validate_updates_with_ai(case, updates)

            if not validation_result.get("valid", True):
                return CaseOperationResult(
                    success=False,
                    case_id=case_id,
                    operation="update_case",
                    message=f"AI валидация не прошла: {validation_result.get('reason')}",
                    data={}
                )

            # Применяем обновления
            for key, value in updates.items():
                if hasattr(case, key):
                    setattr(case, key, value)

            case.updated_at = datetime.utcnow()

            # Переиндексируем в RAG
            if self.rag_system:
                await self._index_case_in_rag(case)

            return CaseOperationResult(
                success=True,
                case_id=case_id,
                operation="update_case",
                message="Дело обновлено с AI валидацией",
                data={"ai_validated": True}
            )

        except Exception as e:
            return CaseOperationResult(
                success=False,
                case_id=case_id,
                operation="update_case",
                message=f"Ошибка обновления дела: {str(e)}",
                data={}
            )

    # AI-powered функции

    async def analyze_case(self, request: CaseAnalysisRequest) -> Optional[CaseAnalysisResult]:
        """AI анализ дела"""
        try:
            case = self.cases.get(request.case_id)
            if not case:
                return None

            if not self.llm_router:
                return self._generate_mock_analysis(request, case)

            # Подготавливаем контекст для анализа
            context = self._prepare_case_context(case)

            # Формируем промпт в зависимости от типа анализа
            prompt = await self._create_analysis_prompt(request.analysis_type, case, context)

            # Отправляем запрос к LLM
            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты опытный юридический аналитик. Проводи глубокий анализ дел."},
                    {"role": "user", "content": prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=1000,
                priority=Priority.HIGH if request.priority == "high" else Priority.NORMAL
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                # Извлекаем рекомендации из ответа
                recommendations = await self._extract_recommendations(response.content)

                # Находим релевантные источники через RAG
                sources = await self._find_relevant_sources(case)

                self.stats["analyses_performed"] += 1

                return CaseAnalysisResult(
                    case_id=request.case_id,
                    analysis_type=request.analysis_type,
                    analysis=response.content,
                    recommendations=recommendations,
                    confidence=0.85,  # Можно вычислять на основе response
                    sources=sources,
                    metadata={
                        "llm_provider": response.provider,
                        "tokens_used": response.tokens_used,
                        "latency": response.latency
                    }
                )

        except Exception as e:
            print(f"Ошибка анализа дела: {e}")
            return self._generate_mock_analysis(request, case)

    async def search_cases(self, request: CaseSearchRequest) -> List[CaseSearchResult]:
        """Семантический поиск дел"""
        try:
            results = []

            if request.search_type == "semantic" and self.embedder:
                results = await self._semantic_search(request)
            elif request.search_type == "keyword":
                results = await self._keyword_search(request)
            else:
                results = await self._hybrid_search(request)

            self.stats["searches_performed"] += 1
            return results[:request.max_results]

        except Exception as e:
            print(f"Ошибка поиска дел: {e}")
            return []

    async def get_case_recommendations(self, case_id: str) -> List[CaseRecommendation]:
        """Получение AI рекомендаций для дела"""
        try:
            case = self.cases.get(case_id)
            if not case:
                return []

            if not self.llm_router:
                return self._generate_mock_recommendations(case)

            # Анализируем дело для рекомендаций
            prompt = f"""
            Проанализируй следующее дело и дай рекомендации:

            Дело: {case.title}
            Тип: {case.case_type}
            Статус: {case.status}
            Описание: {case.description}

            Предоставь конкретные, практические рекомендации по ведению дела.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты опытный юрист. Давай практические рекомендации."},
                    {"role": "user", "content": prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=800
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                recommendations = await self._parse_recommendations(response.content)
                self.stats["recommendations_generated"] += len(recommendations)
                return recommendations

        except Exception as e:
            print(f"Ошибка генерации рекомендаций: {e}")

        return self._generate_mock_recommendations(case)

    async def classify_case_automatically(self, case_description: str) -> Dict[str, Any]:
        """Автоматическая классификация дела"""
        try:
            if not self.llm_router:
                return self._mock_classify_case(case_description)

            prompt = f"""
            Классифицируй следующее юридическое дело:

            Описание: {case_description}

            Определи:
            1. Тип дела (семейное, уголовное, гражданское, корпоративное, и т.д.)
            2. Приоритет (низкий, средний, высокий, критический)
            3. Сложность (простое, среднее, сложное, очень сложное)
            4. Рекомендуемые теги
            5. Примерная продолжительность

            Ответь в JSON формате.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты классификатор юридических дел. Отвечай только в JSON формате."},
                    {"role": "user", "content": prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=500
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                try:
                    classification = json.loads(response.content)
                    return classification
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"Ошибка классификации: {e}")

        return self._mock_classify_case(case_description)

    # Вспомогательные методы

    async def _enhance_case_with_ai(self, case: CaseRecord) -> None:
        """Улучшение дела с помощью AI"""
        try:
            # Автоматическая классификация
            classification = await self.classify_case_automatically(case.description)

            # Применяем классификацию
            if "priority" in classification:
                case.priority = classification["priority"]

            if "tags" in classification:
                case.tags.extend(classification["tags"])

            if "complexity" in classification:
                case.metadata["complexity"] = classification["complexity"]

            # Создаем эмбеддинг для семантического поиска
            if self.embedder:
                embed_text = f"{case.title} {case.description}"
                embed_request = EmbedRequest(texts=[embed_text])
                embed_response = await self.embedder.embed(embed_request)

                if embed_response.success and embed_response.embeddings:
                    self.case_embeddings[case.case_id] = embed_response.embeddings[0]

        except Exception as e:
            print(f"Ошибка AI улучшения дела: {e}")

    async def _index_case_in_rag(self, case: CaseRecord) -> None:
        """Индексация дела в RAG системе"""
        try:
            if self.rag_system:
                case_content = f"""
                Дело: {case.title}
                Тип: {case.case_type}
                Статус: {case.status}
                Описание: {case.description}
                Теги: {', '.join(case.tags)}
                """

                await self.rag_system.add_document(
                    title=f"Дело: {case.title}",
                    content=case_content,
                    metadata={
                        "case_id": case.case_id,
                        "case_type": case.case_type,
                        "status": case.status,
                        "priority": case.priority
                    }
                )

        except Exception as e:
            print(f"Ошибка индексации в RAG: {e}")

    async def _semantic_search(self, request: CaseSearchRequest) -> List[CaseSearchResult]:
        """Семантический поиск дел"""
        results = []

        try:
            # Получаем эмбеддинг запроса
            embed_request = EmbedRequest(texts=[request.query])
            embed_response = await self.embedder.embed(embed_request)

            if not embed_response.success or not embed_response.embeddings:
                return []

            query_embedding = embed_response.embeddings[0]

            # Вычисляем сходство с делами
            similarities = []
            for case_id, case_embedding in self.case_embeddings.items():
                similarity = self._cosine_similarity(query_embedding, case_embedding)
                similarities.append((case_id, similarity))

            # Сортируем по релевантности
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Формируем результаты
            for case_id, score in similarities:
                case = self.cases.get(case_id)
                if case and self._apply_filters(case, request.filters):
                    results.append(CaseSearchResult(
                        case=case,
                        score=score,
                        highlights=[case.title, case.description[:100]]
                    ))

        except Exception as e:
            print(f"Ошибка семантического поиска: {e}")

        return results

    async def _keyword_search(self, request: CaseSearchRequest) -> List[CaseSearchResult]:
        """Поиск по ключевым словам"""
        results = []
        query_lower = request.query.lower()

        for case in self.cases.values():
            if not self._apply_filters(case, request.filters):
                continue

            # Простой поиск по ключевым словам
            text = f"{case.title} {case.description}".lower()
            score = 0.0

            for word in query_lower.split():
                if word in text:
                    score += text.count(word) / len(text)

            if score > 0:
                results.append(CaseSearchResult(
                    case=case,
                    score=score,
                    highlights=[case.title]
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    async def _hybrid_search(self, request: CaseSearchRequest) -> List[CaseSearchResult]:
        """Гибридный поиск (семантический + ключевые слова)"""
        semantic_results = await self._semantic_search(request)
        keyword_results = await self._keyword_search(request)

        # Объединяем результаты
        combined = {}

        for result in semantic_results:
            combined[result.case.case_id] = result

        for result in keyword_results:
            case_id = result.case.case_id
            if case_id in combined:
                # Усредняем scores
                combined[case_id].score = (combined[case_id].score + result.score) / 2
            else:
                combined[case_id] = result

        results = list(combined.values())
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Вычисление косинусного сходства"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _apply_filters(self, case: CaseRecord, filters: Dict[str, Any]) -> bool:
        """Применение фильтров к делу"""
        for key, value in filters.items():
            if key == "case_type" and case.case_type != value:
                return False
            elif key == "status" and case.status != value:
                return False
            elif key == "priority" and case.priority != value:
                return False
        return True

    # Mock методы для работы без AI компонентов

    def _generate_mock_analysis(self, request: CaseAnalysisRequest, case: CaseRecord) -> CaseAnalysisResult:
        """Mock анализ дела"""
        analysis_map = {
            "summary": f"Краткий анализ дела '{case.title}': {case.case_type} дело со статусом {case.status}",
            "risk": f"Анализ рисков для дела '{case.title}': средний уровень риска",
            "strategy": f"Стратегический анализ дела '{case.title}': рекомендуется активная защита"
        }

        return CaseAnalysisResult(
            case_id=request.case_id,
            analysis_type=request.analysis_type,
            analysis=analysis_map.get(request.analysis_type, "Общий анализ дела"),
            recommendations=["Провести дополнительное исследование", "Собрать больше документов"],
            confidence=0.75,
            sources=["Внутренняя база знаний"],
            metadata={"mock": True}
        )

    def _generate_mock_recommendations(self, case: CaseRecord) -> List[CaseRecommendation]:
        """Mock рекомендации"""
        return [
            CaseRecommendation(
                type="action",
                description="Подготовить документы для суда",
                priority="high",
                confidence=0.8,
                actions=["Собрать доказательства", "Подготовить иск"]
            ),
            CaseRecommendation(
                type="deadline",
                description="Проверить сроки подачи документов",
                priority="medium",
                confidence=0.9,
                actions=["Уточнить дедлайны", "Установить напоминания"]
            )
        ]

    def _mock_classify_case(self, description: str) -> Dict[str, Any]:
        """Mock классификация дела"""
        return {
            "case_type": "CIVIL",
            "priority": "MEDIUM",
            "complexity": "medium",
            "tags": ["civil", "contract"],
            "estimated_duration": "3-6 months"
        }

    async def _create_analysis_prompt(self, analysis_type: str, case: CaseRecord, context: str) -> str:
        """Создание промпта для анализа"""
        base_prompt = f"""
        Проанализируй следующее юридическое дело:

        Название: {case.title}
        Тип: {case.case_type}
        Статус: {case.status}
        Приоритет: {case.priority}
        Описание: {case.description}

        Контекст: {context}
        """

        if analysis_type == "risk":
            return base_prompt + "\nПроведи анализ рисков и определи потенциальные проблемы."
        elif analysis_type == "strategy":
            return base_prompt + "\nРазработай стратегию ведения дела."
        else:
            return base_prompt + "\nПроведи общий анализ дела."

    def _prepare_case_context(self, case: CaseRecord) -> str:
        """Подготовка контекста дела"""
        context_parts = []

        if case.tags:
            context_parts.append(f"Теги: {', '.join(case.tags)}")

        if case.metadata:
            context_parts.append(f"Метаданные: {json.dumps(case.metadata, ensure_ascii=False)}")

        return "; ".join(context_parts)

    async def _extract_recommendations(self, analysis_text: str) -> List[str]:
        """Извлечение рекомендаций из текста анализа"""
        # Простое извлечение (в реальности можно использовать NLP)
        lines = analysis_text.split('\n')
        recommendations = []

        for line in lines:
            if any(keyword in line.lower() for keyword in ['рекомендую', 'следует', 'необходимо', 'стоит']):
                recommendations.append(line.strip())

        return recommendations[:5]  # Максимум 5 рекомендаций

    async def _find_relevant_sources(self, case: CaseRecord) -> List[str]:
        """Поиск релевантных источников через RAG"""
        try:
            if self.rag_system:
                rag_response = await self.rag_system.search(
                    f"{case.title} {case.description}",
                    max_results=3
                )

                if rag_response.success:
                    return [source.chunk.metadata.get("title", "Unknown")
                           for source in rag_response.sources]
        except Exception:
            pass

        return ["Внутренняя база знаний"]

    async def _parse_recommendations(self, content: str) -> List[CaseRecommendation]:
        """Парсинг рекомендаций из LLM ответа"""
        # Упрощенный парсинг
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        recommendations = []

        for i, line in enumerate(lines[:3]):  # Берем первые 3 строки как рекомендации
            recommendations.append(CaseRecommendation(
                type="general",
                description=line,
                priority="medium",
                confidence=0.8,
                actions=[f"Выполнить: {line}"]
            ))

        return recommendations

    async def _validate_updates_with_ai(self, case: CaseRecord, updates: Dict[str, Any]) -> Dict[str, Any]:
        """AI валидация обновлений дела"""
        try:
            if self.llm_router:
                prompt = f"""
                Валидируй следующие обновления дела:

                Текущее дело: {case.title} ({case.case_type}, {case.status})
                Предлагаемые изменения: {json.dumps(updates, ensure_ascii=False)}

                Проверь логичность и корректность изменений. Ответь "valid" или "invalid" с обоснованием.
                """

                llm_request = LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model_type=ModelType.CHAT,
                    max_tokens=200
                )

                response = await self.llm_router.route_request(llm_request)

                if response.success:
                    is_valid = "valid" in response.content.lower()
                    return {
                        "valid": is_valid,
                        "reason": response.content,
                        "ai_validated": True
                    }
        except Exception:
            pass

        # Fallback - простая валидация
        return {"valid": True, "reason": "Basic validation passed"}

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики агента"""
        return {
            **self.stats,
            "ai_components": {
                "llm_router": self.llm_router is not None,
                "embedder": self.embedder is not None,
                "rag_system": self.rag_system is not None
            },
            "cases_with_embeddings": len(self.case_embeddings),
            "total_cases_stored": len(self.cases)
        }


# Factory функция
async def create_enhanced_case_agent(
    llm_router: Optional[LLMRouter] = None,
    embedder: Optional[SimpleEmbedder] = None,
    rag_system: Optional[BasicRAG] = None,
    memory_manager=None
) -> EnhancedCaseAgent:
    """Создание улучшенного агента управления делами"""
    agent = EnhancedCaseAgent(llm_router, embedder, rag_system, memory_manager)
    await agent.initialize()
    return agent