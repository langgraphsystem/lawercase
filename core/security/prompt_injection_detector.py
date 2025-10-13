"""Prompt injection detection system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class InjectionType(str, Enum):
    """Types of prompt injection attacks."""

    DIRECT_INJECTION = "direct_injection"  # Direct command injection
    JAILBREAK = "jailbreak"  # Attempts to bypass restrictions
    ROLE_MANIPULATION = "role_manipulation"  # Trying to change system role
    DELIMITER_ATTACK = "delimiter_attack"  # Using delimiters to confuse
    CONTEXT_SWITCH = "context_switch"  # Switching conversation context
    DATA_EXFILTRATION = "data_exfiltration"  # Attempting to extract data
    NONE = "none"  # No injection detected


@dataclass
class PromptInjectionResult:
    """Result of prompt injection detection."""

    is_injection: bool
    injection_types: list[InjectionType] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 to 1.0
    details: dict[str, Any] = field(default_factory=dict)
    sanitized_prompt: str = ""

    def __post_init__(self) -> None:
        """Calculate overall confidence."""
        if self.injection_types:
            self.is_injection = True
            # Average confidence if multiple types detected
            if "type_confidences" in self.details:
                confidences = self.details["type_confidences"].values()
                self.confidence = sum(confidences) / len(confidences) if confidences else 0.0


class PromptInjectionDetector:
    """Detects and prevents prompt injection attacks."""

    def __init__(self, strictness: float = 0.7) -> None:
        """Initialize detector.

        Args:
            strictness: Detection threshold (0.0-1.0, higher = stricter)
        """
        self.strictness = max(0.0, min(1.0, strictness))
        self._compile_patterns()
        logger.info(f"PromptInjectionDetector initialized with strictness={self.strictness}")

    def _compile_patterns(self) -> None:
        """Compile regex patterns for detection."""
        # Direct injection patterns
        self.direct_injection_patterns = [
            r"ignore\s+(previous|above|all)\s+(instructions?|commands?|prompts?)",
            r"ignore\s+(previous|above|all)\b",
            r"disregard\s+(previous|above|all)",
            r"forget\s+(everything|all|previous)",
            r"new\s+(instructions?|commands?|task|role)",
            r"system\s+(prompt|message|instruction)\s*:",
            r"override\s+(instructions?|settings?|rules?)",
        ]

        # Jailbreak patterns
        self.jailbreak_patterns = [
            r"(you are|act as|pretend to be)\s+(no longer|not)",
            r"(developer|admin|root)\s+mode",
            r"(bypass|disable|turn off)\s+(safety|filter|restriction)",
            r"(DAN|Do Anything Now)",
            r"hypothetically|theoretically.*unethical",
        ]

        # Role manipulation patterns
        self.role_manipulation_patterns = [
            r"you are now\s+(?!an? assistant)",
            r"your (new )?role is",
            r"from now on,?\s+you (will|must|should|are)",
            r"(act|behave|respond)\s+as (if|though).*different",
        ]

        # Delimiter attacks
        self.delimiter_patterns = [
            r"['\"]?system['\"]?\s*[:=]",
            r"<\|.*?\|>",  # Special tokens
            r"```\s*system",
            r"###\s*(system|instruction|prompt)",
        ]

        # Context switching
        self.context_switch_patterns = [
            r"(end|stop|finish)\s+previous\s+(task|conversation)",
            r"(new|different)\\s+(conversation|topic|task).*\\s+start",
            r"(clear|reset)\s+(context|history|memory)",
        ]

        # Data exfiltration
        self.data_exfiltration_patterns = [
            r"(show|display|print|reveal|expose)[\s\S]{0,40}(data|information|secrets\?|keys\?|passwords\?|tokens\?)",
            r"what (are|is)\s+your?\s+(system prompt|instructions?|rules?)",
            r"(dump|export|extract)\s+(database|data|information)",
        ]

    def detect(self, prompt: str) -> PromptInjectionResult:
        """Detect prompt injection in input.

        Args:
            prompt: User prompt to check

        Returns:
            PromptInjectionResult with detection details
        """
        injection_types: list[InjectionType] = []
        type_confidences: dict[str, float] = {}
        matched_patterns: list[str] = []

        prompt_lower = prompt.lower()

        # Check each category
        checks = [
            (
                InjectionType.DIRECT_INJECTION,
                self.direct_injection_patterns,
            ),
            (InjectionType.JAILBREAK, self.jailbreak_patterns),
            (InjectionType.ROLE_MANIPULATION, self.role_manipulation_patterns),
            (InjectionType.DELIMITER_ATTACK, self.delimiter_patterns),
            (InjectionType.CONTEXT_SWITCH, self.context_switch_patterns),
            (InjectionType.DATA_EXFILTRATION, self.data_exfiltration_patterns),
        ]

        for injection_type, patterns in checks:
            matches = 0
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    matches += 1
                    matched_patterns.append(pattern)

            if matches > 0:
                # Treat any single-category hit as strong enough for detection
                confidence = 0.9
                if confidence >= self.strictness:
                    injection_types.append(injection_type)
                    type_confidences[injection_type.value] = confidence

        # Additional heuristics
        heuristic_score = self._heuristic_checks(prompt)
        if heuristic_score >= self.strictness:
            type_confidences["heuristic"] = heuristic_score

        # Create result
        result = PromptInjectionResult(
            is_injection=bool(injection_types),
            injection_types=injection_types,
            details={
                "type_confidences": type_confidences,
                "matched_patterns": matched_patterns[:5],  # Limit for readability
                "heuristic_score": heuristic_score,
            },
            sanitized_prompt=self._sanitize(prompt) if injection_types else prompt,
        )

        if result.is_injection:
            logger.warning(
                f"Prompt injection detected: {injection_types} "
                f"(confidence: {result.confidence:.2f})"
            )

        return result

    def _heuristic_checks(self, prompt: str) -> float:
        """Perform heuristic checks for suspicious patterns.

        Args:
            prompt: Prompt to check

        Returns:
            Heuristic score (0.0-1.0)
        """
        score = 0.0

        # Excessive capitalization
        upper_ratio = sum(1 for c in prompt if c.isupper()) / len(prompt) if prompt else 0
        if upper_ratio > 0.3:
            score += 0.2

        # Excessive punctuation
        punct_count = sum(1 for c in prompt if c in "!?*#")
        if punct_count > 10:
            score += 0.2

        # Multiple language switches (very rough check)
        if re.search(r"[а-яА-Я].*[a-zA-Z]|[a-zA-Z].*[а-яА-Я]", prompt):
            if len(re.findall(r"[а-яА-Я]+|[a-zA-Z]+", prompt)) > 10:
                score += 0.1

        # Suspicious keywords density
        suspicious_words = [
            "hack",
            "exploit",
            "vulnerability",
            "bypass",
            "jailbreak",
            "injection",
        ]
        keyword_count = sum(1 for word in suspicious_words if word in prompt.lower())
        if keyword_count > 2:
            score += 0.3

        # Very long prompt (potential attack)
        if len(prompt) > 5000:
            score += 0.2

        return min(1.0, score)

    def _sanitize(self, prompt: str) -> str:
        """Attempt to sanitize a potentially malicious prompt.

        Args:
            prompt: Prompt to sanitize

        Returns:
            Sanitized prompt
        """
        sanitized = prompt

        # Remove obvious injection attempts
        patterns_to_remove = [
            r"ignore\s+(previous|above).*?\.",
            r"system\s*(prompt|instruction)\s*:.*?(\n|$)",
            r"<\|.*?\|>",
            r"```\s*system.*?```",
        ]

        for pattern in patterns_to_remove:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Normalize excessive characters
        sanitized = re.sub(r"!{3,}", "!", sanitized)
        sanitized = re.sub(r"\?{3,}", "?", sanitized)
        sanitized = re.sub(r"\*{3,}", "", sanitized)

        # Remove extra whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        logger.info("Prompt sanitized")

        return sanitized

    def is_safe(self, prompt: str, auto_sanitize: bool = False) -> tuple[bool, str]:
        """Check if prompt is safe to process.

        Args:
            prompt: Prompt to check
            auto_sanitize: Whether to auto-sanitize unsafe prompts

        Returns:
            Tuple of (is_safe, prompt_to_use)
        """
        result = self.detect(prompt)

        if not result.is_injection:
            return True, prompt

        if auto_sanitize:
            logger.info("Auto-sanitizing unsafe prompt")
            return False, result.sanitized_prompt

        return False, prompt


# Global instance
_detector: PromptInjectionDetector | None = None


def get_prompt_detector(strictness: float = 0.7) -> PromptInjectionDetector:
    """Get or create global prompt injection detector.

    Args:
        strictness: Detection threshold (only used for new instance)

    Returns:
        Global PromptInjectionDetector instance
    """
    global _detector
    if _detector is None:
        _detector = PromptInjectionDetector(strictness=strictness)
    return _detector
