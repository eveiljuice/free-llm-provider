from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from bot.providers.client import get_client
from bot.providers.registry import Model, Provider
from bot.utils.streaming import StreamingEditor

log = logging.getLogger(__name__)

GLOBAL_FALLBACK_CHAIN: list[tuple[str, str]] = [
    ("Groq", "llama-3.3-70b-versatile"),
    ("Google Gemini", "gemini-2.5-flash"),
    ("Cerebras", "llama3.1-8b"),
    ("Mistral AI", "mistral-large-latest"),
    ("OpenRouter", "openrouter/auto"),
    ("LLM7.io", "gpt-4o-mini"),
]

# When a provider rejects with 429/5xx we skip it for this many seconds.
COOLDOWN_SECS = 60.0
_cooldown: dict[str, float] = {}
_REASONING_BLOCK_RE = re.compile(r"<(think|thinking)>.*?</\1>", re.IGNORECASE | re.DOTALL)
_REASONING_OPEN_RE = re.compile(r"<(think|thinking)>", re.IGNORECASE)
_REASONING_TAG_RE = re.compile(r"</?(think|thinking)>", re.IGNORECASE)


@dataclass
class CompletionResult:
    text: str
    provider_name: str
    model_id: str
    ok: bool


def _in_cooldown(provider_name: str) -> bool:
    until = _cooldown.get(provider_name, 0.0)
    return until > time.monotonic()


def _cool_down(provider_name: str) -> None:
    _cooldown[provider_name] = time.monotonic() + COOLDOWN_SECS


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, AuthenticationError):
        return False
    if isinstance(exc, BadRequestError):
        return False
    if isinstance(
        exc,
        (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError),
    ):
        return True
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", None) or 0
        return code == 429 or 500 <= code < 600
    return False


def _strip_reasoning_blocks(text: str) -> str:
    cleaned = _REASONING_BLOCK_RE.sub("", text)
    last_open: int | None = None
    for match in _REASONING_OPEN_RE.finditer(cleaned):
        last_open = match.start()
    if last_open is not None:
        tail = cleaned[last_open:]
        if not _REASONING_BLOCK_RE.search(tail):
            cleaned = cleaned[:last_open]
    cleaned = _REASONING_TAG_RE.sub("", cleaned)
    return cleaned.strip()


def _display_text(text: str, *, show_reasoning: bool) -> str:
    if show_reasoning:
        return (
            text.replace("<think>", "💭 Размышления:\n")
            .replace("</think>", "\n\n")
            .replace("<thinking>", "💭 Размышления:\n")
            .replace("</thinking>", "\n\n")
            .strip()
        )
    return _strip_reasoning_blocks(text)


def _request_kwargs(
    provider: Provider,
    model: Model,
    *,
    reasoning_enabled: bool,
) -> dict[str, Any]:
    mid = model.id.lower()
    if provider.name == "GitHub Models" and mid.startswith(("o1", "o3", "o4")):
        return {"reasoning_effort": "medium" if reasoning_enabled else "low"}
    return {}


def _pick_candidates(
    registry: list[Provider],
    primary: tuple[str, str],
    *,
    require_vision: bool,
) -> list[tuple[Provider, Model]]:
    ordered: list[tuple[str, str]] = [primary]
    for pair in GLOBAL_FALLBACK_CHAIN:
        if pair != primary:
            ordered.append(pair)

    seen: set[tuple[str, str]] = set()
    out: list[tuple[Provider, Model]] = []
    for prov_name, model_id in ordered:
        key = (prov_name, model_id)
        if key in seen:
            continue
        seen.add(key)
        prov = next((p for p in registry if p.name == prov_name), None)
        if prov is None or not prov.available:
            continue
        model = next((m for m in prov.models if m.id == model_id), None)
        if model is None:
            continue
        if require_vision and not model.supports_vision:
            continue
        out.append((prov, model))

    # If vision required and chain gave nothing, scan the full registry.
    if require_vision and not out:
        for prov in registry:
            if not prov.available:
                continue
            for m in prov.models:
                if m.supports_vision and (prov.name, m.id) not in seen:
                    out.append((prov, m))
                    seen.add((prov.name, m.id))
    return out


async def _stream_one(
    provider: Provider,
    model: Model,
    messages: list[dict[str, Any]],
    editor: StreamingEditor,
    *,
    reasoning_enabled: bool,
    show_reasoning: bool,
) -> str:
    client = get_client(provider)
    started = editor.text
    stream = await client.chat.completions.create(
        model=model.id,
        messages=messages,
        stream=True,
        **_request_kwargs(
            provider,
            model,
            reasoning_enabled=reasoning_enabled,
        ),
    )
    collected = ""
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = ((delta.content or "") if delta else "") or (
            (delta.refusal or "") if delta else ""
        )
        if piece:
            collected += piece
            await editor.set(
                started + _display_text(collected, show_reasoning=show_reasoning)
            )
    await editor.set(started + _display_text(collected, show_reasoning=show_reasoning))
    await editor.finish()
    return _strip_reasoning_blocks(collected)


async def chat_complete_with_fallback(
    *,
    registry: list[Provider],
    messages: list[dict[str, Any]],
    primary: tuple[str, str],
    editor: StreamingEditor,
    require_vision: bool = False,
    reasoning_enabled: bool = False,
    show_reasoning: bool = False,
) -> CompletionResult:
    """Stream a completion, falling back through GLOBAL_FALLBACK_CHAIN on errors."""
    candidates = _pick_candidates(registry, primary, require_vision=require_vision)
    if not candidates:
        await editor.push(
            "😔 Нет доступных моделей. Проверь .env и задай хотя бы один ключ."
        )
        await editor.finish()
        return CompletionResult("", primary[0], primary[1], ok=False)

    last_error: str | None = None
    for idx, (prov, model) in enumerate(candidates):
        if idx > 0 and _in_cooldown(prov.name):
            log.info("skip %s (cooldown)", prov.name)
            continue
        if idx > 0:
            await editor.prefix(
                f"⚠️ {last_error}. Переключаюсь на {prov.name} / {model.name}…\n\n"
            )
        t0 = time.monotonic()
        try:
            text = await _stream_one(
                prov,
                model,
                messages,
                editor,
                reasoning_enabled=reasoning_enabled,
                show_reasoning=show_reasoning,
            )
            log.info(
                "ok %s/%s in %.1fs", prov.name, model.id, time.monotonic() - t0
            )
            return CompletionResult(text, prov.name, model.id, ok=True)
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            label = type(exc).__name__
            last_error = f"{prov.name} → {status or label}"
            log.warning(
                "fail %s/%s (%s) in %.1fs",
                prov.name,
                model.id,
                label,
                time.monotonic() - t0,
            )
            if _is_retryable(exc):
                _cool_down(prov.name)
                continue
            # Non-retryable: still move on, but without cooling the provider
            # (so the user can retry after /model change).
            continue

    await editor.prefix(
        "😔 Все провайдеры недоступны. Попробуй позже или смени модель через /model.\n\n"
    )
    await editor.finish()
    return CompletionResult("", primary[0], primary[1], ok=False)
