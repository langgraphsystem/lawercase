"""
Tests for core/intake/validation.py and core/intake/schema.py.

Covers all public validation functions, Pydantic models,
enum values, and the INTAKE_BLOCKS / BLOCKS_BY_ID registries.
"""

from __future__ import annotations

import pytest

from core.intake.schema import (
    BLOCKS_BY_ID,
    INTAKE_BLOCKS,
    IntakeBlock,
    IntakeCondition,
    IntakeQuestion,
    QuestionType,
)
from core.intake.validation import (
    parse_list,
    validate_date,
    validate_select,
    validate_text,
    validate_yes_no,
)

# =====================================================================
# 1. validate_date
# =====================================================================


class TestValidateDate:
    """Tests for validate_date(text) -> (bool, str | None)."""

    # --- valid dates ---

    def test_standard_yyyy_mm_dd(self):
        ok, val = validate_date("2023-05-15")
        assert ok is True
        assert val == "2023-05-15"

    def test_zero_padded_normalization(self):
        """Single-digit month/day should be zero-padded in output."""
        ok, val = validate_date("2023-5-3")
        assert ok is True
        assert val == "2023-05-03"

    def test_dot_separator(self):
        ok, val = validate_date("2023.05.15")
        assert ok is True
        assert val == "2023-05-15"

    def test_slash_separator(self):
        ok, val = validate_date("2023/05/15")
        assert ok is True
        assert val == "2023-05-15"

    def test_leading_trailing_whitespace(self):
        ok, val = validate_date("  2023-01-01  ")
        assert ok is True
        assert val == "2023-01-01"

    def test_leap_year_feb_29(self):
        ok, val = validate_date("2024-02-29")
        assert ok is True
        assert val == "2024-02-29"

    def test_first_day_of_year(self):
        ok, val = validate_date("2000-01-01")
        assert ok is True
        assert val == "2000-01-01"

    def test_last_day_of_year(self):
        ok, val = validate_date("1999-12-31")
        assert ok is True
        assert val == "1999-12-31"

    # --- invalid dates ---

    def test_invalid_month(self):
        ok, val = validate_date("2023-13-01")
        assert ok is False
        assert val is None

    def test_invalid_day(self):
        ok, val = validate_date("2023-02-30")
        assert ok is False
        assert val is None

    def test_non_leap_year_feb_29(self):
        ok, val = validate_date("2023-02-29")
        assert ok is False
        assert val is None

    def test_random_text(self):
        ok, val = validate_date("not a date")
        assert ok is False
        assert val is None

    def test_empty_string(self):
        ok, val = validate_date("")
        assert ok is False
        assert val is None

    def test_dd_mm_yyyy_not_accepted(self):
        """DD.MM.YYYY European format is NOT supported (only YYYY first)."""
        ok, val = validate_date("15.05.2023")
        assert ok is False
        assert val is None

    def test_mm_dd_yyyy_not_accepted(self):
        ok, val = validate_date("05-15-2023")
        assert ok is False
        assert val is None

    def test_only_year(self):
        ok, val = validate_date("2023")
        assert ok is False
        assert val is None

    def test_partial_date(self):
        ok, val = validate_date("2023-05")
        assert ok is False
        assert val is None

    def test_date_with_time(self):
        ok, val = validate_date("2023-05-15T12:00:00")
        assert ok is False
        assert val is None

    def test_date_with_extra_text(self):
        ok, val = validate_date("2023-05-15 hello")
        assert ok is False
        assert val is None


# =====================================================================
# 2. validate_yes_no
# =====================================================================


