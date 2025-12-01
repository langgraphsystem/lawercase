"""
ValidatorAgent - Валидация и проверка качества документов.

Обеспечивает:
- Формальная валидация документов
- MAGCC quality assessment
- Мультиуровневая система проверок
- Интеграция с workflow валидации
- Автоматическое обнаружение ошибок
- Рекомендации по улучшению
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..llm_interface.intelligent_router import IntelligentRouter, LLMRequest
from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent
from .models import ValidationResult


class _ValidatorBaseModel(BaseModel):
    """Base class to keep dumps JSON-friendly for enums/datetimes."""

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        return super().model_dump(*args, **kwargs)


class ValidationLevel(str, Enum):
    """Уровни валидации"""

    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    EXPERT = "expert"


class ValidationCategory(str, Enum):
    """Категории валидации"""

    FORMAL = "formal"  # Формальные требования
    LEGAL = "legal"  # Правовые аспекты
    LINGUISTIC = "linguistic"  # Языковые требования
    STRUCTURE = "structure"  # Структурные требования
    CONTENT = "content"  # Содержательные аспекты
    MAGCC = "magcc"  # MAGCC quality assessment


class ValidationRuleType(str, Enum):
    """Типы правил валидации"""

    REQUIRED = "required"
    PATTERN = "pattern"
    LENGTH = "length"
    FORMAT = "format"
    STRUCTURE = "structure"
    LOGIC = "logic"
    SEMANTIC = "semantic"


class ValidationRule(_ValidatorBaseModel):
    """Правило валидации"""

    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название правила")
    category: ValidationCategory = Field(..., description="Категория")
    rule_type: ValidationRuleType = Field(..., description="Тип правила")
    pattern: str | None = Field(None, description="Паттерн для проверки")
    min_length: int | None = Field(None, description="Минимальная длина")
    max_length: int | None = Field(None, description="Максимальная длина")
    required_fields: list[str] = Field(default_factory=list, description="Обязательные поля")
    severity: str = Field(default="error", description="Критичность: error, warning, info")
    message: str = Field(..., description="Сообщение об ошибке")
    is_active: bool = Field(default=True, description="Активность правила")


class ValidationIssue(_ValidatorBaseModel):
    """Проблема валидации"""

    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = Field(..., description="ID правила")
    category: ValidationCategory = Field(..., description="Категория")
    severity: str = Field(..., description="Критичность")
    message: str = Field(..., description="Описание проблемы")
    location: str | None = Field(None, description="Местоположение в документе")
    suggestion: str | None = Field(None, description="Предложение по исправлению")
    auto_fixable: bool = Field(default=False, description="Может быть исправлено автоматически")


class MAGCCAssessment(_ValidatorBaseModel):
    """MAGCC quality assessment"""

    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metrics: dict[str, float] = Field(default_factory=dict, description="Метрики качества")
    accuracy_score: float = Field(default=0.0, description="Точность")
    completeness_score: float = Field(default=0.0, description="Полнота")
    coherence_score: float = Field(default=0.0, description="Связность")
    compliance_score: float = Field(default=0.0, description="Соответствие требованиям")
    overall_score: float = Field(default=0.0, description="Общая оценка")
    recommendations: list[str] = Field(default_factory=list, description="Рекомендации")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationRequest(_ValidatorBaseModel):
    """Запрос на валидацию"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    content: str = Field(..., description="Содержимое для валидации")
    document_type: str = Field(..., description="Тип документа")
    validation_level: ValidationLevel = Field(default=ValidationLevel.STANDARD)
    categories: list[ValidationCategory] = Field(
        default_factory=lambda: list(ValidationCategory), description="Категории для проверки"
    )
    custom_rules: list[str] = Field(default_factory=list, description="Дополнительные правила")
    case_id: str | None = Field(None, description="Связанное дело")
    user_id: str = Field(..., description="ID пользователя")


class ValidationReport(_ValidatorBaseModel):
    """Отчет валидации"""

    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(..., description="ID запроса")
    document_id: str = Field(..., description="ID документа")
    validation_level: ValidationLevel = Field(..., description="Уровень валидации")
    overall_result: ValidationResult = Field(..., description="Общий результат")
    issues: list[ValidationIssue] = Field(default_factory=list, description="Найденные проблемы")
    magcc_assessment: MAGCCAssessment | None = Field(None, description="MAGCC оценка")
    execution_time: float = Field(..., description="Время выполнения")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validated_by: str = Field(..., description="ID валидатора")


