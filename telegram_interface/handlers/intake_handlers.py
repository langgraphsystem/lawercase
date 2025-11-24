"""
Intake questionnaire handlers for collecting case information via Telegram.

Provides multi-turn conversation flow for structured data collection after case creation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.groupagents.intake_questionnaire import (
    IntakeQuestion,
    format_question_with_help,
    get_questions_for_category,
)
from core.memory.models import MemoryRecord

from .context import BotContext

logger = structlog.get_logger(__name__)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("❌ Unauthorized")
    return False


# --- Intake State Management in RMT Buffer ---


async def _get_intake_state(bot_context: BotContext, update: Update) -> dict[str, Any] | None:
    """Retrieve intake state from RMT buffer."""
    thread_id = bot_context.thread_id_for_update(update)
    slots = await bot_context.mega_agent.memory.aget_rmt(thread_id)
    if not slots:
        return None
    return slots.get("intake_state")


async def _set_intake_state(
    bot_context: BotContext, update: Update, intake_state: dict[str, Any] | None
) -> None:
    """Store intake state in RMT buffer."""
    thread_id = bot_context.thread_id_for_update(update)
    slots = await bot_context.mega_agent.memory.aget_rmt(thread_id)
    if not slots:
        slots = {
            "persona": "",
            "long_term_facts": "",
            "open_loops": "",
            "recent_summary": "",
        }
    if intake_state is None:
        # Remove intake state
        slots.pop("intake_state", None)
    else:
        slots["intake_state"] = intake_state
    await bot_context.mega_agent.memory.aset_rmt(thread_id, slots)


async def _clear_intake_state(bot_context: BotContext, update: Update) -> None:
    """Clear intake state from RMT buffer."""
    await _set_intake_state(bot_context, update, None)


# --- Command Handlers ---


async def intake_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start the intake questionnaire for the active case.
    Usage: /intake_start
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    # Check if intake is already in progress
    existing_state = await _get_intake_state(bot_context, update)
    if existing_state and existing_state.get("active"):
        await message.reply_text(
            "📝 Intake questionnaire is already in progress.\n\n"
            "Use /intake_status to see your progress\n"
            "Use /intake_cancel to cancel and start over"
        )
        return

    # Get active case
    active_case_id = await bot_context.get_active_case(update)
    if not active_case_id:
        await message.reply_text(
            "❌ No active case found. Please create or select a case first:\n"
            "• /case_create <title> - Create new case\n"
            "• /case_get <case_id> - Select existing case"
        )
        return

    # Get case details to determine category
    try:
        from core.groupagents.mega_agent import CommandType, MegaAgentCommand

        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": active_case_id},
        )
        result = await bot_context.mega_agent.execute(command)

        case_data = result.get("case", {})
        category = case_data.get("category")
        case_title = case_data.get("title", "Unknown")

    except Exception as e:
        logger.error("intake.start.get_case_failed", error=str(e), case_id=active_case_id)
        await message.reply_text("❌ Failed to retrieve case details. Please try again.")
        return

    # Get questions for this case category
    questions = get_questions_for_category(category)
    if not questions:
        await message.reply_text("❌ No questions found for this case type.")
        return

    # Initialize intake state
    intake_state = {
        "active": True,
        "case_id": active_case_id,
        "case_title": case_title,
        "category": category,
        "current_question": 0,
        "total_questions": len(questions),
        "responses": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    await _set_intake_state(bot_context, update, intake_state)

    # Send welcome message and first question
    welcome_text = (
        f"🎯 Starting intake questionnaire for: *{case_title}*\n\n"
        f"I'll ask you {len(questions)} questions to build a strong case.\n"
        f"You can:\n"
        f"• Answer each question directly\n"
        f"• /skip - Skip optional questions\n"
        f"• /intake_status - Check progress\n"
        f"• /intake_cancel - Cancel anytime\n\n"
        f"Let's begin! 🚀"
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    # Send first question
    await _send_current_question(bot_context, update, questions, intake_state)


async def intake_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Skip the current question (only works for optional questions).
    Usage: /skip
    """
    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not message:
        return

    # Get intake state
    intake_state = await _get_intake_state(bot_context, update)
    if not intake_state or not intake_state.get("active"):
        await message.reply_text(
            "❌ No active intake questionnaire. Start with /intake_start"
        )
        return

    # Get current question
    category = intake_state.get("category")
    questions = get_questions_for_category(category)
    current_idx = intake_state.get("current_question", 0)

    if current_idx >= len(questions):
        await message.reply_text("✅ Questionnaire already completed!")
        return

    current_question = questions[current_idx]

    # Check if question is required
    if current_question.required:
        await message.reply_text(
            "❌ This question is required and cannot be skipped.\n"
            "Please provide an answer or use /intake_cancel to cancel."
        )
        return

    # Skip the question
    logger.info(
        "intake.question_skipped",
        case_id=intake_state.get("case_id"),
        question_id=current_question.id,
    )

    # Move to next question
    intake_state["current_question"] = current_idx + 1
    await _set_intake_state(bot_context, update, intake_state)

    # Check if completed
    if intake_state["current_question"] >= len(questions):
        await _complete_intake(bot_context, update, intake_state, questions)
    else:
        await message.reply_text("⏭ Question skipped.")
        await _send_current_question(bot_context, update, questions, intake_state)


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

    # Get intake state
    intake_state = await _get_intake_state(bot_context, update)
    if not intake_state or not intake_state.get("active"):
        await message.reply_text(
            "❌ No active intake questionnaire.\n"
            "Start with /intake_start or /intake_resume"
        )
        return

    current = intake_state.get("current_question", 0)
    total = intake_state.get("total_questions", 0)
    responses = intake_state.get("responses", {})
    case_title = intake_state.get("case_title", "Unknown")

    percentage = int((current / total) * 100) if total > 0 else 0

    status_text = (
        f"📊 *Intake Progress for {case_title}*\n\n"
        f"Progress: {current}/{total} questions ({percentage}%)\n"
        f"Answered: {len(responses)} questions\n\n"
    )

    if current >= total:
        status_text += "✅ Questionnaire completed!"
    else:
        status_text += f"Currently on question {current + 1}\n\n" "Continue by answering the current question."

    await message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


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

    # Get intake state
    intake_state = await _get_intake_state(bot_context, update)
    if not intake_state or not intake_state.get("active"):
        await message.reply_text("❌ No active intake questionnaire to cancel.")
        return

    # Clear state
    await _clear_intake_state(bot_context, update)

    logger.info(
        "intake.cancelled",
        case_id=intake_state.get("case_id"),
        questions_answered=len(intake_state.get("responses", {})),
    )

    await message.reply_text(
        "❌ Intake questionnaire cancelled.\n\n"
        "You can start again anytime with /intake_start"
    )


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

    # Get intake state
    intake_state = await _get_intake_state(bot_context, update)
    if not intake_state:
        await message.reply_text(
            "❌ No intake questionnaire found.\n" "Start a new one with /intake_start"
        )
        return

    if intake_state.get("active"):
        await message.reply_text(
            "📝 Intake questionnaire is already active!\n"
            "Just answer the current question to continue."
        )
        return

    # Reactivate
    intake_state["active"] = True
    await _set_intake_state(bot_context, update, intake_state)

    # Get questions and send current
    category = intake_state.get("category")
    questions = get_questions_for_category(category)

    await message.reply_text("▶️ Resuming intake questionnaire...")
    await _send_current_question(bot_context, update, questions, intake_state)


