from __future__ import annotations

import tempfile
from pathlib import Path

from aiogram import F, Router
from aiogram.types import Message

from bot.llm.complete import chat_complete_with_fallback
from bot.llm.transcribe import TranscriptionUnavailable, transcribe_audio
from bot.providers.registry import Provider
from bot.storage.session import Sessions
from bot.utils.streaming import StreamingEditor

router = Router(name="voice")


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(F.voice | F.audio)
    async def on_voice(message: Message) -> None:
        audio = message.voice or message.audio
        if audio is None:
            return

        notice = await message.answer("🎙 Распознаю…")

        suffix = ".ogg" if message.voice else ".mp3"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()
        tmp_path = Path(tmp.name)
        try:
            await message.bot.download(audio, destination=tmp_path)
            try:
                transcript = await transcribe_audio(tmp_path)
            except TranscriptionUnavailable as exc:
                await notice.edit_text(f"⚠️ {exc}")
                return
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

        if not transcript:
            await notice.edit_text("⚠️ Не удалось распознать речь.")
            return

        await notice.edit_text(f"🎙 → «{transcript}»")

        session = sessions.get(message.from_user.id)
        session.history.append({"role": "user", "content": transcript})

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
            try:
                session.history.pop()
            except IndexError:
                pass

    return router
