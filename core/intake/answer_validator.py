"""
AI-powered answer validation for intake questionnaire.

Uses Gemini Flash to validate that answers are meaningful and relevant.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from core.intake.schema import IntakeQuestion

logger = structlog.get_logger(__name__)

# Blacklist of meaningless answers (before AI check)
MEANINGLESS_PATTERNS = [
    r"^[\s\.\,\!\?\-\_\+\=\*\#\@\$\%\^\&\(\)]+$",  # Only punctuation/symbols
    r"^[a-zA-Zа-яА-Я]$",  # Single letter
    r"^[0-9]+$",  # Only numbers (unless it's a number question)
    r"^(тест|test|asdf|qwerty|123|abc|ааа|ббб)$",  # Common test inputs
]

# Skip AI validation for these short answers that are obviously valid
VALID_SHORT_ANSWERS = {
    "да",
    "нет",
    "yes",
    "no",
    "м",
    "ж",
    "m",
    "f",  # Gender
}


def is_meaningless_answer(answer: str) -> bool:
    """Check if answer matches known meaningless patterns."""
    answer_clean = answer.strip().lower()

    # Allow known valid short answers
    if answer_clean in VALID_SHORT_ANSWERS:
        return False

    # Check against meaningless patterns
    return any(re.match(pattern, answer_clean, re.IGNORECASE) for pattern in MEANINGLESS_PATTERNS)


def build_validation_prompt(question_text: str, question_type: str, answer: str) -> str:
    """Build prompt for Gemini to validate answer."""
    return f"""Проверь ответ пользователя на вопрос анкеты для иммиграционного кейса EB-1A.

Вопрос: {question_text}
Тип вопроса: {question_type}
Ответ пользователя: {answer}

Оцени, является ли ответ осмысленным и релевантным вопросу.

ПРАВИЛА:
1. Ответ должен быть по теме вопроса
2. Ответ не должен быть бессмысленным набором символов
3. Для текстовых вопросов ожидается содержательный ответ (не "да"/"нет" если спрашивают описание)
4. Будь толерантен к кратким, но релевантным ответам
5. Если вопрос про дату - проверь формат
6. Если вопрос YES/NO - принимай любую форму да/нет

Ответь ТОЛЬКО JSON без markdown:
{{"is_valid": true/false, "reason": "причина если false", "suggestion": "как исправить если false"}}

Примеры:
- Вопрос "Ваше имя?", ответ "Иван Петров" → {{"is_valid": true}}
- Вопрос "Ваше имя?", ответ "." → {{"is_valid": false, "reason": "Ответ не содержит имени", "suggestion": "Укажите ваше полное имя"}}
- Вопрос "Область деятельности?", ответ "да" → {{"is_valid": false, "reason": "Ожидается название области", "suggestion": "Укажите вашу профессиональную область (например: IT, медицина)"}}
- Вопрос "Есть ли у вас награды?", ответ "нет" → {{"is_valid": true}}

JSON:"""


def parse_validation_response(response_text: str) -> dict:
    """Parse Gemini response to extract validation result."""
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Find JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))

        # Try parsing entire response as JSON
        return json.loads(text)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("answer_validator.parse_error", error=str(e), response=response_text[:200])
        # Default to valid if we can't parse (fail open)
        return {"is_valid": True}


async def validate_answer_with_ai(
    question: IntakeQuestion,
    answer: str,
) -> tuple[bool, str | None]:
    """
    Validate answer using Gemini Flash AI.

    Args:
        question: The intake question being answered
        answer: User's answer text

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if answer is valid
        - (False, "error message") if answer needs correction
    """
    answer_stripped = answer.strip()

    # Quick check for meaningless answers (no API call needed)
    if is_meaningless_answer(answer_stripped):
        return (False, "Пожалуйста, введите осмысленный ответ.")

    # Get question type
    question_type = question.type.value if hasattr(question.type, "value") else str(question.type)

    # Skip AI for да/нет answers ONLY for YES_NO questions
    if answer_stripped.lower() in VALID_SHORT_ANSWERS:
        if question_type == "yes_no":
            return (True, None)
        # For other question types, да/нет might be invalid - let AI check

    # Skip AI validation for document questions (handled separately)
    if question_type == "document":
        return (True, None)

    try:
        import google.generativeai as genai

        from config.settings import get_settings

        settings = get_settings()
        api_key = settings.gemini_api_key

        if not api_key:
            logger.warning("answer_validator.no_api_key")
            # Fail open - allow answer if no API key
            return (True, None)

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Build prompt
        prompt = build_validation_prompt(
            question_text=question.text_template,
            question_type=question_type,
            answer=answer_stripped,
        )

        # Call Gemini Flash
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                max_output_tokens=256,
            ),
        )

        if not response or not response.text:
            logger.warning("answer_validator.empty_response")
            return (True, None)

        # Parse response
        result = parse_validation_response(response.text)

        is_valid = result.get("is_valid", True)

        if is_valid:
            logger.info(
                "answer_validator.valid",
                question_id=question.id,
                answer_length=len(answer_stripped),
            )
            return (True, None)
        reason = result.get("reason", "Ответ не соответствует вопросу")
        suggestion = result.get("suggestion", "Пожалуйста, уточните ваш ответ")
        error_message = f"{reason}. {suggestion}"

        logger.info(
            "answer_validator.invalid",
            question_id=question.id,
            reason=reason,
        )
        return (False, error_message)

    except Exception as e:
        logger.exception("answer_validator.error", error=str(e))
        # Fail open on errors
        return (True, None)


async def validate_answer_basic(answer: str, min_words: int = 1) -> tuple[bool, str | None]:
    """
    Basic validation without AI (fast check).

    Args:
        answer: User's answer text
        min_words: Minimum number of words required

    Returns:
        Tuple of (is_valid, error_message)
    """
    answer_stripped = answer.strip()

    # Check for empty
    if not answer_stripped:
        return (False, "Ответ не может быть пустым.")

    # Check for meaningless
    if is_meaningless_answer(answer_stripped):
        return (False, "Пожалуйста, введите осмысленный ответ.")

    # Check minimum words
    word_count = len(answer_stripped.split())
    if word_count < min_words:
        return (False, f"Ответ слишком короткий (минимум {min_words} слов).")

    return (True, None)
