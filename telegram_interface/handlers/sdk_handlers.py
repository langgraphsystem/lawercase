"""Handlers that integrate directly with the OpenAI SDK."""

from __future__ import annotations

from collections.abc import Iterable
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import Model
import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .context import BotContext

# CRITICAL: Override system environment variables with .env file
load_dotenv(override=True)

logger = structlog.get_logger(__name__)

_client: AsyncOpenAI | None = None


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    authorized = bot_context.is_authorized(user_id)
    logger.debug("telegram.sdk.auth_check", user_id=user_id, authorized=authorized)
    if not authorized and update.effective_message:
        update.effective_message.reply_text("🚫 Access denied.")
    return authorized


def _get_client() -> AsyncOpenAI:
    """Lazily instantiate an AsyncOpenAI client using env configuration."""

    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    _client = AsyncOpenAI(api_key=api_key)
    return _client


async def _reply(update: Update, text: str) -> None:
    """Reply to a message, splitting long responses to satisfy Telegram limits."""

    message = update.effective_message
    if message is None:
        return

    chunk_size = 3500  # Telegram hard limit is 4096 characters
    chunks: Iterable[str] = (text[i : i + chunk_size] for i in range(0, len(text), chunk_size))
    for chunk in chunks:
        await message.reply_text(chunk)


async def models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available OpenAI models for the current account."""

    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.models.received", user_id=user_id)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.models.unauthorized", user_id=user_id)
        return

    try:
        client = _get_client()
        logger.debug("telegram.models.fetching", user_id=user_id)
        result = await client.models.list()
        models: list[Model] = result.data  # type: ignore[assignment]

        sorted_models = sorted((m.id for m in models if isinstance(m.id, str)), key=str.lower)
        if not sorted_models:
            await _reply(update, "⚠️ No models returned by OpenAI API.")
            return

        header = "🧠 *Available OpenAI models*\n"
        limited = sorted_models[:20]
        body = "\n".join(f"• `{name}`" for name in limited)
        if len(sorted_models) > len(limited):
            body += f"\n…and {len(sorted_models) - len(limited)} more"

        await _reply(update, header + body)
        logger.info("telegram.models.sent", count=len(sorted_models))
    except Exception as exc:  # pragma: no cover - network/runtime
        logger.exception("telegram.models.error", error=str(exc))
        await _reply(update, f"❌ Error loading models: {exc}")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple direct chat interface backed by GPT-5."""

    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.chat.received", user_id=user_id)
    if not _is_authorized(bot_context, update):
        logger.warning("telegram.chat.unauthorized", user_id=user_id)
        return

    if not context.args:
        await _reply(update, "Usage: /chat <your question>")
        logger.warning("telegram.chat.no_args", user_id=user_id)
        return

    prompt = " ".join(context.args)
    logger.info("telegram.chat.processing", user_id=user_id, prompt_length=len(prompt))

    try:
        client = _get_client()
        model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5-mini")
        logger.debug("telegram.chat.request", user_id=user_id, model=model)

        # GPT-5 API call with correct parameters
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are MegaAgent Pro assistant for EB-1A visa questions. Provide clear, concise answers in Russian.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=2000,  # High limit for GPT-5 reasoning tokens
            # NO temperature - GPT-5 only supports default (1)
        )

        if not response.choices:
            await _reply(update, "⚠️ No response from model.")
            logger.warning("telegram.chat.empty_response", user_id=user_id)
            return

        content = response.choices[0].message.content

        if not content:
            await _reply(update, "⚠️ GPT-5 returned empty response.")
            logger.warning(
                "telegram.chat.empty_content", user_id=user_id, usage=str(response.usage)
            )
            return

        await _reply(update, content)

        # Log token usage including reasoning tokens
        usage = response.usage
        reasoning_tokens = (
            getattr(usage.completion_tokens_details, "reasoning_tokens", 0)
            if hasattr(usage, "completion_tokens_details")
            else 0
        )
        logger.info(
            "telegram.chat.sent",
            user_id=user_id,
            response_length=len(content),
            tokens=usage.total_tokens,
            reasoning_tokens=reasoning_tokens,
        )
    except Exception as exc:  # pragma: no cover - network/runtime
        logger.exception("telegram.chat.error", user_id=user_id, error=str(exc))
        await _reply(update, f"❌ OpenAI error: {exc}")


def get_handlers(bot_context: BotContext) -> list[CommandHandler]:
    """Expose Telegram command handlers for SDK utilities."""

    return [
        CommandHandler("models", models),
        CommandHandler("chat", chat),
    ]