class ValidatorError(Exception):
    """Исключение для ошибок ValidatorAgent"""


class ValidationRuleError(Exception):
    """Исключение для ошибок правил валидации"""


class ValidatorAgent:
    """
    Агент для валидации и проверки качества документов.

    Основные функции:
    - Мультиуровневая система валидации
    - MAGCC quality assessment
    - Формальная и содержательная проверка
    - Автоматическое обнаружение ошибок
    - Предложения по улучшению
    - Интеграция с workflow
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        llm_router: IntelligentRouter | None = None,
    ):
        """
        Инициализация ValidatorAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
            llm_router: Роутер для доступа к LLM (Claude Opus 4.5)
        """
        self.memory = memory_manager or MemoryManager()
        self.llm_router = llm_router

        # Хранилища
        self._validation_rules: dict[str, ValidationRule] = {}
        self._validation_reports: dict[str, ValidationReport] = {}

        # Статистика
        self._validation_stats: dict[str, int] = {}

        # Инициализация базовых правил
        self._load_default_rules()

    async def avalidate_document(self, request: ValidationRequest) -> ValidationReport:
        """
        Основная функция валидации документа.

        Args:
            request: Запрос на валидацию

        Returns:
            ValidationReport: Полный отчет валидации

        Raises:
            ValidatorError: При ошибках валидации
        """
        try:
            start_time = datetime.utcnow()

            # Получение активных правил для запроса
            rules = self._get_applicable_rules(request)

            # Выполнение валидации по категориям
            issues = []
            category_results = {}

            for category in request.categories:
                category_rules = [r for r in rules if r.category == category]
                category_issues = await self._validate_by_category(
                    request.content, category_rules, category
                )
                issues.extend(category_issues)
                category_results[category.value] = len(category_issues)

            # MAGCC assessment если требуется
            magcc_assessment = None
            if ValidationCategory.MAGCC in request.categories:
                magcc_assessment = await self._perform_magcc_assessment(request)

            # Формирование общего результата
            overall_result = self._calculate_overall_result(issues, magcc_assessment)

            # Создание отчета
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            report = ValidationReport(
                request_id=request.request_id,
                document_id=request.document_id,
                validation_level=request.validation_level,
                overall_result=overall_result,
                issues=issues,
                magcc_assessment=magcc_assessment,
                execution_time=execution_time,
                validated_by="validator_agent",
            )

            # Сохранение отчета
            self._validation_reports[report.report_id] = report

            # Audit log
            await self._log_validation_completed(request, report)

            # Обновление статистики
            self._update_stats(request.validation_level, len(issues))

            return report

        except Exception as e:
            await self._log_validation_error(request, e)
            raise ValidatorError(f"Validation failed: {e!s}")

    async def avalidate(self, request: ValidationRequest) -> ValidationResult:
        """
        Совместимый с ТЗ упрощённый интерфейс: возвращает только ValidationResult.

        Args:
            request: Запрос на валидацию

        Returns:
            ValidationResult: Сводный результат валидации
        """
        report = await self.avalidate_document(request)
        return report.overall_result

    async def aadd_validation_rule(self, rule_data: dict[str, Any], user_id: str) -> ValidationRule:
        """
        Добавление нового правила валидации.

        Args:
            rule_data: Данные правила
            user_id: ID пользователя

        Returns:
            ValidationRule: Созданное правило
        """
        try:
            rule = ValidationRule(**rule_data)

            # Валидация правила
            await self._validate_rule(rule)

            # Сохранение правила
            self._validation_rules[rule.rule_id] = rule

            # Audit log
            await self._log_rule_created(rule, user_id)

            return rule

        except Exception as e:
            await self._log_rule_error(rule_data, user_id, e)
            raise ValidationRuleError(f"Failed to create rule: {e!s}")

    async def aget_validation_report(self, report_id: str, user_id: str) -> ValidationReport:
        """
        Получение отчета валидации.

        Args:
            report_id: ID отчета
            user_id: ID пользователя

        Returns:
            ValidationReport: Отчет валидации
        """
        report = self._validation_reports.get(report_id)
        if not report:
            raise ValidatorError(f"Validation report {report_id} not found")

        # Audit log
        await self._log_report_accessed(report, user_id)

        return report

    async def asearch_validation_reports(
        self, filters: dict[str, Any], user_id: str
    ) -> list[ValidationReport]:
        """
        Поиск отчетов валидации.

        Args:
            filters: Фильтры поиска
            user_id: ID пользователя

        Returns:
            List[ValidationReport]: Найденные отчеты
        """
        results = []

        for report in self._validation_reports.values():
            if self._matches_report_filters(report, filters):
                results.append(report)

        # Сортировка по дате создания
        results.sort(key=lambda x: x.validated_at, reverse=True)

        # Audit log
        await self._log_reports_searched(filters, len(results), user_id)

        return results

    async def aupdate_rule_status(
        self, rule_id: str, is_active: bool, user_id: str
    ) -> ValidationRule:
        """
        Обновление статуса правила валидации.

        Args:
            rule_id: ID правила
            is_active: Новый статус
            user_id: ID пользователя

        Returns:
            ValidationRule: Обновленное правило
        """
        rule = self._validation_rules.get(rule_id)
        if not rule:
            raise ValidatorError(f"Validation rule {rule_id} not found")

        old_status = rule.is_active
        rule.is_active = is_active

        # Audit log
        await self._log_rule_updated(rule, old_status, user_id)

        return rule

    def _get_applicable_rules(self, request: ValidationRequest) -> list[ValidationRule]:
        """Получение применимых правил для запроса"""
        applicable_rules = []

        for rule in self._validation_rules.values():
            if not rule.is_active:
                continue

            # Проверка категории
            if rule.category not in request.categories:
                continue

            # Проверка уровня валидации
            if not self._rule_applies_to_level(rule, request.validation_level):
                continue

            applicable_rules.append(rule)

        # Добавление кастомных правил
        for rule_id in request.custom_rules:
            rule = self._validation_rules.get(rule_id)
            if rule and rule.is_active:
                applicable_rules.append(rule)

        return applicable_rules

    def _rule_applies_to_level(self, rule: ValidationRule, level: ValidationLevel) -> bool:
        """Проверка применимости правила к уровню валидации"""
        rule_levels = {
            ValidationLevel.BASIC: ["error"],
            ValidationLevel.STANDARD: ["error", "warning"],
            ValidationLevel.STRICT: ["error", "warning", "info"],
            ValidationLevel.EXPERT: ["error", "warning", "info"],
        }

        return rule.severity in rule_levels.get(level, ["error"])

    async def _validate_by_category(
        self, content: str, rules: list[ValidationRule], category: ValidationCategory
    ) -> list[ValidationIssue]:
        """Валидация по категории"""
        issues = []

        for rule in rules:
            rule_issues = await self._apply_validation_rule(content, rule)
            issues.extend(rule_issues)

        return issues

    async def _apply_validation_rule(
        self, content: str, rule: ValidationRule
    ) -> list[ValidationIssue]:
        """Применение правила валидации"""
        issues = []

        try:
            if rule.rule_type == ValidationRuleType.REQUIRED:
                issues.extend(self._check_required_fields(content, rule))
            elif rule.rule_type == ValidationRuleType.PATTERN:
                issues.extend(self._check_pattern(content, rule))
            elif rule.rule_type == ValidationRuleType.LENGTH:
                issues.extend(self._check_length(content, rule))
            elif rule.rule_type == ValidationRuleType.FORMAT:
                issues.extend(self._check_format(content, rule))
            elif rule.rule_type == ValidationRuleType.STRUCTURE:
                issues.extend(self._check_structure(content, rule))
            elif rule.rule_type == ValidationRuleType.LOGIC:
                issues.extend(self._check_logic(content, rule))
            elif rule.rule_type == ValidationRuleType.SEMANTIC:
                issues.extend(await self._check_semantic(content, rule))

        except Exception as e:
            # Логирование ошибки правила но продолжение валидации
            await self._log_rule_execution_error(rule, e)

        return issues

    def _check_required_fields(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка обязательных полей"""
        issues = []

        for field in rule.required_fields:
            if field.lower() not in content.lower():
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        category=rule.category,
                        severity=rule.severity,
                        message=f"Required field '{field}' is missing",
                        suggestion=f"Add '{field}' to the document",
                        auto_fixable=False,
                    )
                )

        return issues

    def _check_pattern(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка паттерна"""
        import re

        issues = []

        if rule.pattern:
            if not re.search(rule.pattern, content):
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        category=rule.category,
                        severity=rule.severity,
                        message=rule.message,
                        suggestion="Ensure the content matches the required pattern",
                        auto_fixable=False,
                    )
                )

        return issues

    def _check_length(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка длины"""
        issues = []
        content_length = len(content.strip())

        if rule.min_length and content_length < rule.min_length:
            issues.append(
                ValidationIssue(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    message=f"Content too short: {content_length} < {rule.min_length} characters",
                    suggestion=f"Expand content to at least {rule.min_length} characters",
                    auto_fixable=False,
                )
            )

        if rule.max_length and content_length > rule.max_length:
            issues.append(
                ValidationIssue(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    message=f"Content too long: {content_length} > {rule.max_length} characters",
                    suggestion=f"Reduce content to maximum {rule.max_length} characters",
                    auto_fixable=False,
                )
            )

        return issues

    def _check_format(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка формата"""
        issues = []

        # Базовые форматные проверки
        if "email" in rule.name.lower():
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            emails = re.findall(r"\S+@\S+\.\S+", content)
            for email in emails:
                if not re.match(email_pattern, email):
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            category=rule.category,
                            severity=rule.severity,
                            message=f"Invalid email format: {email}",
                            suggestion="Use valid email format",
                            auto_fixable=True,
                        )
                    )

        return issues

    def _check_structure(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка структуры"""
        issues = []

        # Проверка структуры документа
        lines = content.split("\n")

        if "header" in rule.name.lower() and not lines[0].strip():
            issues.append(
                ValidationIssue(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    message="Document should start with a header",
                    suggestion="Add a header to the beginning of the document",
                    auto_fixable=False,
                )
            )

        return issues

    def _check_logic(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Проверка логики"""
        issues = []

        # Логические проверки содержания
        sentences = content.split(".")
        if len(sentences) < 3 and "coherence" in rule.name.lower():
            issues.append(
                ValidationIssue(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    message="Document lacks coherent structure",
                    suggestion="Organize content into logical paragraphs",
                    auto_fixable=False,
                )
            )

        return issues

    async def _check_semantic(self, content: str, rule: ValidationRule) -> list[ValidationIssue]:
        """Семантическая проверка с помощью LLM (Claude Opus 4.5)"""
        if not self.llm_router:
            # Fallback if no LLM available
            return []

        issues = []
        import json

        prompt = (
            f"You are an expert legal document validator (using Claude Opus 4.5 logic). "
            f"Analyze the following text against this specific rule:\n\n"
            f"RULE: {rule.name}\n"
            f"DESCRIPTION: {rule.message}\n"
            f"CATEGORY: {rule.category.value}\n\n"
            f"TEXT TO ANALYZE:\n{content[:4000]}...\n\n"  # Truncate if too long, though Opus handles 200k
            f"Return a JSON object with these fields:\n"
            f"- is_valid (bool): true if the rule is satisfied\n"
            f"- issue (string): description of the violation if any, else null\n"
            f"- suggestion (string): how to fix it, else null\n"
            f"- severity (string): 'error' or 'warning'\n"
        )

        try:
            request = LLMRequest(
                prompt=prompt,
                temperature=0.0,
                task_complexity="ultra",  # Requesting Claude Opus 4.5 tier
                metadata={"preferred_model": "claude-3-opus", "agent": "ValidatorAgent"},
            )

            response = await self.llm_router.acomplete(request)
            response_text = response.get("response", "")

            # Simple JSON extraction
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1:
                json_str = response_text[start : end + 1]
                data = json.loads(json_str)

                if not data.get("is_valid", True):
                    issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            category=rule.category,
                            severity=data.get("severity", rule.severity),
                            message=data.get("issue") or rule.message,
                            suggestion=data.get("suggestion"),
                            auto_fixable=False,
                        )
                    )
        except Exception as e:
            # Log but don't crash validation
            print(f"Semantic validation failed: {e}")

        return issues

    async def _perform_magcc_assessment(self, request: ValidationRequest) -> MAGCCAssessment:
        """Выполнение MAGCC quality assessment"""

        # Базовая MAGCC оценка
        content_length = len(request.content)
        word_count = len(request.content.split())

        # Расчет метрик
        accuracy_score = min(1.0, word_count / 100)  # Базовая оценка точности
        completeness_score = min(1.0, content_length / 500)  # Оценка полноты
        coherence_score = 0.8 if word_count > 50 else 0.5  # Базовая связность
        compliance_score = 0.9  # Базовое соответствие

        overall_score = (
            accuracy_score + completeness_score + coherence_score + compliance_score
        ) / 4

        recommendations = []
        if accuracy_score < 0.7:
            recommendations.append("Improve accuracy by adding more specific details")
        if completeness_score < 0.7:
            recommendations.append("Expand content to provide more comprehensive coverage")
        if coherence_score < 0.7:
            recommendations.append("Improve document structure and flow")

        return MAGCCAssessment(
            metrics={
                "content_length": content_length,
                "word_count": word_count,
                "sentence_count": len(request.content.split(".")),
            },
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            coherence_score=coherence_score,
            compliance_score=compliance_score,
            overall_score=overall_score,
            recommendations=recommendations,
        )

    def _calculate_overall_result(
        self, issues: list[ValidationIssue], magcc_assessment: MAGCCAssessment | None
    ) -> ValidationResult:
        """Расчет общего результата валидации"""

        # Подсчет ошибок по типам
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        # Определение результата
        is_valid = len(errors) == 0

        # Расчет общего score
        score = 1.0
        if errors:
            score -= len(errors) * 0.2
        if warnings:
            score -= len(warnings) * 0.1

        if magcc_assessment:
            score = (score + magcc_assessment.overall_score) / 2

        score = max(0.0, min(1.0, score))

        return ValidationResult(
            is_valid=is_valid,
            errors=[i.message for i in errors],
            warnings=[i.message for i in warnings],
            score=score,
        )

    def _matches_report_filters(self, report: ValidationReport, filters: dict[str, Any]) -> bool:
        """Проверка соответствия отчета фильтрам"""
        for key, value in filters.items():
            if (key == "document_id" and report.document_id != value) or (
                key == "validation_level" and report.validation_level != value
            ):
                return False
            if (key == "is_valid" and report.overall_result.is_valid != value) or (
                key == "has_errors" and (len(report.overall_result.errors) > 0) != value
            ):
                return False

        return True

    async def _validate_rule(self, rule: ValidationRule) -> None:
        """Валидация правила валидации"""
        if not rule.name.strip():
            raise ValidationRuleError("Rule name cannot be empty")

        if rule.rule_type == ValidationRuleType.PATTERN and not rule.pattern:
            raise ValidationRuleError("Pattern rule must have a pattern")

        if rule.rule_type == ValidationRuleType.REQUIRED and not rule.required_fields:
            raise ValidationRuleError("Required rule must have required_fields")

    def _load_default_rules(self) -> None:
        """Загрузка базовых правил валидации"""

        default_rules = [
            # Формальные правила
            {
                "name": "Document Title Required",
                "category": ValidationCategory.FORMAL,
                "rule_type": ValidationRuleType.REQUIRED,
                "required_fields": ["title", "subject"],
                "severity": "error",
                "message": "Document must have a title or subject",
            },
            {
                "name": "Minimum Content Length",
                "category": ValidationCategory.FORMAL,
                "rule_type": ValidationRuleType.LENGTH,
                "min_length": 50,
                "severity": "warning",
                "message": "Document content is too short",
            },
            # Структурные правила
            {
                "name": "Document Header Check",
                "category": ValidationCategory.STRUCTURE,
                "rule_type": ValidationRuleType.STRUCTURE,
                "severity": "warning",
                "message": "Document should have a clear header structure",
            },
            # Лингвистические правила
            {
                "name": "Email Format Validation",
                "category": ValidationCategory.LINGUISTIC,
                "rule_type": ValidationRuleType.FORMAT,
                "severity": "error",
                "message": "Invalid email format detected",
            },
            # Логические правила
            {
                "name": "Document Coherence",
                "category": ValidationCategory.CONTENT,
                "rule_type": ValidationRuleType.LOGIC,
                "severity": "warning",
                "message": "Document should have coherent structure",
            },
            # Семантические правила (LLM)
            {
                "name": "Legal Consistency Check",
                "category": ValidationCategory.LEGAL,
                "rule_type": ValidationRuleType.SEMANTIC,
                "severity": "error",
                "message": "Ensure there are no logical contradictions or factual inconsistencies in the legal arguments.",
            },
            {
                "name": "Professional Tone",
                "category": ValidationCategory.LINGUISTIC,
                "rule_type": ValidationRuleType.SEMANTIC,
                "severity": "warning",
                "message": "Ensure the tone is professional, objective, and suitable for a USCIS petition.",
            },
        ]

        for rule_data in default_rules:
            try:
                rule = ValidationRule(**rule_data)
                self._validation_rules[rule.rule_id] = rule
            except Exception as e:
                # Log rule initialization errors but continue
                print(f"Warning: Failed to initialize validation rule: {e}")

    def _update_stats(self, level: ValidationLevel, issue_count: int) -> None:
        """Обновление статистики валидации"""
        key = f"{level.value}_validations"
        self._validation_stats[key] = self._validation_stats.get(key, 0) + 1

        issues_key = "total_issues"
        self._validation_stats[issues_key] = self._validation_stats.get(issues_key, 0) + issue_count

    async def _log_validation_completed(
        self, request: ValidationRequest, report: ValidationReport
    ) -> None:
        """Логирование завершенной валидации"""
        await self._log_audit_event(
            user_id=request.user_id,
            action="validation_completed",
            payload={
                "request_id": request.request_id,
                "document_id": request.document_id,
                "validation_level": request.validation_level.value,
                "is_valid": report.overall_result.is_valid,
                "issues_count": len(report.issues),
                "execution_time": report.execution_time,
                "overall_score": report.overall_result.score,
            },
        )

    async def _log_validation_error(self, request: ValidationRequest, error: Exception) -> None:
        """Логирование ошибки валидации"""
        await self._log_audit_event(
            user_id=request.user_id,
            action="validation_error",
            payload={
                "request_id": request.request_id,
                "document_id": request.document_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    async def _log_rule_created(self, rule: ValidationRule, user_id: str) -> None:
        """Логирование создания правила"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_rule_created",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "category": rule.category.value,
                "rule_type": rule.rule_type.value,
            },
        )

    async def _log_rule_error(
        self, rule_data: dict[str, Any], user_id: str, error: Exception
    ) -> None:
        """Логирование ошибки правила"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_rule_error",
            payload={
                "rule_data": rule_data,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    async def _log_rule_execution_error(self, rule: ValidationRule, error: Exception) -> None:
        """Логирование ошибки выполнения правила"""
        await self._log_audit_event(
            user_id="system",
            action="rule_execution_error",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    async def _log_report_accessed(self, report: ValidationReport, user_id: str) -> None:
        """Логирование доступа к отчету"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_report_accessed",
            payload={"report_id": report.report_id, "document_id": report.document_id},
        )

    async def _log_reports_searched(
        self, filters: dict[str, Any], count: int, user_id: str
    ) -> None:
        """Логирование поиска отчетов"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_reports_searched",
            payload={"filters": filters, "results_count": count},
        )

    async def _log_rule_updated(self, rule: ValidationRule, old_status: bool, user_id: str) -> None:
        """Логирование обновления правила"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_rule_updated",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "old_status": old_status,
                "new_status": rule.is_active,
            },
        )

    async def _log_audit_event(self, user_id: str, action: str, payload: dict[str, Any]) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"validator_agent_{user_id}",
            source="validator_agent",
            action=action,
            payload=payload,
            tags=["validator_agent", "document_validation"],
        )

        await self.memory.alog_audit(event)

    async def get_stats(self) -> dict[str, Any]:
        """Получение статистики ValidatorAgent"""
        return {
            "validation_stats": self._validation_stats.copy(),
            "total_rules": len(self._validation_rules),
            "active_rules": len([r for r in self._validation_rules.values() if r.is_active]),
            "total_reports": len(self._validation_reports),
        }
