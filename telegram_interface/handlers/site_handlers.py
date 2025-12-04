"""Handlers for case site generation via Telegram bot."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .context import BotContext

logger = structlog.get_logger(__name__)


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Get BotContext from application bot_data."""
    return context.application.bot_data["bot_context"]


async def generate_site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and publish a case site.

    Usage: /generate_site [case_id]
    If no case_id provided, uses the active case.
    """
    bot_ctx = _bot_context(context)
    user = update.effective_user
    message = update.effective_message

    if not message:
        return

    # Get case_id from args or active case
    case_id = None
    if context.args:
        case_id = context.args[0]
    else:
        case_id = await bot_ctx.get_active_case(update)

    if not case_id:
        await message.reply_text(
            "❌ Кейс не указан.\n\n"
            "Использование: /generate_site [case_id]\n"
            "Или сначала выберите активный кейс: /case_select"
        )
        return

    await message.reply_text(f"🔄 Генерирую сайт для кейса {case_id[:8]}...")

    try:
        # Get case data
        from core.groupagents.mega_agent import (CommandType, MegaAgentCommand,
                                                 UserRole)

        command = MegaAgentCommand(
            user_id=str(user.id),
            command_type=CommandType.CASE,
            action="get",
            payload={"case_id": case_id},
        )
        response = await bot_ctx.mega_agent.handle_command(command, user_role=UserRole.LAWYER)

        if not response.success:
            await message.reply_text(f"❌ Кейс не найден: {case_id}")
            return

        case_data = response.data.get("case", {})

        # Prepare data for site generation
        user_data = {
            "full_name": case_data.get("title", "Client Name"),
            "email": f"user_{user.id}@case.local",
        }

        site_case_data = {
            "field": case_data.get("category", "EB-1A"),
            "criteria": case_data.get("criteria", []),
            "status": case_data.get("status", "active"),
        }

        # Generate the site
        from core.services.case_site_generator import CaseSiteGenerator

        generator = CaseSiteGenerator()
        site_path = generator.generate_site(case_id, site_case_data, user_data)

        # Upload to Supabase Storage
        site_url = await _upload_site_to_storage(case_id, site_path)

        if site_url:
            await message.reply_text(
                f"✅ Сайт кейса сгенерирован!\n\n"
                f"🌐 **URL:** {site_url}\n\n"
                f"📊 Страницы:\n"
                f"• Dashboard - обзор кейса\n"
                f"• USCIS Forms - формы\n"
                f"• Petition - черновик петиции\n"
                f"• Exhibits - документы",
                parse_mode="Markdown",
            )
        else:
            await message.reply_text(
                f"✅ Сайт сгенерирован локально: {site_path}\n\n" "⚠️ Не удалось загрузить в облако."
            )

        logger.info(
            "site.generated",
            case_id=case_id,
            user_id=user.id,
            site_url=site_url,
        )

    except Exception as e:
        logger.exception("site.generation_failed", error=str(e), case_id=case_id)
        await message.reply_text(f"❌ Ошибка генерации сайта: {e}")


async def _upload_site_to_storage(case_id: str, site_path: str) -> str | None:
    """Upload generated site to Supabase Storage.

    Args:
        case_id: Case identifier
        site_path: Local path to generated site

    Returns:
        Public URL of the uploaded site or None if failed
    """
    try:
        from pathlib import Path

        from supabase import create_client

        from config.settings import get_settings

        settings = get_settings()
        client = create_client(
            settings.supabase_url,
            settings.supabase_service_key or settings.supabase_anon_key,
        )

        site_dir = Path(site_path)
        bucket_name = "case-sites"
        uploaded_files = []

        # Upload all HTML files
        for html_file in site_dir.rglob("*.html"):
            relative_path = html_file.relative_to(site_dir)
            storage_path = f"{case_id}/{relative_path}"

            content = html_file.read_bytes()

            try:
                client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=content,
                    file_options={
                        "content-type": "text/html",
                        "x-upsert": "true",
                    },
                )
                uploaded_files.append(storage_path)
            except Exception as e:
                logger.warning(f"Failed to upload {storage_path}: {e}")

        if uploaded_files:
            # Return URL to index.html
            base_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket_name}"
            return f"{base_url}/{case_id}/index.html"

    except Exception as e:
        logger.warning("site.upload_failed", error=str(e))

    return None


async def site_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check status of generated sites.

    Usage: /site_status [case_id]
    """
    bot_ctx = _bot_context(context)
    message = update.effective_message

    if not message:
        return

    case_id = None
    if context.args:
        case_id = context.args[0]
    else:
        case_id = await bot_ctx.get_active_case(update)

    if not case_id:
        await message.reply_text("❌ Укажите case_id или выберите активный кейс.")
        return

    try:
        from pathlib import Path

        from config.settings import get_settings

        settings = get_settings()

        # Check local
        local_path = Path("sites") / case_id
        local_exists = local_path.exists()

        # Check Supabase
        supabase_url = None
        try:
            from supabase import create_client

            client = create_client(
                settings.supabase_url,
                settings.supabase_service_key or settings.supabase_anon_key,
            )

            # Try to get file info
            bucket_name = "case-sites"
            response = client.storage.from_(bucket_name).list(case_id)
            if response:
                base_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket_name}"
                supabase_url = f"{base_url}/{case_id}/index.html"
        except Exception:  # nosec B110 - intentional: check is non-critical
            pass

        status_lines = [f"📊 **Статус сайта для кейса {case_id[:8]}...**\n"]

        if local_exists:
            status_lines.append(f"✅ Локально: {local_path}")
        else:
            status_lines.append("❌ Локально: не найден")

        if supabase_url:
            status_lines.append(f"✅ Облако: {supabase_url}")
        else:
            status_lines.append("❌ Облако: не загружен")

        if not local_exists and not supabase_url:
            status_lines.append("\n💡 Сгенерируйте сайт: /generate_site")

        await message.reply_text("\n".join(status_lines), parse_mode="Markdown")

    except Exception as e:
        logger.exception("site.status_failed", error=str(e))
        await message.reply_text(f"❌ Ошибка: {e}")


def get_handlers(bot_context: BotContext) -> list:
    """Get site generation handlers.

    Args:
        bot_context: Bot context

    Returns:
        List of Telegram handlers
    """
    return [
        CommandHandler("generate_site", generate_site),
        CommandHandler("site_status", site_status),
    ]
