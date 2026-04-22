from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.providers.registry import Provider
from bot.storage.session import Sessions

router = Router(name="start")


def _greeting(registry: list[Provider]) -> str:
    lines = [
        "👋 *FreeGPT* — чат с 14 бесплатными LLM-провайдерами в одном окне.",
        "",
        "Команды:",
        "• /model — выбрать провайдера и модель",
        "• /reset — очистить историю диалога",
        "• /providers — список подключённых провайдеров",
        "• /help — эта справка",
        "",
        "Шли текст, фото (vision) или голосовое (распознаётся через Groq Whisper).",
        "При ошибке провайдера бот автоматически переключится на резервную модель.",
    ]
    return "\n".join(lines)


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(CommandStart())
    async def start(message: Message) -> None:
        sessions.get(message.from_user.id)  # init session
        await message.answer(_greeting(registry))

    @router.message(Command("help"))
    async def help_cmd(message: Message) -> None:
        await message.answer(_greeting(registry))

    @router.message(Command("providers"))
    async def providers(message: Message) -> None:
        lines = [f"Доступно провайдеров: *{len(registry)}*", ""]
        for p in registry:
            flag = p.flag or "🌐"
            lines.append(f"{flag} *{p.name}* — {len(p.models)} моделей")
        await message.answer("\n".join(lines))

    return router
