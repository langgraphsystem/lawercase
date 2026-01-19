"""
Dynamic career intake handlers for detailed company-by-company questioning.

Commands:
- /career_start - Start detailed career intake
- /career_status - Show career intake progress
- /career_skip - Skip to next company or phase

This module provides a sophisticated career data collection flow that:
1. Loops through each employer one by one
2. Collects detailed information per company
3. Generates contextual follow-up questions using LLM
4. Collects evidence and recommenders
"""

from __future__ import annotations

import json

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.intake.career_intake import (
    FOLLOWUP_QUESTION_PROMPT,
    AchievementEntry,
    CareerEntry,
    CareerIntakeState,
    CompanyType,
    PositionEntry,
    get_next_phase,
    get_phase_questions,
    map_company_type,
)
from core.memory.models import MemoryRecord

from .context import BotContext

logger = structlog.get_logger(__name__)

# Redis/storage key prefix for career intake state
CAREER_STATE_KEY = "career_intake:{user_id}:{case_id}"


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("❌ Не авторизован")
    return False


# --- State Management ---


async def _get_career_state(
    bot_context: BotContext, user_id: str, case_id: str
) -> CareerIntakeState | None:
    """Get career intake state from storage."""
    try:
        key = CAREER_STATE_KEY.format(user_id=user_id, case_id=case_id)
        # Use memory metadata or a dedicated storage
        # For now, store in user_data via context
        # In production, use Redis or database
        state_data = bot_context._career_states.get(key)
        if state_data:
            return CareerIntakeState.model_validate(state_data)
    except Exception as e:
        logger.warning("career_intake.get_state_error", error=str(e))
    return None


async def _save_career_state(bot_context: BotContext, state: CareerIntakeState) -> None:
    """Save career intake state to storage."""
    try:
        key = CAREER_STATE_KEY.format(user_id=state.user_id, case_id=state.case_id)
        # Initialize storage if needed
        if not hasattr(bot_context, "_career_states"):
            bot_context._career_states = {}
        bot_context._career_states[key] = state.model_dump()
    except Exception as e:
        logger.error("career_intake.save_state_error", error=str(e))


async def _delete_career_state(bot_context: BotContext, user_id: str, case_id: str) -> None:
    """Delete career intake state."""
    try:
        key = CAREER_STATE_KEY.format(user_id=user_id, case_id=case_id)
        if hasattr(bot_context, "_career_states"):
            bot_context._career_states.pop(key, None)
    except Exception as e:
        logger.warning("career_intake.delete_state_error", error=str(e))


# --- Command Handlers ---


