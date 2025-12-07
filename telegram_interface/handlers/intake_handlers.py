"""
Intake questionnaire handlers for collecting case information via Telegram.

Provides multi-block conversation flow with Russian UI, DB persistence,
inline navigation, and fact synthesis for semantic memory.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.agui.events import AGUIEvent
from core.intake.schema import (BLOCKS_BY_ID, INTAKE_BLOCKS, IntakeBlock,
                                IntakeQuestion, QuestionType)
from core.intake.synthesis import synthesize_intake_fact
from core.intake.validation import (parse_list, validate_date, validate_select,
                                    validate_text, validate_yes_no)
from core.memory.models import MemoryRecord
from core.storage.intake_progress import (advance_step, complete_block,
                                          get_progress, reset_progress,
                                          set_progress)

from .context import BotContext

logger = structlog.get_logger(__name__)


def _emit_agui_event(event: AGUIEvent) -> None:
    """Emit AG-UI event for logging/analytics (fire-and-forget)."""
    try:
        logger.info(
            "agui.event.emitted",
            event_type=event.type.value,
            case_id=event.case_id,
            metadata=event.metadata,
        )
    except Exception:
        pass  # nosec B110 - Non-critical logging, don't interrupt intake flow


# Configuration
QUESTIONS_PER_BATCH = 1  # Send 1 question at a time for better UX


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("❌ Не авторизован")
    return False


def ensure_case_exists(func):
    """
    Decorator to ensure case exists before processing intake operations.

    Automatically creates missing case records to prevent orphaned intake progress.
    This is a critical protection against the bug where intake_progress exists
    but the corresponding case record is missing.

    Usage:
        @ensure_case_exists
        async def intake_handler(update, context):
            ...
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        bot_context = _bot_context(context)
        user_id = str(update.effective_user.id)

        # Get active case ID from context
        active_case_id = await bot_context.get_active_case(update)

        if not active_case_id:
            # No active case - handler will deal with it
            return await func(update, context, *args, **kwargs)

        # Verify case exists in database
        try:
            await bot_context.mega_agent.case_agent.aget_case(active_case_id, user_id)
            # Case exists - proceed normally
        except Exception as e:
            # Case not found - auto-create missing case (ORPHAN RECOVERY)
            logger.warning(
                "ensure_case_exists.case_missing",
                user_id=user_id,
                case_id=active_case_id,
                handler=func.__name__,
                error=str(e),
                action="creating_case_automatically",
            )

            try:
                from core.groupagents.models import CaseType

                case = await bot_context.mega_agent.case_agent.acreate_case(
                    user_id=user_id,
                    case_data={
                        "case_id": active_case_id,  # Preserve existing case_id
                        "title": "Intake Session (Recovered)",
                        "description": "Case automatically created to fix orphaned intake progress",
                        "client_id": user_id,
                        "case_type": CaseType.IMMIGRATION.value,
                        "status": "draft",
                    },
                )

                logger.info(
                    "ensure_case_exists.case_created",
                    user_id=user_id,
                    case_id=active_case_id,
                    handler=func.__name__,
                )

            except Exception as create_error:
                logger.error(
                    "ensure_case_exists.case_creation_failed",
                    error=str(create_error),
                    case_id=active_case_id,
                    handler=func.__name__,
                )
                # Continue anyway - let the handler deal with the error

        return await func(update, context, *args, **kwargs)

    return wrapper


# --- Command Handlers ---


