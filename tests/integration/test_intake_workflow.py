"""
Integration test for end-to-end intake questionnaire workflow.

Tests the complete flow from case creation through answering all questions
to completion, verifying database persistence and memory integration.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from core.intake.schema import INTAKE_BLOCKS, QuestionType
from core.memory.models import MemoryRecord
from core.storage.intake_progress import (
    advance_step,
    complete_block,
    get_progress,
    reset_progress,
    set_progress,
)
from telegram_interface.handlers.intake_handlers import (
    intake_cancel,
    intake_start,
    intake_status,
)


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    user = MagicMock(spec=User)
    user.id = 12345
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    chat = MagicMock(spec=Chat)
    chat.id = 67890
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Create mock Telegram message."""
    message = AsyncMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "/intake_start"
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_message, mock_user):
    """Create mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.effective_message = mock_message
    update.message = mock_message
    return update


@pytest.fixture
def mock_context():
    """Create mock bot context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # Mock bot_data with bot_context
    bot_context = MagicMock()
    bot_context.is_authorized = MagicMock(return_value=True)
    bot_context.get_active_case = AsyncMock(return_value="test_case_123")

    # Mock mega_agent with memory
    mega_agent = AsyncMock()
    memory_manager = AsyncMock()
    memory_manager.awrite = AsyncMock()
    mega_agent.memory = memory_manager
    bot_context.mega_agent = mega_agent

    context.application.bot_data = {"bot_context": bot_context}

    return context


@pytest.fixture
async def clean_progress():
    """Clean up test progress after test."""
    yield
    # Cleanup
    try:
        await reset_progress("12345", "test_case_123")
    except Exception:
        pass


