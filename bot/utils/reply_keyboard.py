from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.storage.session import UserSession

BUTTON_MODEL = "🤖 Модель"
BUTTON_PROVIDERS = "📡 Провайдеры"
BUTTON_REASONING_STATUS = "⚙️ Reasoning"
BUTTON_RESET = "♻️ Сброс"
BUTTON_HELP = "ℹ️ Помощь"


def reasoning_button(session: UserSession) -> str:
    return f"🧠 Reasoning: {'ON' if session.reasoning_enabled else 'OFF'}"


def show_reasoning_button(session: UserSession) -> str:
    return f"💭 Thoughts: {'ON' if session.show_reasoning else 'OFF'}"


def is_reasoning_button(text: str | None) -> bool:
    return bool(text) and text.startswith("🧠 Reasoning:")


def is_show_reasoning_button(text: str | None) -> bool:
    return bool(text) and text.startswith("💭 Thoughts:")


def main_reply_keyboard(session: UserSession) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BUTTON_MODEL),
                KeyboardButton(text=BUTTON_PROVIDERS),
            ],
            [
                KeyboardButton(text=reasoning_button(session)),
                KeyboardButton(text=show_reasoning_button(session)),
            ],
            [
                KeyboardButton(text=BUTTON_REASONING_STATUS),
                KeyboardButton(text=BUTTON_RESET),
                KeyboardButton(text=BUTTON_HELP),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Напиши сообщение или выбери действие ниже…",
    )
