# State Management — Technical Reference

This document describes how conversation state is stored, updated, and used in the Telegram-Joplin bot.

## Overview

The bot uses a **per-user state** to support multi-turn conversations. State enables:

- **Clarification flows**: When the LLM needs more information, the bot stores the original message and asks a question; the user's reply is merged with the original and re-processed.
- **Persona sessions**: Commands like `/braindump`, `/stoic`, `/dream`, `/planning`, and `/search` start interactive sessions; subsequent messages are routed to the correct handler based on `active_persona`.
- **OAuth flows**: Google Tasks authorization stores temporary `google_auth_state` during the OAuth callback.
- **Reading queue**: The reading list feature stores `reading_queue_items` in state.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Telegram Message Handler                      │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  state_manager.get_state()    │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │ pending state │               │ no state      │
            └───────────────┘               └───────────────┘
                    │                               │
        ┌───────────┼───────────┐                   │
        ▼           ▼           ▼                   ▼
   GTD_EXPERT  STOIC_JOURNAL  SEARCH...      _handle_new_request
   braindump   stoic          search        (routing, note creation)
        │           │           │
        └───────────┴───────────┴──► persona-specific handler
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  state_manager.update_state() │
                    │  state_manager.clear_state()  │
                    └───────────────────────────────┘
```

## Storage

### Backend

- **Production**: SQLite database at `data/bot/conversation_state.db` (or path from `STATE_DB_PATH`).
- **Testing**: `InMemoryStateManager` — state is lost when the process exits.

### Schema

```sql
CREATE TABLE user_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,           -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_states_updated ON user_states(updated_at);
```

### Configuration

- `STATE_DB_PATH` (or `database.state_db_path` in settings) controls the SQLite file location.
- Runtime data lives under `data/` locally or `/app/data` on Fly.io.

## StateManager API

| Method | Description |
|--------|-------------|
| `get_state(user_id: int) -> dict \| None` | Returns the current state dict or `None` if no state. |
| `update_state(user_id: int, state: dict) -> bool` | Upserts state (insert or replace). |
| `clear_state(user_id: int) -> bool` | Deletes state for the user. |
| `has_pending_state(user_id: int) -> bool` | Returns `True` if user has any state. |
| `cleanup_old_states(days_old: int = 7) -> int` | Deletes states older than N days; returns count deleted. |
| `get_all_active_users() -> list[int]` | Returns all user IDs with active state. |
| `migrate_from_dict(dict_states) -> bool` | Migrates in-memory states to SQLite (for transition). |

### Thread Safety

All operations use a `threading.Lock` to ensure thread-safe access to the database.

## State Structure (Keys)

State is a JSON-serializable `dict`. Keys vary by flow:

### General Clarification Flow

| Key | Type | Description |
|-----|------|-------------|
| `original_message` | str | The user's original message before clarification. |
| `existing_tags` | list[str] | Tags available in Joplin (for LLM context). |
| `routing_pending` | bool | Set when content routing asked for clarification; reply re-runs routing. |
| `llm_response` | dict | Serialized LLM response when note creation asked for clarification. |

### Persona Sessions

| Key | Type | Description |
|-----|------|-------------|
| `active_persona` | str | One of: `GTD_EXPERT`, `STOIC_JOURNAL`, `DREAM_ANALYST`, `PLANNING_COACH`, `SEARCH`. |
| `session_start` | str | ISO timestamp when session started (e.g. braindump). |
| `captured_items` | list | Items captured during session. |
| `conversation_history` | list[dict] | `[{role, content}, ...]` for LLM context. |
| `final_note` | dict | Note data when session completes. |

### Other

| Key | Type | Description |
|-----|------|-------------|
| `google_auth_state` | str | OAuth state during Google Tasks authorization; cleared after callback. |
| `reading_queue_items` | list | Reading list items (key: `READING_STATE_KEY`). |

## Message Routing Logic

Entry point: `_message()` in `src/handlers/core.py`.

1. **Greeting** (`hello`, `hi`, etc.): Always clears state and shows menu. Acts as escape hatch from any pending flow.
2. **Pending state**: If `get_state(user_id)` returns a dict:
   - `active_persona == "GTD_EXPERT"` → `handle_braindump_message`
   - `active_persona == "STOIC_JOURNAL"` → `handle_stoic_message`
   - `active_persona == "DREAM_ANALYST"` → `handle_dream_message`
   - `active_persona == "PLANNING_COACH"` → `handle_planning_message`
   - `active_persona == "SEARCH"` → `handle_search_selection`
   - Otherwise → `_handle_clarification_reply` (general note clarification)
3. **No state**: `_handle_new_request` — routes via content routing or direct note creation.

## When State Is Updated

| Event | Action |
|-------|--------|
| Content routing needs clarification | `update_state` with `original_message`, `routing_pending`, `existing_tags` |
| Note creation needs clarification | `update_state` with `original_message`, `existing_tags`, `llm_response` |
| User replies to clarification | `clear_state` then re-route, or merge and `process_message` then `clear_state` on success |
| Persona command starts (e.g. `/braindump`) | `update_state` with `active_persona`, session data |
| Persona session continues | `update_state` with updated `conversation_history`, etc. |
| Persona session ends | `clear_state` |
| `/start` or greeting | `clear_state` |
| Note created successfully | `clear_state` (when `clear_state=True` passed to `_process_llm_response`) |
| Google OAuth callback | `update_state` with `google_auth_state`; cleared after use |

## When State Is Cleared

- Successful note creation (with `clear_state=True`)
- User sends greeting (escape hatch)
- `/start` command
- Persona session completion (`/braindump_stop`, etc.)
- Clarification reply processed successfully
- Google OAuth flow completed

## Cleanup

- `cleanup_old_states(days_old=7)` removes states not updated in the last 7 days.
- No automatic scheduled cleanup is wired by default; it can be called from a cron job or maintenance script.

## Files Reference

| File | Role |
|------|------|
| `src/state_manager.py` | `StateManager`, `InMemoryStateManager` |
| `src/container.py` | Instantiates `StateManager` with `state_db_path` |
| `src/telegram_orchestrator.py` | Uses `state_manager` for routing |
| `src/handlers/core.py` | Main routing, clarification, `_process_llm_response` |
| `src/handlers/braindump.py` | GTD_EXPERT persona |
| `src/handlers/stoic.py` | STOIC_JOURNAL persona |
| `src/handlers/dream.py` | DREAM_ANALYST persona |
| `src/handlers/planning.py` | PLANNING_COACH persona |
| `src/handlers/search.py` | SEARCH persona |
| `src/handlers/google_tasks.py` | `google_auth_state` |
| `src/handlers/reading.py` | `reading_queue_items` |

## Testing

Use `InMemoryStateManager` for tests; state does not persist across runs. The container can be configured to use it when running in test mode.
