from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.storage.session import Sessions
from bot.utils.reply_keyboard import BUTTON_RESET, main_reply_keyboard

router = Router(name="reset")


def register(sessions: Sessions) -> Router:
    @router.message(Command("reset"))
    @router.message(F.text == BUTTON_RESET)
    async def reset_cmd(message: Message) -> None:
        sessions.reset(message.from_user.id)
        await message.answer(
            "🗑 История диалога очищена.",
            reply_markup=main_reply_keyboard(sessions.get(message.from_user.id)),
        )

    return router
