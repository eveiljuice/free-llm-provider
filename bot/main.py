from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import chat, model, reset, start, vision, voice
from bot.providers.registry import load_registry
from bot.storage.session import Sessions


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    _setup_logging()
    log = logging.getLogger("freegpt")

    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Fill bot/.env.")

    registry = load_registry()
    if not registry:
        raise SystemExit(
            "No providers available. Configure at least one API key in bot/.env."
        )

    default_provider = registry[0]
    default_model = default_provider.models[0]
    log.info(
        "Default: %s / %s", default_provider.name, default_model.id
    )
    sessions = Sessions(default_provider, default_model)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.register(sessions, registry))
    dp.include_router(reset.register(sessions))
    dp.include_router(model.register(sessions, registry))
    dp.include_router(vision.register(sessions, registry))
    dp.include_router(voice.register(sessions, registry))
    dp.include_router(chat.register(sessions, registry))  # text handler last

    log.info("Starting polling…")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
