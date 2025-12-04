"""
Unit tests for intake validation module.

Tests all validators: date, yes/no, select, text, list parsing, and media detection.
"""

from __future__ import annotations

from core.intake.validation import (is_media_message, parse_list,
                                    validate_date, validate_select,
                                    validate_text, validate_yes_no)


class TestValidateDate:
    """Test date validation and normalization."""

    def test_valid_date_yyyy_mm_dd(self):
        """Test valid date in YYYY-MM-DD format."""
        is_valid, normalized = validate_date("2023-05-15")
        assert is_valid is True
        assert normalized == "2023-05-15"

    def test_valid_date_with_padding(self):
        """Test date with single-digit month/day gets zero-padded."""
        is_valid, normalized = validate_date("2023-5-15")
        assert is_valid is True
        assert normalized == "2023-05-15"

    def test_valid_date_dot_separator(self):
        """Test date with dot separators."""
        is_valid, normalized = validate_date("2023.05.15")
        assert is_valid is True
        assert normalized == "2023-05-15"

    def test_valid_date_slash_separator(self):
        """Test date with slash separators."""
        is_valid, normalized = validate_date("2023/05/15")
        assert is_valid is True
        assert normalized == "2023-05-15"

    def test_invalid_date_format(self):
        """Test invalid date format returns False."""
        is_valid, normalized = validate_date("15.05.2023")
        assert is_valid is False
        assert normalized is None

    def test_invalid_date_text(self):
        """Test non-date text returns False."""
        is_valid, normalized = validate_date("invalid")
        assert is_valid is False
        assert normalized is None

    def test_invalid_date_values(self):
        """Test invalid date values (e.g., month 13)."""
        is_valid, normalized = validate_date("2023-13-99")
        assert is_valid is False
        assert normalized is None

    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        is_valid, normalized = validate_date("  2023-05-15  ")
        assert is_valid is True
        assert normalized == "2023-05-15"


class TestValidateYesNo:
    """Test yes/no validation and normalization."""

    def test_yes_russian(self):
        """Test Russian 'да'."""
        is_valid, normalized = validate_yes_no("да")
        assert is_valid is True
        assert normalized is True

    def test_yes_english(self):
        """Test English 'yes'."""
        is_valid, normalized = validate_yes_no("yes")
        assert is_valid is True
        assert normalized is True

    def test_yes_short(self):
        """Test short 'y'."""
        is_valid, normalized = validate_yes_no("y")
        assert is_valid is True
        assert normalized is True

    def test_yes_variants(self):
        """Test various yes variants."""
        for variant in ["конечно", "безусловно", "ага", "угу", "ок", "ok"]:
            is_valid, normalized = validate_yes_no(variant)
            assert is_valid is True, f"Failed for variant: {variant}"
            assert normalized is True

    def test_no_russian(self):
        """Test Russian 'нет'."""
        is_valid, normalized = validate_yes_no("нет")
        assert is_valid is True
        assert normalized is False

    def test_no_english(self):
        """Test English 'no'."""
        is_valid, normalized = validate_yes_no("no")
        assert is_valid is True
        assert normalized is False

    def test_no_short(self):
        """Test short 'n'."""
        is_valid, normalized = validate_yes_no("n")
        assert is_valid is True
        assert normalized is False

    def test_no_variants(self):
        """Test various no variants."""
        for variant in ["не", "никак", "неа"]:
            is_valid, normalized = validate_yes_no(variant)
            assert is_valid is True, f"Failed for variant: {variant}"
            assert normalized is False

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        is_valid, normalized = validate_yes_no("YES")
        assert is_valid is True
        assert normalized is True

    def test_ambiguous_response(self):
        """Test ambiguous response returns False, None."""
        is_valid, normalized = validate_yes_no("может быть")
        assert is_valid is False
        assert normalized is None

    def test_whitespace_handling(self):
        """Test whitespace stripping."""
        is_valid, normalized = validate_yes_no("  да  ")
        assert is_valid is True
        assert normalized is True


class TestValidateSelect:
    """Test select (option list) validation."""

    def test_exact_match(self):
        """Test exact match to option."""
        options = ["Python", "JavaScript", "Go"]
        is_valid, matched = validate_select("Python", options)
        assert is_valid is True
        assert matched == "Python"

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        options = ["Python", "JavaScript", "Go"]
        is_valid, matched = validate_select("python", options)
        assert is_valid is True
        assert matched == "Python"

    def test_partial_match_option_in_text(self):
        """Test partial match when option is substring of text."""
        options = ["Python", "JavaScript"]
        is_valid, matched = validate_select("I like Python", options)
        assert is_valid is True
        assert matched == "Python"

    def test_partial_match_text_in_option(self):
        """Test partial match when text is substring of option."""
        options = ["Python Programming", "JavaScript"]
        is_valid, matched = validate_select("Python", options)
        assert is_valid is True
        assert matched == "Python Programming"

    def test_no_match(self):
        """Test no match returns False, None."""
        options = ["Python", "JavaScript"]
        is_valid, matched = validate_select("Ruby", options)
        assert is_valid is False
        assert matched is None

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        options = ["Python", "JavaScript"]
        is_valid, matched = validate_select("  Python  ", options)
        assert is_valid is True
        assert matched == "Python"


