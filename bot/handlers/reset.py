from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.storage.session import Sessions

router = Router(name="reset")


def register(sessions: Sessions) -> Router:
    @router.message(Command("reset"))
    async def reset_cmd(message: Message) -> None:
        sessions.reset(message.from_user.id)
        await message.answer("🗑 История диалога очищена.")

    return router
