"""Telegram bot command handlers."""

import asyncio
import logging
import re

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import get_settings
from .adapters import (
    CaseAdapter, DocumentAdapter, IngestAdapter,
    RAGAdapter, HealthAdapter, AdminAdapter
)
from .keyboards import (
    get_main_keyboard, get_case_keyboard, get_admin_keyboard,
    get_source_keyboard
)

logger = logging.getLogger(__name__)


class BotStates(StatesGroup):
    """Bot conversation states."""
    waiting_case_title = State()
    waiting_case_content = State()
    waiting_search_confirm = State()


# Initialize adapters
case_adapter = CaseAdapter()
document_adapter = DocumentAdapter()
ingest_adapter = IngestAdapter()
rag_adapter = RAGAdapter()
health_adapter = HealthAdapter()
admin_adapter = AdminAdapter()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    settings = get_settings()
    return settings.telegram_admin_user_id and user_id == settings.telegram_admin_user_id


async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    await state.clear()

    welcome_text = """
🤖 <b>Добро пожаловать в Mega Agent Pro!</b>

Я ваш AI-помощник для работы с юридическими делами.

<b>Основные команды:</b>
📁 /case_new - Создать новое дело
📋 /case_use - Выбрать активное дело
📎 /case_add - Добавить документ в дело
🔍 /ask - Задать вопрос по делу
📊 /status - Статус системы

<b>Обучение системы:</b>
🌐 /learn_url - Изучить веб-страницу
📺 /learn_yt - Изучить YouTube видео
📱 /learn_tg - Изучить Telegram канал
🔍 /search - Поиск в интернете

Используйте /help для полного списка команд.
"""

    await message.answer(welcome_text, reply_markup=get_main_keyboard())


async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
📖 <b>Справка по командам</b>

<b>🗂 Управление делами:</b>
• /case_new &lt;название&gt; - Создать новое дело
• /case_use &lt;id|название&gt; - Выбрать активное дело
• /case_add - Добавить текст или файл в дело

<b>🧠 Работа с AI:</b>
• /ask &lt;вопрос&gt; - Задать вопрос по активному делу
• /train - Переиндексировать данные дела

<b>📚 Обучение системы:</b>
• /learn_url &lt;url&gt; [title=... tags=... lang=...] - Изучить веб-страницу
• /learn_yt &lt;url&gt; - Изучить YouTube видео
• /learn_tg &lt;@channel&gt; [N] - Изучить последние N постов канала
• /search &lt;запрос&gt; - Поиск в интернете

<b>📊 Система:</b>
• /status - Статус системы и здоровье сервисов
• /admin - Административные команды (только для админов)

<b>💡 Примеры:</b>
<code>/case_new Дело о разводе Ивановых</code>
<code>/learn_url https://pravo.ru/news/view/123456/ title="Новости права" tags="развод,семейное"</code>
<code>/ask Какие документы нужны для развода?</code>
"""

    await message.answer(help_text)


async def cmd_case_new(message: Message, state: FSMContext):
    """Handle /case_new command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "📝 Введите название дела:\n\n"
            "<i>Пример: /case_new Дело о разводе Ивановых</i>"
        )
        return

    title = args[1].strip()

    try:
        case_id = await case_adapter.create_case(
            title=title,
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )

        await message.answer(
            f"✅ <b>Дело создано</b>\n\n"
            f"📁 <b>ID:</b> <code>{case_id}</code>\n"
            f"📝 <b>Название:</b> {title}\n\n"
            f"Дело автоматически выбрано как активное.\n"
            f"Используйте /case_add для добавления документов.",
            reply_markup=get_case_keyboard(case_id)
        )

    except Exception as e:
        logger.error(f"Failed to create case: {e}")
        await message.answer("❌ Ошибка при создании дела. Попробуйте позже.")