async def intake_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start the intake questionnaire for the active case.
    Usage: /intake_start

    CRITICAL: Creates Case record BEFORE intake progress to prevent orphaned records.
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    user_id = str(update.effective_user.id)

    # Get or create active case
    active_case_id = await bot_context.get_active_case(update)
    case_title = "Intake Session"

    # STEP 1: Ensure Case exists BEFORE creating intake progress (CRITICAL FIX)
    if not active_case_id:
        # No active case - create a new one for intake
        try:
            from core.groupagents.models import CaseType

            case = await bot_context.mega_agent.case_agent.acreate_case(
                user_id=user_id,
                case_data={
                    "title": "Intake Session",
                    "description": "Case created during intake questionnaire",
                    "client_id": user_id,
                    "case_type": CaseType.IMMIGRATION.value,
                    "status": "draft",
                },
            )
            active_case_id = case.case_id
            case_title = case.title

            # Set as active case
            await bot_context.set_active_case(update, active_case_id)

            logger.info(
                "intake.case_created",
                user_id=user_id,
                case_id=active_case_id,
                reason="No active case for intake",
            )

        except Exception as e:
            logger.error("intake.start.create_case_failed", error=str(e), user_id=user_id)
            await message.reply_text(
                "❌ Не удалось создать кейс для анкетирования. Попробуйте снова.\n\n"
                f"Ошибка: {e!s}"
            )
            return
    else:
        # Verify case exists in database (protection against orphaned intake progress)
        try:
            case = await bot_context.mega_agent.case_agent.aget_case(active_case_id, user_id)
            case_title = case.title
        except Exception as e:
            # Case not found - create it retroactively
            logger.warning(
                "intake.case_missing",
                user_id=user_id,
                case_id=active_case_id,
                error=str(e),
                action="creating_case_retroactively",
            )
            try:
                from core.groupagents.models import CaseType

                case = await bot_context.mega_agent.case_agent.acreate_case(
                    user_id=user_id,
                    case_data={
                        "case_id": active_case_id,  # Use existing case_id
                        "title": "Intake Session (Recovered)",
                        "description": "Case created retroactively for existing intake progress",
                        "client_id": user_id,
                        "case_type": CaseType.IMMIGRATION.value,
                        "status": "draft",
                    },
                )
                case_title = case.title

                logger.info(
                    "intake.case_recovered",
                    user_id=user_id,
                    case_id=active_case_id,
                )
            except Exception as create_error:
                logger.error(
                    "intake.case_recovery_failed", error=str(create_error), case_id=active_case_id
                )
                await message.reply_text("❌ Не удалось восстановить кейс. Попробуйте снова.")
                return

    # Check if intake is already in progress
    existing_progress = await get_progress(user_id, active_case_id)
    if existing_progress:
        await message.reply_text(
            "📝 Анкета уже в процессе заполнения.\n\n"
            "Используйте /intake_status для просмотра прогресса\n"
            "Используйте /intake_cancel для отмены и начала сначала"
        )
        return

    # STEP 2: Initialize intake progress - ONLY AFTER case exists
    first_block = INTAKE_BLOCKS[0]
    try:
        await set_progress(
            user_id=user_id,
            case_id=active_case_id,
            current_block=first_block.id,
            current_step=0,
            completed_blocks=[],
        )
    except Exception as e:
        logger.error(
            "intake.start.create_progress_failed",
            error=str(e),
            case_id=active_case_id,
            user_id=user_id,
        )
        await message.reply_text("❌ Не удалось начать анкетирование. Попробуйте снова.")
        return

    logger.info(
        "intake.started",
        user_id=user_id,
        case_id=active_case_id,
        total_blocks=len(INTAKE_BLOCKS),
    )

    # Emit AG-UI event for intake start
    _emit_agui_event(
        AGUIEvent.run_started(
            case_id=active_case_id,
            metadata={"operation": "intake_questionnaire", "total_blocks": len(INTAKE_BLOCKS)},
        )
    )

    # Send welcome message
    total_questions = sum(len(block.questions) for block in INTAKE_BLOCKS)
    welcome_text = (
        f"🎯 *Начинаем анкетирование для кейса:* {case_title}\n\n"
        f"Я задам вам вопросы по {len(INTAKE_BLOCKS)} блокам (~{total_questions} вопросов).\n\n"
        f"*Блоки анкеты:*\n"
    )
    for i, block in enumerate(INTAKE_BLOCKS, 1):
        welcome_text += f"{i}. {block.title}\n"

    welcome_text += (
        "\n*Как это работает:*\n"
        "• Вопросы отправляются небольшими партиями\n"
        "• Отвечайте на каждый вопрос текстовым сообщением\n"
        "• Используйте кнопки для навигации (Назад/Пауза/Продолжить)\n"
        "• /intake_status - Проверить прогресс\n"
        "• /intake_cancel - Отменить в любой момент\n\n"
        "Начнём! 🚀"
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    # Send first batch of questions
    await _send_question_batch(bot_context, update, user_id, active_case_id)


@ensure_case_exists
async def intake_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show current progress through the intake questionnaire.
    Usage: /intake_status
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        await message.reply_text(
            "❌ Активный кейс не найден.\n" "Используйте /case_get <case_id> для выбора кейса."
        )
        return

    # Get intake progress
    progress = await get_progress(user_id, active_case_id)
    if not progress:
        await message.reply_text(
            "❌ Анкета не начата.\n" "Используйте /intake_start для начала анкетирования."
        )
        return

    # Calculate statistics
    completed_count = len(progress.completed_blocks)
    total_blocks = len(INTAKE_BLOCKS)
    current_block_id = progress.current_block
    current_step = progress.current_step

    current_block = BLOCKS_BY_ID.get(current_block_id)
    block_title = current_block.title if current_block else "Неизвестно"

    percentage = int((completed_count / total_blocks) * 100) if total_blocks > 0 else 0

    status_text = (
        f"📊 *Прогресс анкетирования*\n\n"
        f"Завершено блоков: {completed_count}/{total_blocks} ({percentage}%)\n\n"
        f"*Текущий блок:* {block_title}\n"
        f"Шаг в блоке: {current_step + 1}\n\n"
    )

    if completed_count >= total_blocks:
        status_text += "✅ Анкета полностью завершена!"
    else:
        status_text += "Продолжайте, отвечая на текущие вопросы."

    reply_markup = None
    if completed_count < total_blocks:
        # Offer to continue right away
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Продолжить анкету", callback_data="intake_continue")]]
        )
        status_text += "\n\nНажмите «Продолжить анкету», чтобы продолжить с текущего шага."

    await message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


