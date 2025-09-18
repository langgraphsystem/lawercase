"""Telegram bot keyboards and inline markup."""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📁 Новое дело"),
                KeyboardButton(text="📋 Выбрать дело")
            ],
            [
                KeyboardButton(text="🔍 Поиск"),
                KeyboardButton(text="📊 Статус")
            ],
            [
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


def get_case_keyboard(case_id: str) -> InlineKeyboardMarkup:
    """Get case management keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📎 Добавить документ",
                    callback_data=f"case_add_{case_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Задать вопрос",
                    callback_data=f"case_ask_{case_id}"
                ),
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data=f"case_stats_{case_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Переиндексировать",
                    callback_data=f"case_retrain_{case_id}"
                )
            ]
        ]
    )
    return keyboard


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin menu keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Провайдеры",
                    callback_data="admin_providers"
                ),
                InlineKeyboardButton(
                    text="📊 Лимиты",
                    callback_data="admin_limits"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Переобучение",
                    callback_data="admin_retrain"
                )
            ]
        ]
    )
    return keyboard


def get_source_keyboard(source_id: str) -> InlineKeyboardMarkup:
    """Get source/document actions keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Подробнее",
                    callback_data=f"source_details_{source_id}"
                ),
                InlineKeyboardButton(
                    text="⬇️ Скачать",
                    callback_data=f"source_download_{source_id}"
                )
            ]
        ]
    )
    return keyboard


def get_confirm_keyboard(action: str, target_id: str) -> InlineKeyboardMarkup:
    """Get confirmation keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data=f"confirm_{action}_{target_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=f"cancel_{action}_{target_id}"
                )
            ]
        ]
    )
    return keyboard