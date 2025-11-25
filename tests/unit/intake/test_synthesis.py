"""
Unit tests for intake fact synthesis module.

Tests conversion of Q&A pairs into declarative statements for semantic memory.
"""

from __future__ import annotations

import pytest

from core.intake.schema import IntakeQuestion, QuestionType
from core.intake.synthesis import synthesize_intake_fact


class TestSynthesizeIntakeFact:
    """Test fact synthesis for different question types."""

    def test_full_name_synthesis(self):
        """Test synthesis for full_name question."""
        question = IntakeQuestion(
            id="full_name",
            text_template="Как ваше полное имя?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "Иван Петров")
        assert "[INTAKE][basic_info]" in fact
        assert "Полное имя пользователя: Иван Петров" in fact

    def test_date_of_birth_synthesis(self):
        """Test synthesis for date_of_birth question."""
        question = IntakeQuestion(
            id="date_of_birth",
            text_template="Какова ваша дата рождения?",
            type=QuestionType.DATE,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "1990-05-15")
        assert "[INTAKE][basic_info]" in fact
        assert "Дата рождения пользователя: 1990-05-15" in fact

    def test_place_of_birth_synthesis(self):
        """Test synthesis for place_of_birth question."""
        question = IntakeQuestion(
            id="place_of_birth",
            text_template="Где вы родились?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "Москва, Россия")
        assert "[INTAKE][basic_info]" in fact
        assert "Пользователь родился в Москва, Россия" in fact

    def test_school_timeline_synthesis(self):
        """Test synthesis for school question with timeline."""
        question = IntakeQuestion(
            id="school_years",
            text_template="В какие годы вы учились в школе?",
            type=QuestionType.TEXT,
            tags=["intake", "school", "timeline"],
        )
        fact = synthesize_intake_fact(question, "2005-2016, Школа №57 в Москве")
        assert "[INTAKE][school][timeline]" in fact
        assert "С 2005 по 2016 годы пользователь учился" in fact
        assert "Школа №57 в Москве" in fact

    def test_university_timeline_synthesis(self):
        """Test synthesis for university question with timeline."""
        question = IntakeQuestion(
            id="universities",
            text_template="Где вы учились в университете?",
            type=QuestionType.TEXT,
            tags=["intake", "university", "timeline"],
        )
        fact = synthesize_intake_fact(question, "2016-2020, МГУ, Москва")
        assert "[INTAKE][university][timeline]" in fact
        assert "С 2016 по 2020 годы пользователь учился" in fact

    def test_career_critical_role_synthesis(self):
        """Test synthesis for EB-1A critical role question."""
        question = IntakeQuestion(
            id="career_critical_role",
            text_template="Занимали ли вы критическую роль?",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: critical role.",
            tags=["intake", "career", "achievements", "eb1a_criterion"],
        )
        fact = synthesize_intake_fact(question, "Да, был CTO в стартапе")
        assert "[INTAKE][career][achievements][eb1a_criterion]" in fact
        assert "[EB-1A criterion: critical role]" in fact
        assert "Да, был CTO в стартапе" in fact

    def test_career_high_salary_synthesis(self):
        """Test synthesis for EB-1A high salary question."""
        question = IntakeQuestion(
            id="career_high_salary",
            text_template="Получали ли вы высокую зарплату?",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: high remuneration.",
            tags=["intake", "career", "eb1a_criterion"],
        )
        fact = synthesize_intake_fact(question, "Да, $200k в год")
        assert "[INTAKE][career][eb1a_criterion]" in fact
        assert "[EB-1A criterion: high salary]" in fact
        assert "Да, $200k в год" in fact

    def test_publications_synthesis(self):
        """Test synthesis for publications question."""
        question = IntakeQuestion(
            id="publications",
            text_template="Есть ли у вас публикации?",
            type=QuestionType.TEXT,
            tags=["intake", "projects_research"],
        )
        fact = synthesize_intake_fact(question, "5 статей в IEEE")
        assert "[INTAKE][projects_research]" in fact
        assert "Публикации и метрики: 5 статей в IEEE" in fact

    def test_awards_synthesis(self):
        """Test synthesis for awards question."""
        question = IntakeQuestion(
            id="awards",
            text_template="Были ли у вас награды?",
            type=QuestionType.TEXT,
            tags=["intake", "awards"],
        )
        fact = synthesize_intake_fact(question, "Приз на хакатоне")
        assert "[INTAKE][awards]" in fact
        assert "Награды и достижения: Приз на хакатоне" in fact

    def test_expert_roles_synthesis(self):
        """Test synthesis for expert/judging roles."""
        question = IntakeQuestion(
            id="expert_roles",
            text_template="Были ли вы экспертом или судьей?",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: judging.",
            tags=["intake", "talks_public_activity", "eb1a_criterion"],
        )
        fact = synthesize_intake_fact(question, "Да, судья на конференции")
        assert "[INTAKE][talks_public_activity][eb1a_criterion]" in fact
        assert "[EB-1A criterion: judging]" in fact
        assert "Экспертные роли: Да, судья на конференции" in fact

    def test_recommenders_synthesis(self):
        """Test synthesis for recommenders question."""
        question = IntakeQuestion(
            id="recommender_summary",
            text_template="Кто может вас порекомендовать?",
            type=QuestionType.TEXT,
            tags=["intake", "recommenders"],
        )
        fact = synthesize_intake_fact(question, "Профессор Иванов, CEO компании X")
        assert "[INTAKE][recommenders]" in fact
        assert "Потенциальные рекомендатели: Профессор Иванов, CEO компании X" in fact

    def test_goals_synthesis(self):
        """Test synthesis for goals/motivation question."""
        question = IntakeQuestion(
            id="goals_usa",
            text_template="Почему вы хотите переехать в США?",
            type=QuestionType.TEXT,
            tags=["intake", "goals"],
        )
        fact = synthesize_intake_fact(question, "Развивать бизнес и инновации")
        assert "[INTAKE][goals]" in fact
        # synthesis extracts key phrase from question
        assert "Развивать бизнес и инновации" in fact

    def test_generic_synthesis(self):
        """Test generic synthesis for unknown question_id."""
        question = IntakeQuestion(
            id="unknown_question",
            text_template="Какой-то вопрос?",
            type=QuestionType.TEXT,
            tags=["intake", "other"],
        )
        fact = synthesize_intake_fact(question, "Какой-то ответ")
        assert "[INTAKE][other]" in fact
        assert "Какой-то ответ" in fact

    def test_tag_prefix_building(self):
        """Test that tags are properly formatted into prefix."""
        question = IntakeQuestion(
            id="test_question",
            text_template="Тестовый вопрос?",
            type=QuestionType.TEXT,
            tags=["intake", "school", "timeline", "location"],
        )
        fact = synthesize_intake_fact(question, "Ответ")
        # First tag capitalized, others lowercase
        assert "[INTAKE][school][timeline][location]" in fact

    def test_no_tags_default(self):
        """Test synthesis with no tags defaults to [INTAKE]."""
        question = IntakeQuestion(
            id="test_question",
            text_template="Тестовый вопрос?",
            type=QuestionType.TEXT,
            tags=[],
        )
        fact = synthesize_intake_fact(question, "Ответ")
        assert "[INTAKE]" in fact

    def test_macro_context_synthesis(self):
        """Test synthesis for macro_context questions."""
        question = IntakeQuestion(
            id="other_macro",  # Not starting with "school" to avoid timeline synthesis
            text_template="Какие важные события происходили в то время?",
            type=QuestionType.TEXT,
            tags=["intake", "macro_context"],
        )
        fact = synthesize_intake_fact(question, "Финансовый кризис")
        assert "[INTAKE][macro_context]" in fact
        assert "Макро-контекст: Финансовый кризис" in fact

    def test_empty_answer(self):
        """Test synthesis with empty answer (edge case)."""
        question = IntakeQuestion(
            id="full_name",
            text_template="Как ваше полное имя?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "")
        assert "[INTAKE][basic_info]" in fact
        # Should still produce a fact, even if empty
        assert "Полное имя пользователя:" in fact

    def test_unicode_handling(self):
        """Test synthesis handles Unicode characters properly."""
        question = IntakeQuestion(
            id="place_of_birth",
            text_template="Где вы родились?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "Санкт-Петербург, Россия 🇷🇺")
        assert "[INTAKE][basic_info]" in fact
        assert "Санкт-Петербург, Россия 🇷🇺" in fact
