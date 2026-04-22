from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.storage.session import Sessions
from bot.utils.reply_keyboard import main_reply_keyboard

router = Router(name="memory")


def register(sessions: Sessions) -> Router:
    @router.message(Command("memory"))
    async def memory_cmd(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        await message.answer(
            sessions.memory_snapshot(message.from_user.id),
            reply_markup=main_reply_keyboard(session),
        )

    @router.message(Command("remember"))
    async def remember_cmd(message: Message, command: CommandObject) -> None:
        note = (command.args or "").strip()
        session = sessions.get(message.from_user.id)
        if not note:
            await message.answer(
                "Используй: /remember <что запомнить>",
                reply_markup=main_reply_keyboard(session),
            )
            return

        created = sessions.remember(message.from_user.id, note)
        if created:
            text = f"🧠 Запомнил: {note}"
        else:
            text = f"🧠 Это уже есть в durable memory: {note}"
        await message.answer(text, reply_markup=main_reply_keyboard(session))

    return router
