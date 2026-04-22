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
        sessions.add_user_turn(message.from_user.id, message.text)

        placeholder = await message.answer("⏳ …")
        editor = StreamingEditor(
            message.bot, chat_id=placeholder.chat.id, message_id=placeholder.message_id
        )

        result = await chat_complete_with_fallback(
            registry=registry,
            messages=session.messages(),
            primary=(session.provider_name, session.model_id),
            editor=editor,
            reasoning_enabled=session.reasoning_enabled,
            show_reasoning=session.show_reasoning,
        )
        if result.ok and result.text:
            sessions.add_assistant_turn(message.from_user.id, result.text)
            await sessions.maybe_auto_distill(message.from_user.id, registry)
        else:
            # Roll back the user turn so they can retry cleanly.
            sessions.rollback_user_turn(message.from_user.id)

    return router
