# FreeGPT Telegram Bot

Telegram-бот, дающий доступ в одном окне ко всем LLM-провайдерам из
корневого [`data.json`](../data.json) этого репозитория. 14 провайдеров с
постоянным бесплатным тиром, автоматические фоллбеки при ошибках, vision
для фото и транскрипция голосовых через Groq Whisper.

## Возможности

- **`/model`** — инлайн-клавиатура: сначала провайдер, потом модель. Список
  собирается из `data.json` при старте.
- **Стриминг ответа.** Бот дописывает сообщение по мере генерации.
- **История диалога** — последние 20 сообщений на юзера, `/reset` чистит.
- **Vision.** Шлёшь фото — бот прогоняет через vision-модель (Gemini 2.5,
  Pixtral, Llama-4-Scout и т.п.). Если текущая модель не поддерживает
  картинки, переключается автоматически.
- **Голосовые.** `voice`/`audio` → Groq Whisper (`whisper-large-v3-turbo`,
  бесплатно) → обычный чат-пайплайн. В истории остаётся транскрипт.
- **Фоллбеки.** При 429/5xx/таймаутах бот переходит на следующую модель
  из `GLOBAL_FALLBACK_CHAIN` (Groq → Gemini → Cerebras → Mistral →
  OpenRouter → LLM7.io) и уведомляет юзера одной строкой.

## Быстрый старт

```bash
cd free-llm-provider
python -m venv .venv && source .venv/bin/activate
pip install -r bot/requirements.txt
cp bot/.env.example bot/.env
# отредактируй bot/.env — минимум TELEGRAM_BOT_TOKEN и один ключ провайдера
python -m bot.main
```

Самый быстрый путь к рабочему боту:
1. [@BotFather](https://t.me/BotFather) → `/newbot` → получи токен.
2. [console.groq.com/keys](https://console.groq.com/keys) — регистрация без
   карты, `GROQ_API_KEY` покрывает сразу и текстовые модели, и Whisper.
3. Впиши оба в `bot/.env`, запусти `python -m bot.main`.

## Переменные окружения

Обязательная: `TELEGRAM_BOT_TOKEN`.

Провайдеры (любой набор — недоступные скрываются из `/model`):

| Переменная | Провайдер |
|---|---|
| `COHERE_API_KEY` | Cohere |
| `GEMINI_API_KEY` | Google Gemini |
| `MISTRAL_API_KEY` | Mistral AI |
| `ZHIPU_API_KEY` | Z AI (Zhipu AI) |
| `CEREBRAS_API_KEY` | Cerebras |
| `GITHUB_TOKEN` | GitHub Models |
| `GROQ_API_KEY` | Groq + Whisper (voice) |
| `HF_TOKEN` | Hugging Face |
| `KILO_API_KEY` | Kilo Code |
| `LLM7_API_KEY` | LLM7.io (работает и без ключа) |
| `MODELSCOPE_API_KEY` | ModelScope |
| `NVIDIA_API_KEY` | NVIDIA NIM |
| `OPENROUTER_API_KEY` | OpenRouter |
| `SILICONFLOW_API_KEY` | SiliconFlow |

Ссылки на получение ключей — в [`.env.example`](.env.example) и в
[`../free-llm-apis/references/`](../free-llm-apis/references/).

## Ограничения

- **Cloudflare Workers AI** и **Ollama Cloud** пропущены: их API не
  OpenAI-совместимые.
- **State в памяти.** При рестарте истории и выбранные модели
  обнуляются. Для продакшена замени `bot/storage/session.py` на Redis.
- **Централизованные ключи.** Все юзеры бота делят лимиты владельца.
  Следи за RPM/RPD, не разворачивай бота «для всего мира» без BYOK.

## Когда `data.json` обновится

Реестр собирается при старте. После `git pull` достаточно перезапустить
бота — новые модели появятся в `/model` автоматически. Если в репо
добавится новый провайдер, нужно:

1. Добавить одну строку в `PROVIDER_ENV_VAR` в `bot/config.py`.
2. Если провайдер не OpenAI-совместимый — добавить его в `UNSUPPORTED_PROVIDERS`.
3. При желании — вписать в `GLOBAL_FALLBACK_CHAIN` в `bot/llm/complete.py`.

## Структура

```
bot/
├── main.py              # точка входа
├── config.py            # .env, маппинг провайдер→env
├── providers/
│   ├── registry.py      # парсит data.json
│   └── client.py        # AsyncOpenAI per provider
├── llm/
│   ├── complete.py      # стриминг с fallback-цепочкой
│   └── transcribe.py    # Groq Whisper
├── handlers/            # старт, /model, chat, vision, voice, reset
├── storage/session.py   # in-memory {user_id: UserSession}
└── utils/streaming.py   # throttled edit_message_text
```
