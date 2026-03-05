# External API Reference

This document lists every external API the bot uses, why we chose it, what it costs, and its capabilities. Use this when evaluating new features or troubleshooting integrations.

---

## Summary

| API | Purpose | Cost | Env Variable | Required? |
|-----|---------|------|--------------|-----------|
| [Telegram Bot API](#telegram-bot-api) | User interface | Free | `TELEGRAM_BOT_TOKEN` | Yes |
| [DeepSeek](#deepseek-llm) | LLM (note generation, classification, conversations) | ~$0.14/M input tokens | `DEEPSEEK_API_KEY` | Yes (default provider) |
| [Joplin Web Clipper](#joplin-web-clipper-api) | Note storage | Free (self-hosted) | `JOPLIN_WEB_CLIPPER_TOKEN` | Yes |
| [Google Tasks API](#google-tasks-api) | Task management | Free | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional |
| [Gemini (Google AI Studio)](#gemini-google-ai-studio) | Image generation, OCR, vision | Free tier | `GEMINI_API_KEY` | Optional |
| [PageShot](#pageshot) | URL screenshots | Free | None (no key) | Optional |
| [OpenAI](#openai) | Alternative LLM provider | ~$3–15/M tokens | `OPENAI_API_KEY` | Optional |
| [Ollama](#ollama) | Local LLM (no cloud) | Free (self-hosted) | `OLLAMA_BASE_URL` | Optional |

---

## Preferred Stack

For a personal-use bot deployed on Fly.io (`shared-cpu-1x`, 1 GB RAM):

| Role | Preferred API | Why |
|------|--------------|-----|
| **LLM** | DeepSeek | Best cost/quality ratio, OpenAI-compatible API |
| **Vision / OCR** | Gemini 1.5 Flash | Free tier, excellent quality, context-aware (not just raw OCR) |
| **Image generation** | Gemini (image model) | Free tier, already configured |
| **Screenshots** | PageShot | Free, no API key, no infrastructure |
| **Notes** | Joplin CLI (in-container) | Free, self-hosted, full control |
| **Tasks** | Google Tasks | Free, widely used, good API |

---

## API Details

### Telegram Bot API

| | |
|---|---|
| **Purpose** | Receive messages from users, send responses |
| **Used in** | `src/handlers/`, `src/telegram_orchestrator.py` |
| **Base URL** | `https://api.telegram.org/bot{token}/` |
| **Auth** | Bot token from @BotFather |
| **Cost** | Free |
| **Rate limits** | 30 messages/second, 20 messages/minute per chat |
| **Env var** | `TELEGRAM_BOT_TOKEN` |

**Capabilities used:**
- Webhook and polling modes
- Text messages, inline keyboards
- Photo downloads (for future OCR feature)
- Message editing (progress indicators)

---

### DeepSeek LLM

| | |
|---|---|
| **Purpose** | Primary LLM for note generation, content classification, PARA routing, conversations |
| **Used in** | `src/llm_providers.py` (DeepSeekProvider), `src/llm_orchestrator.py` |
| **Base URL** | `https://api.deepseek.com/chat/completions` |
| **Auth** | Bearer token |
| **Cost** | ~$0.14/M input, ~$0.28/M output (deepseek-chat) |
| **Rate limits** | Generous for personal use |
| **Env vars** | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` (default: `deepseek-chat`) |

**Why DeepSeek over alternatives:**
- 10-50x cheaper than OpenAI GPT-4 for comparable quality
- OpenAI-compatible API format (easy to switch)
- Fast response times
- Handles structured JSON output well (folder/tag decisions)

**Capabilities used:**
- Chat completions (multi-turn conversations)
- Function calling (for structured decisions)
- System prompts (personas: GTD coach, stoic mentor, note librarian)

**Limitations:**
- No vision/image support (use Gemini for that)
- No image generation (use Gemini for that)

---

### Joplin Web Clipper API

| | |
|---|---|
| **Purpose** | CRUD operations on notes, folders, tags, and resources |
| **Used in** | `src/joplin_client.py` |
| **Base URL** | `http://localhost:41184` (same container on Fly.io) |
| **Auth** | Token query parameter (`?token=...`) |
| **Cost** | Free (Joplin CLI runs in the Docker container) |
| **Rate limits** | None (localhost) |
| **Env vars** | `JOPLIN_WEB_CLIPPER_TOKEN`, `JOPLIN_WEB_CLIPPER_PORT` |

**Capabilities used:**
- `GET /notes` — list and search notes
- `POST /notes` — create notes with markdown body
- `PUT /notes/:id` — update notes
- `GET /folders` — list folder tree (PARA structure)
- `POST /folders` — create folders
- `GET /tags` — list tags
- `POST /tags` — create and assign tags
- `POST /resources` — upload attachments (images)
- `GET /search` — full-text search

**Architecture note:** Joplin CLI runs inside the same Docker container as the bot. The entrypoint starts `joplin server` in the background on port 41184 before launching the bot. See [Fly.io deployment docs](fly-io-joplin-deployment.md).

---

### Google Tasks API

| | |
|---|---|
| **Purpose** | Create, list, and manage tasks extracted from user messages |
| **Used in** | `src/task_service.py`, `src/handlers/google_tasks.py` |
| **Base URL** | `https://tasks.googleapis.com/tasks/v1/` |
| **Auth** | OAuth 2.0 (user grants access, refresh token stored) |
| **Cost** | Free |
| **Rate limits** | 50,000 queries/day |
| **Env vars** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |

**Capabilities used:**
- List task lists
- Create tasks (title, notes, due date)
- List tasks (with completion status filter)
- Update task status (complete/incomplete)

**Setup:** Requires a Google Cloud project with Tasks API enabled and OAuth consent screen configured. Users authorize via `/authorize_google_tasks` command. See [OAuth docs](google-tasks-oauth-and-token-refresh.md).

---

### Gemini (Google AI Studio)

| | |
|---|---|
| **Purpose** | Recipe image generation (current), OCR/vision (planned FR-030), image understanding |
| **Used in** | `src/recipe_image.py` |
| **Base URL** | `https://generativelanguage.googleapis.com/v1beta/` |
| **Auth** | API key query parameter |
| **Cost** | **Free tier** — see limits below |
| **Env var** | `GEMINI_API_KEY` |

**Free tier limits (as of 2026):**

| Model | RPM | TPM | RPD |
|-------|-----|-----|-----|
| Gemini 1.5 Flash | 15 | 1,000,000 | 1,500 |
| Gemini 2.5 Flash (image gen) | 10 | — | 500 |

These limits are more than sufficient for personal use (a few dozen interactions per day).

**Capabilities and what we use them for:**

| Capability | Model | Current use | Planned use |
|------------|-------|-------------|-------------|
| **Image generation** | `gemini-2.5-flash-image` | Recipe images (`src/recipe_image.py`) | — |
| **Vision / OCR** | `gemini-1.5-flash` | — | FR-030: Photo OCR capture |
| **Text generation** | `gemini-1.5-flash` | — | Could serve as fallback LLM |
| **Structured output** | `gemini-1.5-flash` | — | FR-030: JSON extraction from images |

**Why Gemini for vision/OCR (FR-030):**
- Already have the API key configured
- Free tier covers personal use
- Does more than raw OCR — understands context (receipts, business cards, whiteboards)
- Single API call does OCR + classification + structured data extraction
- No Docker image bloat (vs Tesseract adding ~150MB)
- No RAM pressure on the 1GB Fly.io VM

**Image generation flow** (current, in `src/recipe_image.py`):
1. Send text prompt describing the dish
2. Receive inline image data (base64 PNG)
3. Embed as data URL in Joplin note

**Vision/OCR flow** (planned, FR-030):
1. Send photo as base64 inline data
2. Ask Gemini to extract text + classify content type + suggest title
3. Receive structured JSON with extracted text and metadata
4. Use extracted text for PARA routing via DeepSeek

---

### PageShot

| | |
|---|---|
| **Purpose** | Capture webpage screenshots for URL-based notes |
| **Used in** | `src/url_screenshot.py` |
| **Base URL** | `https://pageshot.site/v1/screenshot` |
| **Auth** | None (no API key required) |
| **Cost** | Free |
| **Rate limits** | 30 req/min per IP |
| **Env var** | None |

**Capabilities used:**
- POST a URL, receive PNG screenshot
- Configurable viewport (1280x720 default)
- Full page or viewport-only capture

**Limitations:**
- No auth support (can't screenshot login-protected pages)
- Occasional timeouts on slow pages

---

### OpenAI

| | |
|---|---|
| **Purpose** | Alternative LLM provider |
| **Used in** | `src/llm_providers.py` (OpenAIProvider) |
| **Auth** | Bearer token |
| **Cost** | GPT-4o: ~$2.50/M input, $10/M output |
| **Env var** | `OPENAI_API_KEY` |

Available as a provider option (`LLM_PROVIDER=openai`) but **not the default** due to cost. Use when you need specific OpenAI capabilities or prefer GPT models.

---

### Ollama

| | |
|---|---|
| **Purpose** | Local LLM (no cloud, no API costs, full privacy) |
| **Used in** | `src/llm_providers.py` (OllamaProvider) |
| **Base URL** | `http://localhost:11434` (configurable) |
| **Auth** | None |
| **Cost** | Free (runs on your hardware) |
| **Env vars** | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default: `llama2`) |

Available as a provider option (`LLM_PROVIDER=ollama`). Best for local development or when privacy is paramount. Not suitable for Fly.io deployment (insufficient GPU/RAM).

---

## Provider Selection Guide

### For Fly.io deployment (recommended)

```
LLM_PROVIDER=deepseek       # Cheap, fast, good quality
DEEPSEEK_API_KEY=...         # ~$1-2/month for personal use
GEMINI_API_KEY=...           # Free tier for images + OCR
```

### For local development

```
LLM_PROVIDER=ollama          # Free, private, no API costs
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### For maximum quality (higher cost)

```
LLM_PROVIDER=openai          # Best-in-class models
OPENAI_API_KEY=...           # ~$10-30/month depending on usage
GEMINI_API_KEY=...           # Still free for images + OCR
```

---

## Cost Estimate (Personal Use on Fly.io)

| Service | Monthly estimate |
|---------|-----------------|
| Fly.io compute (sleep when idle) | ~$0–4 |
| DeepSeek API | ~$1–2 |
| Gemini | $0 (free tier) |
| Google Tasks | $0 (free) |
| PageShot | $0 (free) |
| Joplin | $0 (self-hosted) |
| **Total** | **~$1–6/month** |
