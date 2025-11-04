"""Tests for PII Detection."""

from __future__ import annotations

import pytest

from core.security import PIIDetector, PIIType, get_pii_detector


class TestPIIDetector:
    """Test PII detection."""

    @pytest.fixture
    def detector(self) -> PIIDetector:
        """Create detector for testing."""
        return PIIDetector()

    def test_email_detection(self, detector: PIIDetector) -> None:
        """Test email detection."""
        text = "Contact me at john.doe@example.com for details"
        result = detector.detect(text)

        assert result.has_pii
        assert len(result.matches) == 1
        assert result.matches[0].pii_type == PIIType.EMAIL
        assert "john.doe@example.com" in result.matches[0].value

    def test_phone_detection(self, detector: PIIDetector) -> None:
        """Test phone number detection."""
        text = "Call me at (555) 123-4567"
        result = detector.detect(text)

        assert result.has_pii
        phone_matches = [m for m in result.matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) > 0

    def test_ssn_detection(self, detector: PIIDetector) -> None:
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        result = detector.detect(text)

        assert result.has_pii
        ssn_matches = [m for m in result.matches if m.pii_type == PIIType.SSN]
        assert len(ssn_matches) == 1

    def test_credit_card_detection(self, detector: PIIDetector) -> None:
        """Test credit card detection."""
        # Valid test credit card (passes Luhn check)
        text = "Card: 4532-1488-0343-6467"
        result = detector.detect(text)

        assert result.has_pii
        cc_matches = [m for m in result.matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) > 0

    def test_ip_detection(self, detector: PIIDetector) -> None:
        """Test IP address detection."""
        text = "Server IP: 192.168.1.100"
        result = detector.detect(text)

        assert result.has_pii
        ip_matches = [m for m in result.matches if m.pii_type == PIIType.IP_ADDRESS]
        assert len(ip_matches) == 1

    def test_multiple_pii_types(self, detector: PIIDetector) -> None:
        """Test detection of multiple PII types."""
        text = "Email: test@example.com Phone: 555-1234 SSN: 123-45-6789"
        result = detector.detect(text)

        assert result.has_pii
        assert len(result.matches) >= 2
        types_found = {m.pii_type for m in result.matches}
        assert PIIType.EMAIL in types_found

    def test_redaction(self, detector: PIIDetector) -> None:
        """Test PII redaction."""
        text = "My email is john@example.com and phone is 555-1234"
        result = detector.detect(text)

        assert result.has_pii
        assert "john@example.com" not in result.redacted_text
        assert "[REDACTED]" in result.redacted_text

    def test_redact_method(self, detector: PIIDetector) -> None:
        """Test convenience redact method."""
        text = "Contact: alice@example.com"
        redacted = detector.redact(text)

        assert "alice@example.com" not in redacted
        assert "[REDACTED]" in redacted

    def test_specific_pii_types(self, detector: PIIDetector) -> None:
        """Test detection of specific PII types only."""
        text = "Email: test@example.com Phone: 555-1234"

        # Only detect emails
        result = detector.detect(text, pii_types=[PIIType.EMAIL])

        email_matches = [m for m in result.matches if m.pii_type == PIIType.EMAIL]
        phone_matches = [m for m in result.matches if m.pii_type == PIIType.PHONE]

        assert len(email_matches) > 0
        assert len(phone_matches) == 0

    def test_scan_dict(self, detector: PIIDetector) -> None:
        """Test scanning dictionary for PII."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "notes": "Regular text",
        }

        redacted = detector.scan_dict(data, sensitive_keys=["email"])

        assert redacted["email"] == "[REDACTED]"
        assert redacted["notes"] == "Regular text"

    def test_no_pii(self, detector: PIIDetector) -> None:
        """Test text without PII."""
        text = "This is a normal sentence without any sensitive information"
        result = detector.detect(text)

        assert not result.has_pii
        assert len(result.matches) == 0
        assert result.redacted_text == text

    def test_luhn_validation(self, detector: PIIDetector) -> None:
        """Test that credit card detection uses Luhn validation."""
        # Invalid credit card number (doesn't pass Luhn)
        text = "Card: 1234-5678-9012-3456"
        result = detector.detect(text)

        cc_matches = [m for m in result.matches if m.pii_type == PIIType.CREDIT_CARD]
        # Should not detect invalid cards
        assert len(cc_matches) == 0

    def test_global_instance(self) -> None:
        """Test global detector instance."""
        detector1 = get_pii_detector()
        detector2 = get_pii_detector()

        assert detector1 is detector2  # Same instance