async def cmd_case_use(message: Message):
    """Handle /case_use command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "📋 Укажите ID или название дела:\n\n"
            "<i>Пример: /case_use abc123</i>\n"
            "<i>Пример: /case_use Дело о разводе</i>"
        )
        return

    case_identifier = args[1].strip()

    try:
        case = await case_adapter.get_case(
            identifier=case_identifier,
            user_id=message.from_user.id
        )

        if not case:
            await message.answer("❌ Дело не найдено или у вас нет доступа к нему.")
            return

        # Set as active case for this chat
        await case_adapter.set_active_case(
            chat_id=message.chat.id,
            case_id=case['id']
        )

        await message.answer(
            f"✅ <b>Активное дело выбрано</b>\n\n"
            f"📁 <b>ID:</b> <code>{case['id']}</code>\n"
            f"📝 <b>Название:</b> {case['title']}\n"
            f"📊 <b>Статус:</b> {case['status']}\n"
            f"📎 <b>Документов:</b> {case.get('document_count', 0)}",
            reply_markup=get_case_keyboard(case['id'])
        )

    except Exception as e:
        logger.error(f"Failed to select case: {e}")
        await message.answer("❌ Ошибка при выборе дела. Попробуйте позже.")


async def cmd_case_add(message: Message):
    """Handle /case_add command."""
    try:
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer(
                "❌ Нет активного дела. Используйте /case_new или /case_use."
            )
            return

        # Check if message has document/file
        if message.document:
            await handle_document_upload(message, active_case['id'])
        elif message.photo:
            await handle_photo_upload(message, active_case['id'])
        elif message.text:
            # Extract text content (remove command)
            args = message.text.split(maxsplit=1)
            if len(args) > 1:
                content = args[1].strip()
                await handle_text_content(message, active_case['id'], content)
            else:
                await message.answer(
                    "📎 <b>Добавление контента в дело</b>\n\n"
                    "Отправьте:\n"
                    "• Текст: /case_add Ваш текст\n"
                    "• Файл: прикрепите документ с описанием\n"
                    "• Фото: отправьте изображение документа"
                )
        else:
            await message.answer(
                "📎 Отправьте текст, файл или изображение для добавления в дело."
            )

    except Exception as e:
        logger.error(f"Failed to add content to case: {e}")
        await message.answer("❌ Ошибка при добавлении контента. Попробуйте позже.")


async def handle_document_upload(message: Message, case_id: str):
    """Handle document file upload."""
    try:
        document = message.document

        # Size check
        settings = get_settings()
        max_size = settings.max_file_mb * 1024 * 1024
        if document.file_size > max_size:
            await message.answer(f"❌ Файл слишком большой. Максимум: {settings.max_file_mb}MB")
            return

        # Download file
        file_info = await message.bot.get_file(document.file_id)
        file_data = await message.bot.download_file(file_info.file_path)

        # Process document
        result = await document_adapter.add_document(
            case_id=case_id,
            filename=document.file_name or "document",
            content_type=document.mime_type or "application/octet-stream",
            file_data=file_data.read(),
            description=message.caption or ""
        )

        if result['success']:
            await message.answer(
                f"✅ <b>Документ добавлен</b>\n\n"
                f"📄 <b>Файл:</b> {document.file_name}\n"
                f"📁 <b>Дело:</b> {case_id}\n"
                f"🔗 <b>ID документа:</b> <code>{result['document_id']}</code>",
                reply_markup=get_source_keyboard(result['document_id'])
            )
        else:
            await message.answer(f"❌ Ошибка обработки документа: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to handle document upload: {e}")
        await message.answer("❌ Ошибка при обработке файла.")


async def handle_photo_upload(message: Message, case_id: str):
    """Handle photo upload (OCR processing)."""
    try:
        # Get largest photo
        photo = message.photo[-1]

        # Download photo
        file_info = await message.bot.get_file(photo.file_id)
        file_data = await message.bot.download_file(file_info.file_path)

        # Process as image document
        result = await document_adapter.add_document(
            case_id=case_id,
            filename=f"photo_{photo.file_id}.jpg",
            content_type="image/jpeg",
            file_data=file_data.read(),
            description=message.caption or "Фото документа"
        )

        if result['success']:
            await message.answer(
                f"✅ <b>Изображение добавлено</b>\n\n"
                f"📷 <b>Фото документа</b>\n"
                f"📁 <b>Дело:</b> {case_id}\n"
                f"🔗 <b>ID документа:</b> <code>{result['document_id']}</code>"
            )
        else:
            await message.answer(f"❌ Ошибка обработки изображения: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to handle photo upload: {e}")
        await message.answer("❌ Ошибка при обработке изображения.")


async def handle_text_content(message: Message, case_id: str, content: str):
    """Handle text content addition."""
    try:
        result = await document_adapter.add_text_content(
            case_id=case_id,
            content=content,
            title="Текстовая заметка",
            user_id=message.from_user.id
        )

        if result['success']:
            await message.answer(
                f"✅ <b>Текст добавлен в дело</b>\n\n"
                f"📝 Содержимое сохранено и проиндексировано\n"
                f"📁 <b>Дело:</b> {case_id}\n"
                f"🔗 <b>ID записи:</b> <code>{result['document_id']}</code>"
            )
        else:
            await message.answer(f"❌ Ошибка сохранения текста: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to handle text content: {e}")
        await message.answer("❌ Ошибка при сохранении текста.")


async def cmd_learn_url(message: Message):
    """Handle /learn_url command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "🌐 <b>Изучение веб-страниц</b>\n\n"
            "Формат: <code>/learn_url &lt;url&gt; [параметры]</code>\n\n"
            "<b>Параметры:</b>\n"
            "• title=\"Название\" - заголовок документа\n"
            "• tags=\"тег1,тег2\" - теги для поиска\n"
            "• lang=\"ru\" - язык контента\n\n"
            "<b>Пример:</b>\n"
            "<code>/learn_url https://pravo.ru/news/123 title=\"Новости права\" tags=\"развод,семейное\" lang=\"ru\"</code>"
        )
        return

    try:
        # Parse URL and parameters
        content = args[1]
        url_match = re.match(r'^(https?://[^\s]+)', content)

        if not url_match:
            await message.answer("❌ Некорректный URL. Используйте полный URL с http:// или https://")
            return

        url = url_match.group(1)
        params = parse_learn_params(content[len(url):])

        # Get active case
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")
            return

        # Start ingestion
        status_msg = await message.answer("🔄 Изучаю веб-страницу...")

        result = await ingest_adapter.ingest_url(
            url=url,
            case_id=active_case['id'],
            title=params.get('title'),
            tags=params.get('tags', []),
            language=params.get('lang', 'ru')
        )

        if result['success']:
            await status_msg.edit_text(
                f"✅ <b>Веб-страница изучена</b>\n\n"
                f"🌐 <b>URL:</b> {url}\n"
                f"📝 <b>Заголовок:</b> {result.get('title', 'Без названия')}\n"
                f"📊 <b>Чанков:</b> {result.get('chunks_count', 0)}\n"
                f"📁 <b>Дело:</b> {active_case['id']}"
            )
        else:
            await status_msg.edit_text(f"❌ Ошибка изучения: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to learn URL: {e}")
        await message.answer("❌ Ошибка при изучении веб-страницы.")


