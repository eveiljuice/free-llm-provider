from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.providers.registry import Provider
from bot.storage.session import Sessions
from bot.utils.reply_keyboard import (
    BUTTON_HELP,
    BUTTON_PROVIDERS,
    main_reply_keyboard,
)

router = Router(name="start")


def _greeting(registry: list[Provider]) -> str:
    lines = [
        "👋 *FreeGPT* — чат с 14 бесплатными LLM-провайдерами в одном окне.",
        "",
        "Основные действия вынесены в кнопки под полем ввода.",
        "Слеш-команды тоже остались как запасной вариант.",
        "Durable memory: кнопка 🧠 Memory, /remember <note>, /memory, /memoryexport.",
        "",
        "Шли текст, фото (vision) или голосовое (распознаётся через Groq Whisper).",
        "При ошибке провайдера бот автоматически переключится на резервную модель.",
    ]
    return "\n".join(lines)


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(CommandStart())
    async def start(message: Message) -> None:
        session = sessions.get(message.from_user.id)  # init session
        await message.answer(
            _greeting(registry), reply_markup=main_reply_keyboard(session)
        )

    @router.message(Command("help"))
    @router.message(F.text == BUTTON_HELP)
    async def help_cmd(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        await message.answer(
            _greeting(registry), reply_markup=main_reply_keyboard(session)
        )

    @router.message(Command("providers"))
    @router.message(F.text == BUTTON_PROVIDERS)
    async def providers(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        lines = [f"Доступно провайдеров: *{len(registry)}*", ""]
        for p in registry:
            flag = p.flag or "🌐"
            lines.append(f"{flag} *{p.name}* — {len(p.models)} моделей")
        await message.answer(
            "\n".join(lines), reply_markup=main_reply_keyboard(session)
        )

    return router