class TestValidateYesNo:
    """Tests for validate_yes_no(text) -> (bool, bool | None)."""

    # --- positive responses ---

    @pytest.mark.parametrize("word", ["да", "yes", "y", "конечно", "безусловно", "ага", "угу", "ок", "ok"])
    def test_positive_variants(self, word: str):
        ok, val = validate_yes_no(word)
        assert ok is True
        assert val is True

    def test_positive_case_insensitive(self):
        ok, val = validate_yes_no("YES")
        assert ok is True
        assert val is True

    def test_positive_mixed_case(self):
        ok, val = validate_yes_no("Да")
        assert ok is True
        assert val is True

    def test_positive_with_whitespace(self):
        ok, val = validate_yes_no("  yes  ")
        assert ok is True
        assert val is True

    # --- negative responses ---

    @pytest.mark.parametrize("word", ["нет", "no", "n", "не", "никак", "неа"])
    def test_negative_variants(self, word: str):
        ok, val = validate_yes_no(word)
        assert ok is True
        assert val is False

    def test_negative_case_insensitive(self):
        ok, val = validate_yes_no("NO")
        assert ok is True
        assert val is False

    def test_negative_mixed_case(self):
        ok, val = validate_yes_no("Нет")
        assert ok is True
        assert val is False

    def test_negative_with_whitespace(self):
        ok, val = validate_yes_no("  no  ")
        assert ok is True
        assert val is False

    # --- ambiguous / invalid ---

    def test_ambiguous_maybe(self):
        ok, val = validate_yes_no("может быть")
        assert ok is False
        assert val is None

    def test_random_text(self):
        ok, val = validate_yes_no("hello world")
        assert ok is False
        assert val is None

    def test_empty_string(self):
        ok, val = validate_yes_no("")
        assert ok is False
        assert val is None

    def test_number(self):
        ok, val = validate_yes_no("1")
        assert ok is False
        assert val is None

    def test_partial_match_not_accepted(self):
        """'yesterday' starts with 'yes' but should not match."""
        ok, val = validate_yes_no("yesterday")
        assert ok is False
        assert val is None


# =====================================================================
# 3. validate_select
# =====================================================================


class TestValidateSelect:
    """Tests for validate_select(text, options) -> (bool, str | None)."""

    OPTIONS = ["Python", "JavaScript", "Go"]

    # --- exact match ---

    def test_exact_match(self):
        ok, val = validate_select("Python", self.OPTIONS)
        assert ok is True
        assert val == "Python"

    def test_exact_match_case_insensitive(self):
        ok, val = validate_select("python", self.OPTIONS)
        assert ok is True
        assert val == "Python"

    def test_exact_match_upper(self):
        ok, val = validate_select("JAVASCRIPT", self.OPTIONS)
        assert ok is True
        assert val == "JavaScript"

    def test_exact_match_with_whitespace(self):
        ok, val = validate_select("  Go  ", self.OPTIONS)
        assert ok is True
        assert val == "Go"

    # --- partial match ---

    def test_partial_match_text_in_option(self):
        """'java' is a substring of 'JavaScript', so partial match applies."""
        ok, val = validate_select("java", self.OPTIONS)
        assert ok is True
        assert val == "JavaScript"

    def test_partial_match_option_in_text(self):
        """'Go language' contains 'go', which matches option 'Go'."""
        ok, val = validate_select("Go language", self.OPTIONS)
        assert ok is True
        assert val == "Go"

    # --- no match ---

    def test_no_match(self):
        ok, val = validate_select("Rust", self.OPTIONS)
        assert ok is False
        assert val is None

    def test_empty_text_matches_first_via_partial(self):
        """Empty string is a substring of every option, so partial match returns first option."""
        ok, val = validate_select("", self.OPTIONS)
        assert ok is True
        assert val == "Python"  # first option wins via partial match

    def test_no_match_empty_options(self):
        ok, val = validate_select("Python", [])
        assert ok is False
        assert val is None

    # --- edge: first match wins ---

    def test_first_partial_match_wins(self):
        """When multiple partials could match, the first option wins."""
        options = ["Apple Pie", "Apple Sauce"]
        ok, val = validate_select("apple", options)
        # Exact-lowered check first: neither matches exactly
        # Partial: "apple" in "apple pie" -> first match
        assert ok is True
        assert val == "Apple Pie"


# =====================================================================
# 4. parse_list
# =====================================================================