@ensure_case_exists
async def intake_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cancel the current intake questionnaire.
    Usage: /intake_cancel
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        await message.reply_text("❌ Активный кейс не найден.")
        return

    # Check if intake exists
    progress = await get_progress(user_id, active_case_id)
    if not progress:
        await message.reply_text("❌ Нет активной анкеты для отмены.")
        return

    # Delete progress
    await reset_progress(user_id, active_case_id)

    logger.info(
        "intake.cancelled",
        user_id=user_id,
        case_id=active_case_id,
        completed_blocks=len(progress.completed_blocks),
    )

    await message.reply_text(
        "❌ Анкетирование отменено.\n\n"
        "Вы можете начать заново в любой момент с помощью /intake_start"
    )


@ensure_case_exists
async def intake_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Resume a paused intake questionnaire.
    Usage: /intake_resume
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        await message.reply_text(
            "❌ Активный кейс не найден.\n" "Используйте /case_get <case_id> для выбора кейса."
        )
        return

    # Get intake progress
    progress = await get_progress(user_id, active_case_id)
    if not progress:
        await message.reply_text("❌ Анкета не найдена.\n" "Начните новую с помощью /intake_start")
        return

    await message.reply_text("▶️ Возобновляем анкетирование...")
    await _send_question_batch(bot_context, update, user_id, active_case_id)


