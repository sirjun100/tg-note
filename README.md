# Intelligent Joplin Librarian

A Telegram bot that uses AI to intelligently create, organize, and manage notes in Joplin — with Google Tasks integration, GTD brain dumps, daily priority reports, and database reorganization.

## Features

- **AI-powered note creation** — send natural language, get structured Joplin notes
- **Google Tasks integration** — action items automatically become tasks
- **GTD brain dump** — interactive mind-sweep sessions via `/braindump`
- **Daily priority reports** — aggregated view of notes, tasks, and pending items
- **Joplin reorganization** — PARA-based folder structure with AI enrichment
- **Multiple LLM providers** — OpenAI, DeepSeek, and Ollama supported
- **Whitelist access control** — only authorized Telegram users can interact
- **Zero-cost when idle** — Fly.io machine sleeps between messages

## Architecture

The bot and Joplin CLI run in a **single container**. Joplin starts first, then the bot connects to it on `localhost:41184`. On Fly.io the machine auto-stops when idle and wakes in ~10 seconds when you send a message (via Telegram webhooks).

```
telegram-joplin/
├── main.py                        # Entry point
├── entrypoint.sh                  # Starts Joplin, waits, then starts bot
├── Dockerfile                     # Unified: Python + Node.js + Joplin CLI + bot
├── config.py                      # Backward-compat shim → src/settings.py
├── src/
│   ├── settings.py                # Pydantic-settings config (env vars, .env)
│   ├── constants.py               # Magic numbers, thresholds, indicators
│   ├── exceptions.py              # Domain exceptions (JoplinError, LLMError, …)
│   ├── container.py               # Service container / dependency injection
│   ├── log_config.py              # Structured logging (structlog)
│   ├── webhook_server.py          # Async HTTP: health checks + Telegram webhooks
│   │
│   ├── handlers/                  # Telegram command & message handlers
│   │   ├── core.py                # /start, /status, /helpme, message routing
│   │   ├── google_tasks.py        # /authorize_google_tasks, /list_inbox_tasks, …
│   │   ├── reports.py             # /daily_report, /configure_report_time, …
│   │   ├── braindump.py           # /braindump, /braindump_stop
│   │   └── reorg.py               # /reorg_status, /reorg_init, /enrich_notes, …
│   │
│   ├── telegram_orchestrator.py   # Thin coordinator — webhook or polling mode
│   ├── joplin_client.py           # Async Joplin Web Clipper API (httpx)
│   ├── llm_orchestrator.py        # AI processing with structured outputs
│   ├── llm_providers.py           # Provider abstraction (OpenAI, Ollama, DeepSeek)
│   ├── state_manager.py           # SQLite conversation state
│   ├── logging_service.py         # Decision / message / tag audit logging
│   ├── security_utils.py          # Whitelist, validation, error formatting
│   ├── report_generator.py        # Daily priority report generation
│   ├── scheduler_service.py       # Scheduled report delivery
│   ├── reorg_orchestrator.py      # PARA reorganization engine
│   ├── enrichment_service.py      # AI metadata enrichment for notes
│   ├── task_service.py            # Google Tasks bridge
│   ├── google_tasks_client.py     # Google Tasks OAuth + API
│   └── auth_service.py            # OAuth helpers
│
├── tests/                         # Test suite
├── docs/                          # Historical docs & sprint summaries
├── .github/workflows/ci.yml       # CI/CD (ruff, mypy, pytest, deploy)
├── docker-compose.yml             # Local Docker (single service)
├── fly.toml                       # Fly.io config (single machine)
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Dev dependencies (ruff, mypy, pytest)
└── ruff.toml                      # Linter config
```

## Quick Start

### Prerequisites

- Python 3.10+
- [Joplin](https://joplinapp.org/) with Web Clipper enabled (port 41184)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- An LLM provider API key (DeepSeek recommended)

### Local Setup (polling mode — no public URL needed)

```bash
git clone <repository-url>
cd telegram-joplin
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY, ALLOWED_TELEGRAM_USER_IDS, JOPLIN_WEB_CLIPPER_TOKEN

python main.py
```

### Docker (local)

```bash
cp .env.example .env   # edit with your keys
docker-compose up -d --build
docker-compose logs -f
```

Data persists in `./data/` (bot databases + Joplin notes in subdirectories).

## Fly.io Deployment

Everything runs on a **single machine** that sleeps when you're not using it and wakes up when you send a message (~10 second cold start).

### 1. Create App & Volume

```bash
fly launch --no-deploy
fly volumes create telegram_joplin_data --region lax --size 1 -a telegram-joplin
```

### 2. One-Time Joplin Setup

Deploy first, then SSH in to configure Joplin sync:

```bash
fly deploy

# SSH into the running machine
fly ssh console

# Inside the container:
joplin config sync.target 7 --profile /app/data/joplin   # Dropbox
joplin sync --profile /app/data/joplin                     # follow the URL, authorize, paste code
joplin config api.token --profile /app/data/joplin         # copy this token
exit
```

### 3. Set Secrets

```bash
fly secrets set \
  TELEGRAM_BOT_TOKEN=your_bot_token \
  ALLOWED_TELEGRAM_USER_IDS=your_user_id \
  DEEPSEEK_API_KEY=your_key \
  JOPLIN_WEB_CLIPPER_TOKEN=the_token_from_step_2
```

The machine will restart and auto-register the Telegram webhook. The bot is live.

### How Auto-Sleep Works

1. You send a message to the bot in Telegram
2. Telegram POSTs to `https://telegram-joplin.fly.dev/webhook`
3. Fly.io sees the request, boots the machine (~3s), starts Joplin (~5s), starts bot (~2s)
4. Bot processes your message and responds
5. After ~5 minutes of no traffic, machine stops — **costs $0 while sleeping**

### Updating

```bash
fly deploy
```

## Google Tasks Integration

1. Create a Google Cloud project and enable the **Google Tasks API**
2. Create OAuth 2.0 credentials (Desktop app)
3. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env` (or `fly secrets set`)
4. In Telegram, run `/authorize_google_tasks` and follow the flow

## Joplin Web Clipper Token

Joplin requires an API token passed as `?token=…`. To configure:

1. Open Joplin → Tools → Options → Web Clipper
2. Copy (or generate) the authorization token
3. Set `JOPLIN_WEB_CLIPPER_TOKEN` in `.env`

For headless/Docker: use `joplin config api.token --profile <path>` to retrieve it.

## Development

```bash
pip install -r requirements-dev.txt

ruff check .          # lint
ruff format .         # auto-format
mypy src/             # type-check
pytest tests/ -v      # run tests
```

CI runs automatically on push via GitHub Actions (see `.github/workflows/ci.yml`).

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/status` | Check Joplin & Google Tasks connectivity |
| `/helpme` | Full command reference |
| `/braindump` | Start GTD mind-sweep session |
| `/daily_report` | Generate priority report |
| `/list_inbox_tasks` | View pending Google Tasks |
| `/reorg_status` | Joplin organization health |
| `/reorg_init status\|roles` | Initialize PARA folders |
| `/enrich_notes [n]` | AI-enrich notes with metadata |

Run `/helpme` in the bot for the complete list.