class TestParseList:
    """Tests for parse_list(text) -> list[str]."""

    def test_comma_separated(self):
        result = parse_list("Python, JavaScript, Go")
        assert result == ["Python", "JavaScript", "Go"]

    def test_newline_separated(self):
        result = parse_list("Python\nJavaScript\nGo")
        assert result == ["Python", "JavaScript", "Go"]

    def test_semicolon_separated(self):
        result = parse_list("Python; JavaScript; Go")
        assert result == ["Python", "JavaScript", "Go"]

    def test_mixed_separators(self):
        result = parse_list("Python, JavaScript\nGo; Rust")
        assert result == ["Python", "JavaScript", "Go", "Rust"]

    def test_strips_whitespace(self):
        result = parse_list("  Python  ,  JavaScript  ,  Go  ")
        assert result == ["Python", "JavaScript", "Go"]

    def test_removes_empty_items(self):
        result = parse_list("Python,,Go")
        assert result == ["Python", "Go"]

    def test_removes_whitespace_only_items(self):
        result = parse_list("Python,  ,  , Go")
        assert result == ["Python", "Go"]

    def test_empty_string(self):
        result = parse_list("")
        assert result == []

    def test_single_item(self):
        result = parse_list("Python")
        assert result == ["Python"]

    def test_trailing_comma(self):
        result = parse_list("Python,Go,")
        assert result == ["Python", "Go"]

    def test_leading_comma(self):
        result = parse_list(",Python,Go")
        assert result == ["Python", "Go"]

    def test_only_separators(self):
        result = parse_list(",,,")
        assert result == []

    def test_only_whitespace(self):
        result = parse_list("   ")
        assert result == []


# =====================================================================
# 5. validate_text
# =====================================================================


class TestValidateText:
    """Tests for validate_text(text, min_length, max_length) -> (bool, str)."""

    def test_normal_text(self):
        ok, msg = validate_text("Some text here")
        assert ok is True
        assert msg == ""

    def test_minimum_one_char(self):
        ok, msg = validate_text("x")
        assert ok is True
        assert msg == ""

    def test_empty_string_default_min(self):
        ok, msg = validate_text("")
        assert ok is False
        assert "минимум" in msg

    def test_whitespace_only(self):
        """Stripped to empty -> too short."""
        ok, msg = validate_text("   ")
        assert ok is False
        assert "минимум" in msg

    def test_too_long_default_max(self):
        ok, msg = validate_text("x" * 10001)
        assert ok is False
        assert "максимум" in msg

    def test_exactly_max_length(self):
        ok, msg = validate_text("x" * 10000)
        assert ok is True
        assert msg == ""

    def test_exactly_min_length_custom(self):
        ok, msg = validate_text("abcde", min_length=5)
        assert ok is True
        assert msg == ""

    def test_below_custom_min_length(self):
        ok, msg = validate_text("abc", min_length=5)
        assert ok is False
        assert "минимум 5" in msg

    def test_above_custom_max_length(self):
        ok, msg = validate_text("abcdef", max_length=5)
        assert ok is False
        assert "максимум 5" in msg

    def test_leading_trailing_whitespace_stripped(self):
        """Whitespace is stripped before length check."""
        ok, msg = validate_text("  hello  ", min_length=1, max_length=5)
        assert ok is True
        assert msg == ""

    def test_unicode_text(self):
        ok, msg = validate_text("Привет мир")
        assert ok is True
        assert msg == ""

    def test_min_zero_allows_empty(self):
        ok, msg = validate_text("", min_length=0)
        assert ok is True
        assert msg == ""


# =====================================================================
# 6. Schema: QuestionType enum
# =====================================================================


class TestQuestionType:
    """Tests for the QuestionType enum."""

    def test_all_expected_values_exist(self):
        expected = {"text", "yes_no", "date", "select", "list", "document"}
        actual = {qt.value for qt in QuestionType}
        assert actual == expected

    def test_member_count(self):
        assert len(QuestionType) == 6

    def test_text_value(self):
        assert QuestionType.TEXT.value == "text"

    def test_yes_no_value(self):
        assert QuestionType.YES_NO.value == "yes_no"

    def test_date_value(self):
        assert QuestionType.DATE.value == "date"

    def test_select_value(self):
        assert QuestionType.SELECT.value == "select"

    def test_list_value(self):
        assert QuestionType.LIST.value == "list"

    def test_document_value(self):
        assert QuestionType.DOCUMENT.value == "document"

    def test_is_str_subclass(self):
        """QuestionType inherits from str, so members are strings."""
        assert isinstance(QuestionType.TEXT, str)


