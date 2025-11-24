"""
Validation module for different question types in intake questionnaire.

Provides type-specific validation and normalization for user answers.
"""

from __future__ import annotations

import re
from datetime import datetime


def validate_date(text: str) -> tuple[bool, str | None]:
    """
    Validate and normalize date input.

    Expects YYYY-MM-DD format.

    Args:
        text: User's input

    Returns:
        Tuple of (is_valid, normalized_value)
        - is_valid: True if format is correct
        - normalized_value: Date string in YYYY-MM-DD format, or None if invalid

    Examples:
        "2023-05-15" → (True, "2023-05-15")
        "2023-5-15" → (True, "2023-05-15")  # Zero-padded
        "15.05.2023" → (False, None)
        "invalid" → (False, None)
    """
    text = text.strip()

    # Try to parse various date formats
    date_patterns = [
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", "%Y-%m-%d"),  # 2023-05-15
        (r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", "%Y.%m.%d"),  # 2023.05.15
        (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", "%Y/%m/%d"),  # 2023/05/15
    ]

    for pattern, fmt in date_patterns:
        match = re.match(pattern, text)
        if match:
            try:
                # Parse and re-format to ensure valid date
                parsed_date = datetime.strptime(text, fmt)
                normalized = parsed_date.strftime("%Y-%m-%d")
                return (True, normalized)
            except ValueError:
                # Invalid date (e.g., 2023-13-99)
                return (False, None)

    return (False, None)


def validate_yes_no(text: str) -> tuple[bool, bool | None]:
    """
    Validate and normalize yes/no input.

    Accepts: да, нет, yes, no (case-insensitive) and variations.

    Args:
        text: User's input

    Returns:
        Tuple of (is_valid, normalized_value)
        - is_valid: True if recognized as yes/no
        - normalized_value: True for yes, False for no, None if unclear

    Examples:
        "да" → (True, True)
        "нет" → (True, False)
        "yes" → (True, True)
        "no" → (True, False)
        "может быть" → (False, None)
    """
    text_lower = text.lower().strip()

    # Positive responses
    yes_variants = ["да", "yes", "y", "конечно", "безусловно", "ага", "угу", "ок", "ok"]
    if text_lower in yes_variants:
        return (True, True)

    # Negative responses
    no_variants = ["нет", "no", "n", "не", "никак", "неа"]
    if text_lower in no_variants:
        return (True, False)

    # Unclear or ambiguous
    return (False, None)


def validate_select(text: str, options: list[str]) -> tuple[bool, str | None]:
    """
    Validate that text matches one of the provided options.

    Performs case-insensitive and fuzzy matching.

    Args:
        text: User's input
        options: List of valid options

    Returns:
        Tuple of (is_valid, matched_option)
        - is_valid: True if input matches an option
        - matched_option: The matched option string, or None if no match

    Examples:
        text="Python", options=["Python", "JavaScript", "Go"]
        → (True, "Python")

        text="python", options=["Python", "JavaScript"]
        → (True, "Python")  # Case-insensitive match

        text="Java", options=["Python", "JavaScript"]
        → (False, None)
    """
    text_lower = text.lower().strip()

    # Exact match (case-insensitive)
    for option in options:
        if option.lower() == text_lower:
            return (True, option)

    # Partial match (text contains option or vice versa)
    for option in options:
        option_lower = option.lower()
        if option_lower in text_lower or text_lower in option_lower:
            return (True, option)

    return (False, None)


def parse_list(text: str) -> list[str]:
    """
    Parse comma-separated or newline-separated list.

    Args:
        text: User's input with multiple items

    Returns:
        List of items (stripped, non-empty)

    Examples:
        "Python, JavaScript, Go" → ["Python", "JavaScript", "Go"]
        "Python\\nJavaScript\\nGo" → ["Python", "JavaScript", "Go"]
        "Python; JavaScript; Go" → ["Python", "JavaScript", "Go"]
        "  Python  ,  ,  Go  " → ["Python", "Go"]  # Empty items removed
    """
    # Replace newlines and semicolons with commas
    text = text.replace("\n", ",").replace(";", ",")

    # Split by comma
    items = text.split(",")

    # Strip whitespace and filter out empty items
    items = [item.strip() for item in items if item.strip()]

    return items


def validate_text(text: str, min_length: int = 1, max_length: int = 10000) -> tuple[bool, str]:
    """
    Validate free-form text input.

    Args:
        text: User's input
        min_length: Minimum required length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if text meets length requirements
        - error_message: Explanation if invalid, empty string if valid

    Examples:
        "Some text" → (True, "")
        "" → (False, "Ответ не может быть пустым.")
        "x" * 20000 → (False, "Ответ слишком длинный (максимум 10000 символов).")
    """
    text = text.strip()

    if len(text) < min_length:
        return (False, f"Ответ слишком короткий (минимум {min_length} символов).")

    if len(text) > max_length:
        return (False, f"Ответ слишком длинный (максимум {max_length} символов).")

    return (True, "")


def is_media_message(update) -> bool:
    """
    Check if Telegram update contains media instead of text.

    Args:
        update: Telegram Update object

    Returns:
        True if message contains voice, photo, document, video, or sticker
    """
    if not update or not update.effective_message:
        return False

    message = update.effective_message

    return any(
        [
            message.voice,
            message.photo,
            message.document,
            message.video,
            message.sticker,
            message.audio,
            message.animation,
        ]
    )
