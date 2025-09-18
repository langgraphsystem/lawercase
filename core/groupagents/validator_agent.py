from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.dto.route_policy import RoutePolicy
from core.dto.task_request import TaskRequest
from core.llm.router import LLMRouter
from core.rag.retrieve import HybridRetriever, _default_retriever


class ValidationType(str, Enum):
    DOCUMENT = "document"
    CASE_DATA = "case_data"
    COMPARISON = "comparison"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ValidationRule:
    rule_id: str
    name: str
    severity: SeverityLevel
    validation_type: ValidationType
    expression: str
    message: str


class ValidationIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: uuid4().hex)
    rule_id: str
    message: str
    severity: SeverityLevel
    location: Optional[str] = None
    suggested_fix: Optional[str] = None


class ValidationResult(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    llm_feedback: Optional[str] = None


class ValidatorAgent:
    """Rule-based validator augmented with LLM feedback and RAG context."""

    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
    }

    def __init__(
        self,
        *,
        router: Optional[LLMRouter] = None,
        retriever: Optional[HybridRetriever] = None,
    ) -> None:
        self._router = router or LLMRouter()
        self._retriever = retriever or _default_retriever
        self._rules: List[ValidationRule] = self._default_rules()

    async def avalidate(self, *, data: Dict[str, Any], validation_type: ValidationType) -> ValidationResult:
        issues = [issue for issue in self._run_rules(data, validation_type)]
        is_valid = not any(issue.severity in {SeverityLevel.CRITICAL, SeverityLevel.HIGH} for issue in issues)
        summary = self._summarize(issues)
        feedback = await self._llm_feedback(data, issues) if issues else None
        return ValidationResult(is_valid=is_valid, issues=issues, summary=summary, llm_feedback=feedback)

    async def acompare_versions(self, *, left: Dict[str, Any], right: Dict[str, Any]) -> ValidationResult:
        diffs: List[ValidationIssue] = []
        for key in set(left) | set(right):
            if left.get(key) != right.get(key):
                diffs.append(
                    ValidationIssue(
                        rule_id="comparison",
                        message=f"Field '{key}' differs between versions",
                        severity=SeverityLevel.MEDIUM,
                        location=key,
                    )
                )
        summary = "No differences detected" if not diffs else f"Detected {len(diffs)} differences"
        feedback = await self._llm_feedback({"left": left, "right": right}, diffs) if diffs else None
        return ValidationResult(is_valid=not diffs, issues=diffs, summary=summary, llm_feedback=feedback)

    def _run_rules(self, data: Dict[str, Any], validation_type: ValidationType) -> Iterable[ValidationIssue]:
        for rule in self._rules:
            if rule.validation_type != validation_type:
                continue
            success = self._evaluate_expression(rule.expression, data)
            if not success:
                yield ValidationIssue(rule_id=rule.rule_id, message=rule.message, severity=rule.severity)

    def _evaluate_expression(self, expression: str, data: Dict[str, Any]) -> bool:
        tree = ast.parse(expression, mode="eval")
        return bool(self._eval_node(tree.body, data))

    def _eval_node(self, node: ast.AST, data: Dict[str, Any]) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(v, data) for v in node.values]
            result = values[0]
            for value in values[1:]:
                result = self.SAFE_OPERATORS[type(node.op)](result, value)
            return result
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, data)
            right = self._eval_node(node.right, data)
            return self.SAFE_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, data)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, data)
                if not self.SAFE_OPERATORS[type(op)](left, right):
                    return False
            return True
        if isinstance(node, ast.Name):
            return data.get(node.id)
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    def _summarize(self, issues: List[ValidationIssue]) -> str:
        if not issues:
            return "Validation passed with no issues"
        counts = {SeverityLevel.CRITICAL: 0, SeverityLevel.HIGH: 0, SeverityLevel.MEDIUM: 0, SeverityLevel.LOW: 0}
        for issue in issues:
            counts[issue.severity] += 1
        parts = [f"{severity}: {count}" for severity, count in counts.items() if count]
        return "Validation uncovered issues - " + ", ".join(parts)

    async def _llm_feedback(self, data: Dict[str, Any], issues: List[ValidationIssue]) -> str:
        query = " ".join(issue.message for issue in issues) or "validation guidance"
        context_chunks = await self._retriever.retrieve(query)
        context_text = "\n".join(chunk.text for chunk in context_chunks[:3])
        prompt = (
            "Provide actionable remediation guidance for the following validation issues."
            f"\nData: {data}\nIssues: {[issue.message for issue in issues]}\n"
        )
        if context_text:
            prompt = f"Context:\n{context_text}\n\n{prompt}"
        response = await self._router.invoke(
            TaskRequest(prompt=prompt, policy=RoutePolicy(label="validator_feedback", provider_priority=["anthropic", "openai"]))
        )
        return response.text

    def _default_rules(self) -> List[ValidationRule]:
        return [
            ValidationRule(
                rule_id=uuid4().hex,
                name="Document title length",
                severity=SeverityLevel.MEDIUM,
                validation_type=ValidationType.DOCUMENT,
                expression="len(title or \'\'\') >= 5",
                message="Document title must contain at least five characters",
            ),
            ValidationRule(
                rule_id=uuid4().hex,
                name="Document content length",
                severity=SeverityLevel.LOW,
                validation_type=ValidationType.DOCUMENT,
                expression="len(content or \'\'\') >= 50",
                message="Document content is too short",
            ),
            ValidationRule(
                rule_id=uuid4().hex,
                name="Case required fields",
                severity=SeverityLevel.CRITICAL,
                validation_type=ValidationType.CASE_DATA,
                expression="title is not None and description is not None and client_id is not None",
                message="Missing required fields (title, description, client_id)",
            ),
        ]