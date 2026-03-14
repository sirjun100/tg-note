# MCP Tasks and Joplin Server

MCP server that lets an LLM query and mutate **Google Tasks** and **Joplin** notes. Standalone; config via env and optional config file.

## Features

- **Tasks (Google Tasks API):** List task lists, list/get/create/update/complete/delete tasks, pagination via `page_token`.
- **Joplin:** List folders, list notes, full-text search, get note; create/update/delete/move notes, create folders. Pagination via `offset`/`limit` and `next_offset`/`has_more`.
- **Semantic search:** Stub for vector search over note index (set `MCP_NOTE_INDEX_DB_PATH` and build index separately; see spec).

## Setup

### 1. Install

```bash
cd mcp-tasks-joplin
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configuration

**Secrets (env):** You can set these in your shell (e.g. `~/.zshrc`) or in the MCP client's `env` block. The server reads them at startup.

| Variable | Required | Description |
|----------|----------|-------------|
| `JOPLIN_URL` | Yes | Joplin API base URL (e.g. `http://localhost:41184`) |
| `JOPLIN_TOKEN` | Yes | Joplin API token |
| `GOOGLE_CLIENT_ID` | Yes | OAuth2 client ID for Google Tasks |
| `GOOGLE_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `GOOGLE_TASKS_TOKEN_JSON` | Or path | JSON string of token, or use `GOOGLE_TASKS_TOKEN_PATH` |
| `GOOGLE_TASKS_TOKEN_PATH` | Or JSON | Path to token JSON file |

**Non-secrets:** Copy `config.json.example` to `config.json` and adjust timeouts, pagination, etc. Env overrides file.

**Google token:** Run a one-time OAuth flow (e.g. with the main telegram-joplin bot or a small script) to obtain `access_token` and `refresh_token`; save as JSON and set `GOOGLE_TASKS_TOKEN_PATH` or `GOOGLE_TASKS_TOKEN_JSON`.

### 3. Add to Cursor (or other MCP client)

Example (paths and env depend on your machine):

```json
{
  "mcpServers": {
    "tasks-and-joplin": {
      "command": "/path/to/mcp-tasks-joplin/.venv/bin/python",
      "args": ["-m", "mcp_tasks_joplin.server"],
      "cwd": "/path/to/mcp-tasks-joplin",
      "env": {
        "JOPLIN_URL": "http://localhost:41184",
        "JOPLIN_TOKEN": "${JOPLIN_TOKEN}",
        "GOOGLE_CLIENT_ID": "...",
        "GOOGLE_CLIENT_SECRET": "...",
        "GOOGLE_TASKS_TOKEN_PATH": "/path/to/token.json"
      }
    }
  }
}
```

If your MCP client doesn't expand `${JOPLIN_TOKEN}`, use the literal token value instead.

## Tools

- **tasks_list_lists** — List all task lists  
- **tasks_list_tasks** — List tasks (with filters, limit, page_token)  
- **tasks_get_task** — Get one task  
- **tasks_create** / **tasks_update** / **tasks_complete** / **tasks_delete**  
- **joplin_list_folders** / **joplin_get_folder** / **joplin_list_notes** / **joplin_get_note** / **joplin_search**  
- **joplin_semantic_search** — Vector search (requires index; see spec)  
- **joplin_create_note** / **joplin_update_note** / **joplin_delete_note** / **joplin_move_note** / **joplin_create_folder**

## Spec

See [docs/mcp-tasks-joplin-spec.md](../docs/mcp-tasks-joplin-spec.md) in the parent repo for full tool parameters, pagination contract, and implementation notes.
