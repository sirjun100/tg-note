# User Story: US-040 - Check if Task or Note Exists, Offer Update or Append

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 8
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog

## Description

Before creating a new note or task, check whether a similar one already exists. If a match is found, ask the user whether they want to **update** (replace), **append** (add to existing), or **create new** (ignore match and create anyway). This reduces duplicates and gives users control when they accidentally re-send or want to add to an existing item.

## User Story

As a user who captures notes and tasks through Telegram,
I want the bot to detect when I'm adding something that already exists,
so that I can choose to update or append instead of creating duplicates.

## Acceptance Criteria

### Notes

- [ ] Before creating a Joplin note, search for similar notes via US-026 `NoteIndex.search()` (all notes)
- [ ] If 1 match: show "Similar note exists: [title]. Update? Append? Create new?"
- [ ] If multiple matches (top 3): let user pick which one, then show Update/Append/New
- [ ] **Update**: Ask user—body only, or body + title
- [ ] **Append**: Add with `---` + timestamp separator (e.g. `---\n\n2026-03-06 14:30\n\n{content}`)
- [ ] **Create new**: Proceed with creating a new note (ignore the match)
- [ ] User selects via inline buttons **and** text reply ("update", "append", "new")
- [ ] Similarity threshold: 0.9 default (configurable)

### Tasks

- [ ] Before creating a Google Task, search similar tasks across **all** user's task lists
- [ ] If similar task found, show: "Similar task exists: [title]. Update? Append? Create new?"
- [ ] **Update**: Replace the existing task's title and/or notes with the new content
- [ ] **Append**: Add the new content to the existing task's notes field (same format: `---` + timestamp)
- [ ] **Create new**: Proceed with creating a new task
- [ ] User selects via inline buttons **and** text reply

### General

- [ ] Works for **all** flows: plain messages, `/task`, `/note`, braindump, dream, recipe, Stoic, planning, photo, read-later
- [ ] State is stored during the prompt so user's reply is handled correctly
- [ ] **Timeout**: If user doesn't respond within 5 minutes, create new (ignore match)

## Business Value

- **Reduces duplicates**: Users often re-send the same meeting notes or task; detecting and offering update/append prevents clutter
- **User control**: Aligns with Stoic's replace/append pattern (DEF-008); users appreciate being asked
- **Better data hygiene**: Append option lets users add context to existing items instead of fragmenting across multiple notes

## Technical Requirements

### 1. Similarity Detection

**Notes**:
- Use **US-026 Semantic Search** (`NoteIndex.search()`) for similarity detection—already implemented
- Search scope: **all notes** (not limited to target folder)
- Multiple matches: show top 3, let user pick
- Match threshold: **0.9** default (configurable); industry practice favors higher threshold to reduce false-positive prompts
- Fallback: Joplin `search_notes(query)` if NoteIndex unavailable

**Tasks**:
- Fetch user's Google Tasks across **all** task lists
- Compare proposed title to existing task titles (case-insensitive, optionally fuzzy)
- Match: exact or high similarity (e.g. Levenshtein or "title in proposed" / "proposed in title")

### 2. User Prompt Flow

```
Similar note exists: "Meeting notes - Project X"
What would you like to do?
  [Update]  - Replace existing content
  [Append]  - Add to existing note
  [New]     - Create a new note anyway
```

State keys: `pending_duplicate_action`, `existing_note_id` or `existing_task_id`, `pending_note_data` or `pending_task_data`, `original_message`

### 3. Update / Append Implementation

**Note update**: Ask user: body only, or body + title. Then `joplin_client.update_note(note_id, ...)`
**Note append**: Fetch note body, append with `\n\n---\n\n{timestamp}\n\n{new_content}` (e.g. `2026-03-06 14:30`), update note
**Task update**: `google_tasks_client.update_task(task_id, task_list_id, {"title": ..., "notes": ...})`
**Task append**: Fetch task, append to notes field with `---` + timestamp (same format as notes), update

### 4. Integration Points

- `_handle_new_request()` — before calling `_process_llm_response` or `create_task_directly`, run duplicate check
- `_handle_clarification_reply()` — extend to handle `pending_duplicate_action` state
- New handler or branch for "update" / "append" / "new" reply when in duplicate-pending state

## Reference Documents

- [US-026: Semantic Search and Q&A](US-026-semantic-search-qa.md) — use `NoteIndex.search()` for note similarity
- [DEF-008: Stoic Evening Deletes Morning](../defects/DEF-008-stoic-evening-deletes-morning.md) — replace/append pattern
- [DEF-005: Stoic Duplicate Session](../defects/DEF-005-stoic-journal-timezone-and-data-loss.md) — duplicate detection
- [US-023: Intelligent Content Routing](US-023-intelligent-content-routing.md) — note/task creation flow
- [US-012: Google Tasks Integration](US-012-google-tasks-integration.md)
- [Reading queue duplicate detection](../../../src/reading_service.py) — URL duplicate check pattern

## Technical References

- `src/note_index.py` — `NoteIndex.search()` (US-026 semantic search)
- `src/handlers/core.py` — `_handle_new_request()`, `_handle_clarification_reply()`, `_process_llm_response()`
- `src/handlers/stoic.py` — `_finish_stoic_session()`, `_check_section_exists()`, `/stoic_replace`, `/stoic_append`
- `src/joplin_client.py` — `search_notes()`, `get_note()`, `update_note` (if exists)
- `src/google_tasks_client.py` — `get_tasks()`, `update_task()`
- `src/task_service.py` — `create_task_with_metadata()`, `create_task_directly()`
- `src/reading_service.py` — `add_to_queue()` duplicate URL check
- `src/state_manager.py` — state for pending duplicate action

## Dependencies

- Joplin API (note search, update)
- Google Tasks API (task list, update)
- Content routing (US-023) ✅

## Design Decisions (2026-03-06)

- **Multiple matches**: Let user pick from top 3
- **Note scope**: All notes (not target folder only)
- **Flows**: Run duplicate check for **all** flows (braindump, dream, recipe, Stoic, planning, etc.)
- **Timeout**: Create new (ignore match) if user doesn't respond within 5 min
- **Append separator**: `---` + timestamp
- **Note update**: Ask user each time—body only, or body + title
- **Interaction**: Both inline buttons and text reply
- **Task scope**: All user's task lists
- **Similarity threshold**: 0.9 default (configurable)

## Notes

- Reading queue detects duplicate URLs but only informs ("Already in queue"); it does not offer update/append. This FR extends that pattern.
- Stoic's `/stoic_replace` and `/stoic_append` are good UX references.
- Use InlineKeyboardMarkup for [Update] [Append] [New] buttons; also accept text reply ("update", "append", "new").

## History

- 2026-03-06 - Created
- 2026-03-06 - Design decisions: multiple matches (pick from 3), all notes/lists, all flows, timeout 5 min→create new, append with timestamp (notes + tasks), update asks user, 0.9 threshold
- 2026-03-06 - Story points increased to 8 (expanded scope)