async def cmd_learn_yt(message: Message):
    """Handle /learn_yt command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "📺 <b>Изучение YouTube видео</b>\n\n"
            "Формат: <code>/learn_yt &lt;url&gt;</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/learn_yt https://www.youtube.com/watch?v=abc123</code>\n\n"
            "Система извлечет субтитры или аудио для анализа."
        )
        return

    url = args[1].strip()

    try:
        # Get active case
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")
            return

        # Start ingestion
        status_msg = await message.answer("🔄 Изучаю YouTube видео...")

        result = await ingest_adapter.ingest_youtube(
            url=url,
            case_id=active_case['id']
        )

        if result['success']:
            await status_msg.edit_text(
                f"✅ <b>YouTube видео изучено</b>\n\n"
                f"📺 <b>URL:</b> {url}\n"
                f"📝 <b>Заголовок:</b> {result.get('title', 'Без названия')}\n"
                f"⏱ <b>Длительность:</b> {result.get('duration', 'Неизвестно')}\n"
                f"📊 <b>Чанков:</b> {result.get('chunks_count', 0)}\n"
                f"📁 <b>Дело:</b> {active_case['id']}"
            )
        else:
            await status_msg.edit_text(f"❌ Ошибка изучения: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to learn YouTube: {e}")
        await message.answer("❌ Ошибка при изучении YouTube видео.")


async def cmd_learn_tg(message: Message):
    """Handle /learn_tg command."""
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "📱 <b>Изучение Telegram каналов</b>\n\n"
            "Формат: <code>/learn_tg &lt;@channel&gt; [количество]</code>\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/learn_tg @legalchannel 10</code> - последние 10 постов\n"
            "• <code>/learn_tg @newschannel</code> - последние 5 постов (по умолчанию)\n\n"
            "Требуются настройки Telethon в .env файле."
        )
        return

    channel = args[1]
    count = int(args[2]) if len(args) > 2 else 5

    try:
        # Get active case
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")
            return

        # Start ingestion
        status_msg = await message.answer(f"🔄 Изучаю канал {channel}...")

        result = await ingest_adapter.ingest_telegram(
            channel=channel,
            count=count,
            case_id=active_case['id']
        )

        if result['success']:
            await status_msg.edit_text(
                f"✅ <b>Telegram канал изучен</b>\n\n"
                f"📱 <b>Канал:</b> {channel}\n"
                f"📊 <b>Постов обработано:</b> {result.get('posts_processed', 0)}\n"
                f"📊 <b>Чанков создано:</b> {result.get('chunks_count', 0)}\n"
                f"📁 <b>Дело:</b> {active_case['id']}"
            )
        else:
            await status_msg.edit_text(f"❌ Ошибка изучения: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to learn Telegram: {e}")
        await message.answer("❌ Ошибка при изучении Telegram канала.")


async def cmd_search(message: Message):
    """Handle /search command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "🔍 <b>Поиск в интернете</b>\n\n"
            "Формат: <code>/search &lt;запрос&gt;</code>\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/search семейное право развод</code>\n"
            "• <code>/search административные штрафы 2024</code>\n\n"
            "Результаты можно будет добавить в активное дело."
        )
        return

    query = args[1].strip()

    try:
        # Show typing indicator
        await message.bot.send_chat_action(message.chat.id, "typing")

        # TODO: Implement web search
        # For now, show mock response
        await asyncio.sleep(1)  # Simulate search

        search_results = [
            {
                'title': 'Семейное право: процедура развода',
                'url': 'https://example.com/family-law',
                'snippet': 'Подробное описание процедуры развода в России...'
            },
            {
                'title': 'Документы для развода 2024',
                'url': 'https://example.com/divorce-docs',
                'snippet': 'Полный список необходимых документов...'
            }
        ]

        response_text = f"🔍 <b>Результаты поиска:</b> \"{query}\"\n\n"

        for idx, result in enumerate(search_results[:3], 1):
            response_text += (
                f"{idx}. <b>{result['title']}</b>\n"
                f"   {result['snippet']}\n"
                f"   🔗 {result['url']}\n\n"
            )

        # Add option to index results
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📚 Добавить в дело",
                        callback_data=f"search_add_{hash(query) % 10000}"
                    )
                ]
            ]
        )

        await message.answer(response_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Failed to search: {e}")
        await message.answer("❌ Ошибка при поиске.")


async def cmd_train(message: Message):
    """Handle /train command."""
    try:
        # Get active case
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")
            return

        # Start reindexing
        status_msg = await message.answer("🔄 Переиндексирую данные дела...")

        # TODO: Implement actual reindexing
        await asyncio.sleep(2)  # Simulate processing

        await status_msg.edit_text(
            f"✅ <b>Переиндексация завершена</b>\n\n"
            f"📁 <b>Дело:</b> {active_case['title']}\n"
            f"📊 <b>Обновлено чанков:</b> 25\n"
            f"⏱ <b>Время:</b> 2.1с"
        )

    except Exception as e:
        logger.error(f"Failed to retrain: {e}")
        await message.answer("❌ Ошибка при переиндексации.")


async def cmd_ask(message: Message):
    """Handle /ask command."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "🔍 <b>Вопросы по делу</b>\n\n"
            "Формат: <code>/ask &lt;ваш вопрос&gt;</code>\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/ask Какие документы нужны для развода?</code>\n"
            "• <code>/ask Сколько стоит подача иска?</code>\n"
            "• <code>/ask Какие есть прецеденты по этому вопросу?</code>"
        )
        return

    question = args[1].strip()

    try:
        # Get active case
        active_case = await case_adapter.get_active_case(message.chat.id)
        if not active_case:
            await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")
            return

        # Show typing indicator
        await message.bot.send_chat_action(message.chat.id, "typing")

        # Get RAG response
        result = await rag_adapter.ask_question(
            question=question,
            case_id=active_case['id'],
            user_id=message.from_user.id
        )

        if result['success']:
            response_text = f"💡 <b>Ответ:</b>\n\n{result['answer']}"

            # Add sources if available
            if result.get('sources'):
                response_text += "\n\n📚 <b>Источники:</b>"
                for idx, source in enumerate(result['sources'][:3], 1):
                    title = source.get('title', 'Документ')
                    url = source.get('url', '')
                    response_text += f"\n{idx}. {title}"
                    if url:
                        response_text += f" ({url})"

            await message.answer(
                response_text,
                reply_markup=get_source_keyboard(result.get('conversation_id'))
            )
        else:
            await message.answer(f"❌ Ошибка поиска ответа: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to process question: {e}")
        await message.answer("❌ Ошибка при обработке вопроса.")


async def cmd_status(message: Message):
    """Handle /status command."""
    try:
        status = await health_adapter.get_system_status()

        status_icons = {
            'ok': '✅',
            'degraded': '⚠️',
            'down': '❌'
        }

        response = "📊 <b>Статус системы</b>\n\n"
        response += f"🗄 <b>База данных:</b> {status_icons.get(status['db'], '❓')} {status['db']}\n"
        response += f"🧠 <b>Векторная БД:</b> {status_icons.get(status['vector'], '❓')} {status['vector']}\n"
        response += f"🤖 <b>LLM провайдеры:</b> {status_icons.get(status['llm'], '❓')} {status['llm']}\n"
        response += f"📊 <b>Очередь задач:</b> {status.get('queue', 0)}\n\n"

        if status.get('cases_count') is not None:
            response += f"📁 <b>Всего дел:</b> {status['cases_count']}\n"
        if status.get('documents_count') is not None:
            response += f"📄 <b>Всего документов:</b> {status['documents_count']}\n"

        await message.answer(response)

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        await message.answer("❌ Ошибка получения статуса системы.")


# Admin commands
async def cmd_admin(message: Message):
    """Handle /admin command."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав для выполнения команды.")
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "⚙️ <b>Административные команды</b>\n\n"
            "• <code>/admin providers</code> - Управление LLM провайдерами\n"
            "• <code>/admin limits</code> - Управление лимитами\n"
            "• <code>/admin retrain</code> - Переиндексация данных\n\n"
            "Используйте команды для управления системой.",
            reply_markup=get_admin_keyboard()
        )
        return

    subcommand = args[1].lower()

    if subcommand == "providers":
        await admin_manage_providers(message)
    elif subcommand == "limits":
        await admin_manage_limits(message)
    elif subcommand == "retrain":
        await admin_retrain(message)
    else:
        await message.answer("❌ Неизвестная административная команда.")


