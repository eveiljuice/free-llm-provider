#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data.json'), 'utf8'));

const HEADER = `<div align="center">
\t<br>
\t<img src="media/awesome-free-llm-apis.png" width="500" alt="FreeGPT">
\t<br>
\t<br>
\t<h1>FreeGPT — one Telegram bot, every free LLM</h1>
\t<p>Chat with 14 providers and ~60 models from a single Telegram window.<br>No credit card, no trial credits, no vendor lock-in.</p>
\t<p>
\t\t<a href="bot/README.md"><strong>Get the bot →</strong></a>
\t\t·
\t\t<a href="#providers--models">Provider list</a>
\t\t·
\t\t<a href="data.json">data.json</a>
\t</p>
\t<br>
</div>`;

const INTRO = `## What is this?

A Telegram bot, **FreeGPT** ([\`bot/\`](bot/)), plus the curated dataset it runs on ([\`data.json\`](data.json) — ${data.providers.length} providers with *permanent* free tiers, no trial credits).

Pick a provider and model with \`/model\`, send a message, and the bot streams the reply back. Photos go through a vision model, voice messages are transcribed by Groq Whisper, and if a provider rate-limits you the bot transparently fails over to the next one in the chain.

## Quick start

\`\`\`bash
git clone https://github.com/eveiljuice/free-llm-provider
cd free-llm-provider
python -m venv .venv && source .venv/bin/activate
pip install -r bot/requirements.txt
cp bot/.env.example bot/.env      # fill in TELEGRAM_BOT_TOKEN + at least one provider key
python -m bot.main
\`\`\`

Fastest path to a working bot: a BotFather token and a free [Groq key](https://console.groq.com/keys) — that single key covers text chat *and* voice transcription (Whisper).

Full setup, env vars, and troubleshooting: [\`bot/README.md\`](bot/README.md).

## Features

- **One picker, every provider.** \`/model\` opens an inline keyboard of every provider that has a key in your \`.env\`. Model list is loaded from [\`data.json\`](data.json) at startup — no hardcoded IDs.
- **Streamed replies.** The bot edits its message as tokens arrive, throttled to respect Telegram flood limits.
- **Conversation memory.** Last 20 turns per user, \`/reset\` clears it.
- **Vision.** Send a photo and the bot routes it to a multimodal model (Gemini 2.5, Pixtral, Llama-4-Scout, …). If your current model is text-only, it falls back automatically.
- **Voice → text.** Voice notes and audio files are transcribed by Groq Whisper (\`whisper-large-v3-turbo\`, free tier) and fed back into the chat pipeline.
- **Automatic provider fallback.** On \`429\`, \`5xx\`, timeouts, or connection errors the bot moves to the next model in \`GLOBAL_FALLBACK_CHAIN\` (Groq → Gemini → Cerebras → Mistral → OpenRouter → LLM7.io) and tells the user in one line.
- **Centralized keys.** Owner keeps API keys in \`.env\`; users don't see them. For large deployments replace the in-memory session store with Redis and consider BYOK.

## Providers & Models

Everything below is generated from [\`data.json\`](data.json). Keep this list truthful by editing the JSON, then run \`node scripts/generate-readme.js\`.

Two providers are shown here for completeness but **not wired into the bot** because their APIs aren't OpenAI-compatible: Cloudflare Workers AI (custom REST) and Ollama Cloud (Ollama native API).`;

function buildTable(models) {
	const lines = [];
	lines.push('| Model Name | Context | Max Output | Modality | Rate Limit |');
	lines.push('|---|---|---|---|---|');
	for (const m of models) {
		lines.push(`| ${m.name} | ${m.context} | ${m.maxOutput} | ${m.modality} | ${m.rateLimit} |`);
	}
	return lines.join('\n');
}

function buildProviderSection(provider) {
	const desc = provider.footnoteRef != null
		? `${provider.description} [^${provider.footnoteRef}]`
		: provider.description;
	const parts = [
		`### [${provider.name}](${provider.url}) ${provider.flag}`,
		'',
		desc,
	];
	if (provider.baseUrl != null) {
		parts.push('', `Base URL: \`${provider.baseUrl}\``);
	}
	parts.push('', buildTable(provider.models));
	return parts.join('\n');
}

const providerAPIs = data.providers
	.filter(p => p.category === 'provider_api')
	.sort((a, b) => a.name.localeCompare(b.name));

const inferenceProviders = data.providers
	.filter(p => p.category === 'inference_provider')
	.sort((a, b) => a.name.localeCompare(b.name));

const glossaryRows = data.glossary
	.map(g => `| **${g.abbreviation}** | ${g.meaning} |`)
	.join('\n');

const footnoteLines = data.footnotes
	.sort((a, b) => a.id - b.id)
	.map(f => `[^${f.id}]: ${f.text}`)
	.join('\n');

const parts = [
	HEADER,
	'',
	'## Contents',
	'',
	'- [What is this?](#what-is-this)',
	'- [Quick start](#quick-start)',
	'- [Features](#features)',
	'- [Providers & Models](#providers--models)',
	'  - [Provider APIs](#provider-apis)',
	'  - [Inference providers](#inference-providers)',
	'- [Contributing](#contributing)',
	'- [Glossary](#glossary)',
	'',
	INTRO,
	'',
	'### Provider APIs',
	'',
	'APIs run by the companies that train or fine-tune the models themselves.',
	'',
	providerAPIs.map(buildProviderSection).join('\n\n'),
	'',
	'### Inference providers',
	'',
	'Third-party platforms that host open-weight models from various sources.',
	'',
	inferenceProviders.map(buildProviderSection).join('\n\n'),
	'',
	'## Contributing',
	'',
	'Know a free tier that\'s missing? [Open a PR](contributing.md). Include the provider, endpoint, rate limits (link to their docs), and a few notable models. Trial credits and time-limited promos don\'t count.',
	'',
	'New provider wiring for the bot: add one line to `PROVIDER_ENV_VAR` in [`bot/config.py`](bot/config.py). If the API is OpenAI-compatible, that\'s all — the registry picks up the new provider automatically on next restart.',
	'',
	'## Glossary',
	'',
	'| Abbreviation | Meaning |',
	'|---|---|',
	glossaryRows,
	'',
	'## Notes',
	'',
	'- All endpoints are OpenAI SDK-compatible unless noted.',
	'- Each provider link points to its API key page.',
	'- Data last updated: ' + data.lastUpdated + '.',
	'',
	footnoteLines,
	'',
];

const output = parts.join('\n');
fs.writeFileSync(path.join(ROOT, 'README.md'), output);
console.log('README.md generated successfully.');
