from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

log = logging.getLogger(__name__)

MIN_INTERVAL = 1.5  # seconds between edits
TELEGRAM_TEXT_LIMIT = 4096


class StreamingEditor:
    """Edits a Telegram message with accumulated text, throttled."""

    def __init__(self, bot: Bot, chat_id: int, message_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id
        self._buffer = ""
        self._last_rendered = ""
        self._last_edit_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def text(self) -> str:
        return self._buffer

    async def push(self, delta: str) -> None:
        if not delta:
            return
        self._buffer += delta
        now = time.monotonic()
        if now - self._last_edit_at < MIN_INTERVAL:
            return
        await self._flush()

    async def set(self, text: str) -> None:
        self._buffer = text or ""
        now = time.monotonic()
        if now - self._last_edit_at < MIN_INTERVAL:
            return
        await self._flush()

    async def prefix(self, line: str) -> None:
        """Prepend a one-off notification line (e.g. fallback notice)."""
        if not line:
            return
        self._buffer = line + self._buffer
        await self._flush(force=True)

    async def finish(self) -> str:
        await self._flush(force=True)
        return self._buffer

    async def _flush(self, *, force: bool = False) -> None:
        async with self._lock:
            text = self._buffer[-TELEGRAM_TEXT_LIMIT:] or "…"
            if text == self._last_rendered:
                return
            try:
                await self._bot.edit_message_text(
                    text=text,
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                )
                self._last_rendered = text
                self._last_edit_at = time.monotonic()
            except TelegramRetryAfter as e:
                log.warning("Flood wait %.1fs on edit", e.retry_after)
                await asyncio.sleep(e.retry_after)
                if force:
                    try:
                        await self._bot.edit_message_text(
                            text=text,
                            chat_id=self._chat_id,
                            message_id=self._message_id,
                        )
                        self._last_rendered = text
                        self._last_edit_at = time.monotonic()
                    except TelegramBadRequest:
                        pass
            except TelegramBadRequest as e:
                # "message is not modified" or formatting issues — ignore
                if "not modified" not in str(e):
                    log.warning("edit_message_text failed: %s", e)
