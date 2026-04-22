from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from bot.config import KEYLESS_PROVIDERS
from bot.providers.registry import Provider


@lru_cache(maxsize=None)
def _client(name: str, base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def get_client(provider: Provider) -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client for this provider."""
    key = provider.api_key or (
        "anonymous" if provider.name in KEYLESS_PROVIDERS else ""
    )
    if not key:
        raise RuntimeError(f"No API key configured for provider {provider.name!r}")
    return _client(provider.name, provider.base_url, key)
