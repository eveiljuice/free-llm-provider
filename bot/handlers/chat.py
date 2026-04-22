from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.llm.complete import chat_complete_with_fallback
from bot.providers.registry import Provider
from bot.storage.session import Sessions
from bot.utils.streaming import StreamingEditor

router = Router(name="chat")


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(F.text & ~F.text.startswith("/"))
    async def on_text(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        session.history.append({"role": "user", "content": message.text})

        placeholder = await message.answer("⏳ …")
        editor = StreamingEditor(
            message.bot, chat_id=placeholder.chat.id, message_id=placeholder.message_id
        )

        result = await chat_complete_with_fallback(
            registry=registry,
            messages=session.messages(),
            primary=(session.provider_name, session.model_id),
            editor=editor,
        )
        if result.ok and result.text:
            session.history.append({"role": "assistant", "content": result.text})
        else:
            # Roll back the user turn so they can retry cleanly.
            try:
                session.history.pop()
            except IndexError:
                pass

    return router
