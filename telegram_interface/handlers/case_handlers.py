"""Case-related Telegram handlers."""

from __future__ import annotations

from typing import Any

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from core.groupagents.mega_agent import CommandType, MegaAgentCommand, UserRole
from core.intake.schema import BLOCKS_BY_ID
from core.storage.intake_progress import get_progress

from .context import BotContext

logger = structlog.get_logger(__name__)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _extract_case_payload(
    result: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """
    Normalizes MegaAgent responses by surfacing the actual case payload and ID.

    Returns:
        (result_dict, case_dict, case_id)
    """
    result_dict = result or {}
    case_data = result_dict.get("case")
    if not isinstance(case_data, dict):
        case_result = result_dict.get("case_result")
        if isinstance(case_result, dict):
            nested_case = case_result.get("case")
            if isinstance(nested_case, dict):
                case_data = nested_case
    if not isinstance(case_data, dict):
        case_data = {}

    case_id = result_dict.get("case_id") or case_data.get("case_id")
    return result_dict, case_data, case_id


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("🚫 Access denied.")
    logger.warning("telegram.case.unauthorized", user_id=user_id)
    return False


async def _maybe_offer_resume(
    bot_context: BotContext, update: Update, case_id: str, case_title: str
) -> None:
    """If there is unfinished intake for the case, offer to resume from last step."""

    user = update.effective_user
    user_id = str(user.id) if user else None
    if not user_id:
        return

    try:
        progress = await get_progress(user_id, case_id)
    except Exception as exc:  # pragma: no cover - defensive guard around DB access
        logger.warning(
            "telegram.case_active.progress_lookup_failed",
            user_id=user_id,
            case_id=case_id,
            error=str(exc),
        )
        return

    if not progress or progress.current_block == "intake_complete":
        return

    block = BLOCKS_BY_ID.get(progress.current_block)
    block_title = block.title if block else progress.current_block
    total_questions = len(block.questions) if block else None
    question_progress = f"{progress.current_step + 1}"
    if total_questions:
        question_progress = f"{question_progress}/{total_questions}"

    followup_text = (
        "⏳ Для этого кейса есть незавершённые шаги анкетирования.\n"
        f"Кейс: {case_title}\n"
        f"Блок: {block_title}\n"
        f"Текущий вопрос: {question_progress}\n\n"
        "Продолжить с места остановки? Можно также использовать /intake_status или "
        "/intake_cancel."
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("▶️ Продолжить анкету", callback_data="intake_continue")]]
    )

    await update.effective_message.reply_text(followup_text, reply_markup=keyboard)
    logger.info(
        "telegram.case_active.offer_resume",
        user_id=user_id,
        case_id=case_id,
        block=progress.current_block,
        step=progress.current_step,
    )


