# Defect: DEF-026 - Braindump and Image OCR Cannot Save to Joplin (NoneType AttributeError)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 1
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Assigned Sprint**: Backlog

## Description

Both braindump sessions and photo/image OCR captures fail to save notes to Joplin. Fly.io logs show:

```
Error creating note: 'NoneType' object has no attribute 'get'
```

**Affected flows:**
- **Braindump**: When the GTD session completes and the LLM returns a summary note, the save fails. User sees "Failed to save note to Joplin" and "Brain dump session closed."
- **Photo capture with OCR**: When a user sends a photo, OCR extracts text, the default persona processes it and returns a note, but the save fails with the same error.

## Steps to Reproduce

**Braindump:**
1. Start a braindump session with `/braindump`
2. Complete the GTD capture flow (answer questions until session finishes)
3. Observe: LLM returns SUCCESS with note data, log shows "Note created", then "Error creating note: 'NoneType' object has no attribute 'get'"
4. User sees "Failed to save note to Joplin" and "Brain dump session closed."

**Photo OCR:**
1. Send a photo to the bot (e.g. screenshot of a chat)
2. OCR extracts text, default persona processes it and returns a note
3. Same error: note creation fails with NoneType AttributeError
4. User does not receive the saved note

## Expected Behavior

- Braindump summary notes save successfully to Joplin. User sees "BRAIN DUMP SAVED TO JOPLIN".
- Photo OCR notes save successfully. User receives confirmation and the note appears in Joplin.

## Actual Behavior

- Both flows fail with `AttributeError: 'NoneType' object has no attribute 'get'`
- User sees "Failed to save note to Joplin" (braindump) or no note created (photo)
- Fly.io logs: `Error creating note: 'NoneType' object has no attribute 'get'`

## Root Cause

In `src/handlers/core.py` `create_note_in_joplin()`, line 1684:

```python
url_was_primary = url_context.get("url_was_primary", True)
```

This line runs when `final_image_data_url is None` (always true for braindump and photo OCR, which pass no image). However, both flows call `create_note_in_joplin` with `url_context=None`. Calling `.get()` on `None` raises the AttributeError.

The `url_was_primary` logic was added for [DEF-025](DEF-025-recipe-pasted-text-shows-screenshot-skipped.md) (recipe pasted text) and correctly guards the *if* block with `url_context`, but the assignment itself is executed unconditionally before that check.

## Proposed Fix

Guard the assignment:

```python
url_was_primary = url_context.get("url_was_primary", True) if url_context else True
```

Or move the assignment inside the `if url_context:` block.

## Affected Code

- `src/handlers/core.py` — `create_note_in_joplin()`, lines 1684–1697

## References

- [DEF-025: Recipe Pasted Text Shows Screenshot Skipped](DEF-025-recipe-pasted-text-shows-screenshot-skipped.md) — introduced `url_was_primary`
- User report via Fly.io logs and Google Task: "braindump does not save in joplin it crashes and image ocr crashes too"

## Solution Implemented

- Guarded `url_was_primary` assignment: `url_context.get("url_was_primary", True) if url_context else True`
- Added regression test `test_create_note_in_joplin_with_url_context_none` in `tests/test_braindump.py`

## History

- 2026-03-09 - Created from Fly.io logs analysis; user reported via task creation
- 2026-03-09 - Fix: guard url_context.get when url_context is None; added regression test