@ensure_case_exists
async def handle_intake_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from inline keyboard buttons.
    """
    bot_context = _bot_context(context)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if not await _is_authorized(bot_context, update):
        return

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        await query.message.reply_text("❌ Активный кейс не найден.")
        return

    data = query.data
    if not data:
        return

    # Parse callback data
    if data == "intake_pause":
        await query.message.reply_text(
            "⏸ Анкетирование приостановлено.\n\n"
            "Используйте /intake_resume для продолжения в любое время."
        )
        logger.info("intake.paused", user_id=user_id, case_id=active_case_id)

    elif data == "intake_back":
        # Go back one step
        progress = await get_progress(user_id, active_case_id)
        if not progress:
            await query.message.reply_text("❌ Анкета не найдена.")
            return

        current_step = progress.current_step
        if current_step > 0:
            # Go back within current block
            new_step = current_step - 1
            await set_progress(
                user_id=user_id,
                case_id=active_case_id,
                current_block=progress.current_block,
                current_step=new_step,
                completed_blocks=progress.completed_blocks,
            )
            await query.message.reply_text("⬅️ Возвращаемся к предыдущему вопросу...")
            await _send_question_batch(bot_context, update, user_id, active_case_id)
        else:
            # At beginning of block, go to previous block
            completed_blocks = progress.completed_blocks
            if completed_blocks:
                # Remove last completed block, go back to it
                prev_block_id = completed_blocks[-1]
                new_completed = completed_blocks[:-1]
                prev_block = BLOCKS_BY_ID.get(prev_block_id)
                if prev_block:
                    await set_progress(
                        user_id=user_id,
                        case_id=active_case_id,
                        current_block=prev_block_id,
                        current_step=0,
                        completed_blocks=new_completed,
                    )
                    await query.message.reply_text(f"⬅️ Возвращаемся к блоку: {prev_block.title}")
                    await _send_question_batch(bot_context, update, user_id, active_case_id)
                else:
                    await query.message.reply_text("❌ Предыдущий блок не найден.")
            else:
                await query.message.reply_text("❌ Вы уже в начале анкеты.")

    elif data in ("intake_next_block", "intake_continue"):
        # Move to next block or continue within block
        await _send_question_batch(bot_context, update, user_id, active_case_id)


async def handle_intake_response(bot_context: BotContext, update: Update, user_text: str) -> bool:
    """
    Handle a text response during active intake questionnaire.

    Returns:
        True if message was handled as intake response, False otherwise
    """
    message = update.effective_message
    if not message:
        return False

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        return False

    # Check if intake is active
    progress = await get_progress(user_id, active_case_id)
    if not progress:
        return False

    # Get current block and question
    current_block_id = progress.current_block
    current_step = progress.current_step

    current_block = BLOCKS_BY_ID.get(current_block_id)
    if not current_block:
        logger.error("intake.invalid_block", block_id=current_block_id)
        return False

    # Get questions for current batch
    questions = _get_questions_for_step(current_block, current_step)
    if not questions:
        # No questions in this batch, possibly all conditional questions were skipped
        return False

    # Expecting response for the first unanswered question in the batch
    # We need to track which questions in the batch have been answered
    # For simplicity, we'll expect answers in order

    # Get the index within the batch for this step
    batch_start = (current_step // QUESTIONS_PER_BATCH) * QUESTIONS_PER_BATCH
    batch_question_idx = current_step - batch_start

    if batch_question_idx >= len(questions):
        # Already answered all questions in this batch
        return False

    current_question = questions[batch_question_idx]

    # Validate response based on question type
    is_valid, validation_result = await _validate_response(current_question, user_text)

    if not is_valid:
        error_msg = (
            validation_result
            if isinstance(validation_result, str)
            else "❌ Некорректный формат ответа."
        )
        await message.reply_text(f"{error_msg}\n\nПожалуйста, попробуйте снова.")
        return True

    # Normalize and store response
    normalized_value = validation_result

    # Save to semantic memory with fact synthesis
    await _save_response_to_memory(
        bot_context, update, active_case_id, current_question, user_text, normalized_value
    )

    logger.info(
        "intake.response_received",
        user_id=user_id,
        case_id=active_case_id,
        question_id=current_question.id,
        response_length=len(user_text),
    )

    # Emit AG-UI event for answer
    _emit_agui_event(
        AGUIEvent.intake_answer(
            case_id=active_case_id,
            question_id=current_question.id,
            answer=user_text[:500],  # Truncate for event (privacy + size)
        )
    )

    # Advance to next question
    await advance_step(user_id, active_case_id)

    # Check if batch is complete or block is complete
    new_step = current_step + 1
    next_batch_start = (new_step // QUESTIONS_PER_BATCH) * QUESTIONS_PER_BATCH

    if next_batch_start > batch_start:
        # Batch complete, show navigation buttons
        await message.reply_text("✅ Партия вопросов завершена!")
        await _send_question_batch(bot_context, update, user_id, active_case_id)
    else:
        # More questions in current batch
        remaining = len(questions) - (batch_question_idx + 1)
        if remaining > 0:
            # Note: with QUESTIONS_PER_BATCH=1, this branch never executes
            await message.reply_text("✅ Принято! Следующий вопрос:")
            # Send next question immediately
            next_question = questions[batch_question_idx + 1]
            await _send_single_question(
                message, next_question, case_id=active_case_id, block_id=current_block_id
            )
        else:
            await _send_question_batch(bot_context, update, user_id, active_case_id)

    return True


# --- Helper Functions ---


def _get_questions_for_step(block: IntakeBlock, step: int) -> list[IntakeQuestion]:
    """
    Get the batch of questions for the current step.
    Filters out conditional questions that shouldn't be shown.
    """
    # For now, we return all questions in the block
    # TODO: Implement conditional filtering based on previous answers
    # This requires storing answered questions and their values

    batch_start = (step // QUESTIONS_PER_BATCH) * QUESTIONS_PER_BATCH
    batch_end = batch_start + QUESTIONS_PER_BATCH

    # Get all questions (conditional filtering would go here)
    all_questions = block.questions
    batch_questions = all_questions[batch_start:batch_end]

    return batch_questions


async def _send_question_batch(
    bot_context: BotContext,
    update: Update,
    user_id: str,
    case_id: str,
) -> None:
    """Send the current batch of questions to the user."""
    message = update.effective_message or update.callback_query.message
    if not message:
        return

    # Get progress
    progress = await get_progress(user_id, case_id)
    if not progress:
        await message.reply_text("❌ Анкета не найдена.")
        return

    current_block_id = progress.current_block
    current_step = progress.current_step
    completed_blocks = progress.completed_blocks

    current_block = BLOCKS_BY_ID.get(current_block_id)
    if not current_block:
        await message.reply_text("❌ Блок не найден.")
        return

    # Special handling for career block - use detailed company-by-company intake
    # Career block triggers detailed intake flow (career_intake.py) instead of simple questions
    if current_block_id == "career":
        # Always start detailed career intake for this block
        # The detailed intake will call continue_intake_after_career when done
        await _start_detailed_career_intake(bot_context, update, user_id, case_id)
        return

    # Check if block is complete
    total_questions = len(current_block.questions)
    if current_step >= total_questions:
        # Find next block
        next_block = _get_next_block(current_block_id)

        # Block complete, move to next
        if next_block:
            await complete_block(user_id, case_id, current_block_id, next_block.id)
        else:
            # Last block - use special marker for completion
            await complete_block(user_id, case_id, current_block_id, "intake_complete")

        if next_block:
            await message.reply_text(
                f"✅ Блок *{current_block.title}* завершён!\n\n"
                f"Переходим к следующему блоку: *{next_block.title}*\n"
                f"{next_block.description}",
                parse_mode=ParseMode.MARKDOWN,
            )
            await _send_question_batch(bot_context, update, user_id, case_id)
        else:
            # All blocks complete
            await _complete_intake(bot_context, update, user_id, case_id)
        return

    # Get questions for current batch
    questions = _get_questions_for_step(current_block, current_step)
    if not questions:
        # No questions in batch (all conditional), skip to next
        await advance_step(user_id, case_id)
        await _send_question_batch(bot_context, update, user_id, case_id)
        return

    # Send batch header (simplified for single-question mode)
    question_num = current_step + 1  # 1-indexed for display

    if current_step == 0:
        # First question in block - show block description
        header = (
            f"📋 *Блок: {current_block.title}*\n"
            f"{current_block.description}\n\n"
            f"Вопрос {question_num} из {total_questions}"
        )
    else:
        # Subsequent questions - compact header
        header = f"📋 *{current_block.title}* (вопрос {question_num}/{total_questions})"

    await message.reply_text(header, parse_mode=ParseMode.MARKDOWN)

    # Send questions (now always 1 question per batch)
    for question in questions:
        await _send_single_question(message, question, case_id=case_id, block_id=current_block_id)

    # If batch has been fully sent, show navigation buttons
    # (user needs to answer all questions first, buttons shown after last answer)


async def _send_single_question(
    message,
    question: IntakeQuestion,
    case_id: str | None = None,
    block_id: str | None = None,
) -> None:
    """Send a single question with formatting."""
    # Emit AG-UI event for question
    if case_id:
        _emit_agui_event(
            AGUIEvent.intake_question(
                case_id=case_id,
                block_id=block_id or "unknown",
                question_id=question.id,
                question_text=question.text_template,
            )
        )

    # Simplified: just show the question text without numbering
    question_text = f"{question.text_template}"

    if question.hint:
        question_text += f"\n\n💡 _Подсказка: {question.hint}_"

    if question.rationale:
        question_text += f"\n\n📌 {question.rationale}"

    if question.type == QuestionType.YES_NO:
        question_text += "\n\n(Ответьте: да/нет или yes/no)"
    elif question.type == QuestionType.DATE:
        question_text += "\n\n(Формат: ГГГГ-ММ-ДД, например 1990-05-15)"
    elif question.type == QuestionType.SELECT and question.options:
        question_text += "\n\nВыберите один из вариантов:\n"
        for opt in question.options:
            question_text += f"• {opt}\n"
    elif question.type == QuestionType.LIST:
        question_text += "\n\n(Перечислите через запятую или с новой строки)"
    elif question.type == QuestionType.DOCUMENT:
        question_text += (
            "\n\n📤 Отправьте файл (PDF или фото) или напишите 'пропустить' чтобы пропустить."
        )

    await message.reply_text(question_text, parse_mode=ParseMode.MARKDOWN)


def _get_next_block(current_block_id: str) -> IntakeBlock | None:
    """Get the next block after the current one."""
    for i, block in enumerate(INTAKE_BLOCKS):
        if block.id == current_block_id:
            if i + 1 < len(INTAKE_BLOCKS):
                return INTAKE_BLOCKS[i + 1]
            return None
    return None


async def _start_detailed_career_intake(
    bot_context: BotContext,
    update: Update,
    user_id: str,
    case_id: str,
) -> None:
    """Start detailed career intake within the main intake flow."""
    message = update.effective_message or update.callback_query.message
    if not message:
        return

    try:
        from core.intake.career_intake import CareerIntakeState

        from .career_intake_handlers import _send_career_question

        # Initialize career intake state with callback to continue main intake
        state = CareerIntakeState(
            user_id=user_id,
            case_id=case_id,
            current_phase="company_count",
        )

        # Mark that this is part of main intake (for callback)
        if not hasattr(bot_context, "_career_states"):
            bot_context._career_states = {}
        state_dict = state.model_dump()
        state_dict["_continue_main_intake"] = True  # Flag to continue after completion
        key = f"career_intake:{user_id}:{case_id}"
        bot_context._career_states[key] = state_dict

        logger.info(
            "intake.career_block_started",
            user_id=user_id,
            case_id=case_id,
        )

        # Send career intake intro
        intro_text = (
            "🏢 *Блок: Профессиональный путь*\n\n"
            "Сейчас мы подробно пройдёмся по каждому месту вашей работы.\n\n"
            "Для каждой компании я спрошу:\n"
            "• Информация о компании\n"
            "• Ваши должности и обязанности\n"
            "• Проекты и достижения\n"
            "• Потенциальные рекомендатели\n"
            "• Подтверждающие документы\n\n"
            "Начнём!"
        )
        await message.reply_text(intro_text, parse_mode=ParseMode.MARKDOWN)

        # Send first career question
        await _send_career_question(bot_context, update, state)

    except ImportError as e:
        logger.error("intake.career_import_error", error=str(e))
        # Fallback: skip career block and move to next
        await message.reply_text(
            "⚠️ Детальный опрос по карьере недоступен.\n"
            "Пропускаем блок и переходим к следующему.",
            parse_mode=ParseMode.MARKDOWN,
        )
        # Mark career as complete and continue
        await continue_intake_after_career(bot_context, update, user_id, case_id)


async def continue_intake_after_career(
    bot_context: BotContext,
    update: Update,
    user_id: str,
    case_id: str,
) -> None:
    """Continue main intake after career block completion."""
    message = update.effective_message or update.callback_query.message
    if not message:
        return

    # Get current progress
    progress = await get_progress(user_id, case_id)
    if not progress:
        return

    # Mark career block as complete and move to next
    current_block = BLOCKS_BY_ID.get("career")
    next_block = _get_next_block("career")

    if next_block:
        await complete_block(user_id, case_id, "career", next_block.id)
        await message.reply_text(
            f"✅ Блок *Профессиональный путь* завершён!\n\n"
            f"Переходим к следующему блоку: *{next_block.title}*\n"
            f"{next_block.description}",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _send_question_batch(bot_context, update, user_id, case_id)
    else:
        # Career was last block
        await complete_block(user_id, case_id, "career", "intake_complete")
        await _complete_intake(bot_context, update, user_id, case_id)


async def _validate_response(question: IntakeQuestion, user_text: str) -> tuple[bool, Any]:
    """
    Validate user response based on question type.

    Returns:
        Tuple of (is_valid, normalized_value_or_error_message)
    """
    if question.type == QuestionType.TEXT:
        is_valid, error_msg = validate_text(user_text, min_length=1)
        return (is_valid, error_msg if not is_valid else user_text)

    if question.type == QuestionType.YES_NO:
        is_valid, normalized = validate_yes_no(user_text)
        if not is_valid:
            return (False, "❌ Пожалуйста, ответьте 'да' или 'нет'.")
        return (True, normalized)

    if question.type == QuestionType.DATE:
        is_valid, normalized = validate_date(user_text)
        if not is_valid:
            return (
                False,
                "❌ Некорректный формат даты. Используйте ГГГГ-ММ-ДД (например, 1990-05-15).",
            )
        return (True, normalized)

    if question.type == QuestionType.SELECT:
        if not question.options:
            return (True, user_text)
        is_valid, matched = validate_select(user_text, question.options)
        if not is_valid:
            return (
                False,
                f"❌ Пожалуйста, выберите один из предложенных вариантов:\n{', '.join(question.options)}",
            )
        return (True, matched)

    if question.type == QuestionType.LIST:
        items = parse_list(user_text)
        if not items:
            return (False, "❌ Пожалуйста, укажите хотя бы один элемент.")
        return (True, items)

    if question.type == QuestionType.DOCUMENT:
        # Allow skip commands for documents
        skip_words = ["пропустить", "skip", "пропуск", "готово", "done", "нет"]
        if user_text.lower().strip() in skip_words:
            return (True, f"[Документ пропущен: {question.id}]")
        # Otherwise, expect file upload - text response is invalid
        return (
            False,
            "❌ Для этого вопроса нужно отправить файл (PDF или фото).\n"
            "Или напишите 'пропустить', чтобы пропустить загрузку.",
        )

    # Default: accept any text
    return (True, user_text)


async def _save_response_to_memory(
    bot_context: BotContext,
    update: Update,
    case_id: str,
    question: IntakeQuestion,
    raw_response: str,
    normalized_value: Any,
) -> None:
    """Save intake response to semantic memory with fact synthesis."""
    user_id = str(update.effective_user.id)

    # Synthesize fact from Q&A
    fact_text = synthesize_intake_fact(question, raw_response)

    memory_record = MemoryRecord(
        text=fact_text,
        user_id=user_id,
        type="semantic",
        case_id=case_id,
        tags=question.tags if question.tags else ["intake"],
        metadata={
            "source": "intake_questionnaire",
            "question_id": question.id,
            "raw_response": raw_response,
            "normalized_value": str(normalized_value),
        },
    )

    try:
        await bot_context.mega_agent.memory.awrite([memory_record])
        logger.info(
            "intake.response_saved_to_memory",
            case_id=case_id,
            question_id=question.id,
        )
    except Exception as e:
        # Use logger.exception() to get full stack trace
        logger.exception(
            "intake.save_memory_failed",
            error=str(e),
            case_id=case_id,
            question_id=question.id,
        )

        # Notify user about the issue (but don't stop the questionnaire)
        try:
            await update.effective_message.reply_text(
                "⚠️ Ваш ответ записан, но возникла проблема с сохранением в долговременную память. "
                "Администратор уведомлён. Вы можете продолжать анкету.",
                parse_mode=None,
            )
        except Exception:
            # If notification fails, just log it (don't break the flow)
            logger.exception("intake.user_notification_failed")


async def _complete_intake(
    bot_context: BotContext,
    update: Update,
    user_id: str,
    case_id: str,
) -> None:
    """Handle completion of the entire intake questionnaire."""
    message = update.effective_message or update.callback_query.message
    if not message:
        return

    # Get case title
    try:
        from core.groupagents.mega_agent import (CommandType, MegaAgentCommand,
                                                 UserRole)

        command = MegaAgentCommand(
            user_id=user_id,
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": case_id},
        )
        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        case_data = response.result.get("case", {}) if response.success else {}
        case_title = case_data.get("title", "Без названия")
    except Exception:
        case_title = "Без названия"

    # Save completion record to semantic memory
    completion_record = MemoryRecord(
        text=f"Анкетирование завершено для кейса '{case_title}'. Собрана полная биографическая информация по {len(INTAKE_BLOCKS)} блокам.",
        user_id=user_id,
        type="semantic",
        case_id=case_id,
        tags=["intake_completed", "case_status"],
        metadata={
            "source": "intake_questionnaire",
            "intake_completed": True,
            "total_blocks": len(INTAKE_BLOCKS),
            "completed_at": datetime.now(UTC).isoformat(),
        },
    )

    try:
        await bot_context.mega_agent.memory.awrite([completion_record])
    except Exception as e:
        logger.error("intake.completion_record_failed", error=str(e), case_id=case_id)

    logger.info(
        "intake.completed",
        user_id=user_id,
        case_id=case_id,
        total_blocks=len(INTAKE_BLOCKS),
    )

    # Emit AG-UI event for completion
    _emit_agui_event(
        AGUIEvent.run_finished(
            case_id=case_id,
            metadata={"operation": "intake_questionnaire", "total_blocks": len(INTAKE_BLOCKS)},
        )
    )

    # Send completion message
    completion_text = (
        f"🎉 *Анкетирование завершено!*\n\n"
        f"Все {len(INTAKE_BLOCKS)} блоков успешно пройдены.\n\n"
        f"Все ответы сохранены и будут использованы для построения вашего кейса.\n\n"
        f"*Следующие шаги:*\n"
        f"• /ask - Задать вопросы о вашем кейсе\n"
        f"• /generate_letter - Сгенерировать петицию\n"
        f"• Загрузить подтверждающие документы\n\n"
        f"Используйте /intake_status для просмотра статуса в любое время."
    )

    await message.reply_text(completion_text, parse_mode=ParseMode.MARKDOWN)


# --- Document Upload Handler for Intake ---


@ensure_case_exists
async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle document/photo uploads during active intake questionnaire.

    Returns:
        True if message was handled as intake document, False otherwise
    """
    bot_context = _bot_context(context)
    message = update.effective_message
    if not message:
        return False

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        return False

    # Check if intake is active
    progress = await get_progress(user_id, active_case_id)
    if not progress:
        return False

    # Get current question
    current_block_id = progress.current_block
    current_step = progress.current_step

    current_block = BLOCKS_BY_ID.get(current_block_id)
    if not current_block:
        return False

    questions = _get_questions_for_step(current_block, current_step)
    if not questions:
        return False

    batch_start = (current_step // QUESTIONS_PER_BATCH) * QUESTIONS_PER_BATCH
    batch_question_idx = current_step - batch_start

    if batch_question_idx >= len(questions):
        return False

    current_question = questions[batch_question_idx]

    # Only accept documents for DOCUMENT type questions
    if current_question.type != QuestionType.DOCUMENT:
        await message.reply_text(
            "❌ Для этого вопроса нужен текстовый ответ, а не файл.\n"
            "Пожалуйста, напишите ваш ответ текстом."
        )
        return True

    # Get file info
    file = None
    file_name = "document"
    file_type = "unknown"

    if message.document:
        file = message.document
        file_name = message.document.file_name or "document"
        file_type = message.document.mime_type or "application/octet-stream"
    elif message.photo:
        # Get largest photo
        file = message.photo[-1]
        file_name = f"photo_{file.file_id[:8]}.jpg"
        file_type = "image/jpeg"

    if not file:
        return False

    try:
        # Download file
        telegram_file = await file.get_file()

        # Download to bytes
        file_bytes = await telegram_file.download_as_bytearray()

        logger.info(
            "intake.document_received",
            user_id=user_id,
            case_id=active_case_id,
            question_id=current_question.id,
            file_name=file_name,
            file_size=len(file_bytes),
        )

        # Process and save document
        await _save_document_to_memory(
            bot_context=bot_context,
            update=update,
            case_id=active_case_id,
            question=current_question,
            file_bytes=bytes(file_bytes),
            file_name=file_name,
            file_type=file_type,
        )

        # Advance to next question
        await advance_step(user_id, active_case_id)

        await message.reply_text(
            f"✅ Документ '{file_name}' получен и сохранён!\n" "Переходим к следующему вопросу..."
        )

        # Send next question
        await _send_question_batch(bot_context, update, user_id, active_case_id)
        return True

    except Exception as e:
        logger.exception(
            "intake.document_upload_failed",
            error=str(e),
            case_id=active_case_id,
            question_id=current_question.id,
        )
        await message.reply_text(
            f"❌ Ошибка при загрузке документа: {e!s}\n"
            "Попробуйте снова или напишите 'пропустить'."
        )
        return True


async def _save_document_to_memory(
    bot_context: BotContext,
    update: Update,
    case_id: str,
    question: IntakeQuestion,
    file_bytes: bytes,
    file_name: str,
    file_type: str,
) -> None:
    """Save uploaded document to storage and semantic memory with OCR processing."""
    user_id = str(update.effective_user.id)
    message = update.effective_message

    # Initialize document text and storage info
    document_text = f"Загружен документ: {file_name}"
    ocr_text = ""
    ocr_method = "none"
    storage_path = ""
    storage_url = ""

    # Step 1: Save file to document storage (Supabase/R2/local)
    try:
        from core.services.document_storage import get_document_storage

        storage = get_document_storage()
        storage_result = await storage.save_document(
            file_bytes=file_bytes,
            file_name=file_name,
            file_type=file_type,
            user_id=user_id,
            case_id=case_id,
            question_id=question.id,
            metadata={"block": question.tags[0] if question.tags else "intake"},
        )

        if storage_result.get("success"):
            storage_path = storage_result.get("storage_path", "")
            storage_url = storage_result.get("storage_url", "")
            logger.info(
                "intake.document_stored",
                file_name=file_name,
                storage_path=storage_path,
                backend=storage_result.get("backend"),
            )
        else:
            logger.warning(
                "intake.document_storage_failed",
                file_name=file_name,
                error=storage_result.get("error"),
            )
    except Exception as e:
        logger.warning("intake.document_storage_error", error=str(e), file_name=file_name)

    # Send processing notification for images/scanned docs
    is_image = file_type.startswith("image/") or file_name.lower().endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    )
    is_pdf = file_type == "application/pdf" or file_name.lower().endswith(".pdf")

    if is_image or is_pdf:
        try:
            if message:
                await message.reply_text("🔍 Сканирую документ (OCR)...")
        except Exception:  # nosec B110 - intentional: notification failure is non-critical
            pass

    # Process with OCR for images and PDFs
    if is_image or is_pdf:
        try:
            from core.services.ocr_service import get_ocr_service

            ocr_service = get_ocr_service()
            ocr_result = await ocr_service.process_document(file_bytes, file_name, file_type)

            if ocr_result.get("extracted_text"):
                ocr_text = ocr_result["extracted_text"]
                ocr_method = ocr_result.get("method", "ocr")
                confidence = ocr_result.get("confidence", "unknown")

                # Build document text with OCR content
                # Truncate for memory but keep substantial content
                max_ocr_length = 5000
                if len(ocr_text) > max_ocr_length:
                    ocr_preview = ocr_text[:max_ocr_length]
                    document_text = (
                        f"📄 Документ '{file_name}' (OCR, {confidence}):\n\n"
                        f"{ocr_preview}\n\n... (текст обрезан, полная длина: {len(ocr_text)} символов)"
                    )
                else:
                    document_text = f"📄 Документ '{file_name}' (OCR, {confidence}):\n\n{ocr_text}"

                logger.info(
                    "intake.ocr_complete",
                    file_name=file_name,
                    text_length=len(ocr_text),
                    method=ocr_method,
                    confidence=confidence,
                )
            else:
                # OCR failed or returned empty
                error_msg = ocr_result.get("error", "No text extracted")
                logger.warning(
                    "intake.ocr_no_text",
                    file_name=file_name,
                    error=error_msg,
                )
                document_text = f"📄 Документ '{file_name}' (текст не извлечён: {error_msg})"

        except Exception as e:
            logger.exception("intake.ocr_failed", error=str(e), file_name=file_name)
            # Fallback to basic extraction for PDFs
            if is_pdf:
                try:
                    from core.rag.document_parser import MarkitdownParser

                    parser = MarkitdownParser()
                    parsed_doc = await parser.parse_bytes(file_bytes, file_name)
                    if parsed_doc.content and len(parsed_doc.content) > 50:
                        content_preview = parsed_doc.content[:3000]
                        document_text = f"Документ '{file_name}':\n{content_preview}"
                        if len(parsed_doc.content) > 3000:
                            document_text += "\n... (документ обрезан)"
                        ocr_method = "markitdown_fallback"
                except Exception as fallback_error:
                    logger.warning(
                        "intake.fallback_extraction_failed",
                        error=str(fallback_error),
                        file_name=file_name,
                    )

    # Add OCR tag if text was extracted
    doc_tags = (
        [*question.tags, "uploaded_document"] if question.tags else ["intake", "uploaded_document"]
    )
    if ocr_text:
        doc_tags = [*doc_tags, "ocr_processed"]

    # Create memory record with OCR and storage metadata
    memory_record = MemoryRecord(
        text=document_text,
        user_id=user_id,
        type="semantic",
        case_id=case_id,
        tags=doc_tags,
        metadata={
            "source": "intake_document_upload",
            "question_id": question.id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": len(file_bytes),
            "ocr_method": ocr_method,
            "ocr_text_length": len(ocr_text) if ocr_text else 0,
            "storage_path": storage_path,
            "storage_url": storage_url,
        },
    )

    try:
        await bot_context.mega_agent.memory.awrite([memory_record])
        logger.info(
            "intake.document_saved_to_memory",
            case_id=case_id,
            question_id=question.id,
            file_name=file_name,
            ocr_method=ocr_method,
            ocr_text_length=len(ocr_text) if ocr_text else 0,
        )
    except Exception as e:
        logger.exception(
            "intake.document_save_failed",
            error=str(e),
            case_id=case_id,
            file_name=file_name,
        )