async def handle_intake_response(
    bot_context: BotContext, update: Update, user_text: str
) -> bool:
    """
    Handle a text response during active intake questionnaire.

    Returns:
        True if message was handled as intake response, False otherwise
    """
    message = update.effective_message
    if not message:
        return False

    # Check if intake is active
    intake_state = await _get_intake_state(bot_context, update)
    if not intake_state or not intake_state.get("active"):
        return False

    # Get current question
    category = intake_state.get("category")
    questions = get_questions_for_category(category)
    current_idx = intake_state.get("current_question", 0)

    if current_idx >= len(questions):
        # Already completed
        await _clear_intake_state(bot_context, update)
        return False

    current_question = questions[current_idx]

    # Store response
    intake_state["responses"][current_question.id] = user_text
    logger.info(
        "intake.response_received",
        case_id=intake_state.get("case_id"),
        question_id=current_question.id,
        response_length=len(user_text),
    )

    # Save to semantic memory immediately
    await _save_response_to_memory(
        bot_context, update, intake_state, current_question, user_text
    )

    # Move to next question
    intake_state["current_question"] = current_idx + 1
    await _set_intake_state(bot_context, update, intake_state)

    # Check if completed
    if intake_state["current_question"] >= len(questions):
        await _complete_intake(bot_context, update, intake_state, questions)
    else:
        await message.reply_text("✅ Got it! Next question:")
        await _send_current_question(bot_context, update, questions, intake_state)

    return True


# --- Helper Functions ---


