# Defect: DEF-031 - Note Creation Should Show Full Save Path and Trigger Sync

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 2
**Created**: 2026-03-09
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19

---

## Problem Statement

When a note is created (via any flow: plain message, /note, braindump, photo OCR, recipe, etc.), the success message should display the **full path** where the note was saved (e.g. "Resources/Books/My Book") and the bot should run sync so the note appears on the user's other devices promptly.

**User impact:** Users see only the parent folder name (e.g. "Inbox") instead of the full path, making it harder to locate the note in Joplin. Sync may not run in all flows or may be inconsistent.

---

## Expected Behavior

1. **Full path in success message:** "✅ Note created: 'Meeting notes' in **Resources/Work/Projects/ClientX**" (full path from root)
2. **Sync runs automatically:** After every note creation, trigger Joplin sync (equivalent to /sync) so the note appears on other devices without manual /sync

---

## Actual Behavior

1. **Path:** Success message often shows only the direct parent folder name (e.g. "in folder 'Inbox'"), not the full path like "Areas/Work/Projects/ClientX"
2. **Sync:** `_schedule_joplin_sync()` exists and is called in some flows (e.g. core LLM response, stoic, dream) but may not be called in all note-creation paths (e.g. braindump, photo OCR, recipe, planning). User may need to run /sync manually.

---

## Steps to Reproduce

1. Create a note in a nested folder (e.g. "Areas/Work/Projects/MyProject")
2. Observe the success message — it may show only "Projects" or "MyProject", not full path
3. Check sync — note may not appear on other devices until user runs /sync

---

## Affected Code

| File | Notes |
|------|-------|
| `src/handlers/core.py` | `_process_llm_response` — success_msg uses `folder_name` (parent only); `create_note_in_joplin`; `_schedule_joplin_sync` |
| `src/handlers/braindump.py` | Note creation success; may not call sync |
| `src/handlers/photo.py` | Photo OCR note creation; path and sync |
| `src/handlers/core.py` (recipe) | Recipe note creation |
| `src/handlers/planning.py` | Planning note creation |
| `src/joplin_client.py` | May need `get_folder_path` or similar to resolve full path from folder_id |

---

## Proposed Solution

1. **Full path:** Add helper to resolve full folder path from folder_id (walk parent chain, build path string). Use in success message.
2. **Sync everywhere:** Ensure `_schedule_joplin_sync()` is called after every successful note creation path (braindump, photo, recipe, planning, core, stoic, dream, etc.).

## History

- 2026-03-09 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
