from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROVIDER_ENV_VAR: dict[str, str] = {
    "Cohere": "COHERE_API_KEY",
    "Google Gemini": "GEMINI_API_KEY",
    "Mistral AI": "MISTRAL_API_KEY",
    "Z AI (Zhipu AI)": "ZHIPU_API_KEY",
    "Cerebras": "CEREBRAS_API_KEY",
    "GitHub Models": "GITHUB_TOKEN",
    "Groq": "GROQ_API_KEY",
    "Hugging Face": "HF_TOKEN",
    "Kilo Code": "KILO_API_KEY",
    "LLM7.io": "LLM7_API_KEY",
    "ModelScope": "MODELSCOPE_API_KEY",
    "NVIDIA NIM": "NVIDIA_API_KEY",
    "OpenRouter": "OPENROUTER_API_KEY",
    "SiliconFlow": "SILICONFLOW_API_KEY",
}

# Providers whose APIs aren't OpenAI-compatible — skipped from /model for MVP.
UNSUPPORTED_PROVIDERS: set[str] = {
    "Cloudflare Workers AI",
    "Ollama Cloud",
    # HF Serverless Inference is not OpenAI-compatible in this MVP wiring.
    "Hugging Face",
}

# Providers that work without an API key (degraded / anonymous tier).
KEYLESS_PROVIDERS: set[str] = {"LLM7.io"}

# Some providers need a base_url different from what data.json advertises
# (e.g. Gemini exposes an OpenAI-compatible sub-path).
BASE_URL_OVERRIDES: dict[str, str] = {
    "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

DATA_JSON_PATH: Path = Path(
    os.getenv("DATA_JSON_PATH") or (Path(__file__).parent.parent / "data.json")
).resolve()

HISTORY_LIMIT: int = int(os.getenv("HISTORY_LIMIT", "20"))

MEMORY_ROOT: Path = Path(
    os.getenv("MEMORY_ROOT") or (Path(__file__).parent / "runtime-memory" / "users")
).resolve()

SYSTEM_PROMPT: str | None = os.getenv("SYSTEM_PROMPT") or None


def provider_keys() -> dict[str, str]:
    """Map of provider_name -> api_key for providers with a value in env."""
    out: dict[str, str] = {}
    for name, var in PROVIDER_ENV_VAR.items():
        val = os.getenv(var, "").strip()
        if val:
            out[name] = val
    return out


def groq_api_key() -> str | None:
    val = os.getenv("GROQ_API_KEY", "").strip()
    return val or None