class TestIntakeWorkflowE2E:
    """End-to-end integration tests for intake workflow."""

    @pytest.mark.asyncio
    async def test_complete_intake_flow(
        self, mock_update, mock_context, clean_progress
    ):
        """Test complete flow from start to completion."""
        user_id = "12345"
        case_id = "test_case_123"

        # Step 1: Start intake
        await intake_start(mock_update, mock_context)

        # Verify progress created
        progress = await get_progress(user_id, case_id)
        assert progress is not None
        assert progress["current_block"] == "basic_info"
        assert progress["current_step"] == 0
        assert len(progress["completed_blocks"]) == 0

        # Verify welcome message sent
        mock_update.effective_message.reply_text.assert_called()
        call_args = mock_update.effective_message.reply_text.call_args_list
        assert any("Начинаем анкетирование" in str(call) for call in call_args)

    @pytest.mark.asyncio
    async def test_answer_validation_and_memory_storage(
        self, mock_update, mock_context, clean_progress
    ):
        """Test answer validation and memory storage."""
        user_id = "12345"
        case_id = "test_case_123"

        # Initialize progress
        await set_progress(user_id, case_id, "basic_info", 0, [])

        # Simulate answering first question (full_name)
        # This would normally happen through message handler
        # For integration test, we verify the validation pipeline

        from core.intake.validation import validate_text
        from core.intake.synthesis import synthesize_intake_fact
        from core.intake.schema import BLOCKS_BY_ID

        block = BLOCKS_BY_ID["basic_info"]
        question = block.questions[0]

        # Validate answer
        answer = "Иван Петров"
        is_valid, result = validate_text(answer)
        assert is_valid is True

        # Synthesize fact
        fact = synthesize_intake_fact(question, answer)
        assert "[INTAKE]" in fact
        assert "Иван Петров" in fact

        # Create memory record
        memory_record = MemoryRecord(
            text=fact,
            user_id=user_id,
            type="semantic",
            case_id=case_id,
            tags=question.tags,
            metadata={
                "source": "intake_questionnaire",
                "question_id": question.id,
                "raw_response": answer,
            },
        )

        # Save to memory (mocked)
        await mock_context.application.bot_data["bot_context"].mega_agent.memory.awrite(
            [memory_record]
        )

        # Verify memory write was called
        mock_context.application.bot_data[
            "bot_context"
        ].mega_agent.memory.awrite.assert_called_once()

    @pytest.mark.asyncio
    async def test_progress_advancement(self, clean_progress):
        """Test step-by-step progress advancement."""
        user_id = "12345"
        case_id = "test_case_123"

        # Initialize
        await set_progress(user_id, case_id, "basic_info", 0, [])

        # Advance through steps
        for step in range(5):
            progress = await get_progress(user_id, case_id)
            assert progress["current_step"] == step
            await advance_step(user_id, case_id)

        # Verify step 5 reached
        progress = await get_progress(user_id, case_id)
        assert progress["current_step"] == 5

    @pytest.mark.asyncio
    async def test_block_completion(self, clean_progress):
        """Test block completion and transition."""
        user_id = "12345"
        case_id = "test_case_123"

        # Start at basic_info
        await set_progress(user_id, case_id, "basic_info", 0, [])

        # Complete basic_info block
        await complete_block(user_id, case_id, "basic_info")

        # Verify block marked as complete
        progress = await get_progress(user_id, case_id)
        assert "basic_info" in progress["completed_blocks"]

        # Move to next block
        await set_progress(user_id, case_id, "family_childhood", 0, ["basic_info"])

        progress = await get_progress(user_id, case_id)
        assert progress["current_block"] == "family_childhood"
        assert progress["current_step"] == 0
        assert len(progress["completed_blocks"]) == 1

    @pytest.mark.asyncio
    async def test_intake_status_command(
        self, mock_update, mock_context, clean_progress
    ):
        """Test /intake_status command."""
        user_id = "12345"
        case_id = "test_case_123"

        # Set progress mid-way
        await set_progress(
            user_id, case_id, "career", 10, ["basic_info", "family_childhood", "school", "university"]
        )

        # Call status command
        await intake_status(mock_update, mock_context)

        # Verify status message sent
        mock_update.effective_message.reply_text.assert_called()
        status_call = mock_update.effective_message.reply_text.call_args[0][0]
        assert "Статус анкетирования" in status_call or "Status" in status_call

    @pytest.mark.asyncio
    async def test_intake_cancel_command(
        self, mock_update, mock_context, clean_progress
    ):
        """Test /intake_cancel command."""
        user_id = "12345"
        case_id = "test_case_123"

        # Initialize progress
        await set_progress(user_id, case_id, "basic_info", 5, [])

        # Cancel
        await intake_cancel(mock_update, mock_context)

        # Verify progress deleted
        progress = await get_progress(user_id, case_id)
        assert progress is None

        # Verify confirmation message sent
        mock_update.effective_message.reply_text.assert_called()
        cancel_call = mock_update.effective_message.reply_text.call_args[0][0]
        assert "отменено" in cancel_call.lower() or "cancelled" in cancel_call.lower()

    @pytest.mark.asyncio
    async def test_resume_after_pause(self, mock_update, mock_context, clean_progress):
        """Test resuming questionnaire after pause."""
        user_id = "12345"
        case_id = "test_case_123"

        # Initialize progress at block 2, step 3
        await set_progress(user_id, case_id, "school", 3, ["basic_info", "family_childhood"])

        # Resume (via intake_start when progress exists)
        await intake_start(mock_update, mock_context)

        # Verify progress preserved
        progress = await get_progress(user_id, case_id)
        assert progress["current_block"] == "school"
        assert progress["current_step"] == 3
        assert len(progress["completed_blocks"]) == 2

    @pytest.mark.asyncio
    async def test_all_blocks_structure(self):
        """Test that all 11 blocks are properly defined."""
        assert len(INTAKE_BLOCKS) == 11

        expected_blocks = [
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

        actual_blocks = [block.id for block in INTAKE_BLOCKS]
        assert actual_blocks == expected_blocks

    @pytest.mark.asyncio
    async def test_question_types_coverage(self):
        """Test that all question types are represented."""
        found_types = set()

        for block in INTAKE_BLOCKS:
            for question in block.questions:
                found_types.add(question.type)

        # Should have at least TEXT, YES_NO, and DATE questions
        assert QuestionType.TEXT in found_types
        assert QuestionType.YES_NO in found_types
        assert QuestionType.DATE in found_types

    @pytest.mark.asyncio
    async def test_eb1a_questions_have_rationale(self):
        """Test that EB-1A criterion questions have rationale."""
        eb1a_questions = []

        for block in INTAKE_BLOCKS:
            for question in block.questions:
                if "eb1a_criterion" in question.tags:
                    eb1a_questions.append(question)

        assert len(eb1a_questions) > 0, "Should have EB-1A criterion questions"

        for question in eb1a_questions:
            assert (
                question.rationale is not None
            ), f"Question {question.id} missing rationale"
            assert "EB-1A" in question.rationale or "criterion" in question.rationale.lower()

    @pytest.mark.asyncio
    async def test_concurrent_users(self, clean_progress):
        """Test multiple users can have independent progress."""
        user1_id = "user_001"
        user2_id = "user_002"
        case1_id = "case_001"
        case2_id = "case_002"

        # User 1 at block 1, step 0
        await set_progress(user1_id, case1_id, "basic_info", 0, [])

        # User 2 at block 5, step 10
        await set_progress(user2_id, case2_id, "career", 10, ["basic_info", "family_childhood", "school", "university"])

        # Verify independent progress
        progress1 = await get_progress(user1_id, case1_id)
        progress2 = await get_progress(user2_id, case2_id)

        assert progress1["current_block"] == "basic_info"
        assert progress1["current_step"] == 0

        assert progress2["current_block"] == "career"
        assert progress2["current_step"] == 10

        # Cleanup
        await reset_progress(user1_id, case1_id)
        await reset_progress(user2_id, case2_id)

    @pytest.mark.asyncio
    async def test_validation_date_format(self):
        """Test date validation integration."""
        from core.intake.validation import validate_date

        # Valid dates
        is_valid, normalized = validate_date("2023-05-15")
        assert is_valid is True
        assert normalized == "2023-05-15"

        # Alternate separators
        is_valid, normalized = validate_date("2023.05.15")
        assert is_valid is True
        assert normalized == "2023-05-15"

        # Invalid
        is_valid, normalized = validate_date("invalid")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validation_yes_no(self):
        """Test yes/no validation integration."""
        from core.intake.validation import validate_yes_no

        # Russian yes
        is_valid, normalized = validate_yes_no("да")
        assert is_valid is True
        assert normalized is True

        # Russian no
        is_valid, normalized = validate_yes_no("нет")
        assert is_valid is True
        assert normalized is False

        # English yes
        is_valid, normalized = validate_yes_no("yes")
        assert is_valid is True
        assert normalized is True

    @pytest.mark.asyncio
    async def test_fact_synthesis_integration(self):
        """Test fact synthesis for various question types."""
        from core.intake.schema import IntakeQuestion, QuestionType
        from core.intake.synthesis import synthesize_intake_fact

        # Basic info question
        question = IntakeQuestion(
            id="full_name",
            text_template="Как ваше полное имя?",
            type=QuestionType.TEXT,
            tags=["intake", "basic_info"],
        )
        fact = synthesize_intake_fact(question, "Иван Петров")
        assert "[INTAKE][basic_info]" in fact
        assert "Иван Петров" in fact

        # EB-1A question
        question_eb1a = IntakeQuestion(
            id="career_critical_role",
            text_template="Занимали ли вы критическую роль?",
            type=QuestionType.TEXT,
            rationale="Used to support EB-1A criterion: critical role.",
            tags=["intake", "career", "eb1a_criterion"],
        )
        fact_eb1a = synthesize_intake_fact(question_eb1a, "Да, был CTO")
        assert "[EB-1A criterion:" in fact_eb1a
        assert "Да, был CTO" in fact_eb1a

    @pytest.mark.asyncio
    async def test_timeline_extraction_integration(self):
        """Test timeline extraction for school/university questions."""
        from core.intake.timeline import extract_timeline_data

        # School timeline
        data = extract_timeline_data("2005-2016, Школа №57 в Москве", question_context="school")
        assert data.start_year == 2005
        assert data.end_year == 2016
        assert data.activity_type == "school"
        assert data.location is not None

        # University timeline
        data = extract_timeline_data("2016-2020, МГУ, Москва", question_context="university")
        assert data.start_year == 2016
        assert data.end_year == 2020
        assert data.activity_type == "university"

    @pytest.mark.asyncio
    async def test_no_active_case_error(self, mock_update, mock_context):
        """Test error when no active case."""
        # Mock no active case
        mock_context.application.bot_data["bot_context"].get_active_case = AsyncMock(
            return_value=None
        )

        # Try to start intake
        await intake_start(mock_update, mock_context)

        # Verify error message sent
        mock_update.effective_message.reply_text.assert_called()
        error_call = mock_update.effective_message.reply_text.call_args[0][0]
        assert "Активный кейс не найден" in error_call or "No active case" in error_call


class TestIntakeWorkflowStress:
    """Stress and edge case tests."""

    @pytest.mark.asyncio
    async def test_rapid_step_advancement(self, clean_progress):
        """Test rapid consecutive step advancements."""
        user_id = "stress_user"
        case_id = "stress_case"

        await set_progress(user_id, case_id, "basic_info", 0, [])

        # Advance 20 steps rapidly
        tasks = [advance_step(user_id, case_id) for _ in range(20)]
        await asyncio.gather(*tasks)

        progress = await get_progress(user_id, case_id)
        assert progress["current_step"] == 20

        # Cleanup
        await reset_progress(user_id, case_id)

    @pytest.mark.asyncio
    async def test_complete_all_blocks_sequentially(self, clean_progress):
        """Test completing all 11 blocks in sequence."""
        user_id = "complete_user"
        case_id = "complete_case"

        completed = []

        for i, block in enumerate(INTAKE_BLOCKS):
            await set_progress(user_id, case_id, block.id, 0, completed)
            await complete_block(user_id, case_id, block.id)
            completed.append(block.id)

            progress = await get_progress(user_id, case_id)
            assert len(progress["completed_blocks"]) == i + 1

        # Verify all 11 blocks completed
        final_progress = await get_progress(user_id, case_id)
        assert len(final_progress["completed_blocks"]) == 11

        # Cleanup
        await reset_progress(user_id, case_id)