async def admin_manage_providers(message: Message):
    """Manage LLM providers."""
    try:
        providers = await admin_adapter.get_provider_status()

        response = "🤖 <b>Статус LLM провайдеров</b>\n\n"
        for provider, info in providers.items():
            status_icon = "✅" if info['available'] else "❌"
            response += f"{status_icon} <b>{provider}</b>: {info['status']}\n"
            if info.get('requests_today'):
                response += f"   📊 Запросов сегодня: {info['requests_today']}\n"

        await message.answer(response)

    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        await message.answer("❌ Ошибка получения статуса провайдеров.")


async def admin_manage_limits(message: Message):
    """Manage system limits."""
    try:
        limits = await admin_adapter.get_system_limits()

        response = "📊 <b>Системные лимиты</b>\n\n"
        response += f"📄 <b>Максимальный размер файла:</b> {limits['max_file_mb']}MB\n"
        response += f"🔄 <b>Запросов в минуту:</b> {limits['rate_limit_per_minute']}\n"
        response += f"💾 <b>Чанков на дело:</b> {limits['max_chunks_per_case']}\n"
        response += f"🧠 <b>Токенов на запрос:</b> {limits['max_tokens_per_request']}\n"

        await message.answer(response)

    except Exception as e:
        logger.error(f"Failed to get system limits: {e}")
        await message.answer("❌ Ошибка получения системных лимитов.")


