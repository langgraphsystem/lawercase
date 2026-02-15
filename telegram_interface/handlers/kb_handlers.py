"""Knowledge base handlers for searching and managing reference documents.

Commands:
- /kb_search <query> - Semantic search in knowledge base
- /kb_stats - Show knowledge base statistics
"""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .context import BotContext

logger = structlog.get_logger(__name__)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Get BotContext from application bot_data."""
    return context.application.bot_data["bot_context"]


async def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    """Check if user is authorized."""
    user_id = update.effective_user.id if update.effective_user else None
    if bot_context.is_authorized(user_id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("🚫 Access denied.")
    logger.warning("telegram.kb.unauthorized", user_id=user_id)
    return False


async def kb_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search in knowledge base (reference documents only).

    Usage: /kb_search <query>
    Example: /kb_search EB-1A awards evidence
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.kb_search.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not context.args:
        await message.reply_text(
            "❌ Укажите поисковый запрос.\n\n"
            "Использование: `/kb_search <запрос>`\n"
            "Пример: `/kb_search awards evidence`",
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    logger.info("telegram.kb_search.query", user_id=user_id, query=query)

    await message.reply_text(f"🔍 Поиск в базе знаний: `{query}`\n⏳ Ищу...", parse_mode="Markdown")

    try:
        from core.di.container import get_container

        container = get_container()
        memory = container.get("memory_manager")

        # Use dedicated knowledge base search
        results = await memory.aretrieve_knowledge_base(query=query, topk=5)

        if not results:
            await message.reply_text(
                "📭 Ничего не найдено в базе знаний.\n\n"
                "Загрузите референсные документы через отправку PDF файла "
                'и выбор "📚 Общие знания".'
            )
            logger.info("telegram.kb_search.no_results", user_id=user_id, query=query)
            return

        # Format results (plain text to avoid markdown parsing issues)
        lines = [
            "📚 Результаты поиска в базе знаний:",
            f"Запрос: {query}",
            f"Найдено: {len(results)} документов",
            "",
        ]

        for i, record in enumerate(results, 1):
            # Truncate text for display
            text_preview = record.text[:200] + "..." if len(record.text) > 200 else record.text
            text_preview = text_preview.replace("\n", " ").strip()

            # Get confidence/similarity score
            confidence = record.confidence or 0.0

            # Get tags
            tags = record.tags or []
            tags_str = ", ".join(tags[:3]) if tags else "нет тегов"

            lines.append(f"{i}. [{confidence:.0%} match]")
            lines.append(f"📝 {text_preview}")
            lines.append(f"🏷️ Теги: {tags_str}")
            if record.source:
                source_short = (
                    record.source[:30] + "..." if len(record.source) > 30 else record.source
                )
                lines.append(f"📄 Источник: {source_short}")
            lines.append("")

        response = "\n".join(lines)
        # Telegram message limit is 4096 chars
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (обрезано)"

        await message.reply_text(response, parse_mode=None)
        logger.info(
            "telegram.kb_search.success",
            user_id=user_id,
            query=query,
            results_count=len(results),
        )

    except Exception as e:
        await message.reply_text(f"❌ Ошибка поиска: {e!s}", parse_mode=None)
        try:
            logger.exception("telegram.kb_search.exception", user_id=user_id, error=str(e))
        except Exception:
            logger.error("telegram.kb_search.exception", user_id=user_id, error=str(e))


async def memory_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search ALL semantic memory (KB + RFE + intake + everything).

    Usage: /memory_search <query>
    Example: /memory_search RFE denial reasons
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.memory_search.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    if not context.args:
        await message.reply_text(
            "❌ Укажите поисковый запрос.\n\n"
            "Использование: `/memory_search <запрос>`\n"
            "Пример: `/memory_search RFE denial`\n\n"
            "Эта команда ищет по ВСЕЙ памяти (KB + RFE + intake).",
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    logger.info("telegram.memory_search.query", user_id=user_id, query=query)

    await message.reply_text(
        f"🔍 Поиск по всей памяти: `{query}`\n⏳ Ищу...", parse_mode="Markdown"
    )

    try:
        from core.di.container import get_container

        container = get_container()
        memory = container.get("memory_manager")

        # Search ALL memory without filters
        results = await memory.semantic.aretrieve(
            query=query,
            user_id=None,  # Search across all users
            topk=5,
            filters=None,  # NO filters - search everything
        )

        if not results:
            await message.reply_text(
                "📭 Ничего не найдено в памяти.\n\n"
                "Попробуйте другой запрос или загрузите документы."
            )
            logger.info("telegram.memory_search.no_results", user_id=user_id, query=query)
            return

        # Format results (plain text to avoid markdown parsing issues)
        lines = [
            "🔍 Результаты поиска по всей памяти:",
            f"Запрос: {query}",
            f"Найдено: {len(results)} записей",
            "",
        ]

        for i, record in enumerate(results, 1):
            # Truncate text for display
            text_preview = record.text[:200] + "..." if len(record.text) > 200 else record.text
            text_preview = text_preview.replace("\n", " ").strip()

            # Get confidence/similarity score
            confidence = record.confidence or 0.0

            # Get tags
            tags = record.tags or []
            tags_str = ", ".join(tags[:5]) if tags else "нет тегов"

            lines.append(f"{i}. [{confidence:.0%} match]")
            lines.append(f"📝 {text_preview}")
            lines.append(f"🏷️ Теги: {tags_str}")
            if record.source:
                source_short = (
                    record.source[:40] + "..." if len(record.source) > 40 else record.source
                )
                lines.append(f"📄 Источник: {source_short}")
            lines.append("")

        response = "\n".join(lines)
        # Telegram message limit is 4096 chars
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (обрезано)"

        await message.reply_text(response, parse_mode=None)
        logger.info(
            "telegram.memory_search.success",
            user_id=user_id,
            query=query,
            results_count=len(results),
        )

    except Exception as e:
        await message.reply_text(f"❌ Ошибка поиска: {e!s}", parse_mode=None)
        try:
            logger.exception("telegram.memory_search.exception", user_id=user_id, error=str(e))
        except Exception:
            logger.error("telegram.memory_search.exception", user_id=user_id, error=str(e))


async def memory_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show complete memory statistics with tag breakdown.

    Usage: /memory_stats
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.memory_stats.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    await message.reply_text("📊 Загружаю полную статистику памяти...")

    try:
        from core.di.container import get_container

        container = get_container()
        memory = container.get("memory_manager")

        # Get semantic store for direct stats
        semantic_store = memory.semantic

        # Count total records in semantic_memory
        semantic_count = await semantic_store.acount()

        # Count RFE knowledge records
        rfe_count = await semantic_store.acount_rfe_knowledge()
        rfe_by_criterion = await semantic_store.acount_rfe_by_criterion()

        # Count by different tags
        kb_count = await semantic_store.acount_by_tags(["knowledge_base"])
        case_doc_count = await semantic_store.acount_by_tags(["case_document"])

        # Count other categories
        other_count = semantic_count - kb_count - case_doc_count

        # Total across all tables
        total_count = semantic_count + rfe_count

        # Get all unique sources
        all_sources = await semantic_store.aget_unique_sources()

        # Format response (plain text to avoid markdown parsing issues)
        lines = [
            "📊 Полная статистика памяти:",
            "",
            f"📁 ВСЕГО записей: {total_count}",
            "",
            f"📂 Семантическая память (semantic_memory): {semantic_count}",
            f"   📚 База знаний (knowledge_base): {kb_count}",
            f"   📁 Документы по кейсам: {case_doc_count}",
            f"   📋 Другие (intake и т.д.): {other_count}",
            "",
            f"⚖️ RFE Knowledge база: {rfe_count}",
        ]

        if rfe_by_criterion:
            for crit in rfe_by_criterion[:8]:
                crit_name = crit["criterion"] or "unknown"
                lines.append(f"   • {crit_name}: {crit['count']}")
            lines.append("")

        if all_sources:
            lines.append("📄 Источники документов:")
            for src in all_sources[:10]:
                source_name = src["source"] or "unknown"
                if len(source_name) > 45:
                    source_name = source_name[:42] + "..."
                lines.append(f"   • {source_name}: {src['count']}")
            if len(all_sources) > 10:
                lines.append(f"   ... и ещё {len(all_sources) - 10} источников")
            lines.append("")

        lines.append("💡 Команды поиска:")
        lines.append("   /kb_search - только база знаний")
        lines.append("   /memory_search - ВСЯ память + RFE")

        response = "\n".join(lines)
        await message.reply_text(response, parse_mode=None)

        logger.info(
            "telegram.memory_stats.success",
            user_id=user_id,
            total_count=total_count,
            kb_count=kb_count,
            case_doc_count=case_doc_count,
            other_count=other_count,
            sources_count=len(all_sources),
        )

    except Exception as e:
        await message.reply_text(f"❌ Ошибка: {e!s}", parse_mode=None)
        try:
            logger.exception("telegram.memory_stats.exception", user_id=user_id, error=str(e))
        except Exception:
            logger.error("telegram.memory_stats.exception", user_id=user_id, error=str(e))


async def kb_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show knowledge base statistics.

    Usage: /kb_stats
    """
    user_id = update.effective_user.id if update.effective_user else None
    logger.info("telegram.kb_stats.received", user_id=user_id)

    bot_context = _bot_context(context)
    if not await _is_authorized(bot_context, update):
        return

    message = update.effective_message
    await message.reply_text("📊 Загружаю статистику базы знаний...")

    try:
        from core.di.container import get_container

        container = get_container()
        memory = container.get("memory_manager")

        # Get semantic store for direct stats
        semantic_store = memory.semantic

        # Count total records
        semantic_count = await semantic_store.acount()
        rfe_count = await semantic_store.acount_rfe_knowledge()

        # Count knowledge_base records specifically
        kb_count = await semantic_store.acount_by_tags(["knowledge_base"])

        # Count case documents
        case_doc_count = await semantic_store.acount_by_tags(["case_document"])

        # Get sources for knowledge base documents
        kb_sources = await semantic_store.aget_unique_sources(tags=["knowledge_base"])

        # Format response (plain text to avoid markdown parsing issues)
        lines = [
            "📊 Статистика базы знаний:",
            "",
            f"📚 База знаний (knowledge_base): {kb_count}",
            f"📂 Документы по кейсам: {case_doc_count}",
            f"📋 Другие записи: {semantic_count - kb_count - case_doc_count}",
            f"⚖️ RFE Knowledge: {rfe_count}",
            "",
        ]

        if kb_sources:
            lines.append("📄 Документы в базе знаний:")
            for src in kb_sources[:10]:
                source_name = src["source"] or "unknown"
                if len(source_name) > 40:
                    source_name = source_name[:37] + "..."
                lines.append(f"  • {source_name}: {src['count']} фрагментов")
            lines.append("")

        if kb_count > 0:
            lines.append("✅ База знаний доступна.")
            lines.append("💡 /kb_search - поиск в базе знаний")
            lines.append("💡 /memory_stats - полная статистика")
        else:
            lines.append("⚠️ База знаний пуста.")
            lines.append("")
            lines.append("Загрузите референсные документы:")
            lines.append("1. Отправьте PDF файл")
            lines.append('2. Выберите "📚 Общие знания"')

        response = "\n".join(lines)
        await message.reply_text(response, parse_mode=None)

        logger.info(
            "telegram.kb_stats.success",
            user_id=user_id,
            total_count=semantic_count + rfe_count,
            kb_count=kb_count,
            case_doc_count=case_doc_count,
            sources_count=len(kb_sources),
        )

    except Exception as e:
        await message.reply_text(f"❌ Ошибка: {e!s}", parse_mode=None)
        try:
            logger.exception("telegram.kb_stats.exception", user_id=user_id, error=str(e))
        except Exception:
            logger.error("telegram.kb_stats.exception", user_id=user_id, error=str(e))


def get_handlers(bot_context: BotContext) -> list:
    """Return knowledge-base and memory-related handlers."""
    return [
        CommandHandler("kb_search", kb_search),
        CommandHandler("kb_stats", kb_stats),
        CommandHandler("memory_search", memory_search),
        CommandHandler("memory_stats", memory_stats),
    ]
