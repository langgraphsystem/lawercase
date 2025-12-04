"""
Simple test to verify the intake questionnaire flow.
This tests the core logic without needing a live Telegram bot.
"""

from __future__ import annotations

from core.groupagents.intake_questionnaire import (
    EB1A_QUESTIONS, GENERAL_IMMIGRATION_QUESTIONS, O1_QUESTIONS,
    format_question_with_help, get_questions_for_category)


def test_get_questions_for_category():
    """Test that correct questions are returned for each category"""
    print("Testing get_questions_for_category()...")

    # Test EB-1A
    eb1a_questions = get_questions_for_category("EB1A")
    assert len(eb1a_questions) == len(EB1A_QUESTIONS), "EB1A questions mismatch"
    assert eb1a_questions[0].id == "field_of_work", "First EB1A question incorrect"
    print(f"  ✓ EB1A: {len(eb1a_questions)} questions")

    # Test O-1
    o1_questions = get_questions_for_category("O1")
    assert len(o1_questions) == len(O1_QUESTIONS), "O1 questions mismatch"
    print(f"  ✓ O1: {len(o1_questions)} questions")

    # Test general/fallback
    general_questions = get_questions_for_category(None)
    assert len(general_questions) == len(
        GENERAL_IMMIGRATION_QUESTIONS
    ), "General questions mismatch"
    print(f"  ✓ General: {len(general_questions)} questions")

    # Test unknown category defaults to general
    unknown_questions = get_questions_for_category("UNKNOWN_TYPE")
    assert len(unknown_questions) == len(
        GENERAL_IMMIGRATION_QUESTIONS
    ), "Unknown category should default to general"
    print(f"  ✓ Unknown category defaults to general: {len(unknown_questions)} questions")


def test_question_formatting():
    """Test question formatting for display"""
    print("\nTesting format_question_with_help()...")

    question = EB1A_QUESTIONS[0]  # field_of_work
    formatted = format_question_with_help(question, 1, 13)

    assert "Question 1/13" in formatted, "Question number not shown"
    assert question.question in formatted, "Question text missing"
    assert "Required" in formatted, "Required indicator missing"
    print("  ✓ Required question formatted correctly")

    # Test optional question
    optional_question = EB1A_QUESTIONS[5]  # publications (optional)
    formatted_optional = format_question_with_help(optional_question, 6, 13)

    assert "Optional" in formatted_optional, "Optional indicator missing"
    assert "/skip" in formatted_optional, "Skip hint missing for optional question"
    print("  ✓ Optional question formatted correctly")


def test_question_structure():
    """Test that all questions have required fields"""
    print("\nTesting question structure...")

    all_question_sets = [
        ("EB1A", EB1A_QUESTIONS),
        ("O1", O1_QUESTIONS),
        ("General", GENERAL_IMMIGRATION_QUESTIONS),
    ]

    for set_name, questions in all_question_sets:
        for i, q in enumerate(questions):
            assert q.id, f"{set_name} question {i} missing id"
            assert q.question, f"{set_name} question {i} missing question text"
            assert q.memory_key, f"{set_name} question {i} missing memory_key"
            assert q.memory_category, f"{set_name} question {i} missing memory_category"

        print(f"  ✓ {set_name}: All {len(questions)} questions have required fields")


def test_memory_categories():
    """Test that questions use appropriate memory categories"""
    print("\nTesting memory categories...")

    valid_categories = {"background", "achievements", "evidence", "logistics"}

    for question in EB1A_QUESTIONS:
        assert (
            question.memory_category in valid_categories
        ), f"Question {question.id} has invalid category: {question.memory_category}"

    print(f"  ✓ All questions use valid memory categories: {valid_categories}")


def test_intake_state_simulation():
    """Simulate the intake state management flow"""
    print("\nSimulating intake state flow...")

    # Simulate intake state
    intake_state = {
        "active": True,
        "case_id": "test_case_123",
        "case_title": "Test EB-1A Case",
        "category": "EB1A",
        "current_question": 0,
        "total_questions": len(EB1A_QUESTIONS),
        "responses": {},
    }

    # Simulate answering questions
    questions = get_questions_for_category("EB1A")

    for _ in range(min(3, len(questions))):  # Answer first 3 questions
        current_q = questions[intake_state["current_question"]]
        response = f"Test response for {current_q.id}"

        # Store response
        intake_state["responses"][current_q.id] = response

        # Move to next
        intake_state["current_question"] += 1

    assert len(intake_state["responses"]) == 3, "Should have 3 responses"
    assert intake_state["current_question"] == 3, "Should be on question 4"
    print(f"  ✓ Answered 3 questions, on question {intake_state['current_question'] + 1}")

    # Test completion check
    if intake_state["current_question"] >= len(questions):
        intake_state["active"] = False
        print("  ✓ Intake marked as complete")
    else:
        remaining = len(questions) - intake_state["current_question"]
        print(f"  ✓ {remaining} questions remaining")


if __name__ == "__main__":
    print("=" * 60)
    print("INTAKE QUESTIONNAIRE TEST SUITE")
    print("=" * 60)

    try:
        test_get_questions_for_category()
        test_question_formatting()
        test_question_structure()
        test_memory_categories()
        test_intake_state_simulation()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise
