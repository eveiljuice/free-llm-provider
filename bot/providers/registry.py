from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from bot.config import (
    BASE_URL_OVERRIDES,
    KEYLESS_PROVIDERS,
    UNSUPPORTED_PROVIDERS,
    provider_keys,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Model:
    id: str
    name: str
    context: str
    modality: str
    rate_limit: str

    @property
    def supports_vision(self) -> bool:
        m = self.modality.lower()
        if "audio →" in m or m.startswith("audio"):
            return False
        return "image" in m or "video" in m or "vision" in m


@dataclass
class Provider:
    name: str
    flag: str
    country: str
    base_url: str
    api_key: str | None
    models: list[Model] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return bool(self.models) and (
            self.api_key is not None or self.name in KEYLESS_PROVIDERS
        )


def _is_placeholder_model(raw: dict) -> bool:
    mid = raw.get("id")
    name = (raw.get("name") or "").strip().lower()
    return not mid or name.startswith("+ ")


def _is_chat_model(raw: dict) -> bool:
    modality = (raw.get("modality") or "").lower().strip()
    if not modality or "text" not in modality:
        return False
    # Exclude audio-in models (Whisper etc.) — they use a different endpoint.
    if "audio →" in modality or modality.startswith("audio"):
        return False
    # Exclude pure embeddings / reranking / speech-generation models.
    if "rerank" in modality:
        return False
    if modality in {"embeddings", "embedding", "reranking", "speech"}:
        return False
    if modality.startswith("embedding") and "→" not in modality:
        return False
    return True


def load_registry(path: Path | str | None = None) -> list[Provider]:
    """Parse data.json into a list of available Providers with chat models."""
    from bot.config import DATA_JSON_PATH

    p = Path(path) if path else DATA_JSON_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    keys = provider_keys()

    providers: list[Provider] = []
    for prov in raw.get("providers", []):
        name = prov.get("name")
        if not name or name in UNSUPPORTED_PROVIDERS:
            continue
        api_key = keys.get(name)
        if api_key is None and name not in KEYLESS_PROVIDERS:
            continue

        base_url = BASE_URL_OVERRIDES.get(name, prov.get("baseUrl", ""))
        if not base_url:
            continue

        models: list[Model] = []
        for m in prov.get("models", []):
            if _is_placeholder_model(m) or not _is_chat_model(m):
                continue
            models.append(
                Model(
                    id=m["id"],
                    name=m.get("name") or m["id"],
                    context=m.get("context") or "—",
                    modality=m.get("modality") or "Text",
                    rate_limit=m.get("rateLimit") or "—",
                )
            )
        if not models:
            continue

        # Sort category: provider_api first, then inference_provider.
        providers.append(
            Provider(
                name=name,
                flag=prov.get("flag") or "",
                country=prov.get("country") or "",
                base_url=base_url,
                api_key=api_key,
                models=models,
            )
        )

    # Keep data.json ordering (category is already grouped there).
    log.info(
        "Registry loaded: %d providers, %d models",
        len(providers),
        sum(len(p.models) for p in providers),
    )
    return providers


def find(
    providers: list[Provider], provider_name: str, model_id: str
) -> tuple[Provider, Model] | None:
    for p in providers:
        if p.name != provider_name:
            continue
        for m in p.models:
            if m.id == model_id:
                return p, m
    return None
