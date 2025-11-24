"""
Intake questionnaire module for multi-block biographical data collection.

This module provides:
- Pydantic v2 schema for intake blocks and questions
- Validation and conditional rendering logic
- Fact synthesis and timeline extraction helpers
"""

from core.intake.schema import (
    BLOCKS_BY_ID,
    INTAKE_BLOCKS,
    IntakeBlock,
    IntakeCondition,
    IntakeQuestion,
    QuestionType,
)

__all__ = [
    "QuestionType",
    "IntakeCondition",
    "IntakeQuestion",
    "IntakeBlock",
    "INTAKE_BLOCKS",
    "BLOCKS_BY_ID",
]