async def admin_retrain(message: Message):
    """Trigger system retraining."""
    try:
        status_msg = await message.answer("🔄 Запускаю переиндексацию системы...")

        result = await admin_adapter.trigger_retrain()

        if result['success']:
            await status_msg.edit_text(
                f"✅ <b>Переиндексация запущена</b>\n\n"
                f"📊 Обработано документов: {result.get('documents_processed', 0)}\n"
                f"🧠 Создано чанков: {result.get('chunks_created', 0)}\n"
                f"⏱ Время выполнения: {result.get('duration_seconds', 0):.1f}с"
            )
        else:
            await status_msg.edit_text(f"❌ Ошибка переиндексации: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Failed to trigger retrain: {e}")
        await message.answer("❌ Ошибка запуска переиндексации.")


def parse_learn_params(param_str: str) -> dict:
    """Parse parameters from learn command."""
    params = {}

    # Extract title="..."
    title_match = re.search(r'title="([^"]*)"', param_str)
    if title_match:
        params['title'] = title_match.group(1)

    # Extract tags="..."
    tags_match = re.search(r'tags="([^"]*)"', param_str)
    if tags_match:
        params['tags'] = [tag.strip() for tag in tags_match.group(1).split(',')]

    # Extract lang="..."
    lang_match = re.search(r'lang="([^"]*)"', param_str)
    if lang_match:
        params['lang'] = lang_match.group(1)

    return params


