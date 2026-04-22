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

        session = sessions.get(message.from_user.id)
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

        sessions.add_user_turn(message.from_user.id, transcript)

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
            sessions.rollback_user_turn(message.from_user.id)

    return router