async def _send_current_question(
    bot_context: BotContext,
    update: Update,
    questions: list[IntakeQuestion],
    intake_state: dict[str, Any],
) -> None:
    """Send the current question to the user."""
    message = update.effective_message
    if not message:
        return

    current_idx = intake_state.get("current_question", 0)
    if current_idx >= len(questions):
        return

    current_question = questions[current_idx]
    total = len(questions)

    question_text = format_question_with_help(current_question, current_idx + 1, total)

    await message.reply_text(question_text, parse_mode=ParseMode.MARKDOWN)


async def _save_response_to_memory(
    bot_context: BotContext,
    update: Update,
    intake_state: dict[str, Any],
    question: IntakeQuestion,
    response: str,
) -> None:
    """Save a single intake response to semantic memory."""
    case_id = intake_state.get("case_id")
    user_id = str(update.effective_user.id)

    # Create semantic memory record
    memory_text = f"{question.memory_key}: {response}"

    memory_record = MemoryRecord(
        text=memory_text,
        user_id=user_id,
        type="semantic",
        case_id=case_id,
        tags=["intake", question.memory_category, question.id],
        metadata={
            "source": "intake_questionnaire",
            "question_id": question.id,
            "category": question.memory_category,
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
        logger.error(
            "intake.save_memory_failed",
            error=str(e),
            case_id=case_id,
            question_id=question.id,
        )


async def _complete_intake(
    bot_context: BotContext,
    update: Update,
    intake_state: dict[str, Any],
    questions: list[IntakeQuestion],
) -> None:
    """Handle completion of the intake questionnaire."""
    message = update.effective_message
    if not message:
        return

    case_id = intake_state.get("case_id")
    case_title = intake_state.get("case_title")
    responses = intake_state.get("responses", {})

    # Clear active flag but keep the state for potential review
    intake_state["active"] = False
    intake_state["completed_at"] = datetime.now(timezone.utc).isoformat()
    await _set_intake_state(bot_context, update, intake_state)

    # Update case memory to mark intake as completed
    user_id = str(update.effective_user.id)
    completion_record = MemoryRecord(
        text=f"Intake questionnaire completed for case '{case_title}' with {len(responses)} responses",
        user_id=user_id,
        type="semantic",
        case_id=case_id,
        tags=["intake_completed", "case_status"],
        metadata={
            "source": "intake_questionnaire",
            "intake_completed": True,
            "responses_count": len(responses),
            "completed_at": intake_state["completed_at"],
        },
    )

    try:
        await bot_context.mega_agent.memory.awrite([completion_record])
    except Exception as e:
        logger.error("intake.completion_record_failed", error=str(e), case_id=case_id)

    # Update RMT buffer with summary
    thread_id = bot_context.thread_id_for_update(update)
    slots = await bot_context.mega_agent.memory.aget_rmt(thread_id)
    if slots:
        # Add intake completion to persona or long_term_facts
        if "long_term_facts" in slots:
            existing_facts = slots.get("long_term_facts", "")
            new_fact = f"Completed intake questionnaire for {case_title}."
            slots["long_term_facts"] = f"{existing_facts}\n{new_fact}".strip()
            await bot_context.mega_agent.memory.aset_rmt(thread_id, slots)

    logger.info(
        "intake.completed",
        case_id=case_id,
        responses_count=len(responses),
        total_questions=len(questions),
    )

    # Send completion message
    completion_text = (
        f"🎉 *Intake questionnaire completed!*\n\n"
        f"Answered {len(responses)}/{len(questions)} questions.\n\n"
        f"All responses have been saved and will help build your case.\n\n"
        f"*Next steps:*\n"
        f"• /ask - Ask questions about your case\n"
        f"• /generate_letter - Generate petition letters\n"
        f"• Upload supporting documents\n\n"
        f"Use /intake_status to review your responses anytime."
    )

    await message.reply_text(completion_text, parse_mode=ParseMode.MARKDOWN)


# --- Text Message Handler for Intake Responses ---


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

    # Try to handle as intake response
    handled = await handle_intake_response(bot_context, update, message.text)

    # If not handled, do nothing (let other handlers process it)
    # The message will fall through to unknown_handler or other handlers


# --- Export handlers for registration ---


def get_handlers(bot_context: BotContext):
    """Return list of handlers to register with the Telegram application."""
    from telegram.ext import CommandHandler, MessageHandler, filters

    return [
        # Command handlers
        CommandHandler("intake_start", intake_start),
        CommandHandler("intake_skip", intake_skip),
        CommandHandler("skip", intake_skip),  # Alias for convenience
        CommandHandler("intake_status", intake_status),
        CommandHandler("intake_cancel", intake_cancel),
        CommandHandler("intake_resume", intake_resume),
        # Text message handler for intake responses (should run before other text handlers)
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_message,
            block=False,  # Allow other handlers to run if not handled
        ),
    ]