class TestParseList:
    """Test list parsing from various formats."""

    def test_comma_separated(self):
        """Test comma-separated list."""
        items = parse_list("Python, JavaScript, Go")
        assert items == ["Python", "JavaScript", "Go"]

    def test_newline_separated(self):
        """Test newline-separated list."""
        items = parse_list("Python\nJavaScript\nGo")
        assert items == ["Python", "JavaScript", "Go"]

    def test_semicolon_separated(self):
        """Test semicolon-separated list."""
        items = parse_list("Python; JavaScript; Go")
        assert items == ["Python", "JavaScript", "Go"]

    def test_mixed_separators(self):
        """Test mixed separators (comma and newline)."""
        items = parse_list("Python, JavaScript\nGo")
        assert items == ["Python", "JavaScript", "Go"]

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from items."""
        items = parse_list("  Python  ,  JavaScript  ,  Go  ")
        assert items == ["Python", "JavaScript", "Go"]

    def test_empty_items_filtered(self):
        """Test that empty items are filtered out."""
        items = parse_list("Python, , , Go")
        assert items == ["Python", "Go"]

    def test_single_item(self):
        """Test single item without separators."""
        items = parse_list("Python")
        assert items == ["Python"]

    def test_empty_string(self):
        """Test empty string returns empty list."""
        items = parse_list("")
        assert items == []


class TestValidateText:
    """Test text validation with length constraints."""

    def test_valid_text(self):
        """Test valid text within constraints."""
        is_valid, error = validate_text("Some text")
        assert is_valid is True
        assert error == ""

    def test_text_too_short(self):
        """Test text below minimum length."""
        is_valid, error = validate_text("", min_length=1)
        assert is_valid is False
        assert "короткий" in error.lower()

    def test_text_too_long(self):
        """Test text above maximum length."""
        is_valid, error = validate_text("x" * 20000, max_length=10000)
        assert is_valid is False
        assert "длинный" in error.lower()

    def test_exact_min_length(self):
        """Test text exactly at minimum length."""
        is_valid, error = validate_text("abc", min_length=3)
        assert is_valid is True
        assert error == ""

    def test_exact_max_length(self):
        """Test text exactly at maximum length."""
        is_valid, error = validate_text("x" * 100, max_length=100)
        assert is_valid is True
        assert error == ""

    def test_whitespace_stripped(self):
        """Test that whitespace is stripped before validation."""
        is_valid, error = validate_text("   ", min_length=1)
        assert is_valid is False

    def test_custom_min_length(self):
        """Test custom minimum length."""
        is_valid, error = validate_text("ab", min_length=5)
        assert is_valid is False
        assert "5" in error


class TestIsMediaMessage:
    """Test media message detection."""

    class MockMessage:
        """Mock Telegram message."""

        def __init__(self, **kwargs):
            self.voice = kwargs.get("voice")
            self.photo = kwargs.get("photo")
            self.document = kwargs.get("document")
            self.video = kwargs.get("video")
            self.sticker = kwargs.get("sticker")
            self.audio = kwargs.get("audio")
            self.animation = kwargs.get("animation")

    class MockUpdate:
        """Mock Telegram update."""

        def __init__(self, message=None):
            self.effective_message = message

    def test_text_message(self):
        """Test text-only message returns False."""
        message = self.MockMessage()
        update = self.MockUpdate(message)
        assert is_media_message(update) is False

    def test_voice_message(self):
        """Test voice message returns True."""
        message = self.MockMessage(voice=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_photo_message(self):
        """Test photo message returns True."""
        message = self.MockMessage(photo=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_document_message(self):
        """Test document message returns True."""
        message = self.MockMessage(document=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_video_message(self):
        """Test video message returns True."""
        message = self.MockMessage(video=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_sticker_message(self):
        """Test sticker message returns True."""
        message = self.MockMessage(sticker=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_audio_message(self):
        """Test audio message returns True."""
        message = self.MockMessage(audio=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_animation_message(self):
        """Test animation message returns True."""
        message = self.MockMessage(animation=True)
        update = self.MockUpdate(message)
        assert is_media_message(update) is True

    def test_no_update(self):
        """Test None update returns False."""
        assert is_media_message(None) is False

    def test_no_message(self):
        """Test update with no message returns False."""
        update = self.MockUpdate(None)
        assert is_media_message(update) is False
