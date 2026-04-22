from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from openai import AsyncOpenAI, RateLimitError

from bot.config import groq_api_key

log = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
PRIMARY_MODEL = "whisper-large-v3-turbo"
FALLBACK_MODEL = "whisper-large-v3"


class TranscriptionUnavailable(RuntimeError):
    """Raised when Groq is not configured or transcription failed entirely."""


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    key = groq_api_key()
    if not key:
        raise TranscriptionUnavailable(
            "GROQ_API_KEY is not set — voice transcription is disabled."
        )
    return AsyncOpenAI(api_key=key, base_url=GROQ_BASE_URL)


async def transcribe_audio(path: Path | str) -> str:
    """Transcribe an audio file via Groq Whisper. Returns plain text."""
    client = _client()
    p = Path(path)
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            with p.open("rb") as f:
                result = await client.audio.transcriptions.create(
                    model=model,
                    file=(p.name, f),
                    response_format="text",
                )
            # SDK returns a string when response_format="text"
            text = result if isinstance(result, str) else getattr(result, "text", "")
            return (text or "").strip()
        except RateLimitError:
            log.warning("whisper %s rate-limited, trying next", model)
            continue
        except Exception as exc:  # noqa: BLE001
            log.warning("whisper %s failed: %s", model, exc)
            continue
    raise TranscriptionUnavailable(
        "Groq Whisper is temporarily unavailable. Try again in a bit, or type your message."
    )