async def career_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start detailed career intake questionnaire.
    Usage: /career_start
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
            "❌ Активный кейс не найден.\n"
            "Сначала создайте кейс или выберите существующий с помощью /case_get"
        )
        return

    # Check for existing career intake
    existing_state = await _get_career_state(bot_context, user_id, active_case_id)
    if existing_state and not existing_state.is_complete:
        await message.reply_text(
            "📋 У вас уже есть незавершённый опрос по карьере.\n\n"
            "Используйте /career_status для просмотра прогресса\n"
            "Используйте /career_cancel для отмены и начала сначала"
        )
        return

    # Initialize new career intake state
    state = CareerIntakeState(
        user_id=user_id,
        case_id=active_case_id,
        current_phase="company_count",
    )
    await _save_career_state(bot_context, state)

    logger.info(
        "career_intake.started",
        user_id=user_id,
        case_id=active_case_id,
    )

    # Send welcome message
    welcome_text = (
        "🏢 *Детальный опрос по карьере*\n\n"
        "Сейчас мы подробно пройдёмся по каждому месту вашей работы.\n\n"
        "Для каждой компании я спрошу:\n"
        "• Информация о компании и сфере деятельности\n"
        "• Ваши должности и обязанности\n"
        "• Проекты и инициативы\n"
        "• Достижения и их доказательства\n"
        "• Потенциальные рекомендатели\n\n"
        "На основе ваших ответов я задам дополнительные вопросы, "
        "чтобы собрать максимум информации для вашего кейса EB-1A.\n\n"
        "Начнём! 🚀"
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    # Ask first question - how many companies
    await _send_career_question(bot_context, update, state)


async def career_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show career intake progress.
    Usage: /career_status
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

    state = await _get_career_state(bot_context, user_id, active_case_id)
    if not state:
        await message.reply_text(
            "❌ Опрос по карьере не начат.\n" "Используйте /career_start для начала."
        )
        return

    # Build status message
    status_lines = [
        "📊 *Прогресс опроса по карьере*\n",
    ]

    if state.total_companies > 0:
        status_lines.append(
            f"Компаний: {state.current_company_index + 1} из {state.total_companies}"
        )

    status_lines.append(f"Текущая фаза: {_phase_name(state.current_phase)}")

    if state.career_entries:
        status_lines.append("\n*Собранные компании:*")
        for i, entry in enumerate(state.career_entries, 1):
            status_lines.append(f"{i}. {entry.company_name}")

    if state.current_entry.get("company_name"):
        status_lines.append(f"\n*Текущая компания:* {state.current_entry['company_name']}")

    if state.is_complete:
        status_lines.append("\n✅ Опрос завершён!")
    else:
        status_lines.append("\nПродолжайте отвечать на вопросы.")

    await message.reply_text("\n".join(status_lines), parse_mode=ParseMode.MARKDOWN)


async def career_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cancel career intake.
    Usage: /career_cancel
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

    await _delete_career_state(bot_context, user_id, active_case_id)
    await message.reply_text(
        "❌ Опрос по карьере отменён.\n\n" "Вы можете начать заново с помощью /career_start"
    )


async def career_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Skip current phase or move to next company.
    Usage: /career_skip
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
        return

    state = await _get_career_state(bot_context, user_id, active_case_id)
    if not state:
        return

    # Move to next phase or company
    await _advance_phase(bot_context, update, state, skip=True)


# --- Response Handling ---


async def handle_career_response(bot_context: BotContext, update: Update, user_text: str) -> bool:
    """
    Handle text response during career intake.
    Returns True if handled, False if not in career intake mode.
    """
    message = update.effective_message
    if not message:
        return False

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        return False

    state = await _get_career_state(bot_context, user_id, active_case_id)
    if not state or state.is_complete:
        return False

    logger.info(
        "career_intake.response",
        user_id=user_id,
        phase=state.current_phase,
        response_length=len(user_text),
    )

    # Process response based on current phase
    await _process_career_response(bot_context, update, state, user_text)
    return True


async def handle_career_document(bot_context: BotContext, update: Update) -> bool:
    """
    Handle document upload during career intake evidence phase.
    Returns True if handled, False if not in evidence phase.
    """
    message = update.effective_message
    if not message:
        return False

    user_id = str(update.effective_user.id)
    active_case_id = await bot_context.get_active_case(update)

    if not active_case_id:
        return False

    state = await _get_career_state(bot_context, user_id, active_case_id)
    if not state or state.is_complete:
        return False

    # Only handle documents in evidence phase
    if state.current_phase != "evidence":
        return False

    # Get file info
    file = None
    file_name = "document"

    if message.document:
        file = message.document
        file_name = message.document.file_name or "document"
    elif message.photo:
        file = message.photo[-1]
        file_name = f"photo_{file.file_id[:8]}.jpg"

    if not file:
        return False

    try:
        telegram_file = await file.get_file()
        file_bytes = await telegram_file.download_as_bytearray()

        # Store file reference in current entry
        if "documents" not in state.current_entry:
            state.current_entry["documents"] = []
        state.current_entry["documents"].append(
            {
                "file_name": file_name,
                "file_id": file.file_id,
                "size": len(file_bytes),
            }
        )

        await _save_career_state(bot_context, state)

        await message.reply_text(
            f"✅ Документ '{file_name}' сохранён!\n"
            "Отправьте ещё документы или напишите 'готово' для продолжения."
        )
        return True

    except Exception as e:
        logger.exception("career_intake.document_error", error=str(e))
        await message.reply_text(f"❌ Ошибка загрузки: {e!s}")
        return True


# --- Internal Functions ---


async def _send_career_question(
    bot_context: BotContext,
    update: Update,
    state: CareerIntakeState,
) -> None:
    """Send the current question based on state."""
    message = update.effective_message or update.callback_query.message
    if not message:
        return

    phase = state.current_phase
    company_name = state.current_entry.get("company_name", "")
    company_index = state.current_company_index + 1

    # Get questions for current phase
    questions = get_phase_questions(phase, company_name, company_index)

    if not questions:
        # No questions in this phase, advance
        await _advance_phase(bot_context, update, state)
        return

    # Check for pending follow-up questions first
    if state.pending_questions:
        question_text = state.pending_questions.pop(0)
        await _save_career_state(bot_context, state)
        await message.reply_text(f"❓ {question_text}")
        return

    # Send first question of the phase
    question = questions[0]
    question_text = question["text"]

    if question.get("hint"):
        question_text += f"\n\n💡 _{question['hint']}_"

    if question.get("type") == "select" and question.get("options"):
        question_text += "\n\nВыберите вариант:\n"
        for i, opt in enumerate(question["options"], 1):
            question_text += f"{i}. {opt}\n"

    if question.get("type") == "yes_no":
        question_text += "\n\n(да/нет)"

    if question.get("type") == "document":
        question_text += "\n\n📤 Отправьте файл или напишите 'пропустить'"

    # Add skip button for optional phases
    reply_markup = None
    if phase in ["projects", "evidence"]:
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⏭️ Пропустить", callback_data="career_skip_phase")]]
        )

    await message.reply_text(
        question_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def _process_career_response(
    bot_context: BotContext,
    update: Update,
    state: CareerIntakeState,
    user_text: str,
) -> None:
    """Process user response and update state."""
    message = update.effective_message
    phase = state.current_phase

    # Handle company count phase
    if phase == "company_count":
        try:
            count = int(user_text.strip())
            if count < 1:
                await message.reply_text("❌ Укажите хотя бы одну компанию.")
                return
            if count > 20:
                await message.reply_text("❌ Максимум 20 компаний. Укажите число от 1 до 20.")
                return

            state.total_companies = count
            state.current_phase = "company_basics"
            state.current_company_index = 0
            await _save_career_state(bot_context, state)

            await message.reply_text(
                f"✅ Отлично! Пройдёмся по {count} компаниям.\n\n"
                f"Начнём с первой компании (можно с самой ранней)."
            )
            await _send_career_question(bot_context, update, state)

        except ValueError:
            await message.reply_text("❌ Пожалуйста, укажите число.")
        return

    # Store response in current entry
    questions = get_phase_questions(
        phase,
        state.current_entry.get("company_name", ""),
        state.current_company_index + 1,
    )

    if questions:
        current_q = questions[0]
        field_id = current_q["id"]

        # Handle special types
        if current_q.get("type") == "yes_no":
            normalized = user_text.lower().strip()
            if normalized in ["да", "yes", "д", "y", "1"]:
                state.current_entry[field_id] = True
            elif normalized in ["нет", "no", "н", "n", "0"]:
                state.current_entry[field_id] = False
            else:
                await message.reply_text("❌ Пожалуйста, ответьте 'да' или 'нет'.")
                return
        elif current_q.get("type") == "select":
            # Try to match option
            options = current_q.get("options", [])
            matched = None
            for i, opt in enumerate(options):
                if user_text.strip() == str(i + 1) or user_text.lower() in opt.lower():
                    matched = opt
                    break
            if matched:
                state.current_entry[field_id] = matched
                # Map company type
                if field_id == "company_type":
                    state.current_entry["company_type_enum"] = map_company_type(matched)
            else:
                await message.reply_text("❌ Выберите один из предложенных вариантов.")
                return
        else:
            state.current_entry[field_id] = user_text

    await _save_career_state(bot_context, state)
    await message.reply_text("✅ Принято!")

    # Check if we need to generate follow-up questions
    if phase in ["positions", "achievements"] and not state.pending_questions:
        follow_ups = await _generate_followup_questions(bot_context, state)
        if follow_ups:
            state.pending_questions.extend(follow_ups)
            await _save_career_state(bot_context, state)

    # Advance to next question or phase
    await _advance_phase(bot_context, update, state)


async def _advance_phase(
    bot_context: BotContext,
    update: Update,
    state: CareerIntakeState,
    skip: bool = False,
) -> None:
    """Advance to next phase or company."""
    message = update.effective_message or update.callback_query.message

    # If there are pending follow-up questions, send them first
    if state.pending_questions and not skip:
        await _send_career_question(bot_context, update, state)
        return

    current_phase = state.current_phase
    company_type = state.current_entry.get("company_type_enum", CompanyType.PRIVATE)

    # Get next phase
    next_phase = get_next_phase(current_phase, company_type)

    if next_phase:
        # Move to next phase within current company
        state.current_phase = next_phase
        await _save_career_state(bot_context, state)
        await _send_career_question(bot_context, update, state)
    else:
        # Current company complete - save it
        await _save_current_company(bot_context, update, state)

        # Check if there are more companies
        if state.current_company_index < state.total_companies - 1:
            state.current_company_index += 1
            state.current_phase = "company_basics"
            state.current_entry = {}
            state.pending_questions = []
            await _save_career_state(bot_context, state)

            await message.reply_text(
                f"✅ Компания сохранена!\n\n"
                f"Переходим к компании {state.current_company_index + 1} из {state.total_companies}."
            )
            await _send_career_question(bot_context, update, state)
        else:
            # All companies complete
            await _complete_career_intake(bot_context, update, state)


async def _save_current_company(
    bot_context: BotContext,
    update: Update,
    state: CareerIntakeState,
) -> None:
    """Save current company entry and write to memory."""
    entry_data = state.current_entry

    if not entry_data.get("company_name"):
        return

    # Create CareerEntry
    career_entry = CareerEntry(
        company_name=entry_data.get("company_name", ""),
        company_type=entry_data.get("company_type_enum", CompanyType.OTHER),
        company_industry=entry_data.get("company_industry", ""),
        company_description=entry_data.get("company_description"),
        company_location=entry_data.get("company_location", ""),
        start_date=(
            entry_data.get("employment_period", "").split("-")[0].strip()
            if entry_data.get("employment_period")
            else ""
        ),
    )

    # Add positions
    if entry_data.get("positions_list"):
        career_entry.positions.append(
            PositionEntry(
                title=entry_data.get("positions_list", ""),
                responsibilities=(
                    entry_data.get("main_responsibilities", "").split(",")
                    if entry_data.get("main_responsibilities")
                    else []
                ),
            )
        )

    # Add achievements
    if entry_data.get("significant_achievements"):
        career_entry.achievements.append(
            AchievementEntry(
                description=entry_data.get("significant_achievements", ""),
                category="other",
                impact=entry_data.get("measurable_impact"),
            )
        )

    state.career_entries.append(career_entry)

    # Save to semantic memory
    memory_text = f"""
Опыт работы: {career_entry.company_name}
Тип: {career_entry.company_type.value}
Сфера: {career_entry.company_industry}
Локация: {career_entry.company_location}

Должности: {entry_data.get('positions_list', 'Не указано')}
Обязанности: {entry_data.get('main_responsibilities', 'Не указано')}

Достижения: {entry_data.get('significant_achievements', 'Не указано')}
Измеримые результаты: {entry_data.get('measurable_impact', 'Не указано')}
"""

    memory_record = MemoryRecord(
        text=memory_text.strip(),
        user_id=state.user_id,
        type="semantic",
        case_id=state.case_id,
        tags=["intake", "career", "work_experience", career_entry.company_type.value],
        metadata={
            "source": "career_intake",
            "company_name": career_entry.company_name,
            "company_index": state.current_company_index,
        },
    )

    try:
        await bot_context.mega_agent.memory.awrite([memory_record])
        logger.info(
            "career_intake.company_saved",
            company=career_entry.company_name,
            case_id=state.case_id,
        )
    except Exception as e:
        logger.exception("career_intake.save_memory_error", error=str(e))


async def _complete_career_intake(
    bot_context: BotContext,
    update: Update,
    state: CareerIntakeState,
) -> None:
    """Complete the career intake process."""
    message = update.effective_message or update.callback_query.message

    state.is_complete = True
    await _save_career_state(bot_context, state)

    # Check if this was part of main intake flow
    key = CAREER_STATE_KEY.format(user_id=state.user_id, case_id=state.case_id)
    state_data = bot_context._career_states.get(key, {})
    continue_main_intake = state_data.get("_continue_main_intake", False)

    # Generate summary
    summary_lines = [
        "🎉 *Опрос по карьере завершён!*\n",
        f"Собрана информация по {len(state.career_entries)} компаниям:\n",
    ]

    for i, entry in enumerate(state.career_entries, 1):
        summary_lines.append(f"{i}. *{entry.company_name}* ({entry.company_industry})")

    summary_lines.append("\n✅ Вся информация сохранена в вашем кейсе.")

    await message.reply_text("\n".join(summary_lines), parse_mode=ParseMode.MARKDOWN)

    logger.info(
        "career_intake.completed",
        user_id=state.user_id,
        case_id=state.case_id,
        companies_count=len(state.career_entries),
        continue_main_intake=continue_main_intake,
    )

    # If started from main intake, continue to next block
    if continue_main_intake:
        try:
            from .intake_handlers import continue_intake_after_career

            await continue_intake_after_career(bot_context, update, state.user_id, state.case_id)
        except ImportError as e:
            logger.error("career_intake.continue_import_error", error=str(e))
            await message.reply_text(
                "\n*Следующие шаги:*\n" "• /intake_resume - продолжить анкету",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        # Standalone career intake - show next steps
        await message.reply_text(
            "\n*Следующие шаги:*\n"
            "• /ask - задать вопросы о кейсе\n"
            "• /intake_start - продолжить общую анкету\n"
            "• Загрузить дополнительные документы",
            parse_mode=ParseMode.MARKDOWN,
        )


async def _generate_followup_questions(
    bot_context: BotContext,
    state: CareerIntakeState,
) -> list[str]:
    """Generate contextual follow-up questions using LLM."""
    try:
        entry = state.current_entry
        company_name = entry.get("company_name", "")
        company_type = entry.get("company_type", "")
        company_industry = entry.get("company_industry", "")
        position = entry.get("positions_list", "")
        responsibilities = entry.get("main_responsibilities", "")

        # Skip if not enough context
        if not company_name or not position:
            return []

        # Build prompt
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            company_name=company_name,
            company_type=company_type,
            company_industry=company_industry,
            position=position,
            responsibilities=responsibilities,
            collected_info=json.dumps(entry, ensure_ascii=False, indent=2),
        )

        # Call LLM
        response = await bot_context.mega_agent.router.acomplete(
            messages=[{"role": "user", "content": prompt}],
            model="claude-haiku-4-5-20251215",
            max_tokens=500,
            temperature=0.7,
        )

        # Parse response
        content = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from response
        import re

        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            questions_data = json.loads(json_match.group())
            return [q["question"] for q in questions_data if "question" in q]

    except Exception as e:
        logger.warning("career_intake.followup_generation_error", error=str(e))

    return []


def _phase_name(phase: str) -> str:
    """Get human-readable phase name."""
    names = {
        "company_count": "Количество компаний",
        "company_basics": "Основная информация",
        "positions": "Должности и обязанности",
        "projects": "Проекты",
        "achievements": "Достижения",
        "achievements_government": "Гос. достижения",
        "recommenders": "Рекомендатели",
        "evidence": "Документы",
        "company_summary": "Итог по компании",
    }
    return names.get(phase, phase)


# --- Callback Handler ---


async def handle_career_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callbacks."""
    bot_context = _bot_context(context)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == "career_skip_phase":
        user_id = str(update.effective_user.id)
        active_case_id = await bot_context.get_active_case(update)

        if active_case_id:
            state = await _get_career_state(bot_context, user_id, active_case_id)
            if state:
                await _advance_phase(bot_context, update, state, skip=True)


# --- Export handlers ---


def get_handlers(bot_context: BotContext):
    """Return list of handlers to register."""
    from telegram.ext import CallbackQueryHandler, CommandHandler

    return [
        CommandHandler("career_start", career_start),
        CommandHandler("career_status", career_status),
        CommandHandler("career_cancel", career_cancel),
        CommandHandler("career_skip", career_skip),
        CallbackQueryHandler(handle_career_callback, pattern="^career_"),
    ]