async def case_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_get.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.case_get.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        logger.warning("telegram.case_get.no_args", user_id=user_id)
        await message.reply_text("Usage: /case_get <case_id>")
        return

    case_id = context.args[0]
    logger.info("telegram.case_get.processing", user_id=user_id, case_id=case_id)

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": case_id},
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        logger.info(
            "telegram.case_get.command_created", user_id=user_id, command_id=command.command_id
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.case_get.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            result_payload, case_data, normalized_case_id = _extract_case_payload(response.result)
            title = (
                case_data.get("title")
                or result_payload.get("title")
                or result_payload.get("case_title")
                or "(no title)"
            )
            status = (
                case_data.get("status")
                or result_payload.get("status")
                or result_payload.get("case_status")
                or "unknown"
            )
            display_case_id = normalized_case_id or case_id
            await message.reply_text(f"📁 {display_case_id}: {title}\nStatus: {status}")
            # Set as active case after successful retrieval
            await bot_context.set_active_case(update, display_case_id)
            logger.info(
                "telegram.case_get.sent",
                user_id=user_id,
                case_id=display_case_id,
                status=status,
            )
            # Offer to resume intake if there's unfinished progress
            await _maybe_offer_resume(bot_context, update, display_case_id, title)
        else:
            error_msg = response.error or "case not found"
            # Use parse_mode=None to avoid Markdown parsing errors
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error(
                "telegram.case_get.failed", user_id=user_id, case_id=case_id, error=error_msg
            )
    except Exception as e:
        logger.exception(
            "telegram.case_get.exception", user_id=user_id, case_id=case_id, error=str(e)
        )
        # Use parse_mode=None to avoid Markdown parsing errors
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def case_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_create.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.case_create.unauthorized", user_id=user_id)
        return

    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /case_create <title> | optional description")
        return

    raw = " ".join(context.args)
    parts = [part.strip() for part in raw.split("|", 1)]
    title = parts[0]
    description = parts[1] if len(parts) > 1 else None

    try:
        # Prepare case creation payload with required fields
        payload = {
            "title": title,
            "description": description or f"Case: {title}",  # description is required
            "case_type": "immigration",  # default to immigration (most common type)
            "client_id": str(update.effective_user.id),  # use telegram user_id as client_id
        }

        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="create",
            payload=payload,
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)

        if response.success and response.result:
            result_payload, case_data, case_id = _extract_case_payload(response.result)
            reply_case_id = case_id or result_payload.get("case_id")
            if reply_case_id:
                await bot_context.set_active_case(update, reply_case_id)
            case_title = case_data.get("title") or result_payload.get("title") or title

            # Escape special characters for MarkdownV2
            case_title_escaped = (
                case_title.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("[", "\\[")
                .replace("]", "\\]")
                .replace("(", "\\(")
                .replace(")", "\\)")
                .replace("~", "\\~")
                .replace("`", "\\`")
                .replace(">", "\\>")
                .replace("#", "\\#")
                .replace("+", "\\+")
                .replace("-", "\\-")
                .replace("=", "\\=")
                .replace("|", "\\|")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace(".", "\\.")
                .replace("!", "\\!")
            )
            case_id_escaped = (reply_case_id or "unknown").replace("-", "\\-")

            # Enhanced message with intake guidance and inline buttons
            success_message = (
                f"✅ *Кейс создан: {case_title_escaped}*\n"
                f"ID: `{case_id_escaped}`\n\n"
                f"Этот кейс теперь активен\\. Давайте соберём информацию для построения сильной петиции\\.\n\n"
                f"*Что дальше?*\n"
                f"Рекомендую пройти анкетирование — это поможет мне лучше понять ваши достижения и цели\\."
            )

            # Create inline keyboard with action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🧾 Начать анкету", callback_data="case_start_intake"),
                    InlineKeyboardButton("⏳ Потом", callback_data="case_later"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                success_message, parse_mode="MarkdownV2", reply_markup=reply_markup
            )
            logger.info("telegram.case_create.success", user_id=user_id, case_id=reply_case_id)
        else:
            error_msg = response.error or "case creation failed"
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error("telegram.case_create.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.case_create.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def case_active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_active.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    active_case = await bot_context.get_active_case(update)
    if not active_case:
        await message.reply_text("ℹ️ No active case. Use /case_create or /case_get to select one.")
        return

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": active_case},
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        if response.success and response.result:
            result_payload, case_data, case_id = _extract_case_payload(response.result)
            case_id_display = case_id or active_case
            case_title = case_data.get("title") or result_payload.get("title") or "(no title)"
            case_status = case_data.get("status") or result_payload.get("status") or "unknown"
            await message.reply_text(
                f"📌 Active case: {case_id_display}\nTitle: {case_title}\nStatus: {case_status}"
            )
            await _maybe_offer_resume(bot_context, update, case_id_display, case_title)
        else:
            await message.reply_text(
                f"⚠️ Active case id {active_case} not found (maybe deleted).",
                parse_mode=None,
            )
    except Exception as e:
        logger.exception("telegram.case_active.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def case_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all user's cases with pagination."""
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.case_list.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.case_list.unauthorized", user_id=user_id)
        return

    message = update.effective_message

    # Parse optional page argument (default: page 1)
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
            page = max(page, 1)
        except ValueError:
            await message.reply_text("Usage: /case_list [page_number]")
            return

    # Calculate offset (10 cases per page)
    limit = 10
    offset = (page - 1) * limit

    try:
        command = MegaAgentCommand(
            user_id=str(update.effective_user.id),
            command_type=CommandType.CASE,
            action="search",
            payload={"limit": limit, "offset": offset},
            context={"thread_id": bot_context.thread_id_for_update(update)},
        )
        logger.info(
            "telegram.case_list.command_created",
            user_id=user_id,
            page=page,
            limit=limit,
            offset=offset,
        )

        response = await bot_context.mega_agent.handle_command(command, user_role=UserRole.LAWYER)
        logger.info(
            "telegram.case_list.response_received", user_id=user_id, success=response.success
        )

        if response.success and response.result:
            case_result = response.result.get("case_result", {})
            cases = case_result.get("cases", [])
            total_count = case_result.get("count", 0)

            if not cases:
                if page == 1:
                    await message.reply_text(
                        "📁 У вас пока нет кейсов.\n\n"
                        "Создайте первый кейс с помощью:\n"
                        "/case_create <название> | <описание>"
                    )
                else:
                    await message.reply_text(
                        f"📁 Страница {page} пуста. Используйте /case_list для первой страницы."
                    )
                logger.info("telegram.case_list.no_cases", user_id=user_id, page=page)
                return

            # Format case list
            text = f"📁 *Ваши кейсы* \\(страница {page}\\):\n\n"

            for idx, case in enumerate(cases, start=offset + 1):
                status = case.get("status", "unknown")
                status_emoji = {
                    "draft": "📝",
                    "in_progress": "⏳",
                    "review": "🔍",
                    "submitted": "✅",
                    "approved": "🎉",
                    "rejected": "❌",
                    "archived": "📦",
                }.get(status, "📄")

                title = case.get("title", "(no title)")
                case_id = case.get("case_id", "unknown")

                # Escape special characters for MarkdownV2
                title_escaped = (
                    title.replace("_", "\\_")
                    .replace("*", "\\*")
                    .replace("[", "\\[")
                    .replace("]", "\\]")
                    .replace("(", "\\(")
                    .replace(")", "\\)")
                    .replace("~", "\\~")
                    .replace("`", "\\`")
                    .replace(">", "\\>")
                    .replace("#", "\\#")
                    .replace("+", "\\+")
                    .replace("-", "\\-")
                    .replace("=", "\\=")
                    .replace("|", "\\|")
                    .replace("{", "\\{")
                    .replace("}", "\\}")
                    .replace(".", "\\.")
                    .replace("!", "\\!")
                )
                status_escaped = status.replace("_", "\\_")
                case_id_escaped = case_id.replace("-", "\\-")

                text += f"{idx}\\. {status_emoji} *{title_escaped}*\n"
                text += f"   ID: `{case_id_escaped}`\n"
                text += f"   Статус: {status_escaped}\n\n"

            # Add navigation hints
            text += "\n💡 *Навигация:*\n"
            text += "• `/case_get <case_id>` — открыть кейс\n"
            if total_count > limit:
                next_page = page + 1
                text += f"• `/case_list {next_page}` — следующая страница\n"
            if page > 1:
                prev_page = page - 1
                text += f"• `/case_list {prev_page}` — предыдущая страница"

            await message.reply_text(text, parse_mode="MarkdownV2")
            logger.info(
                "telegram.case_list.sent",
                user_id=user_id,
                page=page,
                count=total_count,
            )
        else:
            error_msg = response.error or "Failed to retrieve cases"
            await message.reply_text(f"❌ Error: {error_msg}", parse_mode=None)
            logger.error("telegram.case_list.failed", user_id=user_id, error=error_msg)
    except Exception as e:
        logger.exception("telegram.case_list.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Exception: {e!s}", parse_mode=None)


async def eb1_potential(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Batch EB-1A POTENTIAL assessment from intake data (single LLM call).

    This provides a preliminary assessment based on questionnaire answers,
    NOT an evaluation of actual documents.

    Usage:
        /eb1_potential [case_id]   - Assess potential for specific case or active case
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.eb1_potential.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.eb1_potential.unauthorized", user_id=user_id)
        return

    message = update.effective_message

    # Get case_id from args or active case
    if context.args:
        case_id = context.args[0]
    else:
        case_id = await bot_context.get_active_case(update)
        if not case_id:
            await message.reply_text(
                "❌ Укажите case_id или выберите активный кейс.\n\n"
                "Использование:\n"
                "• `/eb1_potential <case_id>` — оценка потенциала кейса\n"
                "• `/case_get <case_id>` — выбрать активный кейс",
                parse_mode="Markdown",
            )
            return

    await message.reply_text(
        f"🔍 Оцениваю потенциал EB-1A для кейса `{case_id[:8]}...`\n\n"
        "⏳ Анализ одним запросом (batch)...",
        parse_mode="Markdown",
    )

    try:
        from core.di.container import get_container
        from core.groupagents.eb1a_evidence_analyzer import \
            analyze_intake_potential_batch

        container = get_container()
        memory = container.get("memory_manager")

        # Single LLM call batch analysis
        result = await analyze_intake_potential_batch(case_id, str(user_id), memory)

        # Format response
        response = _format_eb1a_potential(result, case_id)
        await message.reply_text(response, parse_mode="HTML")

        logger.info(
            "telegram.eb1_potential.success",
            user_id=user_id,
            case_id=case_id,
            potential_score=result.overall_potential_score,
            potential_criteria=result.potential_criteria_count,
            llm_calls=result.llm_call_count,
            warnings=len(getattr(result, "warnings", []) or []),
        )

    except Exception as e:
        logger.exception(
            "telegram.eb1_potential.exception",
            user_id=user_id,
            case_id=case_id,
            error=str(e),
        )
        await message.reply_text(f"❌ Ошибка анализа: {e!s}", parse_mode=None)


def _format_eb1a_potential(result: Any, case_id: str) -> str:
    """Format IntakePotentialResult for Telegram."""
    # Emoji based on risk level
    risk_emoji = {
        "low": "🟢",
        "moderate": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }
    risk_display = risk_emoji.get(result.risk_level, "⚪")

    lines = [
        "📊 <b>EB-1A Potential Assessment</b>",
        f"Case: <code>{case_id[:8]}...</code>",
        "<i>(Based on intake questionnaire, 1 LLM call)</i>",
        "",
        f"🎯 <b>Potential Score:</b> {result.overall_potential_score:.0f}/100",
        f"📈 <b>Criteria with potential:</b> {result.potential_criteria_count}/10",
        f"{risk_display} <b>Risk Level:</b> {result.risk_level.upper()}",
        "",
    ]

    # Overall assessment
    if result.overall_assessment:
        lines.append(f"💡 <b>Summary:</b> {result.overall_assessment}")
        lines.append("")

    # Strongest criteria
    if result.strongest_criteria:
        lines.append("<b>💪 Strongest Criteria:</b>")
        for criterion in result.strongest_criteria[:3]:
            lines.append(f"  ✅ {criterion}")
        lines.append("")

    # Weakest criteria
    if result.weakest_criteria:
        lines.append("<b>⚠️ Weakest Criteria:</b>")
        for criterion in result.weakest_criteria[:3]:
            lines.append(f"  ❗ {criterion}")
            # Inline advice/missing info if available
            assessments = getattr(result, "criteria_assessments", {}) or {}
            assessment = assessments.get(criterion, {})
            advice = assessment.get("advice")
            missing = assessment.get("missing_info") or []
            if missing:
                lines.append(f"     ⏳ Missing: {', '.join([str(m) for m in missing[:2]])}")
            if advice:
                lines.append(f"     💡 Advice: {advice}")
        lines.append("")

    # Criteria assessments
    if result.criteria_assessments:
        lines.append("<b>📋 Criteria Breakdown:</b>")
        for crit_name, assessment in list(result.criteria_assessments.items())[:6]:
            score = assessment.get("potential_score", 0)
            has_potential = assessment.get("has_potential", False)
            strength = assessment.get("evidence_strength")
            status = "✅" if has_potential else "❌"
            suffix = f" ({strength})" if strength else ""
            lines.append(f"  {status} {crit_name}: {score}%{suffix}")
        lines.append("")

    # Priority actions
    if result.priority_actions:
        lines.append("<b>📝 Priority Actions:</b>")
        for action in result.priority_actions[:3]:
            lines.append(f"  • {action}")
        lines.append("")

    # Recommendation
    if result.recommendation:
        lines.append(f"🎯 <b>Next Steps:</b> {result.recommendation}")

    # Warnings surfaced to user
    if getattr(result, "warnings", None):
        lines.append("")
        lines.append("<b>⚠️ Warnings:</b>")
        for warning in result.warnings[:3]:
            lines.append(f"  • {warning}")
    elif getattr(result, "llm_call_count", 1) == 0:
        lines.append("")
        lines.append("<b>⚠️ Warnings:</b>")
        lines.append("  • Used heuristic fallback because LLM analysis was unavailable.")

    return "\n".join(lines)


async def eb1_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Analyze EB-1A criteria satisfaction for a case.

    Usage:
        /eb1_analyze [case_id]   - Analyze specific case or active case
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.eb1_analyze.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        logger.warning("telegram.eb1_analyze.unauthorized", user_id=user_id)
        return

    message = update.effective_message

    # Get case_id from args or active case
    if context.args:
        case_id = context.args[0]
    else:
        case_id = await bot_context.get_active_case(update)
        if not case_id:
            await message.reply_text(
                "❌ Укажите case_id или выберите активный кейс.\n\n"
                "Использование:\n"
                "• `/eb1_analyze <case_id>` — анализ конкретного кейса\n"
                "• `/case_get <case_id>` — выбрать активный кейс",
                parse_mode="Markdown",
            )
            return

    await message.reply_text(
        f"🔍 Анализирую критерии EB-1A для кейса `{case_id[:8]}...`\n\n"
        "Это может занять несколько секунд...",
        parse_mode="Markdown",
    )

    try:
        from core.di.container import get_container
        from core.groupagents.eb1a_evidence_analyzer import \
            analyze_intake_for_eb1a

        container = get_container()
        memory = container.get("memory_manager")

        analysis = await analyze_intake_for_eb1a(case_id, str(user_id), memory)

        # Format response
        response = _format_eb1a_analysis(analysis, case_id)
        await message.reply_text(response, parse_mode="HTML")

        logger.info(
            "telegram.eb1_analyze.success",
            user_id=user_id,
            case_id=case_id,
            overall_score=analysis.overall_score,
            satisfied_criteria=analysis.satisfied_criteria_count,
        )

    except Exception as e:
        logger.exception(
            "telegram.eb1_analyze.exception",
            user_id=user_id,
            case_id=case_id,
            error=str(e),
        )
        await message.reply_text(f"❌ Ошибка анализа: {e!s}", parse_mode=None)


def _format_eb1a_analysis(analysis: Any, case_id: str) -> str:
    """Format CaseStrengthAnalysis for Telegram."""
    # Emoji based on risk level
    risk_emoji = {
        "low": "🟢",
        "moderate": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }
    risk_display = risk_emoji.get(analysis.risk_level.value, "⚪")

    lines = [
        "📊 <b>EB-1A Analysis</b>",
        f"Case: <code>{case_id[:8]}...</code>",
        "",
        f"🎯 <b>Overall Score:</b> {analysis.overall_score:.0f}/100",
        f"📈 <b>Approval Probability:</b> {analysis.approval_probability:.0%}",
        f"{risk_display} <b>Risk Level:</b> {analysis.risk_level.value.upper()}",
        "",
        f"✅ <b>Criteria Met:</b> {analysis.satisfied_criteria_count}/10",
    ]

    # Minimum criteria check
    if analysis.meets_minimum_criteria:
        lines.append("✅ <b>Minimum 3 criteria:</b> MET")
    else:
        lines.append("❌ <b>Minimum 3 criteria:</b> NOT MET")

    # Criterion evaluations (if available)
    if analysis.criterion_evaluations:
        lines.append("")
        lines.append("<b>📋 Criteria Breakdown:</b>")
        for criterion, evaluation in analysis.criterion_evaluations.items():
            status = "✅" if evaluation.is_satisfied else "❌"
            score = evaluation.strength_score
            criterion_name = (
                criterion.value.split("_", 1)[1].upper()
                if "_" in criterion.value
                else criterion.value
            )
            lines.append(f"  {status} {criterion_name}: {score:.0f}%")

    # Strengths
    if analysis.strengths:
        lines.append("")
        lines.append("<b>💪 Strengths:</b>")
        for strength in analysis.strengths[:3]:
            lines.append(f"  • {strength}")

    # Priority recommendations
    if analysis.priority_recommendations:
        lines.append("")
        lines.append("<b>📝 Recommendations:</b>")
        for rec in analysis.priority_recommendations[:3]:
            lines.append(f"  • {rec}")

    # Time estimate
    if analysis.estimated_days_to_ready:
        lines.append("")
        lines.append(f"⏱️ <b>Estimated time to filing:</b> ~{analysis.estimated_days_to_ready} days")

    return "\n".join(lines)


async def handle_case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline buttons in case messages."""
    bot_context = _bot_context(context)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if not await _is_authorized(bot_context, update):
        return

    user_id = update.effective_user.id if update.effective_user else None
    data = query.data

    if data == "case_start_intake":
        # User wants to start intake questionnaire
        logger.info("telegram.case_callback.start_intake", user_id=user_id)
        await query.message.reply_text(
            "🚀 Отлично! Запускаю анкетирование...\n\n" "Используйте /intake_start для начала."
        )
        # Automatically trigger intake_start
        from .intake_handlers import intake_start

        await intake_start(update, context)

    elif data == "case_later":
        # User wants to postpone intake
        logger.info("telegram.case_callback.later", user_id=user_id)
        await query.message.reply_text(
            "👌 Хорошо, вы можете начать анкетирование позже.\n\n"
            "Когда будете готовы, используйте /intake_start\n"
            "Или просто задайте мне вопрос с помощью /ask"
        )


def get_handlers(bot_context: BotContext):
    return [
        CommandHandler("case_create", case_create),
        CommandHandler("case_get", case_get),
        CommandHandler("case_active", case_active),
        CommandHandler("case_list", case_list),
        CommandHandler("eb1_analyze", eb1_analyze),
        CommandHandler("eb1_potential", eb1_potential),  # Batch single-call analysis
        CallbackQueryHandler(handle_case_callback, pattern="^case_"),
    ]
