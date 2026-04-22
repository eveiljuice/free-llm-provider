from __future__ import annotations

import base64
import io

from aiogram import F, Router
from aiogram.types import Message

from bot.llm.complete import chat_complete_with_fallback
from bot.providers.registry import Provider, find
from bot.storage.session import Sessions
from bot.utils.streaming import StreamingEditor

router = Router(name="vision")


async def _download_photo_b64(message: Message) -> str:
    photo = message.photo[-1]  # largest size
    buf = io.BytesIO()
    await message.bot.download(photo, destination=buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(F.photo)
    async def on_photo(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        caption = (message.caption or "Опиши это изображение.").strip()

        try:
            b64 = await _download_photo_b64(message)
        except Exception:  # noqa: BLE001
            await message.answer("⚠️ Не удалось загрузить фото. Попробуй ещё раз.")
            return

        content = [
            {"type": "text", "text": caption},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            },
        ]
        session.history.append({"role": "user", "content": content})

        placeholder = await message.answer("⏳ Смотрю на картинку…")
        editor = StreamingEditor(
            message.bot, chat_id=placeholder.chat.id, message_id=placeholder.message_id
        )

        # If the user's current model doesn't support vision, chat_complete will
        # pick the first vision-capable model from the fallback chain.
        current = find(registry, session.provider_name, session.model_id)
        needs_fallback = current is None or not current[1].supports_vision
        if needs_fallback:
            await editor.prefix(
                "🖼 Текущая модель без vision — использую резервную.\n\n"
            )

        result = await chat_complete_with_fallback(
            registry=registry,
            messages=session.messages(),
            primary=(session.provider_name, session.model_id),
            editor=editor,
            require_vision=True,
            reasoning_enabled=session.reasoning_enabled,
            show_reasoning=session.show_reasoning,
        )
        if result.ok and result.text:
            session.history.append({"role": "assistant", "content": result.text})
        else:
            try:
                session.history.pop()
            except IndexError:
                pass

    return router