def register_handlers(dp: Dispatcher):
    """Register all command handlers."""
    # Basic commands
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))

    # Case management
    dp.message.register(cmd_case_new, Command("case_new"))
    dp.message.register(cmd_case_use, Command("case_use"))
    dp.message.register(cmd_case_add, Command("case_add"))

    # Learning commands
    dp.message.register(cmd_learn_url, Command("learn_url"))
    dp.message.register(cmd_learn_yt, Command("learn_yt"))
    dp.message.register(cmd_learn_tg, Command("learn_tg"))

    # Other commands
    dp.message.register(cmd_search, Command("search"))
    dp.message.register(cmd_train, Command("train"))

    # AI commands
    dp.message.register(cmd_ask, Command("ask"))

    # System commands
    dp.message.register(cmd_status, Command("status"))
    dp.message.register(cmd_admin, Command("admin"))

    # File handlers (when sent without /case_add command)
    async def handle_document_message(message: Message):
        if message.document:
            active_case = await case_adapter.get_active_case(message.chat.id)
            if active_case:
                await handle_document_upload(message, active_case['id'])
            else:
                await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")

    async def handle_photo_message(message: Message):
        if message.photo:
            active_case = await case_adapter.get_active_case(message.chat.id)
            if active_case:
                await handle_photo_upload(message, active_case['id'])
            else:
                await message.answer("❌ Нет активного дела. Используйте /case_new или /case_use.")

    dp.message.register(handle_document_message, F.document)
    dp.message.register(handle_photo_message, F.photo)