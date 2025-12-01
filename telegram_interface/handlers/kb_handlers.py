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

        # Format results
        lines = [
            "📚 **Результаты поиска в базе знаний:**",
            f"Запрос: `{query}`",
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

            lines.append(f"**{i}. [{confidence:.0%} match]**")
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

        await message.reply_text(response, parse_mode="Markdown")
        logger.info(
            "telegram.kb_search.success",
            user_id=user_id,
            query=query,
            results_count=len(results),
        )

    except Exception as e:
        logger.exception("telegram.kb_search.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Ошибка поиска: {e!s}", parse_mode=None)


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
        total_count = await semantic_store.acount()

        # Try to get sample of knowledge base records
        # Use a general query to see what's in KB
        kb_sample = await memory.aretrieve_knowledge_base(query="EB-1A immigration", topk=10)

        # Collect tag statistics from sample
        tag_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        for record in kb_sample:
            for tag in record.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            if record.source:
                source_short = record.source.split("/")[-1][:20]
                source_counts[source_short] = source_counts.get(source_short, 0) + 1

        # Format response
        lines = [
            "📊 **Статистика базы знаний:**",
            "",
            f"📁 Всего записей в namespace: {total_count}",
            f"📚 Выборка KB записей: {len(kb_sample)}",
            "",
        ]

        if tag_counts:
            lines.append("🏷️ **Теги в выборке:**")
            for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  • {tag}: {count}")
            lines.append("")

        if source_counts:
            lines.append("📄 **Источники:**")
            for source, count in sorted(source_counts.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  • {source}: {count}")
            lines.append("")

        if kb_sample:
            lines.append("✅ **База знаний доступна и содержит документы.**")
            lines.append("")
            lines.append("💡 Используйте `/kb_search <запрос>` для поиска.")
        else:
            lines.append("⚠️ **База знаний пуста.**")
            lines.append("")
            lines.append("Загрузите референсные документы:")
            lines.append("1. Отправьте PDF файл")
            lines.append('2. Выберите "📚 Общие знания"')

        response = "\n".join(lines)
        await message.reply_text(response, parse_mode="Markdown")

        logger.info(
            "telegram.kb_stats.success",
            user_id=user_id,
            total_count=total_count,
            kb_sample_count=len(kb_sample),
            tags=list(tag_counts.keys()),
        )

    except Exception as e:
        logger.exception("telegram.kb_stats.exception", user_id=user_id, error=str(e))
        await message.reply_text(f"❌ Ошибка: {e!s}", parse_mode=None)


def get_handlers(bot_context: BotContext) -> list:
    """Return knowledge-base related handlers."""
    return [
        CommandHandler("kb_search", kb_search),
        CommandHandler("kb_stats", kb_stats),
    ]
