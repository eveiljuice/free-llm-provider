# free-llm-provider

`free-llm-provider` is a small project built around one practical idea:

> keep a curated registry of free / permanent-free LLM APIs and use it as a live source for a Telegram bot.

So this repo is **not just a list of providers** anymore.
It now has two product layers:

1. **`data.json`** — structured registry of free LLM providers, models, limits, and endpoints.
2. **`bot/`** — Telegram bot that uses this registry to let users chat with working free models in one interface.

---

## What the project does

### Registry layer
The root of the repo contains a maintained dataset of providers that offer:
- permanent free tiers
- free quotas
- prototype-friendly API access
- OpenAI-compatible or near-compatible chat endpoints

This data lives in:
- `data.json`
- `README.md`
- `scripts/generate-readme.js`

### Bot layer
The bot inside [`bot/`](bot/README.md) turns that registry into an actual product:
- provider picker
- model picker
- streaming responses
- fallback routing
- vision for photos
- voice transcription via Groq Whisper
- reasoning toggles
- Telegram reply keyboard UX

---

## Project structure

```text
.
├── README.md                  # project overview
├── data.json                  # structured provider/model registry
├── scripts/
│   └── generate-readme.js     # generates provider-list style docs
├── media/
│   └── awesome-free-llm-apis.png
├── free-llm-apis/             # references / skill assets
└── bot/
    ├── README.md              # bot-specific docs
    ├── main.py
    ├── config.py
    ├── providers/
    ├── handlers/
    ├── llm/
    ├── storage/
    └── utils/
```

---

## Current bot capabilities

The Telegram bot currently supports:
- **reply keyboard controls** under the message input
- **provider and model selection**
- **streamed answers**
- **automatic fallback** when a provider fails
- **voice / audio transcription** through Groq Whisper
- **vision input** for photos
- **reasoning mode toggles**
- **filtering of broken models from the user-facing menu**

See full docs in [`bot/README.md`](bot/README.md).

---

## Current MVP philosophy

This repo prefers **working models over inflated model counts**.

A big lesson from real usage was that many public provider catalogs contain:
- stale model IDs
- region-locked models
- models that exist in docs but are unavailable to a конкретный token
- endpoints that are not truly OpenAI-compatible in practice

Because of that, the bot now intentionally shows only models that were validated in real requests.

---

## Quick start

### Use the registry only
If you just want the provider data, use:
- `data.json`
- generated docs in the root README / references

### Run the bot
```bash
cd free-llm-provider
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt
cp bot/.env.example bot/.env
# fill TELEGRAM_BOT_TOKEN and one or more provider keys
python -m bot.main
```

For production bot setup, see [`bot/README.md`](bot/README.md).

---

## Why this project exists

Most “free LLM” repos stop at documentation.
This project tries to go one step further:
- keep the registry structured
- turn it into a usable bot
- validate real models instead of blindly trusting provider marketing
- make experimentation fast for Telegram users

---

## Roadmap ideas

- live model healthchecks on startup
- persistent user state (Redis / SQLite / Postgres)
- BYOK support
- better provider probing and automatic filtering
- OpenRouter / Gemini / Mistral expansion
- inline actions like regenerate / shorter / smarter

---

## Related docs

- Bot docs: [`bot/README.md`](bot/README.md)
- Contribution guide: [`contributing.md`](contributing.md)

---

## License

See [`license`](license).
