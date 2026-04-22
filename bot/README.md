# FreeGPT Telegram Bot

Telegram-бот поверх реестра из [`../data.json`](../data.json), который даёт доступ к бесплатным LLM-провайдерам в одном окне.

Сейчас в проекте уже есть:
- выбор провайдера и модели
- persistent reply keyboard под полем ввода
- streaming-ответы
- voice transcription через Groq Whisper
- vision для фото
- fallback-цепочка между провайдерами
- toggles для reasoning и показа thoughts
- фильтрация битых моделей из меню
- Ralph-style durable memory для каждого пользователя

## Что умеет

- **Reply keyboard** вместо чисто slash UX:
  - `🤖 Модель`
  - `📡 Провайдеры`
  - `🧠 Memory`
  - `🧠 Reasoning: ON/OFF`
  - `💭 Thoughts: ON/OFF`
  - `⚙️ Reasoning`
  - `♻️ Сброс`
  - `ℹ️ Помощь`
- **Стриминг ответа** через редактирование placeholder-сообщения.
- **Durable memory** в стиле Ralph для каждого пользователя:
  - `prd.json` с machine-readable session state
  - `progress.txt` как append-only log
  - `AGENTS.md` для distilled memory
  - `history.jsonl` для восстановления контекста после рестарта
  - auto-distillation старой истории в `AGENTS.md`
- **Команды памяти**:
  - `/remember <note>`
  - `/memory`
  - `/memoryexport`
- **История диалога** переживает рестарты и собирается из файлов, а не только из RAM.
- **Vision** для фото, с автоматическим fallback на vision-capable модель.
- **Voice / audio** через Groq Whisper.
- **Reasoning controls**:
  - `/thinking on|off`
  - `/showthinking on|off`
  - `/thinkingstatus`
- **Fallback chain** при 429/5xx и таймаутах.

## Рабочие провайдеры в текущем MVP

Бот специально показывает только модели, которые мы реально провалидировали живыми запросами.

Сейчас в коде оставлены:

- **GitHub Models**
  - `gpt-4.1`
  - `gpt-4.1-mini`
  - `gpt-4o`
  - `DeepSeek-R1`
- **Groq**
  - `llama-3.3-70b-versatile`
  - `llama-3.1-8b-instant`
- **LLM7.io**
  - `deepseek-r1-0528`
  - `deepseek-v3-0324`
  - `gemini-2.5-flash-lite`
  - `gpt-4o-mini`
  - `mistral-small-3.1-24b`

Это выглядит строже, чем `data.json`, но зато пользователь не кликает по мёртвым model id.

## Быстрый старт

```bash
cd free-llm-provider
python -m venv .venv && source .venv/bin/activate
pip install -r bot/requirements.txt
cp bot/.env.example bot/.env
# заполни TELEGRAM_BOT_TOKEN и хотя бы один ключ провайдера
python -m bot.main
```

## Прод-режим

На сервере бот удобно гонять через systemd:

```ini
[Unit]
Description=Free LLM Provider Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/free-llm-provider
ExecStart=/path/to/free-llm-provider/.venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

## Переменные окружения

Обязательная:
- `TELEGRAM_BOT_TOKEN`

Поддержанные провайдеры в конфиге:
- `COHERE_API_KEY`
- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`
- `ZHIPU_API_KEY`
- `CEREBRAS_API_KEY`
- `GITHUB_TOKEN`
- `GROQ_API_KEY`
- `HF_TOKEN`
- `KILO_API_KEY`
- `LLM7_API_KEY`
- `MODELSCOPE_API_KEY`
- `NVIDIA_API_KEY`
- `OPENROUTER_API_KEY`
- `SILICONFLOW_API_KEY`

Важно: не все провайдеры из списка сейчас включены в живое меню. Часть требует отдельной интеграции или валидации model ids.

Дополнительно:
- `MEMORY_ROOT` — директория для durable memory (по умолчанию `bot/runtime-memory/users`)

## Текущие ограничения

- **Durable memory file-based**, но пока без Redis/Postgres и без сложной конкурентной синхронизации.
- **Hugging Face временно выключен в MVP**, потому что его serverless endpoint не OpenAI-compatible в текущей реализации.
- **Cloudflare Workers AI** и **Ollama Cloud** пропущены, потому что не ложатся в текущий OpenAI-compatible слой.
- **Централизованные ключи**: все пользователи делят лимиты владельца.

## Что логично делать дальше

- healthcheck моделей на старте
- richer distillation rules for AGENTS.md
- persistent storage backend (Redis / SQLite / Postgres) поверх текущего file-based memory
- BYOK
- OpenRouter / Gemini / Mistral интеграции с live validation
- inline actions вроде regenerate / shorter / smarter

## Структура

```text
bot/
├── main.py
├── config.py
├── providers/
│   ├── registry.py
│   └── client.py
├── llm/
│   ├── complete.py
│   └── transcribe.py
├── handlers/
│   ├── chat.py
│   ├── memory.py
│   ├── model.py
│   ├── reasoning.py
│   ├── reset.py
│   ├── start.py
│   ├── vision.py
│   └── voice.py
├── storage/
│   └── session.py
└── utils/
    ├── reply_keyboard.py
    └── streaming.py
```
