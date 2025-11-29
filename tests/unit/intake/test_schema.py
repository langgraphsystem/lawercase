"""
Unit tests for intake schema module.

Tests Pydantic v2 models, question types, blocks structure, and data validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.intake.schema import (BLOCKS_BY_ID, INTAKE_BLOCKS, IntakeBlock,
                                IntakeCondition, IntakeQuestion, QuestionType)


class TestQuestionType:
    """Test QuestionType enum."""

    def test_all_question_types(self):
        """Test all question types are defined."""
        assert QuestionType.TEXT == "text"
        assert QuestionType.YES_NO == "yes_no"
        assert QuestionType.DATE == "date"
        assert QuestionType.SELECT == "select"
        assert QuestionType.LIST == "list"

    def test_question_type_membership(self):
        """Test membership checks for question types."""
        assert "text" in [qt.value for qt in QuestionType]
        assert "yes_no" in [qt.value for qt in QuestionType]
        assert "invalid" not in [qt.value for qt in QuestionType]


class TestIntakeCondition:
    """Test IntakeCondition model."""

    def test_create_condition(self):
        """Test creating a condition."""
        condition = IntakeCondition(
            depends_on_question_id="has_degree",
            expected_value=True,
        )
        assert condition.depends_on_question_id == "has_degree"
        assert condition.expected_value is True

    def test_condition_with_string_value(self):
        """Test condition with string expected value."""
        condition = IntakeCondition(
            depends_on_question_id="country",
            expected_value="USA",
        )
        assert condition.expected_value == "USA"

    def test_condition_required_fields(self):
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError):
            IntakeCondition(depends_on_question_id="test")  # missing expected_value


class TestIntakeQuestion:
    """Test IntakeQuestion model."""

    def test_create_simple_question(self):
        """Test creating a simple text question."""
        question = IntakeQuestion(
            id="full_name",
            text_template="Как ваше полное имя?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        assert question.id == "full_name"
        assert question.text_template == "Как ваше полное имя?"
        assert question.type == QuestionType.TEXT
        assert question.tags == ["intake", "basic_info"]
        assert question.options is None
        assert question.hint is None
        assert question.rationale is None
        assert question.condition is None

    def test_create_yes_no_question(self):
        """Test creating a yes/no question."""
        question = IntakeQuestion(
            id="has_degree",
            text_template="У вас есть степень?",
            type=QuestionType.YES_NO,
            tags=["intake", "education"],
        )
        assert question.type == QuestionType.YES_NO

    def test_create_date_question(self):
        """Test creating a date question."""
        question = IntakeQuestion(
            id="date_of_birth",
            text_template="Когда вы родились?",
            type=QuestionType.DATE,
            tags=["intake", "basic_info"],
        )
        assert question.type == QuestionType.DATE

    def test_create_select_question(self):
        """Test creating a select question with options."""
        question = IntakeQuestion(
            id="degree_level",
            text_template="Какой уровень степени?",
            type=QuestionType.SELECT,
            options=["Бакалавр", "Магистр", "PhD"],
            tags=["intake", "education"],
        )
        assert question.type == QuestionType.SELECT
        assert question.options == ["Бакалавр", "Магистр", "PhD"]

    def test_create_list_question(self):
        """Test creating a list question."""
        question = IntakeQuestion(
            id="skills",
            text_template="Какие у вас навыки?",
            type=QuestionType.LIST,
            tags=["intake", "skills"],
        )
        assert question.type == QuestionType.LIST

    def test_question_with_hint(self):
        """Test question with hint."""
        question = IntakeQuestion(
            id="test",
            text_template="Вопрос?",
            type=QuestionType.TEXT,
            hint="Это подсказка",
            tags=["intake"],
        )
        assert question.hint == "Это подсказка"

    def test_question_with_rationale(self):
        """Test question with EB-1A rationale."""
        question = IntakeQuestion(
            id="critical_role",
            text_template="Занимали ли вы критическую роль?",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: critical role.",
            tags=["intake", "career", "eb1a_criterion"],
        )
        assert question.rationale == "Used to support EB-1A criterion: critical role."

    def test_question_with_condition(self):
        """Test question with conditional rendering."""
        condition = IntakeCondition(
            depends_on_question_id="has_degree",
            expected_value=True,
        )
        question = IntakeQuestion(
            id="degree_details",
            text_template="Расскажите о вашей степени",
            type=QuestionType.TEXT,
            condition=condition,
            tags=["intake", "education"],
        )
        assert question.condition is not None
        assert question.condition.depends_on_question_id == "has_degree"

    def test_question_default_type(self):
        """Test that default type is TEXT."""
        question = IntakeQuestion(
            id="test",
            text_template="Вопрос?",
            tags=["intake"],
        )
        assert question.type == QuestionType.TEXT

    def test_question_serialization(self):
        """Test question can be serialized."""
        question = IntakeQuestion(
            id="test",
            text_template="Вопрос?",
            type=QuestionType.TEXT,
            tags=["intake", "test"],
        )
        data = question.model_dump()
        assert data["id"] == "test"
        assert data["text_template"] == "Вопрос?"
        assert data["type"] == "text"
        assert data["tags"] == ["intake", "test"]


class TestIntakeBlock:
    """Test IntakeBlock model."""

    def test_create_block(self):
        """Test creating a block with questions."""
        questions = [
            IntakeQuestion(
                id="q1",
                text_template="Вопрос 1?",
                type=QuestionType.TEXT,
                tags=["intake"],
            ),
            IntakeQuestion(
                id="q2",
                text_template="Вопрос 2?",
                type=QuestionType.YES_NO,
                tags=["intake"],
            ),
        ]
        block = IntakeBlock(
            id="test_block",
            title="Тестовый блок",
            description="Описание блока",
            questions=questions,
        )
        assert block.id == "test_block"
        assert block.title == "Тестовый блок"
        assert block.description == "Описание блока"
        assert len(block.questions) == 2
        assert block.questions[0].id == "q1"

    def test_block_required_fields(self):
        """Test that block requires all fields."""
        with pytest.raises(ValidationError):
            IntakeBlock(id="test", title="Test")  # missing description and questions

    def test_block_serialization(self):
        """Test block can be serialized."""
        questions = [
            IntakeQuestion(
                id="q1",
                text_template="Вопрос?",
                type=QuestionType.TEXT,
                tags=["intake"],
            )
        ]
        block = IntakeBlock(
            id="test_block",
            title="Тестовый блок",
            description="Описание",
            questions=questions,
        )
        data = block.model_dump()
        assert data["id"] == "test_block"
        assert data["title"] == "Тестовый блок"
        assert len(data["questions"]) == 1


class TestIntakeBlocks:
    """Test the global INTAKE_BLOCKS structure."""

    def test_intake_blocks_exist(self):
        """Test that INTAKE_BLOCKS is defined and not empty."""
        assert INTAKE_BLOCKS is not None
        assert len(INTAKE_BLOCKS) > 0

    def test_expected_block_count(self):
        """Test that there are exactly 11 blocks."""
        assert len(INTAKE_BLOCKS) == 11

    def test_blocks_by_id_exists(self):
        """Test that BLOCKS_BY_ID dictionary exists."""
        assert BLOCKS_BY_ID is not None
        assert isinstance(BLOCKS_BY_ID, dict)

    def test_blocks_by_id_completeness(self):
        """Test that all blocks are in BLOCKS_BY_ID."""
        assert len(BLOCKS_BY_ID) == len(INTAKE_BLOCKS)
        for block in INTAKE_BLOCKS:
            assert block.id in BLOCKS_BY_ID
            assert BLOCKS_BY_ID[block.id] == block

    def test_block_ids_unique(self):
        """Test that all block IDs are unique."""
        block_ids = [block.id for block in INTAKE_BLOCKS]
        assert len(block_ids) == len(set(block_ids))

    def test_expected_block_ids(self):
        """Test that expected block IDs exist."""
        expected_ids = [
            "basic_info",
            "family_childhood",
            "school",
            "university",
            "career",
            "projects_research",
            "awards",
            "talks_public_activity",
            "courses_certificates",
            "recommenders",
            "goals_usa",
        ]
        actual_ids = [block.id for block in INTAKE_BLOCKS]
        assert actual_ids == expected_ids

    def test_all_blocks_have_questions(self):
        """Test that all blocks have at least one question."""
        for block in INTAKE_BLOCKS:
            assert len(block.questions) > 0, f"Block {block.id} has no questions"

    def test_all_blocks_have_russian_text(self):
        """Test that all blocks have Russian titles and descriptions."""
        for block in INTAKE_BLOCKS:
            assert len(block.title) > 0, f"Block {block.id} has empty title"
            assert len(block.description) > 0, f"Block {block.id} has empty description"
            # Check for Cyrillic characters (Russian text)
            assert any(ord(c) > 1000 for c in block.title), f"Block {block.id} title not in Russian"

    def test_all_questions_have_ids(self):
        """Test that all questions have unique IDs."""
        all_question_ids = []
        for block in INTAKE_BLOCKS:
            for question in block.questions:
                assert question.id, f"Question in block {block.id} has no ID"
                all_question_ids.append(question.id)

        # Check uniqueness across all blocks
        assert len(all_question_ids) == len(set(all_question_ids)), "Duplicate question IDs found"

    def test_all_questions_have_tags(self):
        """Test that all questions have tags."""
        for block in INTAKE_BLOCKS:
            for question in block.questions:
                assert len(question.tags) > 0, f"Question {question.id} has no tags"
                assert "intake" in question.tags, f"Question {question.id} missing 'intake' tag"

    def test_all_questions_have_russian_text(self):
        """Test that all questions have Russian text."""
        for block in INTAKE_BLOCKS:
            for question in block.questions:
                assert len(question.text_template) > 0, f"Question {question.id} has empty text"
                # Check for Cyrillic characters
                assert any(
                    ord(c) > 1000 for c in question.text_template
                ), f"Question {question.id} text not in Russian"

    def test_eb1a_questions_have_rationale(self):
        """Test that EB-1A criterion questions have rationale."""
        for block in INTAKE_BLOCKS:
            for question in block.questions:
                if "eb1a_criterion" in question.tags:
                    assert (
                        question.rationale is not None
                    ), f"EB-1A question {question.id} missing rationale"

    def test_select_questions_have_options(self):
        """Test that SELECT type questions have options."""
        for block in INTAKE_BLOCKS:
            for question in block.questions:
                if question.type == QuestionType.SELECT:
                    assert (
                        question.options is not None
                    ), f"SELECT question {question.id} missing options"
                    assert (
                        len(question.options) > 0
                    ), f"SELECT question {question.id} has empty options"

    def test_question_count(self):
        """Test total question count across all blocks."""
        total_questions = sum(len(block.questions) for block in INTAKE_BLOCKS)
        # Based on promt.txt, we expect around 56 questions
        assert total_questions >= 50, f"Expected at least 50 questions, got {total_questions}"
        assert total_questions <= 70, f"Expected at most 70 questions, got {total_questions}"

    def test_block_order(self):
        """Test that blocks are in the expected order."""
        expected_order = [
            "basic_info",
            "family_childhood",
            "school",
            "university",
            "career",
            "projects_research",
            "awards",
            "talks_public_activity",
            "courses_certificates",
            "recommenders",
            "goals_usa",
        ]
        actual_order = [block.id for block in INTAKE_BLOCKS]
        assert actual_order == expected_order, "Blocks are not in expected order"
