"""
Fact synthesis module for converting Q&A into declarative statements.

Transforms raw user answers into structured, contextual facts suitable for
semantic memory storage and RAG retrieval.
"""

from __future__ import annotations

import re
from typing import Any

from core.intake.schema import IntakeQuestion


def synthesize_intake_fact(
    question: IntakeQuestion, answer: str, user_context: dict[str, Any] | None = None
) -> str:
    """
    Convert a question-answer pair into a declarative statement for semantic memory.

    This function combines the question context with the answer to create a
    self-contained fact that can be understood without the original question.

    Args:
        question: The IntakeQuestion that was asked
        answer: User's text response
        user_context: Optional context from previous answers (for dynamic templates)

    Returns:
        Declarative fact string with appropriate tags

    Examples:
        Q: "Были ли у вас значимые награды?"
        A: "Да, приз на хакатоне"
        → "[INTAKE][awards] Пользователь получил приз на хакатоне."

        Q: "В какой школе вы учились и в какие годы?"
        A: "Школа №57 в Москве, с 2005 по 2016"
        → "[INTAKE][school][timeline] С 2005 по 2016 годы пользователь учился в школе №57 в Москве."
    """
    # Normalize answer
    answer = answer.strip()

    # Build tag prefix from question tags
    tag_prefix = _build_tag_prefix(question.tags)

    # Extract question ID for context-specific synthesis
    question_id = question.id

    # Apply question-specific synthesis rules
    if question_id == "full_name":
        return f"{tag_prefix} Полное имя пользователя: {answer}."

    if question_id == "date_of_birth":
        return f"{tag_prefix} Дата рождения пользователя: {answer}."

    if question_id == "place_of_birth":
        return f"{tag_prefix} Пользователь родился в {answer}."

    if question_id == "citizenship":
        return f"{tag_prefix} Гражданство пользователя: {answer}."

    if question_id == "current_residence":
        return f"{tag_prefix} Пользователь сейчас живёт в {answer}."

    if question_id == "main_field":
        return f"{tag_prefix} Основная область деятельности пользователя: {answer}."

    # Family & childhood
    if question_id in (
        "parents_professions",
        "parents_education",
        "family_attitude_education",
        "early_interests",
    ):
        return f"{tag_prefix} {_extract_key_phrase(question.text_template)}: {answer}."

    # School questions
    if "school" in question_id:
        if "years" in answer.lower() or re.search(r"\d{4}", answer):
            # Timeline-related answer
            return f"{tag_prefix} {_timeline_synthesis(answer, 'школа', 'учился')}."
        return f"{tag_prefix} {_extract_key_phrase(question.text_template)}: {answer}."

    # University questions
    if "university" in question_id or "universities" in question_id:
        if "years" in answer.lower() or re.search(r"\d{4}", answer):
            return f"{tag_prefix} {_timeline_synthesis(answer, 'университет', 'учился')}."
        return f"{tag_prefix} {_extract_key_phrase(question.text_template)}: {answer}."

    # Career questions
    if "career" in question_id:
        if "companies" in question_id and (re.search(r"\d{4}", answer) or "годы" in answer.lower()):
            return f"{tag_prefix} {_timeline_synthesis(answer, 'компания', 'работал')}."
        if "critical_role" in question_id:
            return f"{tag_prefix} [EB-1A criterion: critical role] {answer}."
        if "high_salary" in question_id:
            return f"{tag_prefix} [EB-1A criterion: high salary] {answer}."
        return f"{tag_prefix} {_extract_key_phrase(question.text_template)}: {answer}."

    # Publications & research
    if "publications" in question_id or "metrics" in question_id:
        return f"{tag_prefix} Публикации и метрики: {answer}."

    if "open_source" in question_id:
        return f"{tag_prefix} Вклад в open source: {answer}."

    if "patents" in question_id:
        return f"{tag_prefix} Патенты и изобретения: {answer}."

    if "commercial_products" in question_id:
        return f"{tag_prefix} Коммерческие продукты: {answer}."

    # Awards
    if "awards" in question_id or "competitions" in question_id or "grants" in question_id:
        return f"{tag_prefix} Награды и достижения: {answer}."

    # Talks & public activity
    if "conferences" in question_id or "talks" in question_id:
        return f"{tag_prefix} Выступления на конференциях: {answer}."

    if "expert_roles" in question_id:
        return f"{tag_prefix} [EB-1A criterion: judging] Экспертные роли: {answer}."

    if "media" in question_id or "press" in question_id:
        return f"{tag_prefix} Освещение в СМИ: {answer}."

    # Recommenders
    if "recommender" in question_id:
        return f"{tag_prefix} Потенциальные рекомендатели: {answer}."

    # Goals
    if "goals" in question_id or "motivation" in question_id or "plans" in question_id:
        return f"{tag_prefix} {_extract_key_phrase(question.text_template)}: {answer}."

    # Macro context
    if "macro_context" in question.tags:
        return f"{tag_prefix} Макро-контекст: {answer}."

    # Default fallback
    # Generic synthesis: extract key phrase from question and combine with answer
    key_phrase = _extract_key_phrase(question.text_template)
    return f"{tag_prefix} {key_phrase}: {answer}."


