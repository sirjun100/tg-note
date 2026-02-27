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

## Architecture

```
telegram-joplin/
├── main.py                        # Entry point
├── config.py                      # Backward-compat shim → src/settings.py
├── src/
│   ├── settings.py                # Pydantic-settings config (env vars, .env)
│   ├── constants.py               # Magic numbers, thresholds, indicators
│   ├── exceptions.py              # Domain exceptions (JoplinError, LLMError, …)
│   ├── container.py               # Service container / dependency injection
│   ├── log_config.py              # Structured logging (structlog)
│   ├── health_server.py           # HTTP health check for Fly.io
│   │
│   ├── handlers/                  # Telegram command & message handlers
│   │   ├── __init__.py            # Registers all handler modules
│   │   ├── core.py                # /start, /status, /helpme, message routing
│   │   ├── google_tasks.py        # /authorize_google_tasks, /list_inbox_tasks, …
│   │   ├── reports.py             # /daily_report, /configure_report_time, …
│   │   ├── braindump.py           # /braindump, /braindump_stop
│   │   └── reorg.py               # /reorg_status, /reorg_init, /enrich_notes, …
│   │
│   ├── telegram_orchestrator.py   # Thin coordinator — wires services & handlers
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
│   ├── conftest.py                # Shared fixtures
│   └── …
├── docs/                          # Historical docs & sprint summaries
├── .github/workflows/ci.yml       # CI/CD (ruff, mypy, pytest, deploy)
├── Dockerfile                     # Bot container
├── Dockerfile.joplin              # Headless Joplin container
├── docker-compose.yml             # Local Docker setup
├── fly.toml                       # Fly.io config (bot)
├── fly.joplin.toml                # Fly.io config (Joplin)
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

### Local Setup

```bash
git clone <repository-url>
cd telegram-joplin
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys: TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY, ALLOWED_TELEGRAM_USER_IDS, JOPLIN_WEB_CLIPPER_TOKEN

python main.py
```

### Docker

```bash
cp .env.example .env   # edit with your keys
docker-compose up -d --build
docker-compose logs -f
```

Data persists in `./data/` (bot databases) and `./joplin-data/` (Joplin notes).

## Fly.io Deployment

Deploy both the bot and a headless Joplin instance to [Fly.io](https://fly.io).

### 1. Deploy Joplin

```bash
fly launch -c fly.joplin.toml --no-deploy
fly volumes create joplin_data --region lax --size 1 -a joplin
fly deploy -c fly.joplin.toml
```

### 2. Deploy the Bot

```bash
fly launch --no-deploy
fly volumes create telegram_joplin_data --region lax --size 1 -a telegram-joplin
```

### 3. One-Time Joplin Setup

```bash
fly ssh console -a joplin
joplin config sync.target 7   # Dropbox
joplin sync                    # follow the URL, authorize, paste code
joplin config api.token        # copy the token
exit
```

### 4. Set Secrets & Deploy

```bash
fly secrets set \
  TELEGRAM_BOT_TOKEN=… \
  ALLOWED_TELEGRAM_USER_IDS=… \
  DEEPSEEK_API_KEY=… \
  JOPLIN_WEB_CLIPPER_TOKEN=… \
  -a telegram-joplin

fly deploy -a telegram-joplin
```

Use the same region for both apps. Edit `primary_region` in `fly.toml` / `fly.joplin.toml` if needed.

## Google Tasks Integration

1. Create a Google Cloud project and enable the **Google Tasks API**
2. Create OAuth 2.0 credentials (Desktop app)
3. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`
4. In Telegram, run `/authorize_google_tasks` and follow the flow

## Joplin Web Clipper Token

Joplin requires an API token passed as `?token=…`. To configure:

1. Open Joplin → Tools → Options → Web Clipper
2. Copy (or generate) the authorization token
3. Set `JOPLIN_WEB_CLIPPER_TOKEN` in `.env`

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