# =====================================================================
# 7. Schema: IntakeCondition model
# =====================================================================


class TestIntakeCondition:
    """Tests for IntakeCondition Pydantic model."""

    def test_basic_construction(self):
        cond = IntakeCondition(
            depends_on_question_id="q1",
            expected_value=True,
        )
        assert cond.depends_on_question_id == "q1"
        assert cond.expected_value is True

    def test_expected_value_string(self):
        cond = IntakeCondition(
            depends_on_question_id="q2",
            expected_value="yes",
        )
        assert cond.expected_value == "yes"

    def test_expected_value_none(self):
        cond = IntakeCondition(
            depends_on_question_id="q3",
            expected_value=None,
        )
        assert cond.expected_value is None

    def test_missing_depends_on_raises(self):
        with pytest.raises(Exception):  # noqa: B017
            IntakeCondition(expected_value=True)

    def test_missing_expected_value_raises(self):
        with pytest.raises(Exception):  # noqa: B017
            IntakeCondition(depends_on_question_id="q1")

    def test_serialization_roundtrip(self):
        cond = IntakeCondition(depends_on_question_id="q5", expected_value="hello")
        data = cond.model_dump()
        restored = IntakeCondition(**data)
        assert restored == cond


# =====================================================================
# 8. Schema: IntakeQuestion model
# =====================================================================


class TestIntakeQuestion:
    """Tests for IntakeQuestion Pydantic model."""

    def test_minimal_construction(self):
        q = IntakeQuestion(id="test_q", text_template="What is X?")
        assert q.id == "test_q"
        assert q.text_template == "What is X?"
        assert q.type == QuestionType.TEXT.value  # use_enum_values=True
        assert q.options is None
        assert q.hint is None
        assert q.rationale is None
        assert q.condition is None
        assert q.tags == []

    def test_full_construction(self):
        cond = IntakeCondition(depends_on_question_id="q0", expected_value=True)
        q = IntakeQuestion(
            id="full_q",
            text_template="Choose one:",
            type=QuestionType.SELECT,
            options=["A", "B", "C"],
            hint="Pick carefully",
            rationale="Testing full fields",
            condition=cond,
            tags=["tag1", "tag2"],
        )
        assert q.id == "full_q"
        assert q.type == QuestionType.SELECT.value
        assert q.options == ["A", "B", "C"]
        assert q.hint == "Pick carefully"
        assert q.rationale == "Testing full fields"
        assert q.condition is not None
        assert q.condition.depends_on_question_id == "q0"
        assert q.tags == ["tag1", "tag2"]

    def test_missing_id_raises(self):
        with pytest.raises(Exception):  # noqa: B017
            IntakeQuestion(text_template="What?")

    def test_missing_text_template_raises(self):
        with pytest.raises(Exception):  # noqa: B017
            IntakeQuestion(id="q_no_text")

    def test_enum_values_serialized_as_string(self):
        """model_config use_enum_values=True means type stores the string value."""
        q = IntakeQuestion(id="q", text_template="T", type=QuestionType.YES_NO)
        assert q.type == "yes_no"

    def test_tags_default_factory(self):
        """Each instance gets its own list (no shared mutable default)."""
        q1 = IntakeQuestion(id="q1", text_template="T1")
        q2 = IntakeQuestion(id="q2", text_template="T2")
        q1.tags.append("modified")
        assert "modified" not in q2.tags


# =====================================================================
# 9. Schema: IntakeBlock model
# =====================================================================


