"""Test the answer validator."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))


async def test_validator():
    """Test answer validation."""
    from core.intake.answer_validator import is_meaningless_answer, validate_answer_with_ai
    from core.intake.schema import IntakeQuestion, QuestionType

    print("=" * 60)
    print("Testing answer validator")
    print("=" * 60)

    # Test 1: Meaningless patterns
    print("\n1. Testing meaningless pattern detection...")
    test_cases = [
        (".", True),
        ("...", True),
        ("x", True),
        ("!!!", True),
        ("123", True),
        ("test", True),
        ("да", False),
        ("нет", False),
        ("Иван Петров", False),
        ("Machine Learning", False),
    ]

    for answer, expected_meaningless in test_cases:
        result = is_meaningless_answer(answer)
        status = "✅" if result == expected_meaningless else "❌"
        print(f"   {status} '{answer}' → meaningless={result} (expected={expected_meaningless})")

    # Test 2: AI validation
    print("\n2. Testing AI validation...")

    # Create a mock question
    question = IntakeQuestion(
        id="career_field",
        text_template="Какова ваша основная область деятельности?",
        type=QuestionType.TEXT,
        options=None,
        hint="Например: IT, медицина, финансы",
        rationale=None,
        condition=None,
        tags=["career"],
    )

    test_answers = [
        (".", False),
        ("да", False),
        ("Data Science и машинное обучение", True),
        ("Программирование", True),
    ]

    for answer, expected_valid in test_answers:
        is_valid, error = await validate_answer_with_ai(question, answer)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} '{answer[:30]}...' → valid={is_valid} (expected={expected_valid})")
        if error:
            print(f"      Error: {error[:50]}...")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(test_validator())
