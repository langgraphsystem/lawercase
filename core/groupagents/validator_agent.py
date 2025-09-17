"""
ValidatorAgent - Валидация с самокоррекцией.

Обеспечивает:
- Rule-based валидацию документов и данных
- MAGCC consensus evaluation
- Self-correction mixin
- Confidence scoring
- Version comparison
- Validation rules engine
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from .models import ValidationResult


class ValidationType(str, Enum):
    """Типы валидации"""
    DOCUMENT = "document"
    CASE_DATA = "case_data"
    LEGAL_COMPLIANCE = "legal_compliance"
    BUSINESS_RULES = "business_rules"
    DATA_INTEGRITY = "data_integrity"
    CONTENT_QUALITY = "content_quality"


class SeverityLevel(str, Enum):
    """Уровни серьезности ошибок"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationRule(BaseModel):
    """Правило валидации"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название правила")
    description: str = Field(..., description="Описание правила")
    validation_type: ValidationType = Field(..., description="Тип валидации")
    severity: SeverityLevel = Field(..., description="Уровень серьезности")
    rule_code: str = Field(..., description="Код правила для выполнения")
    enabled: bool = Field(default=True, description="Активно ли правило")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные правила")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationIssue(BaseModel):
    """Проблема валидации"""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = Field(..., description="ID правила")
    rule_name: str = Field(..., description="Название правила")
    severity: SeverityLevel = Field(..., description="Уровень серьезности")
    message: str = Field(..., description="Сообщение об ошибке")
    location: Optional[str] = Field(None, description="Местоположение ошибки")
    suggested_fix: Optional[str] = Field(None, description="Предлагаемое исправление")
    auto_fixable: bool = Field(default=False, description="Можно ли исправить автоматически")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст ошибки")


class ValidationRequest(BaseModel):
    """Запрос на валидацию"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    validation_type: ValidationType = Field(..., description="Тип валидации")
    data: Dict[str, Any] = Field(..., description="Данные для валидации")
    rule_filters: Optional[List[str]] = Field(None, description="Фильтры правил")
    auto_fix: bool = Field(default=False, description="Автоматическое исправление")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Порог уверенности")
    context: Optional[Dict[str, Any]] = Field(None, description="Дополнительный контекст")


class ValidationResponse(BaseModel):
    """Ответ валидации"""
    request_id: str = Field(..., description="ID запроса")
    is_valid: bool = Field(..., description="Результат валидации")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Уверенность в результате")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Найденные проблемы")
    corrections: Dict[str, Any] = Field(default_factory=dict, description="Примененные исправления")
    summary: str = Field(..., description="Краткое резюме")
    validation_time: float = Field(..., description="Время валидации в секундах")
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class ConsensusRequest(BaseModel):
    """Запрос MAGCC consensus"""
    consensus_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str = Field(..., description="Вопрос для консенсуса")
    options: List[str] = Field(..., description="Варианты ответов")
    validation_data: Dict[str, Any] = Field(..., description="Данные для анализа")
    required_confidence: float = Field(default=0.8, description="Требуемая уверенность")
    max_iterations: int = Field(default=3, description="Максимум итераций")


class ConsensusResponse(BaseModel):
    """Ответ MAGCC consensus"""
    consensus_id: str = Field(..., description="ID запроса")
    achieved: bool = Field(..., description="Достигнут ли консенсус")
    selected_option: Optional[str] = Field(None, description="Выбранный вариант")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в выборе")
    iterations: int = Field(..., description="Количество итераций")
    reasoning: str = Field(..., description="Обоснование выбора")
    individual_scores: Dict[str, float] = Field(default_factory=dict, description="Индивидуальные оценки")


class ValidatorError(Exception):
    """Исключение для ошибок валидации"""
    pass


class RuleEngineError(Exception):
    """Исключение для ошибок rule engine"""
    pass


class ValidatorAgent:
    """
    Агент валидации с самокоррекцией и consensus evaluation.

    Основные функции:
    - Rule-based валидация различных типов данных
    - MAGCC consensus для спорных случаев
    - Self-correction с confidence scoring
    - Автоматические исправления
    - Version comparison и tracking
    - Extensible validation rules engine
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Инициализация ValidatorAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилища
        self._validation_rules: Dict[str, ValidationRule] = {}
        self._validation_results: Dict[str, ValidationResponse] = {}
        self._consensus_results: Dict[str, ConsensusResponse] = {}

        # Инициализация базовых правил
        self._initialize_default_rules()

        # Статистика
        self._validation_stats: Dict[str, int] = {}
        self._rule_performance: Dict[str, Dict[str, Any]] = {}

    async def avalidate(
        self,
        request: ValidationRequest,
        user_id: str
    ) -> ValidationResponse:
        """
        Основная функция валидации с rule-based проверками.

        Args:
            request: Запрос на валидацию
            user_id: ID пользователя

        Returns:
            ValidationResponse: Результат валидации

        Raises:
            ValidatorError: При ошибках валидации
        """
        start_time = datetime.utcnow()

        try:
            # Получение применимых правил
            rules = await self._get_applicable_rules(request)

            # Выполнение валидации
            issues = await self._execute_validation_rules(request, rules)

            # Фильтрация по severity
            filtered_issues = await self._filter_issues_by_severity(issues, request)

            # Автоматические исправления
            corrections = {}
            if request.auto_fix:
                corrections = await self._apply_auto_fixes(request, filtered_issues)

            # Расчет confidence score
            confidence_score = await self._calculate_confidence_score(
                filtered_issues, request, corrections
            )

            # Определение общего результата
            is_valid = await self._determine_validity(
                filtered_issues, confidence_score, request.confidence_threshold
            )

            # Создание сводки
            summary = await self._generate_summary(filtered_issues, corrections, is_valid)

            # Расчет времени выполнения
            validation_time = (datetime.utcnow() - start_time).total_seconds()

            # Создание ответа
            response = ValidationResponse(
                request_id=request.request_id,
                is_valid=is_valid,
                confidence_score=confidence_score,
                issues=filtered_issues,
                corrections=corrections,
                summary=summary,
                validation_time=validation_time
            )

            # Сохранение результата
            self._validation_results[response.request_id] = response

            # Audit log
            await self._log_validation(request, response, user_id)

            # Обновление статистики
            self._update_validation_stats(request.validation_type, is_valid)

            return response

        except Exception as e:
            await self._log_validation_error(request, user_id, e)
            raise ValidatorError(f"Validation failed: {str(e)}")

    async def amagcc_consensus(
        self,
        request: ConsensusRequest,
        user_id: str
    ) -> ConsensusResponse:
        """
        MAGCC consensus evaluation для спорных случаев.

        Args:
            request: Запрос на консенсус
            user_id: ID пользователя

        Returns:
            ConsensusResponse: Результат консенсуса
        """
        try:
            # Инициализация MAGCC процесса
            individual_scores = {}
            iterations = 0
            achieved = False
            selected_option = None
            final_confidence = 0.0
            reasoning = ""

            # Итеративный процесс консенсуса
            while iterations < request.max_iterations and not achieved:
                iterations += 1

                # Симуляция множественных агентов (в реальности - вызовы LLM)
                agent_evaluations = await self._simulate_multiple_agents(request)

                # Анализ согласованности
                consensus_data = await self._analyze_consensus(agent_evaluations, request)

                individual_scores = consensus_data["scores"]
                selected_option = consensus_data["option"]
                final_confidence = consensus_data["confidence"]
                reasoning = consensus_data["reasoning"]

                # Проверка достижения консенсуса
                if final_confidence >= request.required_confidence:
                    achieved = True

            response = ConsensusResponse(
                consensus_id=request.consensus_id,
                achieved=achieved,
                selected_option=selected_option,
                confidence=final_confidence,
                iterations=iterations,
                reasoning=reasoning,
                individual_scores=individual_scores
            )

            # Сохранение результата
            self._consensus_results[response.consensus_id] = response

            # Audit log
            await self._log_consensus(request, response, user_id)

            return response

        except Exception as e:
            await self._log_consensus_error(request, user_id, e)
            raise ValidatorError(f"MAGCC consensus failed: {str(e)}")

    async def acompare_versions(
        self,
        version1_data: Dict[str, Any],
        version2_data: Dict[str, Any],
        user_id: str
    ) -> ValidationResponse:
        """
        Сравнение версий с выявлением различий.

        Args:
            version1_data: Данные первой версии
            version2_data: Данные второй версии
            user_id: ID пользователя

        Returns:
            ValidationResponse: Результат сравнения
        """
        try:
            # Создание запроса на сравнение
            comparison_request = ValidationRequest(
                validation_type=ValidationType.DATA_INTEGRITY,
                data={
                    "version1": version1_data,
                    "version2": version2_data,
                    "comparison_mode": True
                }
            )

            # Выполнение специализированных правил сравнения
            comparison_rules = await self._get_comparison_rules()
            issues = await self._execute_validation_rules(comparison_request, comparison_rules)

            # Создание ответа
            response = ValidationResponse(
                request_id=comparison_request.request_id,
                is_valid=len(issues) == 0,
                confidence_score=1.0,  # Сравнение детерминистично
                issues=issues,
                corrections={},
                summary=f"Found {len(issues)} differences between versions",
                validation_time=0.1
            )

            # Audit log
            await self._log_version_comparison(version1_data, version2_data, response, user_id)

            return response

        except Exception as e:
            await self._log_validation_error(comparison_request, user_id, e)
            raise ValidatorError(f"Version comparison failed: {str(e)}")

    async def acreate_validation_rule(
        self,
        rule_data: Dict[str, Any],
        user_id: str
    ) -> ValidationRule:
        """
        Создание нового правила валидации.

        Args:
            rule_data: Данные правила
            user_id: ID пользователя

        Returns:
            ValidationRule: Созданное правило
        """
        try:
            rule = ValidationRule(**rule_data)

            # Валидация правила
            await self._validate_rule_syntax(rule)

            # Сохранение правила
            self._validation_rules[rule.rule_id] = rule

            # Audit log
            await self._log_rule_creation(rule, user_id)

            return rule

        except Exception as e:
            await self._log_rule_error(rule_data, user_id, e)
            raise RuleEngineError(f"Failed to create validation rule: {str(e)}")

    async def _get_applicable_rules(self, request: ValidationRequest) -> List[ValidationRule]:
        """Получение применимых правил валидации"""
        applicable_rules = []

        for rule in self._validation_rules.values():
            if not rule.enabled:
                continue

            # Фильтр по типу валидации
            if rule.validation_type != request.validation_type:
                continue

            # Фильтр по правилам
            if request.rule_filters and rule.rule_id not in request.rule_filters:
                continue

            applicable_rules.append(rule)

        return applicable_rules

    async def _execute_validation_rules(
        self,
        request: ValidationRequest,
        rules: List[ValidationRule]
    ) -> List[ValidationIssue]:
        """Выполнение правил валидации"""
        issues = []

        for rule in rules:
            try:
                rule_issues = await self._execute_single_rule(request, rule)
                issues.extend(rule_issues)

                # Обновление статистики правила
                self._update_rule_performance(rule.rule_id, len(rule_issues))

            except Exception as e:
                # Логирование ошибки правила
                await self._log_rule_execution_error(rule, request, e)

        return issues

    async def _execute_single_rule(
        self,
        request: ValidationRequest,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Выполнение одного правила валидации"""
        issues = []
        data = request.data

        # Правила для валидации документов
        if rule.validation_type == ValidationType.DOCUMENT:
            if rule.name == "Document Title Length":
                title = data.get("title", "")
                if len(title) < 5:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message="Document title is too short (minimum 5 characters)",
                        location="title",
                        suggested_fix="Provide a more descriptive title",
                        auto_fixable=False
                    ))

            elif rule.name == "Document Content Quality":
                content = data.get("content", "")
                if len(content) < 50:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message="Document content is too short for meaningful analysis",
                        location="content",
                        suggested_fix="Add more detailed content",
                        auto_fixable=False
                    ))

        # Правила для валидации данных дела
        elif rule.validation_type == ValidationType.CASE_DATA:
            if rule.name == "Required Fields":
                required_fields = ["title", "description", "case_type", "client_id"]
                for field in required_fields:
                    if not data.get(field):
                        issues.append(ValidationIssue(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            message=f"Required field '{field}' is missing or empty",
                            location=field,
                            suggested_fix=f"Provide value for {field}",
                            auto_fixable=False
                        ))

            elif rule.name == "Case Type Validity":
                case_type = data.get("case_type")
                valid_types = ["immigration", "corporate", "family", "criminal", "civil"]
                if case_type and case_type not in valid_types:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"Invalid case type: {case_type}",
                        location="case_type",
                        suggested_fix=f"Use one of: {', '.join(valid_types)}",
                        auto_fixable=True,
                        context={"valid_types": valid_types}
                    ))

        # Правила для проверки целостности данных
        elif rule.validation_type == ValidationType.DATA_INTEGRITY:
            if rule.name == "Data Consistency":
                # Пример: проверка соответствия связанных полей
                if "version1" in data and "version2" in data:
                    v1 = data["version1"]
                    v2 = data["version2"]

                    # Проверка изменений в критических полях
                    critical_fields = ["case_id", "client_id"]
                    for field in critical_fields:
                        if v1.get(field) != v2.get(field):
                            issues.append(ValidationIssue(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                severity=SeverityLevel.HIGH,
                                message=f"Critical field '{field}' changed between versions",
                                location=field,
                                suggested_fix="Verify this change is intentional",
                                auto_fixable=False
                            ))

        return issues

    async def _filter_issues_by_severity(
        self,
        issues: List[ValidationIssue],
        request: ValidationRequest
    ) -> List[ValidationIssue]:
        """Фильтрация issues по уровню серьезности"""
        # Пока возвращаем все, но можно добавить логику фильтрации
        return issues

    async def _apply_auto_fixes(
        self,
        request: ValidationRequest,
        issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """Применение автоматических исправлений"""
        corrections = {}

        for issue in issues:
            if not issue.auto_fixable:
                continue

            if issue.rule_name == "Case Type Validity":
                # Пример автоисправления: замена на валидный тип
                valid_types = issue.context.get("valid_types", [])
                if valid_types:
                    corrections[issue.location] = valid_types[0]

        return corrections

    async def _calculate_confidence_score(
        self,
        issues: List[ValidationIssue],
        request: ValidationRequest,
        corrections: Dict[str, Any]
    ) -> float:
        """Расчет confidence score"""
        if not issues:
            return 1.0

        # Базовая логика: уменьшение уверенности в зависимости от количества и серьезности issues
        severity_weights = {
            SeverityLevel.CRITICAL: 0.4,
            SeverityLevel.HIGH: 0.3,
            SeverityLevel.MEDIUM: 0.2,
            SeverityLevel.LOW: 0.1,
            SeverityLevel.INFO: 0.05
        }

        total_penalty = 0.0
        for issue in issues:
            penalty = severity_weights.get(issue.severity, 0.1)
            # Уменьшаем штраф, если есть автоисправление
            if issue.auto_fixable and issue.location in corrections:
                penalty *= 0.5
            total_penalty += penalty

        confidence = max(0.0, 1.0 - total_penalty)
        return min(1.0, confidence)

    async def _determine_validity(
        self,
        issues: List[ValidationIssue],
        confidence_score: float,
        threshold: float
    ) -> bool:
        """Определение общей валидности"""
        # Критические ошибки делают результат невалидным
        critical_issues = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
        if critical_issues:
            return False

        # Проверка порога уверенности
        return confidence_score >= threshold

    async def _generate_summary(
        self,
        issues: List[ValidationIssue],
        corrections: Dict[str, Any],
        is_valid: bool
    ) -> str:
        """Генерация сводки валидации"""
        if is_valid and not issues:
            return "Validation passed with no issues found"

        if is_valid and issues:
            return f"Validation passed with {len(issues)} minor issues"

        summary_parts = [f"Validation failed with {len(issues)} issues"]

        # Группировка по severity
        severity_counts = {}
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        severity_details = []
        for severity, count in severity_counts.items():
            severity_details.append(f"{count} {severity.value}")

        if severity_details:
            summary_parts.append(f"({', '.join(severity_details)})")

        if corrections:
            summary_parts.append(f"{len(corrections)} auto-corrections applied")

        return "; ".join(summary_parts)

    async def _simulate_multiple_agents(self, request: ConsensusRequest) -> List[Dict[str, Any]]:
        """Симуляция множественных агентов для MAGCC"""
        # В реальности здесь будут вызовы к разным LLM или разным prompt strategies
        evaluations = []

        for i in range(3):  # Симуляция 3 агентов
            # Случайная оценка для демонстрации
            import random
            selected_option = random.choice(request.options)
            confidence = random.uniform(0.6, 0.9)

            evaluations.append({
                "agent_id": f"agent_{i}",
                "selected_option": selected_option,
                "confidence": confidence,
                "reasoning": f"Agent {i} reasoning for {selected_option}"
            })

        return evaluations

    async def _analyze_consensus(
        self,
        evaluations: List[Dict[str, Any]],
        request: ConsensusRequest
    ) -> Dict[str, Any]:
        """Анализ консенсуса между агентами"""
        # Подсчет голосов
        vote_counts = {}
        confidence_sums = {}
        individual_scores = {}

        for eval_data in evaluations:
            option = eval_data["selected_option"]
            confidence = eval_data["confidence"]
            agent_id = eval_data["agent_id"]

            vote_counts[option] = vote_counts.get(option, 0) + 1
            confidence_sums[option] = confidence_sums.get(option, 0) + confidence
            individual_scores[agent_id] = confidence

        # Определение победителя
        max_votes = max(vote_counts.values())
        winners = [opt for opt, votes in vote_counts.items() if votes == max_votes]

        if len(winners) == 1:
            selected_option = winners[0]
            avg_confidence = confidence_sums[selected_option] / vote_counts[selected_option]
        else:
            # Tie-breaking по средней уверенности
            best_option = max(winners, key=lambda opt: confidence_sums[opt] / vote_counts[opt])
            selected_option = best_option
            avg_confidence = confidence_sums[selected_option] / vote_counts[selected_option]

        reasoning = f"Selected '{selected_option}' with {vote_counts[selected_option]} votes and {avg_confidence:.2f} average confidence"

        return {
            "option": selected_option,
            "confidence": avg_confidence,
            "reasoning": reasoning,
            "scores": individual_scores
        }

    async def _get_comparison_rules(self) -> List[ValidationRule]:
        """Получение правил для сравнения версий"""
        return [rule for rule in self._validation_rules.values()
                if rule.validation_type == ValidationType.DATA_INTEGRITY]

    async def _validate_rule_syntax(self, rule: ValidationRule) -> None:
        """Валидация синтаксиса правила"""
        if not rule.rule_code.strip():
            raise RuleEngineError("Rule code cannot be empty")

        # Базовая проверка синтаксиса (в реальности более сложная)
        if "return" not in rule.rule_code:
            raise RuleEngineError("Rule code must contain return statement")

    def _initialize_default_rules(self) -> None:
        """Инициализация базовых правил валидации"""
        default_rules = [
            {
                "name": "Document Title Length",
                "description": "Checks if document title meets minimum length requirements",
                "validation_type": ValidationType.DOCUMENT,
                "severity": SeverityLevel.MEDIUM,
                "rule_code": "return len(data.get('title', '')) >= 5",
            },
            {
                "name": "Document Content Quality",
                "description": "Validates document content quality and length",
                "validation_type": ValidationType.DOCUMENT,
                "severity": SeverityLevel.LOW,
                "rule_code": "return len(data.get('content', '')) >= 50",
            },
            {
                "name": "Required Fields",
                "description": "Checks for required fields in case data",
                "validation_type": ValidationType.CASE_DATA,
                "severity": SeverityLevel.CRITICAL,
                "rule_code": "required = ['title', 'description', 'case_type', 'client_id']; return all(data.get(f) for f in required)",
            },
            {
                "name": "Case Type Validity",
                "description": "Validates case type against allowed values",
                "validation_type": ValidationType.CASE_DATA,
                "severity": SeverityLevel.HIGH,
                "rule_code": "valid_types = ['immigration', 'corporate', 'family', 'criminal', 'civil']; return data.get('case_type') in valid_types",
            },
            {
                "name": "Data Consistency",
                "description": "Checks data consistency between versions",
                "validation_type": ValidationType.DATA_INTEGRITY,
                "severity": SeverityLevel.HIGH,
                "rule_code": "return True",  # Специальная обработка в execute_single_rule
            }
        ]

        for rule_data in default_rules:
            try:
                rule = ValidationRule(**rule_data)
                self._validation_rules[rule.rule_id] = rule
            except Exception:
                pass  # Ignore initialization errors

    def _update_validation_stats(self, validation_type: ValidationType, is_valid: bool) -> None:
        """Обновление статистики валидации"""
        key = f"{validation_type.value}_{is_valid}"
        self._validation_stats[key] = self._validation_stats.get(key, 0) + 1

    def _update_rule_performance(self, rule_id: str, issues_count: int) -> None:
        """Обновление статистики производительности правил"""
        if rule_id not in self._rule_performance:
            self._rule_performance[rule_id] = {"executions": 0, "total_issues": 0}

        self._rule_performance[rule_id]["executions"] += 1
        self._rule_performance[rule_id]["total_issues"] += issues_count

    async def _log_validation(
        self,
        request: ValidationRequest,
        response: ValidationResponse,
        user_id: str
    ) -> None:
        """Логирование валидации"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_performed",
            payload={
                "request_id": request.request_id,
                "validation_type": request.validation_type.value,
                "is_valid": response.is_valid,
                "confidence_score": response.confidence_score,
                "issues_count": len(response.issues),
                "validation_time": response.validation_time
            }
        )

    async def _log_consensus(
        self,
        request: ConsensusRequest,
        response: ConsensusResponse,
        user_id: str
    ) -> None:
        """Логирование MAGCC consensus"""
        await self._log_audit_event(
            user_id=user_id,
            action="magcc_consensus",
            payload={
                "consensus_id": request.consensus_id,
                "achieved": response.achieved,
                "selected_option": response.selected_option,
                "confidence": response.confidence,
                "iterations": response.iterations
            }
        )

    async def _log_version_comparison(
        self,
        version1: Dict[str, Any],
        version2: Dict[str, Any],
        response: ValidationResponse,
        user_id: str
    ) -> None:
        """Логирование сравнения версий"""
        await self._log_audit_event(
            user_id=user_id,
            action="version_comparison",
            payload={
                "request_id": response.request_id,
                "differences_count": len(response.issues),
                "is_identical": response.is_valid,
                "validation_time": response.validation_time
            }
        )

    async def _log_rule_creation(self, rule: ValidationRule, user_id: str) -> None:
        """Логирование создания правила"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_rule_created",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "validation_type": rule.validation_type.value,
                "severity": rule.severity.value
            }
        )

    async def _log_validation_error(
        self,
        request: ValidationRequest,
        user_id: str,
        error: Exception
    ) -> None:
        """Логирование ошибки валидации"""
        await self._log_audit_event(
            user_id=user_id,
            action="validation_error",
            payload={
                "request_id": request.request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "validation_type": request.validation_type.value
            }
        )

    async def _log_consensus_error(
        self,
        request: ConsensusRequest,
        user_id: str,
        error: Exception
    ) -> None:
        """Логирование ошибки консенсуса"""
        await self._log_audit_event(
            user_id=user_id,
            action="consensus_error",
            payload={
                "consensus_id": request.consensus_id,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

    async def _log_rule_error(
        self,
        rule_data: Dict[str, Any],
        user_id: str,
        error: Exception
    ) -> None:
        """Логирование ошибки правила"""
        await self._log_audit_event(
            user_id=user_id,
            action="rule_creation_error",
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "rule_data": rule_data
            }
        )

    async def _log_rule_execution_error(
        self,
        rule: ValidationRule,
        request: ValidationRequest,
        error: Exception
    ) -> None:
        """Логирование ошибки выполнения правила"""
        await self._log_audit_event(
            user_id="system",
            action="rule_execution_error",
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "request_id": request.request_id,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"validator_agent_{user_id}",
            source="validator_agent",
            action=action,
            payload=payload,
            tags=["validator_agent", "validation", "quality_control"]
        )

        await self.memory.alog_audit(event)

    async def get_validation_stats(self) -> Dict[str, Any]:
        """Получение статистики валидации"""
        return {
            "validation_stats": self._validation_stats.copy(),
            "total_validations": len(self._validation_results),
            "total_rules": len(self._validation_rules),
            "active_rules": len([r for r in self._validation_rules.values() if r.enabled]),
            "consensus_requests": len(self._consensus_results),
            "rule_performance": self._rule_performance.copy()
        }

    async def get_validation_result(self, request_id: str) -> Optional[ValidationResponse]:
        """Получение результата валидации по ID"""
        return self._validation_results.get(request_id)

    async def get_consensus_result(self, consensus_id: str) -> Optional[ConsensusResponse]:
        """Получение результата консенсуса по ID"""
        return self._consensus_results.get(consensus_id)