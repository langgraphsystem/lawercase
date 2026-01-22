"""
Timeline extraction module for parsing temporal data from user answers.

Extracts structured timeline information (dates, locations, roles, activities)
to enable chronological reconstruction of user's life/career history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class TimelineData:
    """
    Structured timeline information extracted from text.

    Attributes:
        start_year: Beginning year (if found)
        end_year: Ending year (if found)
        location: City/country (if found)
        role: User's role/position (if found)
        organization: Company/school/university name (if found)
        activity_type: Type of activity (school, university, job, project, award, course)
        raw_text: Original text for fallback
    """

    start_year: int | None = None
    end_year: int | None = None
    location: str | None = None
    role: str | None = None
    organization: str | None = None
    activity_type: str | None = None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_year": self.start_year,
            "end_year": self.end_year,
            "location": self.location,
            "role": self.role,
            "organization": self.organization,
            "activity_type": self.activity_type,
            "raw_text": self.raw_text,
        }


def extract_timeline_data(answer: str, question_context: str | None = None) -> TimelineData:
    """
    Extract timeline information from user's answer.

    Args:
        answer: User's text response
        question_context: Optional context hint (e.g., "school", "career", "university")

    Returns:
        TimelineData object with extracted information

    Examples:
        "2018-2021, Data Scientist в компании X, Берлин"
        → TimelineData(start=2018, end=2021, role="Data Scientist",
                       organization="компания X", location="Берлин")

        "МГУ, Москва, 2010-2014"
        → TimelineData(start=2010, end=2014, organization="МГУ", location="Москва")
    """
    data = TimelineData(raw_text=answer)

    # Extract years
    years = _extract_years(answer)
    if years:
        if len(years) >= 2:
            data.start_year = min(years)
            data.end_year = max(years)
        elif len(years) == 1:
            data.start_year = years[0]

    # Extract location (city, country)
    data.location = _extract_location(answer)

    # Extract organization name
    data.organization = _extract_organization(answer)

    # Extract role/position
    data.role = _extract_role(answer)

    # Infer activity type from context or keywords
    data.activity_type = _infer_activity_type(answer, question_context)

    return data


def _extract_years(text: str) -> list[int]:
    """
    Extract all 4-digit years from text.

    Examples:
        "2018-2021" → [2018, 2021]
        "с 2010 по 2014" → [2010, 2014]
        "2023" → [2023]
    """
    # Match 4-digit years (1900-2099 range)
    year_pattern = r"\b(19\d{2}|20\d{2})\b"
    matches = re.findall(year_pattern, text)
    return [int(year) for year in matches]


def _extract_location(text: str) -> str | None:
    """
    Extract location (city, country) from text.

    Looks for common patterns like "Москва", "Берлин, Германия", "San Francisco, USA"

    Examples:
        "Google, Цюрих, Швейцария" → "Цюрих, Швейцария"
        "Школа №57, Москва" → "Москва"
    """
    # Common city patterns (Russian and English)
    city_keywords = [
        "Москва",
        "Санкт-Петербург",
        "Петербург",
        "Берлин",
        "Лондон",
        "Париж",
        "Цюрих",
        "Нью-Йорк",
        "New York",
        "San Francisco",
        "Boston",
        "Seattle",
        "Los Angeles",
        "Chicago",
    ]

    # Look for city names
    for city in city_keywords:
        if city in text:
            # Try to extract city + country if present
            # Pattern: "City, Country" or "City (Country)"
            city_match = re.search(rf"{city}[,\s]+([А-ЯЁа-яёA-Za-z\s-]+)", text)
            if city_match:
                country = city_match.group(1).strip()
                # Clean up common trailing words
                country = re.sub(r"\s+(и|в|на|от|до|с|по).*$", "", country).strip()
                if len(country) > 2:  # Reasonable country name length
                    return f"{city}, {country}"
            return city

    # Fallback: look for capitalized words that might be cities (heuristic)
    # Pattern: "Capitalized, Capitalized"
    location_match = re.search(r"([А-ЯЁA-Z][а-яёa-z]+),\s*([А-ЯЁA-Z][а-яёa-z]+)", text)
    if location_match:
        return f"{location_match.group(1)}, {location_match.group(2)}"

    return None


def _extract_organization(text: str) -> str | None:
    """
    Extract organization name (company, school, university).

    Looks for patterns like "в компании X", "школа №57", "университет МГУ"

    Examples:
        "Google, Цюрих" → "Google"
        "Школа №57, Москва" → "Школа №57"
        "МГУ, Москва" → "МГУ"
    """
    # University patterns
    university_patterns = [
        r"(МГУ|СПбГУ|МФТИ|ВШЭ|МГТУ)",  # Russian abbreviations
        r"([А-ЯЁ][а-яё]+\s+университет[а-я]*)",  # "Московский университет"
        r"(University of [A-Z][a-z]+)",  # "University of X"
        r"([A-Z][a-z]+\s+University)",  # "Stanford University"
    ]

    for pattern in university_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    # School patterns
    school_patterns = [
        r"([Шш]кола\s+№?\d+)",  # "Школа №57" or "школа 57"
        r"([А-ЯЁ][а-яё]+\s+гимназия)",  # "Физматшкола", "Математическая гимназия"
    ]

    for pattern in school_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    # Company patterns
    company_indicators = ["компани", "организаци", "корпораци", "фирм", "стартап"]
    for indicator in company_indicators:
        # Pattern: "в компании X"
        pattern = rf"в\s+{indicator}[еи]\s+([А-ЯЁA-Z][а-яёa-zA-Z0-9\s-]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            org_name = match.group(1).strip()
            # Stop at first comma or parenthesis
            org_name = re.split(r"[,(]", org_name)[0].strip()
            return org_name

    # Generic pattern: Capitalized word(s) before comma
    # E.g., "Google, Цюрих" or "Yandex, Москва"
    generic_match = re.search(r"^([А-ЯЁA-Z][а-яёa-zA-Z0-9\s&-]+?),", text)
    if generic_match:
        org_candidate = generic_match.group(1).strip()
        # Filter out dates and common non-org words
        if not re.match(r"^\d{4}$", org_candidate) and len(org_candidate) > 2:
            return org_candidate

    return None


def _extract_role(text: str) -> str | None:
    """
    Extract role/position from text.

    Looks for patterns like "Software Engineer", "Data Scientist", "профессор"

    Examples:
        "Software Engineer в Google" → "Software Engineer"
        "работал дата-сайентистом" → "дата-сайентист"
    """
    # Common English role titles
    english_roles = [
        "Software Engineer",
        "Senior Engineer",
        "Tech Lead",
        "Engineering Manager",
        "Data Scientist",
        "Machine Learning Engineer",
        "Research Scientist",
        "Product Manager",
        "CTO",
        "CEO",
        "Founder",
        "Professor",
        "Researcher",
    ]

    for role in english_roles:
        if role in text:
            return role

    # Russian role patterns
    russian_role_patterns = [
        r"(разработчик[ом]*)",
        r"(инженер[ом]*)",
        r"(дата-сайентист[ом]*)",
        r"(аналитик[ом]*)",
        r"(менеджер[ом]*)",
        r"(директор[ом]*)",
        r"(руководител[ьемя]+)",
        r"(профессор[ом]*)",
        r"(преподавател[ьемя]+)",
        r"(исследовател[ьемя]+)",
        r"(основател[ьемя]+)",
    ]

    for pattern in russian_role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            role = match.group(1)
            # Normalize to nominative case (basic heuristic)
            role = re.sub(r"ом$", "", role)  # Remove instrumental case ending
            role = re.sub(r"ем$", "", role)
            return role

    return None


def _infer_activity_type(text: str, context: str | None) -> str | None:
    """
    Infer the type of activity from text or context.

    Args:
        text: User's answer
        context: Question context hint (e.g., "school", "career")

    Returns:
        Activity type: "school", "university", "job", "project", "award", "course"
    """
    if context:
        context_lower = context.lower()
        if "school" in context_lower:
            return "school"
        if "university" in context_lower or "college" in context_lower:
            return "university"
        if "career" in context_lower or "job" in context_lower or "work" in context_lower:
            return "job"
        if "project" in context_lower or "research" in context_lower:
            return "project"
        if "award" in context_lower or "prize" in context_lower:
            return "award"
        if "course" in context_lower or "certificate" in context_lower:
            return "course"

    # Infer from keywords in text
    text_lower = text.lower()

    if any(word in text_lower for word in ["школа", "school", "гимназия"]):
        return "school"

    if any(
        word in text_lower
        for word in ["университет", "university", "колледж", "college", "институт"]
    ):
        return "university"

    if any(
        word in text_lower
        for word in ["компани", "работ", "должност", "позици", "company", "job", "position"]
    ):
        return "job"

    if any(word in text_lower for word in ["проект", "исследовани", "project", "research"]):
        return "project"

    if any(
        word in text_lower for word in ["награ", "приз", "award", "prize", "конкурс", "competition"]
    ):
        return "award"

    if any(word in text_lower for word in ["курс", "сертификат", "course", "certificate"]):
        return "course"

    return None