class TestIntakeBlock:
    """Tests for IntakeBlock Pydantic model."""

    def test_basic_construction(self):
        q = IntakeQuestion(id="q1", text_template="Question 1?")
        block = IntakeBlock(
            id="test_block",
            title="Test Block",
            description="A block for testing",
            questions=[q],
        )
        assert block.id == "test_block"
        assert block.title == "Test Block"
        assert block.description == "A block for testing"
        assert len(block.questions) == 1
        assert block.questions[0].id == "q1"

    def test_missing_questions_raises(self):
        with pytest.raises(Exception):  # noqa: B017
            IntakeBlock(id="b", title="T", description="D")

    def test_empty_questions_allowed(self):
        block = IntakeBlock(id="b", title="T", description="D", questions=[])
        assert block.questions == []

    def test_multiple_questions(self):
        questions = [
            IntakeQuestion(id=f"q{i}", text_template=f"Q{i}?")
            for i in range(5)
        ]
        block = IntakeBlock(id="b", title="T", description="D", questions=questions)
        assert len(block.questions) == 5


# =====================================================================
# 10. INTAKE_BLOCKS registry
# =====================================================================


class TestIntakeBlocks:
    """Tests for the INTAKE_BLOCKS list and BLOCKS_BY_ID dict."""

    def test_intake_blocks_has_13_entries(self):
        assert len(INTAKE_BLOCKS) == 13

    def test_blocks_by_id_has_13_entries(self):
        assert len(BLOCKS_BY_ID) == 13

    def test_all_blocks_are_intake_block_instances(self):
        for block in INTAKE_BLOCKS:
            assert isinstance(block, IntakeBlock)

    def test_block_ids_unique(self):
        ids = [block.id for block in INTAKE_BLOCKS]
        assert len(ids) == len(set(ids))

    def test_blocks_by_id_keys_match_block_ids(self):
        ids_from_list = {block.id for block in INTAKE_BLOCKS}
        ids_from_dict = set(BLOCKS_BY_ID.keys())
        assert ids_from_list == ids_from_dict

    def test_blocks_by_id_lookup_returns_correct_block(self):
        for block in INTAKE_BLOCKS:
            assert BLOCKS_BY_ID[block.id] is block

    EXPECTED_BLOCK_IDS = [
        "basic_info",
        "family_childhood",
        "school",
        "university",
        "career",
        "projects_research",
        "awards",
        "talks_public_activity",
        "courses_certificates",
        "compensation",
        "recommenders",
        "goals_usa",
        "final_merits",
    ]

    def test_expected_block_ids_present(self):
        actual_ids = [block.id for block in INTAKE_BLOCKS]
        assert actual_ids == self.EXPECTED_BLOCK_IDS

    def test_each_block_has_at_least_one_question(self):
        for block in INTAKE_BLOCKS:
            assert len(block.questions) >= 1, f"Block '{block.id}' has no questions"

    def test_all_question_ids_globally_unique(self):
        all_question_ids = []
        for block in INTAKE_BLOCKS:
            for q in block.questions:
                all_question_ids.append(q.id)
        assert len(all_question_ids) == len(set(all_question_ids)), (
            "Duplicate question IDs found across blocks"
        )

    def test_basic_info_block_structure(self):
        block = BLOCKS_BY_ID["basic_info"]
        assert block.title == "Общая информация"
        question_ids = [q.id for q in block.questions]
        assert "full_name" in question_ids
        assert "date_of_birth" in question_ids

    def test_final_merits_block_structure(self):
        block = BLOCKS_BY_ID["final_merits"]
        assert block.title == "Итоговая оценка достижений"
        question_ids = [q.id for q in block.questions]
        assert "sustained_acclaim" in question_ids
        assert "benefit_to_us" in question_ids

    def test_all_question_types_are_valid(self):
        """Every question type value should be a valid QuestionType."""
        valid_values = {qt.value for qt in QuestionType}
        for block in INTAKE_BLOCKS:
            for q in block.questions:
                assert q.type in valid_values, (
                    f"Question '{q.id}' has invalid type '{q.type}'"
                )

    def test_select_questions_have_options(self):
        """Any question with type 'select' should have non-empty options."""
        for block in INTAKE_BLOCKS:
            for q in block.questions:
                if q.type == QuestionType.SELECT.value:
                    assert q.options is not None and len(q.options) > 0, (
                        f"SELECT question '{q.id}' is missing options"
                    )
