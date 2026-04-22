from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.storage.session import Sessions, UserSession
from bot.utils.reply_keyboard import (
    BUTTON_REASONING_STATUS,
    is_reasoning_button,
    is_show_reasoning_button,
    main_reply_keyboard,
)

router = Router(name="reasoning")

_TRUE = {"on", "1", "true", "yes", "enable", "enabled"}
_FALSE = {"off", "0", "false", "no", "disable", "disabled"}


def _status_text(session: UserSession) -> str:
    reasoning = "ON" if session.reasoning_enabled else "OFF"
    show = "ON" if session.show_reasoning else "OFF"
    return (
        "🧠 Настройки reasoning\n\n"
        f"• Размышление модели: {reasoning}\n"
        f"• Показывать текст размышлений: {show}\n\n"
        "Команды:\n"
        "• /thinking on|off\n"
        "• /showthinking on|off\n"
        "• /thinkingstatus\n\n"
        "Важно: скрытие текста reasoning убирает <think>...</think> блоки из ответа и истории. "
        "На провайдерах без отдельного reasoning API переключатель работает через prompt + отображение."
    )


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return None


def register(sessions: Sessions) -> Router:
    @router.message(Command("thinkingstatus"))
    @router.message(F.text == BUTTON_REASONING_STATUS)
    async def thinking_status(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        await message.answer(
            _status_text(session), reply_markup=main_reply_keyboard(session)
        )

    @router.message(Command(commands=["thinking", "reasoning"]))
    async def thinking_cmd(message: Message, command: CommandObject) -> None:
        value = _parse_bool(command.args)
        if command.args and value is None:
            await message.answer(
                "Используй: /thinking on или /thinking off",
                reply_markup=main_reply_keyboard(sessions.get(message.from_user.id)),
            )
            return
        if value is None:
            session = sessions.get(message.from_user.id)
            await message.answer(
                _status_text(session), reply_markup=main_reply_keyboard(session)
            )
            return
        sessions.set_reasoning(message.from_user.id, value)
        session = sessions.get(message.from_user.id)
        await message.answer(
            f"🧠 Размышление модели {'включено' if value else 'выключено'}.\n\n"
            f"{_status_text(session)}",
            reply_markup=main_reply_keyboard(session),
        )

    @router.message(F.text.func(is_reasoning_button))
    async def thinking_toggle_btn(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        sessions.set_reasoning(message.from_user.id, not session.reasoning_enabled)
        session = sessions.get(message.from_user.id)
        await message.answer(
            f"🧠 Размышление модели {'включено' if session.reasoning_enabled else 'выключено'}.\n\n"
            f"{_status_text(session)}",
            reply_markup=main_reply_keyboard(session),
        )

    @router.message(Command(commands=["showthinking", "showreasoning"]))
    async def showthinking_cmd(message: Message, command: CommandObject) -> None:
        value = _parse_bool(command.args)
        if command.args and value is None:
            await message.answer(
                "Используй: /showthinking on или /showthinking off",
                reply_markup=main_reply_keyboard(sessions.get(message.from_user.id)),
            )
            return
        if value is None:
            session = sessions.get(message.from_user.id)
            await message.answer(
                _status_text(session), reply_markup=main_reply_keyboard(session)
            )
            return
        sessions.set_show_reasoning(message.from_user.id, value)
        session = sessions.get(message.from_user.id)
        await message.answer(
            f"💭 Показ reasoning-текста {'включён' if value else 'выключен'}.\n\n"
            f"{_status_text(session)}",
            reply_markup=main_reply_keyboard(session),
        )

    @router.message(F.text.func(is_show_reasoning_button))
    async def showthinking_toggle_btn(message: Message) -> None:
        session = sessions.get(message.from_user.id)
        sessions.set_show_reasoning(message.from_user.id, not session.show_reasoning)
        session = sessions.get(message.from_user.id)
        await message.answer(
            f"💭 Показ reasoning-текста {'включён' if session.show_reasoning else 'выключен'}.\n\n"
            f"{_status_text(session)}",
            reply_markup=main_reply_keyboard(session),
        )

    return router
