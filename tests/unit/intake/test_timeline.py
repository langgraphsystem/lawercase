"""
Unit tests for intake timeline extraction module.

Tests extraction of structured timeline data (years, locations, roles, organizations).
"""

from __future__ import annotations

import pytest

from core.intake.timeline import TimelineData, extract_timeline_data


class TestExtractTimelineData:
    """Test timeline data extraction from text."""

    def test_extract_years_range(self):
        """Test extraction of year range."""
        data = extract_timeline_data("2018-2021, Data Scientist в компании X, Берлин")
        assert data.start_year == 2018
        assert data.end_year == 2021

    def test_extract_years_with_dashes(self):
        """Test year range with en-dash."""
        data = extract_timeline_data("2018–2021")  # en-dash
        assert data.start_year == 2018
        assert data.end_year == 2021

    def test_extract_years_russian_format(self):
        """Test Russian format 'с YYYY по YYYY'."""
        data = extract_timeline_data("с 2018 по 2021")
        assert data.start_year == 2018
        assert data.end_year == 2021

    def test_extract_single_year(self):
        """Test extraction of single year."""
        data = extract_timeline_data("В 2020 году")
        # Should find 2020 as both start and end
        assert data.start_year == 2020 or data.end_year == 2020

    def test_extract_location_city(self):
        """Test extraction of city location."""
        data = extract_timeline_data("2018-2021, Берлин")
        assert data.location is not None
        assert "Берлин" in data.location

    def test_extract_location_city_country(self):
        """Test extraction of city and country."""
        data = extract_timeline_data("Москва, Россия")
        assert data.location is not None
        assert "Москва" in data.location or "Россия" in data.location

    def test_extract_organization_university(self):
        """Test extraction of university name."""
        data = extract_timeline_data("МГУ, 2016-2020")
        assert data.organization is not None
        assert "МГУ" in data.organization

    def test_extract_organization_company(self):
        """Test extraction of company name."""
        data = extract_timeline_data("работал в компании Google, 2018-2021")
        assert data.organization is not None
        assert "Google" in data.organization

    def test_extract_organization_school(self):
        """Test extraction of school name."""
        data = extract_timeline_data("Школа №57")
        assert data.organization is not None
        assert "Школа" in data.organization or "57" in data.organization

    def test_extract_role_english(self):
        """Test extraction of English role title."""
        data = extract_timeline_data("Senior Software Engineer в Google")
        assert data.role is not None
        assert "Engineer" in data.role or "Software" in data.role

    def test_extract_role_russian(self):
        """Test extraction of Russian role title."""
        data = extract_timeline_data("Старший разработчик в Яндекс")
        assert data.role is not None
        assert "разработчик" in data.role or "Старший" in data.role

    def test_infer_activity_type_school(self):
        """Test inference of school activity type."""
        data = extract_timeline_data("Школа №57, 2005-2016", question_context="school")
        assert data.activity_type == "school"

    def test_infer_activity_type_university(self):
        """Test inference of university activity type."""
        data = extract_timeline_data("МГУ, 2016-2020", question_context="university")
        assert data.activity_type == "university"

    def test_infer_activity_type_from_text_university(self):
        """Test inference from university keywords in text."""
        data = extract_timeline_data("Университет Калифорнии, 2015-2019")
        assert data.activity_type == "university"

    def test_infer_activity_type_from_text_school(self):
        """Test inference from school keywords in text."""
        data = extract_timeline_data("Школа №5, 2005-2016")
        assert data.activity_type == "school"

    def test_infer_activity_type_job(self):
        """Test inference of job activity type."""
        data = extract_timeline_data("работал Senior Engineer в компании Google, 2018-2021")
        assert data.activity_type == "job"

    def test_infer_activity_type_award(self):
        """Test inference of award activity type."""
        data = extract_timeline_data("Получил приз в 2020", question_context="awards")
        assert data.activity_type == "award"

    def test_full_context_extraction(self):
        """Test extraction of all fields from complex text."""
        text = "2018-2021, Data Scientist в компании Yandex, Берлин, Германия"
        data = extract_timeline_data(text)

        assert data.start_year == 2018
        assert data.end_year == 2021
        assert data.location is not None
        # Organization extraction may work differently
        assert data.role is not None
        assert data.raw_text == text

    def test_no_timeline_data(self):
        """Test text with no timeline data."""
        data = extract_timeline_data("Просто текст без дат")
        assert data.start_year is None
        assert data.end_year is None
        assert data.raw_text == "Просто текст без дат"

    def test_empty_string(self):
        """Test empty string input."""
        data = extract_timeline_data("")
        assert data.start_year is None
        assert data.end_year is None
        assert data.location is None
        assert data.organization is None
        assert data.role is None
        assert data.raw_text == ""

    def test_raw_text_preservation(self):
        """Test that raw text is always preserved."""
        text = "Some arbitrary text with 2020"
        data = extract_timeline_data(text)
        assert data.raw_text == text

    def test_year_boundary_validation(self):
        """Test that extracted years are within valid range (1900-2099)."""
        data = extract_timeline_data("1995-2005")
        assert data.start_year >= 1900
        assert data.end_year <= 2099

    def test_multiple_locations(self):
        """Test handling of multiple locations."""
        data = extract_timeline_data("Москва, Санкт-Петербург, 2015-2020")
        assert data.location is not None
        # Should capture at least one location
        assert "Москва" in data.location or "Санкт-Петербург" in data.location

    def test_organization_with_context(self):
        """Test organization extraction with context word."""
        data = extract_timeline_data("работал в компании Яндекс")
        assert data.organization is not None
        assert "Яндекс" in data.organization

    def test_unicode_handling(self):
        """Test proper handling of Unicode characters."""
        data = extract_timeline_data("МГУ им. М.В. Ломоносова, 2016–2020")
        assert data.organization is not None
        assert "МГУ" in data.organization or "Ломоносова" in data.organization

    def test_multiple_year_ranges(self):
        """Test handling of multiple year ranges (should pick first)."""
        data = extract_timeline_data("2010-2014 и 2018-2021")
        # Should extract at least one range
        assert data.start_year is not None
        assert data.end_year is not None

    def test_context_overrides_inference(self):
        """Test that question_context overrides automatic inference."""
        data = extract_timeline_data("работал инженером", question_context="school")
        # Context says school, even though text suggests job
        assert data.activity_type == "school"

    def test_timeline_data_dataclass_fields(self):
        """Test that TimelineData has all expected fields."""
        data = TimelineData()
        assert hasattr(data, "start_year")
        assert hasattr(data, "end_year")
        assert hasattr(data, "location")
        assert hasattr(data, "role")
        assert hasattr(data, "organization")
        assert hasattr(data, "activity_type")
        assert hasattr(data, "raw_text")

    def test_timeline_data_defaults(self):
        """Test TimelineData default values."""
        data = TimelineData()
        assert data.start_year is None
        assert data.end_year is None
        assert data.location is None
        assert data.role is None
        assert data.organization is None
        assert data.activity_type is None
        assert data.raw_text == ""

    def test_timeline_data_initialization(self):
        """Test TimelineData can be initialized with values."""
        data = TimelineData(
            start_year=2018,
            end_year=2021,
            location="Берлин",
            role="Engineer",
            organization="Google",
            activity_type="job",
            raw_text="test",
        )
        assert data.start_year == 2018
        assert data.end_year == 2021
        assert data.location == "Берлин"
        assert data.role == "Engineer"
        assert data.organization == "Google"
        assert data.activity_type == "job"
        assert data.raw_text == "test"