# --- Text Message Handler for Intake Responses ---


@ensure_case_exists
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages that might be intake responses.
    This handler should be registered with high priority to intercept intake responses.
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message or not message.text:
        return

    # Skip if it's a command
    if message.text.startswith("/"):
        return

    # Try career intake first (more specific)
    try:
        from .career_intake_handlers import handle_career_response

        if await handle_career_response(bot_context, update, message.text):
            return  # Handled by career intake
    except ImportError:
        pass  # Career intake not available

    # Try to handle as regular intake response
    # Note: document/photo uploads are handled by handle_document_upload handler
    await handle_intake_response(bot_context, update, message.text)


# --- Export handlers for registration ---


def get_handlers(bot_context: BotContext):
    """Return list of handlers to register with the Telegram application."""
    from telegram.ext import (CallbackQueryHandler, CommandHandler,
                              MessageHandler, filters)

    return [
        # Command handlers
        CommandHandler("intake_start", intake_start),
        CommandHandler("intake_status", intake_status),
        CommandHandler("intake_cancel", intake_cancel),
        CommandHandler("intake_resume", intake_resume),
        # Callback query handler for inline buttons
        CallbackQueryHandler(handle_intake_callback, pattern="^intake_"),
        # Document/photo handler for intake uploads (high priority for document questions)
        MessageHandler(
            filters.Document.ALL | filters.PHOTO,
            handle_document_upload,
            block=False,
        ),
        # Text message handler for intake responses (should run before other text handlers)
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_message,
            block=False,  # Allow other handlers to run if not handled
        ),
    ]
