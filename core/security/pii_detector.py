"""PII (Personally Identifiable Information) detection and filtering."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"  # Social Security Number
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    NAME = "name"  # Proper names
    MEDICAL_RECORD = "medical_record"
    BANK_ACCOUNT = "bank_account"


@dataclass
class PIIMatch:
    """A detected PII match."""

    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class PIIDetectionResult:
    """Result of PII detection."""

    has_pii: bool
    matches: list[PIIMatch] = field(default_factory=list)
    redacted_text: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class PIIDetector:
    """Detects and redacts PII from text."""

    def __init__(self, redaction_marker: str = "[REDACTED]") -> None:
        """Initialize PII detector.

        Args:
            redaction_marker: Marker to use for redacted content
        """
        self.redaction_marker = redaction_marker
        self._compile_patterns()
        logger.info("PIIDetector initialized")

    def _compile_patterns(self) -> None:
        """Compile regex patterns for PII detection."""
        # Email addresses
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

        # Phone numbers (various formats)
        self.phone_patterns = [
            re.compile(r"\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"),  # US
            re.compile(r"\+\d{1,3}\s?\d{1,4}\s?\d{1,4}\s?\d{1,9}"),  # International
        ]

        # SSN (xxx-xx-xxxx)
        self.ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

        # Credit card (simplified - various formats)
        self.credit_card_patterns = [
            re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # 16 digits
            re.compile(r"\b\d{4}[\s-]?\d{6}[\s-]?\d{5}\b"),  # AmEx
        ]

        # IP addresses (IPv4)
        self.ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

        # Passport numbers (simplified - alphanumeric)
        self.passport_pattern = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")

        # Driver's license (simplified - varies by jurisdiction)
        self.driver_license_pattern = re.compile(r"\b[A-Z]\d{7,8}\b")

        # Dates that could be DOB (MM/DD/YYYY, DD-MM-YYYY, etc.)
        self.dob_patterns = [
            re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"),
            re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
        ]

        # Medical record numbers (simplified)
        self.medical_record_pattern = re.compile(r"\bMRN[:\s]?\d{6,10}\b", re.IGNORECASE)

        # Bank account numbers (simplified)
        self.bank_account_pattern = re.compile(r"\b\d{8,17}\b")

    def detect(self, text: str, pii_types: list[PIIType] | None = None) -> PIIDetectionResult:
        """Detect PII in text.

        Args:
            text: Text to scan for PII
            pii_types: Specific PII types to detect (None = all)

        Returns:
            PIIDetectionResult with matches
        """
        if pii_types is None:
            pii_types = list(PIIType)

        matches: list[PIIMatch] = []

        # Email
        if PIIType.EMAIL in pii_types:
            for match in self.email_pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=PIIType.EMAIL,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                )

        # Phone
        if PIIType.PHONE in pii_types:
            for pattern in self.phone_patterns:
                for match in pattern.finditer(text):
                    matches.append(
                        PIIMatch(
                            pii_type=PIIType.PHONE,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                        )
                    )

        # SSN
        if PIIType.SSN in pii_types:
            for match in self.ssn_pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=PIIType.SSN,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                )

        # Credit card
        if PIIType.CREDIT_CARD in pii_types:
            for pattern in self.credit_card_patterns:
                for match in pattern.finditer(text):
                    digits_only = "".join(ch for ch in match.group() if ch.isdigit())
                    is_luhn = self._verify_luhn(match.group())
                    looks_like_card = len(digits_only) in {15, 16} and digits_only[0] in {
                        "3",
                        "4",
                        "5",
                        "6",
                    }
                    if is_luhn or looks_like_card:
                        matches.append(
                            PIIMatch(
                                pii_type=PIIType.CREDIT_CARD,
                                value=match.group(),
                                start=match.start(),
                                end=match.end(),
                                confidence=1.0 if is_luhn else 0.7,
                            )
                        )

        # IP address
        if PIIType.IP_ADDRESS in pii_types:
            for match in self.ip_pattern.finditer(text):
                # Validate IP address
                if self._is_valid_ip(match.group()):
                    matches.append(
                        PIIMatch(
                            pii_type=PIIType.IP_ADDRESS,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                        )
                    )

        # Passport
        if PIIType.PASSPORT in pii_types:
            for match in self.passport_pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=PIIType.PASSPORT,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.7,  # Lower confidence without context
                    )
                )

        # Date of birth
        if PIIType.DATE_OF_BIRTH in pii_types:
            for pattern in self.dob_patterns:
                for match in pattern.finditer(text):
                    matches.append(
                        PIIMatch(
                            pii_type=PIIType.DATE_OF_BIRTH,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=0.6,  # Lower confidence - could be any date
                        )
                    )

        # Medical record
        if PIIType.MEDICAL_RECORD in pii_types:
            for match in self.medical_record_pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=PIIType.MEDICAL_RECORD,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                )

        # Sort matches by position
        matches.sort(key=lambda m: m.start)

        # Create result
        result = PIIDetectionResult(
            has_pii=len(matches) > 0,
            matches=matches,
            redacted_text=self._redact_matches(text, matches) if matches else text,
            details={
                "total_matches": len(matches),
                "types_found": list({m.pii_type for m in matches}),
            },
        )

        if result.has_pii:
            logger.info(
                f"PII detected: {len(matches)} matches of types {result.details['types_found']}"
            )

        return result

    def _verify_luhn(self, number_str: str) -> bool:
        """Verify number using Luhn algorithm (credit card validation).

        Args:
            number_str: Number string to verify

        Returns:
            True if valid
        """
        # Remove non-digits
        digits = [int(d) for d in number_str if d.isdigit()]

        if len(digits) < 13:
            return False

        # Luhn algorithm
        checksum = 0
        reverse_digits = digits[::-1]

        for i, d in enumerate(reverse_digits):
            digit = d
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address.

        Args:
            ip_str: IP address string

        Returns:
            True if valid
        """
        parts = ip_str.split(".")
        if len(parts) != 4:
            return False

        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False

    def _redact_matches(self, text: str, matches: list[PIIMatch]) -> str:
        """Redact matched PII from text.

        Args:
            text: Original text
            matches: PII matches to redact

        Returns:
            Redacted text
        """
        if not matches:
            return text

        # Build redacted text
        result = []
        last_end = 0

        for match in matches:
            # Add text before match
            result.append(text[last_end : match.start])

            # Add redaction marker with type
            marker = f"{self.redaction_marker}[{match.pii_type.value.upper()}]"
            result.append(marker)

            last_end = match.end

        # Add remaining text
        result.append(text[last_end:])

        return "".join(result)

    def redact(
        self,
        text: str,
        pii_types: list[PIIType] | None = None,
        preserve_format: bool = True,
    ) -> str:
        """Detect and redact PII from text.

        Args:
            text: Text to redact
            pii_types: Specific PII types to redact (None = all)
            preserve_format: Whether to preserve format (e.g., xxx-xx-xxxx for SSN)

        Returns:
            Redacted text
        """
        result = self.detect(text, pii_types)
        return result.redacted_text

    def scan_dict(
        self, data: dict[str, Any], sensitive_keys: list[str] | None = None
    ) -> dict[str, Any]:
        """Scan dictionary for PII and redact.

        Args:
            data: Dictionary to scan
            sensitive_keys: Keys that definitely contain PII

        Returns:
            Dictionary with PII redacted
        """
        if sensitive_keys is None:
            sensitive_keys = [
                "email",
                "phone",
                "ssn",
                "credit_card",
                "password",
                "api_key",
                "token",
            ]

        result = {}

        for key, value in data.items():
            # Check if key is known sensitive
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                result[key] = self.redaction_marker
            elif isinstance(value, str):
                # Scan string values
                detection = self.detect(value)
                result[key] = detection.redacted_text if detection.has_pii else value
            elif isinstance(value, dict):
                # Recursively scan nested dicts
                result[key] = self.scan_dict(value, sensitive_keys)
            elif isinstance(value, list):
                # Scan lists
                result[key] = [
                    (
                        self.scan_dict(item, sensitive_keys)
                        if isinstance(item, dict)
                        else self.redact(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            else:
                result[key] = value

        return result


# Global instance
_pii_detector: PIIDetector | None = None


def get_pii_detector() -> PIIDetector:
    """Get or create global PII detector.

    Returns:
        Global PIIDetector instance
    """
    global _pii_detector
    if _pii_detector is None:
        _pii_detector = PIIDetector()
    return _pii_detector
