"""
Enhanced ValidatorAgent - Валидация документов с интеграцией LLM Router и RAG.

Обеспечивает улучшенную валидацию с:
- Интеграция с LLM Router для AI-powered валидации
- RAG поиск для проверки соответствия стандартам
- Контекстно-зависимая валидация
- Автоматическое исправление ошибок
- Многоуровневая система проверок
- Интеллектуальные рекомендации по улучшению
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Импорты новой архитектуры
from ..llm_router import LLMRouter, LLMRequest, ModelType, Priority, create_llm_router
from ..simple_embedder import SimpleEmbedder, create_simple_embedder
from ..basic_rag import BasicRAG, create_basic_rag

# Импорты из validator_agent для совместимости
from .validator_agent import SeverityLevel

# Extended ValidationType with additional AI-powered validation types
class ValidationType(str, Enum):
    # Base types from original validator
    DOCUMENT = "document"
    CASE_DATA = "case_data"
    COMPARISON = "comparison"
    # Extended AI types
    LEGAL_COMPLIANCE = "legal_compliance"
    QUALITY_ASSESSMENT = "quality_assessment"
    STYLE_CHECK = "style_check"
    GRAMMAR_CHECK = "grammar_check"
    FACT_VERIFICATION = "fact_verification"
    CONTENT_QUALITY = "content_quality"
    DATA_INTEGRITY = "data_integrity"


class ValidationRequest(BaseModel):
    """Запрос на валидацию"""
    content: str = Field(..., description="Содержимое для валидации")
    validation_type: ValidationType = Field(..., description="Тип валидации")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст валидации")
    rules: List[str] = Field(default_factory=list, description="Специфичные правила")
    auto_correct: bool = Field(default=False, description="Автоматическое исправление")
    priority: str = Field(default="normal", description="Приоритет валидации")


class ValidationIssue(BaseModel):
    """Проблема валидации"""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID проблемы")
    severity: SeverityLevel = Field(..., description="Серьезность")
    category: str = Field(..., description="Категория проблемы")
    description: str = Field(..., description="Описание проблемы")
    location: str = Field(default="", description="Местоположение в тексте")
    suggestion: str = Field(default="", description="Рекомендация по исправлению")
    auto_fixable: bool = Field(default=False, description="Может быть исправлено автоматически")
    rule_violated: str = Field(default="", description="Нарушенное правило")


class ValidationReport(BaseModel):
    """Отчет валидации"""
    validation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID валидации")
    content: str = Field(..., description="Валидируемый контент")
    validation_type: ValidationType = Field(..., description="Тип валидации")
    overall_score: float = Field(..., description="Общая оценка (0-1)")
    passed: bool = Field(..., description="Прошла ли валидация")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Выявленные проблемы")
    corrected_content: Optional[str] = Field(default=None, description="Исправленный контент")
    recommendations: List[str] = Field(default_factory=list, description="Общие рекомендации")
    validation_time: float = Field(..., description="Время валидации")
    sources_checked: List[str] = Field(default_factory=list, description="Проверенные источники")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")


class ValidationRule(BaseModel):
    """Правило валидации"""
    rule_id: str = Field(..., description="ID правила")
    name: str = Field(..., description="Название правила")
    description: str = Field(..., description="Описание правила")
    validation_type: ValidationType = Field(..., description="Тип валидации")
    severity: SeverityLevel = Field(..., description="Серьезность нарушения")
    pattern: Optional[str] = Field(default=None, description="Паттерн для проверки")
    ai_check: bool = Field(default=False, description="Требует AI проверки")
    auto_fix: bool = Field(default=False, description="Автоматическое исправление")


class ComplianceCheck(BaseModel):
    """Проверка соответствия стандартам"""
    standard_name: str = Field(..., description="Название стандарта")
    compliance_score: float = Field(..., description="Оценка соответствия")
    violations: List[str] = Field(default_factory=list, description="Нарушения")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")


class EnhancedValidatorAgent:
    """
    Улучшенный агент валидации с AI интеграцией.

    Включает:
    - Все функции базового ValidatorAgent
    - LLM Router для AI-powered валидации
    - RAG поиск для проверки стандартов
    - Контекстно-зависимая валидация
    - Автоматическое исправление
    - Многоуровневая система проверок
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

        # Хранилище правил и результатов
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.validation_history: Dict[str, ValidationReport] = {}

        # Инициализируем базовые правила
        self._init_default_rules()

        # Статистика
        self.stats = {
            "validations_performed": 0,
            "issues_found": 0,
            "auto_corrections_made": 0,
            "ai_validations_performed": 0,
            "rag_checks_performed": 0,
            "average_score": 0.0
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

            # Индексируем правила валидации в RAG
            await self._index_validation_standards()

            print("✅ EnhancedValidatorAgent инициализирован с AI компонентами")

        except Exception as e:
            print(f"⚠️ Ошибка инициализации AI компонентов: {e}")

    # Основные методы валидации

    async def validate(self, request: ValidationRequest) -> ValidationReport:
        """Основной метод валидации с AI улучшениями"""
        start_time = datetime.utcnow()

        try:
            validation_id = str(uuid.uuid4())

            # 1. Применяем базовые правила
            base_issues = await self._apply_base_rules(request)

            # 2. AI валидация
            ai_issues = await self._ai_validation(request)

            # 3. RAG проверка соответствия стандартам
            compliance_issues = await self._rag_compliance_check(request)

            # 4. Объединяем все проблемы
            all_issues = base_issues + ai_issues + compliance_issues

            # 5. Вычисляем общую оценку
            overall_score = self._calculate_overall_score(all_issues, request.content)

            # 6. Автоматическое исправление если запрошено
            corrected_content = None
            if request.auto_correct and overall_score < 0.8:
                corrected_content = await self._auto_correct_content(request.content, all_issues)

            # 7. Генерируем рекомендации
            recommendations = await self._generate_recommendations(all_issues, request)

            # 8. Создаем отчет
            validation_time = (datetime.utcnow() - start_time).total_seconds()

            report = ValidationReport(
                validation_id=validation_id,
                content=request.content,
                validation_type=request.validation_type,
                overall_score=overall_score,
                passed=overall_score >= 0.7,  # Порог прохождения
                issues=all_issues,
                corrected_content=corrected_content,
                recommendations=recommendations,
                validation_time=validation_time,
                sources_checked=await self._get_sources_checked(request),
                metadata={
                    "rules_applied": len(self.validation_rules),
                    "ai_enhanced": self.llm_router is not None,
                    "rag_enhanced": self.rag_system is not None
                }
            )

            # Сохраняем результат
            self.validation_history[validation_id] = report

            # Обновляем статистику
            self._update_stats(report)

            return report

        except Exception as e:
            return ValidationReport(
                content=request.content,
                validation_type=request.validation_type,
                overall_score=0.0,
                passed=False,
                validation_time=0.0,
                metadata={"error": str(e)}
            )

    async def validate_document_structure(self, content: str) -> ValidationReport:
        """Специализированная валидация структуры документа"""
        request = ValidationRequest(
            content=content,
            validation_type=ValidationType.DOCUMENT,
            context={"focus": "structure"},
            auto_correct=True
        )

        return await self.validate(request)

    async def validate_legal_compliance(self, content: str, jurisdiction: str = "RU") -> ValidationReport:
        """Валидация соответствия правовым нормам"""
        request = ValidationRequest(
            content=content,
            validation_type=ValidationType.LEGAL_COMPLIANCE,
            context={"jurisdiction": jurisdiction},
            auto_correct=False
        )

        return await self.validate(request)

    async def validate_and_improve(self, content: str, validation_type: ValidationType) -> tuple[ValidationReport, str]:
        """Валидация с автоматическим улучшением"""
        # Первая валидация
        initial_request = ValidationRequest(
            content=content,
            validation_type=validation_type,
            auto_correct=True
        )

        initial_report = await self.validate(initial_request)

        if initial_report.corrected_content and initial_report.overall_score < 0.9:
            # Повторная валидация улучшенного контента
            improved_request = ValidationRequest(
                content=initial_report.corrected_content,
                validation_type=validation_type,
                auto_correct=True
            )

            final_report = await self.validate(improved_request)
            return final_report, initial_report.corrected_content

        return initial_report, initial_report.corrected_content or content

    # Вспомогательные методы

    async def _apply_base_rules(self, request: ValidationRequest) -> List[ValidationIssue]:
        """Применение базовых правил валидации"""
        issues = []

        # Фильтруем правила по типу валидации
        applicable_rules = [
            rule for rule in self.validation_rules.values()
            if rule.validation_type == request.validation_type
        ]

        for rule in applicable_rules:
            rule_issues = await self._check_rule(rule, request.content)
            issues.extend(rule_issues)

        return issues

    async def _ai_validation(self, request: ValidationRequest) -> List[ValidationIssue]:
        """AI валидация через LLM Router"""
        try:
            if not self.llm_router:
                return []

            # Создаем промпт для AI валидации
            validation_prompt = await self._create_ai_validation_prompt(request)

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты эксперт по валидации юридических документов. Проводи тщательную проверку."},
                    {"role": "user", "content": validation_prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=1000,
                priority=Priority.HIGH if request.priority == "high" else Priority.NORMAL
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                self.stats["ai_validations_performed"] += 1
                return await self._parse_ai_validation_response(response.content)

        except Exception as e:
            print(f"Ошибка AI валидации: {e}")

        return []

    async def _rag_compliance_check(self, request: ValidationRequest) -> List[ValidationIssue]:
        """Проверка соответствия стандартам через RAG"""
        try:
            if not self.rag_system:
                return []

            # Поиск релевантных стандартов
            rag_query = f"валидация {request.validation_type} стандарты правила"
            rag_response = await self.rag_system.search(rag_query, max_results=3)

            if rag_response.success and rag_response.sources:
                self.stats["rag_checks_performed"] += 1
                return await self._check_compliance_with_standards(request.content, rag_response.sources)

        except Exception as e:
            print(f"Ошибка RAG проверки: {e}")

        return []

    async def _auto_correct_content(self, content: str, issues: List[ValidationIssue]) -> Optional[str]:
        """Автоматическое исправление контента"""
        try:
            if not self.llm_router or not issues:
                return None

            # Фильтруем исправимые проблемы
            fixable_issues = [issue for issue in issues if issue.auto_fixable]

            if not fixable_issues:
                return None

            # Создаем промпт для исправления
            correction_prompt = f"""
            Исправь следующий текст, устранив указанные проблемы:

            Исходный текст:
            {content}

            Проблемы для исправления:
            {chr(10).join([f"- {issue.description}: {issue.suggestion}" for issue in fixable_issues])}

            Предоставь только исправленный текст без дополнительных комментариев.
            """

            llm_request = LLMRequest(
                messages=[
                    {"role": "system", "content": "Ты редактор документов. Исправляй тексты аккуратно, сохраняя их смысл."},
                    {"role": "user", "content": correction_prompt}
                ],
                model_type=ModelType.CHAT,
                max_tokens=2000
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                self.stats["auto_corrections_made"] += 1
                return response.content.strip()

        except Exception as e:
            print(f"Ошибка автокоррекции: {e}")

        return None

    async def _generate_recommendations(self, issues: List[ValidationIssue], request: ValidationRequest) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        recommendations = []

        # Базовые рекомендации на основе проблем
        issue_categories = {}
        for issue in issues:
            category = issue.category
            if category not in issue_categories:
                issue_categories[category] = []
            issue_categories[category].append(issue)

        for category, category_issues in issue_categories.items():
            if len(category_issues) > 1:
                recommendations.append(f"Обратите внимание на {category} - найдено {len(category_issues)} проблем")

        # AI рекомендации если доступны
        if self.llm_router and len(issues) > 0:
            ai_recommendations = await self._get_ai_recommendations(issues, request)
            recommendations.extend(ai_recommendations[:3])  # Максимум 3 AI рекомендации

        return recommendations

    async def _create_ai_validation_prompt(self, request: ValidationRequest) -> str:
        """Создание промпта для AI валидации"""
        base_prompt = f"""
        Проведи валидацию следующего контента:

        Тип валидации: {request.validation_type}
        Контент для проверки:
        {request.content}
        """

        if request.context:
            base_prompt += f"\nКонтекст: {json.dumps(request.context, ensure_ascii=False)}"

        if request.rules:
            base_prompt += f"\nСпециальные правила: {', '.join(request.rules)}"

        validation_instructions = {
            ValidationType.DOCUMENT: "Проверь структуру, форматирование и полноту документа",
            ValidationType.LEGAL_COMPLIANCE: "Проверь соответствие правовым нормам и стандартам",
            ValidationType.CONTENT_QUALITY: "Оцени качество содержания, ясность и стиль",
            ValidationType.DATA_INTEGRITY: "Проверь целостность и корректность данных"
        }

        instruction = validation_instructions.get(request.validation_type, "Проведи общую валидацию")
        base_prompt += f"\n\nИнструкция: {instruction}"

        base_prompt += """

Ответь в следующем формате JSON:
{
  "issues": [
    {
      "severity": "critical/high/medium/low",
      "category": "категория",
      "description": "описание проблемы",
      "suggestion": "рекомендация по исправлению",
      "auto_fixable": true/false
    }
  ],
  "overall_assessment": "общая оценка"
}
"""

        return base_prompt

    async def _parse_ai_validation_response(self, response_content: str) -> List[ValidationIssue]:
        """Парсинг ответа AI валидации"""
        try:
            # Пытаемся парсить JSON ответ
            data = json.loads(response_content)
            issues = []

            for issue_data in data.get("issues", []):
                issue = ValidationIssue(
                    severity=SeverityLevel(issue_data.get("severity", "medium")),
                    category=issue_data.get("category", "general"),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    auto_fixable=issue_data.get("auto_fixable", False),
                    rule_violated="ai_validation"
                )
                issues.append(issue)

            return issues

        except json.JSONDecodeError:
            # Если не удалось парсить JSON, создаем базовую проблему
            return [ValidationIssue(
                severity=SeverityLevel.MEDIUM,
                category="ai_validation",
                description="AI валидация выявила потенциальные проблемы",
                suggestion="Рекомендуется ручная проверка",
                auto_fixable=False
            )]

    async def _check_compliance_with_standards(self, content: str, sources) -> List[ValidationIssue]:
        """Проверка соответствия стандартам на основе RAG источников"""
        issues = []

        # Простая проверка на основе найденных источников
        for source in sources:
            standard_content = source.chunk.content

            # Ключевые слова для проверки
            required_keywords = ["должен", "обязан", "требуется", "необходимо"]
            found_requirements = []

            for keyword in required_keywords:
                if keyword in standard_content.lower():
                    # Извлекаем предложение с требованием
                    sentences = standard_content.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            found_requirements.append(sentence.strip())
                            break

            # Проверяем выполнение требований
            for requirement in found_requirements:
                if not self._check_requirement_in_content(requirement, content):
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.HIGH,
                        category="compliance",
                        description=f"Не выполнено требование: {requirement[:100]}...",
                        suggestion="Убедитесь, что документ соответствует указанному требованию",
                        auto_fixable=False,
                        rule_violated="standard_compliance"
                    ))

        return issues

    def _check_requirement_in_content(self, requirement: str, content: str) -> bool:
        """Простая проверка выполнения требования в контенте"""
        # Извлекаем ключевые слова из требования
        requirement_words = [word.lower() for word in requirement.split() if len(word) > 3]
        content_lower = content.lower()

        # Проверяем наличие ключевых слов
        found_words = sum(1 for word in requirement_words if word in content_lower)
        return found_words >= len(requirement_words) * 0.5  # 50% совпадений

    async def _check_rule(self, rule: ValidationRule, content: str) -> List[ValidationIssue]:
        """Проверка конкретного правила"""
        issues = []

        # Проверка по паттерну если есть
        if rule.pattern:
            import re
            if not re.search(rule.pattern, content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity=rule.severity,
                    category="pattern_validation",
                    description=f"Нарушено правило: {rule.name}",
                    suggestion=rule.description,
                    auto_fixable=rule.auto_fix,
                    rule_violated=rule.rule_id
                ))

        # AI проверка если требуется
        if rule.ai_check and self.llm_router:
            ai_issues = await self._ai_check_rule(rule, content)
            issues.extend(ai_issues)

        return issues

    async def _ai_check_rule(self, rule: ValidationRule, content: str) -> List[ValidationIssue]:
        """AI проверка конкретного правила"""
        try:
            prompt = f"""
            Проверь соблюдение следующего правила в тексте:

            Правило: {rule.name}
            Описание: {rule.description}

            Текст для проверки:
            {content}

            Ответь "соблюдено" или "нарушено" с кратким обоснованием.
            """

            llm_request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model_type=ModelType.CHAT,
                max_tokens=200
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success and "нарушено" in response.content.lower():
                return [ValidationIssue(
                    severity=rule.severity,
                    category="ai_rule_check",
                    description=f"AI обнаружил нарушение правила: {rule.name}",
                    suggestion=rule.description,
                    auto_fixable=rule.auto_fix,
                    rule_violated=rule.rule_id
                )]

        except Exception:
            pass

        return []

    def _calculate_overall_score(self, issues: List[ValidationIssue], content: str) -> float:
        """Расчет общей оценки валидации"""
        if not issues:
            return 1.0

        # Веса для разных уровней серьезности
        severity_weights = {
            SeverityLevel.CRITICAL: 0.4,
            SeverityLevel.HIGH: 0.3,
            SeverityLevel.MEDIUM: 0.2,
            SeverityLevel.LOW: 0.1
        }

        total_penalty = 0.0
        for issue in issues:
            penalty = severity_weights.get(issue.severity, 0.2)
            total_penalty += penalty

        # Нормализуем по длине контента
        content_factor = min(1.0, len(content.split()) / 100)  # Длинные тексты менее чувствительны к ошибкам
        normalized_penalty = total_penalty * content_factor

        score = max(0.0, 1.0 - normalized_penalty)
        return round(score, 2)

    def _init_default_rules(self) -> None:
        """Инициализация базовых правил валидации"""
        # Правило для структуры документа
        document_structure_rule = ValidationRule(
            rule_id="doc_structure",
            name="Структура документа",
            description="Документ должен иметь заголовок и основную часть",
            validation_type=ValidationType.DOCUMENT,
            severity=SeverityLevel.HIGH,
            pattern=r".{10,}",  # Минимум 10 символов
            auto_fix=False
        )

        # Правило для юридического соответствия
        legal_compliance_rule = ValidationRule(
            rule_id="legal_terms",
            name="Юридическая терминология",
            description="Должны использоваться корректные юридические термины",
            validation_type=ValidationType.LEGAL_COMPLIANCE,
            severity=SeverityLevel.MEDIUM,
            ai_check=True,
            auto_fix=False
        )

        # Правило качества контента
        content_quality_rule = ValidationRule(
            rule_id="content_length",
            name="Минимальная длина контента",
            description="Контент должен содержать минимум 50 слов",
            validation_type=ValidationType.CONTENT_QUALITY,
            severity=SeverityLevel.LOW,
            pattern=r"(\w+\s+){50,}",
            auto_fix=False
        )

        self.validation_rules["doc_structure"] = document_structure_rule
        self.validation_rules["legal_terms"] = legal_compliance_rule
        self.validation_rules["content_length"] = content_quality_rule

    async def _index_validation_standards(self) -> None:
        """Индексация стандартов валидации в RAG"""
        try:
            if not self.rag_system:
                return

            # Добавляем стандарты валидации
            standards = [
                {
                    "title": "Стандарты оформления юридических документов",
                    "content": """
                    Юридические документы должны содержать:
                    1. Четкий заголовок
                    2. Дату составления
                    3. Стороны документа
                    4. Основную часть с изложением сути
                    5. Подписи ответственных лиц
                    """
                },
                {
                    "title": "Требования к деловой переписке",
                    "content": """
                    Деловые письма должны включать:
                    1. Обращение к адресату
                    2. Изложение сути вопроса
                    3. Четкие требования или предложения
                    4. Корректное завершение
                    5. Контактную информацию
                    """
                }
            ]

            for standard in standards:
                await self.rag_system.add_document(
                    standard["title"],
                    standard["content"],
                    {"type": "validation_standard"}
                )

        except Exception as e:
            print(f"Ошибка индексации стандартов: {e}")

    async def _get_ai_recommendations(self, issues: List[ValidationIssue], request: ValidationRequest) -> List[str]:
        """Получение AI рекомендаций"""
        try:
            if not self.llm_router or not issues:
                return []

            issues_summary = "\n".join([f"- {issue.description}" for issue in issues[:5]])

            prompt = f"""
            На основе выявленных проблем в документе дай 3 конкретные рекомендации по улучшению:

            Проблемы:
            {issues_summary}

            Тип документа: {request.validation_type}

            Дай краткие, практические рекомендации (по одному предложению каждая).
            """

            llm_request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model_type=ModelType.CHAT,
                max_tokens=300
            )

            response = await self.llm_router.route_request(llm_request)

            if response.success:
                # Извлекаем рекомендации из ответа
                lines = [line.strip() for line in response.content.split('\n') if line.strip()]
                recommendations = []

                for line in lines:
                    if line.startswith(('-', '•', '1.', '2.', '3.')):
                        recommendation = line.lstrip('-•123. ').strip()
                        if recommendation:
                            recommendations.append(recommendation)

                return recommendations[:3]

        except Exception:
            pass

        return []

    async def _get_sources_checked(self, request: ValidationRequest) -> List[str]:
        """Получение списка проверенных источников"""
        sources = ["Внутренние правила валидации"]

        if self.rag_system:
            sources.append("База стандартов валидации")

        if self.llm_router:
            sources.append("AI анализ качества")

        return sources

    def _update_stats(self, report: ValidationReport) -> None:
        """Обновление статистики"""
        self.stats["validations_performed"] += 1
        self.stats["issues_found"] += len(report.issues)

        if report.corrected_content:
            self.stats["auto_corrections_made"] += 1

        # Обновляем среднюю оценку
        current_avg = self.stats["average_score"]
        total_validations = self.stats["validations_performed"]

        new_avg = ((current_avg * (total_validations - 1)) + report.overall_score) / total_validations
        self.stats["average_score"] = round(new_avg, 2)

    def get_validation_history(self, limit: int = 10) -> List[ValidationReport]:
        """Получение истории валидации"""
        reports = list(self.validation_history.values())
        reports.sort(key=lambda x: x.validation_id, reverse=True)
        return reports[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики агента"""
        return {
            **self.stats,
            "ai_components": {
                "llm_router": self.llm_router is not None,
                "embedder": self.embedder is not None,
                "rag_system": self.rag_system is not None
            },
            "total_rules": len(self.validation_rules),
            "validation_history_size": len(self.validation_history)
        }


# Factory функция
async def create_enhanced_validator_agent(
    llm_router: Optional[LLMRouter] = None,
    embedder: Optional[SimpleEmbedder] = None,
    rag_system: Optional[BasicRAG] = None,
    memory_manager=None
) -> EnhancedValidatorAgent:
    """Создание улучшенного агента валидации"""
    agent = EnhancedValidatorAgent(llm_router, embedder, rag_system, memory_manager)
    await agent.initialize()
    return agent