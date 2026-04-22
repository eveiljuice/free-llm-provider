from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.providers.registry import Provider
from bot.storage.session import Sessions
from bot.utils.reply_keyboard import BUTTON_MODEL

router = Router(name="model")

_PAGE = 8


def _providers_kb(registry: list[Provider]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, p in enumerate(registry):
        flag = p.flag or "🌐"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{flag} {p.name} · {len(p.models)} models",
                    callback_data=f"pickp:{idx}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _models_kb(registry: list[Provider], prov_idx: int) -> InlineKeyboardMarkup:
    prov = registry[prov_idx]
    rows: list[list[InlineKeyboardButton]] = []
    for m_idx, m in enumerate(prov.models[:24]):  # keep UI sane
        vision = "🖼" if m.supports_vision else ""
        label = f"{vision} {m.name} · {m.context}".strip()
        rows.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=f"pickm:{prov_idx}:{m_idx}"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="pickback")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def register(sessions: Sessions, registry: list[Provider]) -> Router:
    @router.message(Command("model"))
    @router.message(F.text == BUTTON_MODEL)
    async def model_cmd(message: Message) -> None:
        await message.answer(
            "Выбери провайдера:", reply_markup=_providers_kb(registry)
        )

    @router.callback_query(F.data.startswith("pickp:"))
    async def pick_provider(cb: CallbackQuery) -> None:
        idx = int(cb.data.split(":")[1])
        if not 0 <= idx < len(registry):
            await cb.answer("Провайдер не найден", show_alert=True)
            return
        prov = registry[idx]
        await cb.message.edit_text(
            f"Модели {prov.flag} *{prov.name}*:",
            reply_markup=_models_kb(registry, idx),
        )
        await cb.answer()

    @router.callback_query(F.data == "pickback")
    async def pick_back(cb: CallbackQuery) -> None:
        await cb.message.edit_text(
            "Выбери провайдера:", reply_markup=_providers_kb(registry)
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("pickm:"))
    async def pick_model(cb: CallbackQuery) -> None:
        _, p_idx_s, m_idx_s = cb.data.split(":")
        p_idx, m_idx = int(p_idx_s), int(m_idx_s)
        if not 0 <= p_idx < len(registry):
            await cb.answer("Провайдер не найден", show_alert=True)
            return
        prov = registry[p_idx]
        if not 0 <= m_idx < len(prov.models):
            await cb.answer("Модель не найдена", show_alert=True)
            return
        model = prov.models[m_idx]
        sessions.set_model(cb.from_user.id, prov, model)
        await cb.message.edit_text(
            f"✅ Выбрано: {prov.flag} *{prov.name}* / *{model.name}*\n"
            f"Контекст: {model.context} · {model.rate_limit}"
        )
        await cb.answer("Готово")

    return router
