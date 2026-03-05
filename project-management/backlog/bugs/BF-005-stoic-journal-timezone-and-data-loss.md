# Bug Fix: BF-005 - Stoic Journal: Timezone Mismatch & Data Loss on Update

**Status**: ⭕ Not Started
**Priority**: 🔴 Critical
**Story Points**: 5
**Created**: 2026-03-03
**Updated**: 2026-03-03
**Assigned Sprint**: Backlog

## Description

The `/stoic` command has three interrelated bugs that cause data loss and incorrect behaviour:

1. **Timezone mismatch**: All `datetime.now()` calls use server time (UTC on Fly.io), not the user's local timezone (Montreal / US/Eastern). Evening reflections done after 7pm Montreal time get dated to the *next day* on the server, resulting in two separate notes instead of one combined daily note.

2. **Data loss on note update**: When appending a second session (e.g. evening) to an existing day's note, the code fetches the existing note body via `get_note()`. If that call fails for any reason, `existing_body` silently falls back to `""`, and the entire note body is **replaced** with only the new section — destroying the morning content.

3. **No duplicate session protection**: A user can run `/stoic morning` twice in the same day. The second time, content is blindly appended, creating a broken note with duplicate morning sections. There is no prompt asking the user what they want to do (replace, append, or cancel), and no offer to start the evening session instead.

## Steps to Reproduce

### Bug 1: Timezone
1. Deploy on Fly.io (UTC server).
2. At 9pm Montreal (2am UTC next day), run `/stoic evening`.
3. Answer questions and `/stoic_done`.
4. Observe: note title is tomorrow's date, not today's.

### Bug 2: Data loss
1. Run `/stoic morning` at 8am, answer questions, `/stoic_done` → note created.
2. Run `/stoic evening` at 9pm, answer questions, `/stoic_done`.
3. If `get_note()` errors or returns empty body, morning content is gone.

### Bug 3: Duplicate session
1. Run `/stoic morning`, answer, `/stoic_done` → note created.
2. Run `/stoic morning` again the same day, answer, `/stoic_done`.
3. Note now has two morning sections stacked.

## Expected Behavior

1. Note title and timestamps use the user's configured timezone (e.g. `US/Eastern`).
2. If fetching the existing note body fails, the update should **abort** rather than overwrite.
3. Before starting a new session, the bot should check if today's note already has that section:
   - If morning already exists and user runs `/stoic morning`:
     "You already have a morning entry today. Would you like to:\n• Replace it\n• Append to it\n• Start evening instead\n• Cancel"
   - If evening already exists and user runs `/stoic evening`: same prompt with morning option.

## Root Cause

### Bug 1 — Timezone
`src/handlers/stoic.py` lines 77, 121, 211, 270 all use `datetime.now()` which returns server-local time (UTC on Fly.io). There is no user timezone configuration for the stoic journal.

```python
# Line 270-271 — determines note title date
now = datetime.now()           # ← UTC on Fly.io
date_str = now.strftime("%Y-%m-%d")  # ← wrong date after 7pm Eastern
title = f"{date_str} - Daily Stoic Reflection"
```

### Bug 2 — Data loss
`src/handlers/stoic.py` lines 304-309:

```python
try:
    full_note = await orch.joplin_client.get_note(note_id)
    existing_body = (full_note.get("body") or "").strip()
except Exception as exc:
    logger.warning("Could not fetch existing note body: %s", exc)
    existing_body = ""   # ← silently loses all existing content
```

When `existing_body` is `""`, line 310 becomes:
```python
new_body = section_content  # morning content is gone
```

### Bug 3 — No session dedup
`src/handlers/stoic.py` line 296-297 checks if a note with today's title exists, but only to decide append vs. create. It never checks whether the specific section (morning/evening) already exists in the note body.

## Proposed Solution

### 1. Add user timezone configuration
- Reuse the existing `report_configurations.timezone` field, OR
- Add a global user timezone setting (preferred — one config used by stoic, reports, and any future time-sensitive feature)
- Replace all `datetime.now()` in `stoic.py` with a timezone-aware helper:

```python
from zoneinfo import ZoneInfo

def _user_now(orch, user_id: int) -> datetime:
    """Return current time in the user's configured timezone."""
    tz_str = _get_user_timezone(orch, user_id)  # e.g. "US/Eastern"
    return datetime.now(ZoneInfo(tz_str))
```

### 2. Abort on body fetch failure
Replace the silent fallback with an error that aborts the save:

```python
try:
    full_note = await orch.joplin_client.get_note(note_id)
    existing_body = (full_note.get("body") or "").strip()
except Exception as exc:
    logger.error("Could not fetch existing note body: %s", exc)
    await message.reply_text(
        "❌ Could not read today's existing note. "
        "Your reflection was NOT saved to avoid overwriting. "
        "Please try again or use /stoic_done later."
    )
    return False  # ← abort, don't destroy
```

### 3. Check for existing section before starting
Before entering the Q&A flow, check if today's note already has the requested section:

```python
# In _stoic handler, after determining mode:
existing_note = _find_todays_note(orch, user_id)
if existing_note:
    has_morning = "### 🌞 Morning" in existing_note.get("body", "")
    has_evening = "### 🌙 Evening" in existing_note.get("body", "")

    if mode == "morning" and has_morning:
        await message.reply_text(
            "📓 You already have a morning entry today.\n\n"
            "• /stoic_replace morning — Replace it\n"
            "• /stoic_append morning — Add to it\n"
            "• /stoic evening — Start evening instead\n"
            "• Cancel — just ignore this"
        )
        return
    if mode == "evening" and has_evening:
        # similar prompt offering morning
```

## Technical References

- File: `src/handlers/stoic.py` — all 3 bugs
- File: `src/logging_service.py` — `report_configurations` table has `timezone` column
- File: `database_schema.sql` — schema for config tables

## Testing

- [ ] Verify note title uses user timezone, not UTC
- [ ] Verify timestamps in morning/evening content use user timezone
- [ ] Verify `get_note()` failure aborts save with user-friendly error (no data loss)
- [ ] Verify starting `/stoic morning` when morning already exists shows prompt with replace/append/evening/cancel
- [ ] Verify starting `/stoic evening` when evening already exists shows prompt with replace/append/morning/cancel
- [ ] Verify starting `/stoic evening` when only morning exists proceeds normally (append)
- [ ] Verify starting `/stoic morning` when only evening exists proceeds normally (append)
- [ ] Unit test: timezone-aware date generation for Montreal at 9pm, 11pm, midnight
- [ ] Unit test: abort on body fetch failure preserves existing content
- [ ] Integration test: full morning → evening flow produces single combined note

## Dependencies

- None (self-contained in `src/handlers/stoic.py`)

## Notes

- The timezone fix should ideally be a **global user setting** (not stoic-specific) so that weekly reports, daily reports, and any future time-aware feature all use the same timezone.
- The `report_configurations` table already has a `timezone` column — we can either reuse it or create a dedicated `user_preferences` table.
- Consider adding `/set_timezone US/Eastern` as a top-level command.

## History

- 2026-03-03 - Created (user-reported: data loss + timezone mismatch in Montreal)
