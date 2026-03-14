# MCP Server Spec: Tasks + Joplin

Spec for a standalone MCP server that lets an LLM query and mutate **Google Tasks** and **Joplin** notes. Live in a **separate repo**; config via env + config file.

---

## 1. Overview

- **Name (suggested):** `mcp-tasks-joplin` (or `tasks-and-joplin` in Cursor).
- **Scope:** One server, two domains: **Tasks** (Google Tasks API) and **Joplin** (REST API + optional semantic search).
- **Config:** Secrets in env; non-secrets in a config file (e.g. `config.json` or `mcp.yaml`).

---

## 2. Configuration

### 2.1 Environment variables (secrets)

| Variable | Required | Description |
|----------|----------|-------------|
| `JOPLIN_URL` | Yes | Joplin API base URL (e.g. `http://localhost:41184`) |
| `JOPLIN_TOKEN` | Yes | Joplin API token |
| `GOOGLE_CLIENT_ID` | Yes | OAuth2 client ID for Google Tasks |
| `GOOGLE_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `GOOGLE_TASKS_TOKEN_JSON` | Or file path | In-memory: JSON string of token `{ "access_token": "...", "refresh_token": "...", ... }`. Alternatively use `GOOGLE_TASKS_TOKEN_PATH` to read from file. |
| `GOOGLE_TASKS_TOKEN_PATH` | Or JSON | Path to token JSON file (if not using `GOOGLE_TASKS_TOKEN_JSON`) |
| `GEMINI_API_KEY` | If semantic search | For embeddings (e.g. `text-embedding-004`); only if semantic search is enabled |

Optional for semantic search / index:

| Variable | Description |
|----------|-------------|
| `MCP_NOTE_INDEX_DB_PATH` | Path to SQLite DB for note embeddings (if MCP maintains its own index) |
| `MCP_EMBEDDING_MODEL` | Override embedding model (default e.g. `text-embedding-004`) |

### 2.2 Config file (non-secrets)

**Path:** e.g. `config.json` in project root, or path from `MCP_CONFIG_PATH`.

**Suggested schema:**

```json
{
  "joplin": {
    "request_timeout_seconds": 30,
    "ping_timeout_seconds": 5
  },
  "google_tasks": {
    "default_list_id": null,
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
  },
  "semantic_search": {
    "enabled": true,
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k_default": 8
  },
  "pagination": {
    "default_limit": 20,
    "max_limit": 100
  }
}
```

- **joplin:** timeouts for REST calls.
- **google_tasks:** optional default list id; redirect URI for OAuth if needed.
- **semantic_search:** enable/disable and indexing defaults (only used if MCP builds its own index).
- **pagination:** default and max `limit` for list/search tools.

Env vars override config file where both exist (e.g. URL in config, token in env).

---

## 3. Tools

Narrow tools per domain. All list/search tools support `limit` and pagination.

### 3.1 Tasks (Google Tasks)

| Tool | Description | Parameters |
|------|-------------|------------|
| `tasks_list_lists` | List all task lists | *(none)* |
| `tasks_list_tasks` | List tasks in a list (with optional filters) | `task_list_id` (required), `show_completed` (bool, default true), `show_hidden` (bool, default false), `due_min` (ISO date, optional), `due_max` (ISO date, optional), `limit` (int, default from config), `page_token` (string, optional) |
| `tasks_get_task` | Get a single task by id | `task_list_id`, `task_id` |
| `tasks_create` | Create a task | `task_list_id`, `title`, `notes` (optional), `due` (RFC3339, optional), `status` (optional) |
| `tasks_update` | Update a task (patch) | `task_list_id`, `task_id`, `title` (optional), `notes` (optional), `due` (optional), `status` (optional) |
| `tasks_complete` | Mark task completed | `task_list_id`, `task_id` |
| `tasks_delete` | Delete a task | `task_list_id`, `task_id` |

**Pagination:** `tasks_list_tasks` returns a `next_page_token` when more results exist; LLM passes it on the next call as `page_token`. If Google API uses `nextPageToken`, expose it as `next_page_token` in the tool result.

---

### 3.2 Joplin – structure and keyword

| Tool | Description | Parameters |
|------|-------------|------------|
| `joplin_list_folders` | List all notebooks/folders (no pagination by default; if many, add optional `limit`/offset) | `parent_id` (optional, root if omitted) |
| `joplin_get_folder` | Get one folder by id | `folder_id` |
| `joplin_list_notes` | List notes in a folder | `folder_id`, `limit`, `page_token` (or offset) |
| `joplin_get_note` | Get full note (id, title, body, parent_id, etc.) | `note_id` |
| `joplin_search` | Full-text search (Joplin REST search) | `query`, `limit`, `page_token` (or offset) |

**Pagination:** For `joplin_list_notes` and `joplin_search`, define a simple scheme: e.g. `offset` (0-based) and `limit`; return `next_offset` and `has_more` so the LLM can request the next page.

---

### 3.3 Joplin – semantic search

| Tool | Description | Parameters |
|------|-------------|------------|
| `joplin_semantic_search` | Vector/semantic search over note chunks | `query`, `limit` (top_k), `min_score` (optional, 0–1) |

**Implementation note:** In a standalone MCP, either (a) the MCP maintains its own SQLite index (e.g. note chunks + embeddings via Gemini), with a way to (re)build the index from Joplin, or (b) the MCP calls an external embedding + vector API. Spec assumes (a) unless you add a separate “index service”. Index can be built by a script that runs periodically or on-demand; MCP only reads.

---

### 3.4 Joplin – write

| Tool | Description | Parameters |
|------|-------------|------------|
| `joplin_create_note` | Create a note | `folder_id`, `title`, `body`, `image_data_url` (optional) |
| `joplin_update_note` | Update note (partial) | `note_id`, `title` (optional), `body` (optional), `parent_id` (optional) |
| `joplin_delete_note` | Delete a note | `note_id` |
| `joplin_move_note` | Move note to another folder | `note_id`, `parent_id` |
| `joplin_create_folder` | Create a notebook/folder | `title`, `parent_id` (optional) |

---

## 4. Pagination contract

- **Tasks:** Follow Google’s `pageToken` / `nextPageToken`; expose as `page_token` and `next_page_token` in tool args and results.
- **Joplin list_notes / search:** Use `offset` + `limit`; return in the result:
  - `next_offset` (int or null if no more)
  - `has_more` (bool)
  - `limit`, `offset` echoed so the LLM can request the next page with `offset = next_offset`.

Config: `pagination.default_limit`, `pagination.max_limit`; cap `limit` at `max_limit`.

---

## 5. Errors and robustness

- **Auth:** If Joplin returns 403 or Google returns 401, return a clear message (e.g. “Joplin: invalid or expired token”) so the LLM can tell the user to check config.
- **Not found:** 404 → return a short message like “Task list not found” or “Note not found” with the given id.
- **Rate limits:** If you hit Joplin or Google rate limits, return a message suggesting to retry later; no need to expose internal backoff in the tool contract.

---

## 6. Implementation notes

- **Language:** Python with FastMCP (or stdio MCP SDK) is a good fit; keeps tool definitions and config simple.
- **Google OAuth:** In a separate repo with its own token store, implement a one-time OAuth flow (e.g. CLI or script) that writes token to file or env; MCP only reads and refreshes tokens.
- **Semantic index:** If the MCP builds the index: one process/script fetches notes from Joplin, chunks text, calls Gemini embeddings, stores in SQLite; MCP’s `joplin_semantic_search` reads from that DB. Optionally support “index last N days” or “full reindex” via a separate admin script, not necessarily as MCP tools.
- **Tool naming:** Prefix tasks with `tasks_` and Joplin with `joplin_` so the LLM can distinguish domains easily.

---

## 7. Cursor integration

User adds this MCP from the **separate repo** (no change to telegram-joplin’s `.mcp.json`). Example entry in Cursor’s MCP config (path and command depend on the new repo):

```json
{
  "mcpServers": {
    "tasks-and-joplin": {
      "command": "python",
      "args": ["-m", "mcp_tasks_joplin.server"],
      "cwd": "/path/to/mcp-tasks-joplin",
      "env": {
        "JOPLIN_URL": "http://localhost:41184",
        "JOPLIN_TOKEN": "<from-env-or-dotenv>",
        "GOOGLE_CLIENT_ID": "...",
        "GOOGLE_CLIENT_SECRET": "...",
        "GOOGLE_TASKS_TOKEN_PATH": "/path/to/token.json"
      }
    }
  }
}
```

Secrets can be in `env` or loaded from a `.env` in `cwd` if the server supports it.

---

## 8. Checklist for the new repo

- [ ] Project layout (e.g. `src/mcp_tasks_joplin/`, `config.json.example`, `README.md`)
- [ ] Config loader: env + config file with overrides
- [ ] Google Tasks client (OAuth refresh, list lists, list/create/update/complete/delete tasks, pagination)
- [ ] Joplin REST client (folders, notes, search, create/update/delete/move, pagination)
- [ ] Semantic search: index builder script + search over SQLite (or external embedding API)
- [ ] MCP server: register all tools, wire to clients, map errors to clear messages
- [ ] One-time OAuth flow for Google (script or CLI) and docs for token setup
- [ ] README: env vars, config file, how to run and add to Cursor

You can copy this spec into the new repo as `SPEC.md` or `docs/spec.md` and implement against it.