def _build_tag_prefix(tags: list[str]) -> str:
    """
    Build a tag prefix string from question tags.

    Examples:
        ["intake", "school", "timeline"] → "[INTAKE][school][timeline]"
        ["intake", "career"] → "[INTAKE][career]"
    """
    if not tags:
        return "[INTAKE]"

    # Capitalize first tag, keep others lowercase
    formatted_tags = [tags[0].upper()] + [tag.lower() for tag in tags[1:]]
    return "".join(f"[{tag}]" for tag in formatted_tags)


def _extract_key_phrase(question_text: str) -> str:
    """
    Extract the key question phrase for fact construction.

    Examples:
        "Какова ваша основная область деятельности?" → "Основная область деятельности"
        "В каких школах вы учились?" → "Школы"
    """
    # Remove question mark and common prefixes
    text = question_text.replace("?", "").strip()

    # Remove common question starters
    prefixes_to_remove = [
        "Как ваше ",
        "Какова ваша ",
        "Каковы ваши ",
        "Какое у вас ",
        "Какие у вас ",
        "Где вы ",
        "Когда вы ",
        "В каких ",
        "В какой ",
        "Были ли у вас ",
        "Есть ли у вас ",
        "Занимались ли вы ",
        "Участвовали ли вы ",
        "Получали ли вы ",
        "Выполняли ли вы ",
        "Выступали ли вы ",
        "Освещалась ли ",
        "Вносили ли вы ",
        "Создавали ли вы ",
        "Управляли ли вы ",
        "Являетесь ли вы ",
        "Проходили ли вы ",
        "Кто ",
        "Почему ",
    ]

    for prefix in prefixes_to_remove:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]

    return text


def _timeline_synthesis(answer: str, context: str, verb: str) -> str:
    """
    Synthesize timeline-specific facts.

    Args:
        answer: User's answer containing dates/years
        context: Context word (школа, университет, компания)
        verb: Action verb (учился, работал)

    Returns:
        Timeline fact string

    Example:
        answer: "2010-2014, МГУ, Москва"
        context: "университет"
        verb: "учился"
        → "С 2010 по 2014 годы пользователь учился в МГУ, Москва"
    """
    # Try to extract year ranges
    year_match = re.search(
        r"(\d{4})\s*[-–]\s*(\d{4})|(\d{4})\s+по\s+(\d{4})|с\s+(\d{4})\s+по\s+(\d{4})", answer
    )

    if year_match:
        groups = year_match.groups()
        start_year = groups[0] or groups[2] or groups[4]
        end_year = groups[1] or groups[3] or groups[5]

        # Remove the matched years from answer to get remaining context
        remaining = re.sub(
            r"(\d{4})\s*[-–]\s*(\d{4})|(\d{4})\s+по\s+(\d{4})|с\s+(\d{4})\s+по\s+(\d{4})",
            "",
            answer,
        ).strip()

        # Clean up remaining punctuation
        remaining = re.sub(r"^[,;\s]+|[,;\s]+$", "", remaining).strip()

        if remaining:
            return f"С {start_year} по {end_year} годы пользователь {verb} в {remaining}"
        return f"С {start_year} по {end_year} годы пользователь {verb} в {context}"

    # No clear timeline, fallback to generic
    return f"Пользователь {verb} в {answer}"


def normalize_yes_no(text: str) -> bool | None:
    """
    Normalize да/нет/yes/no responses to boolean.

    Args:
        text: User's answer

    Returns:
        True for yes, False for no, None if unclear

    Examples:
        "да" → True
        "нет" → False
        "yes" → True
        "no" → False
        "может быть" → None
    """
    text_lower = text.lower().strip()

    # Positive responses
    if text_lower in ("да", "yes", "y", "конечно", "безусловно", "ага", "угу"):
        return True

    # Negative responses
    if text_lower in ("нет", "no", "n", "не", "никак"):
        return False

    # Unclear
    return None
