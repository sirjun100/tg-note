# Bug Fix: BF-022 - /find Command Error in Fly.io Logs

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Sprint 15

## Description

The `/find` (and `/search`) command generates errors in Fly.io logs and fails to return search results to the user. The command previously worked but is no longer functioning in production.

## Steps to Reproduce

1. Ensure user is whitelisted.
2. Send `/find <query>` (e.g., `/find meeting`) to the bot.
3. Observe: Fly.io logs show an error; user may see "Something went wrong" or no response.

## Expected Behavior

- Bot returns search results with note titles, folder names, and snippets.
- User can reply with a number (1–5) to view the full note.

## Actual Behavior

- Error appears in Fly.io logs.
- User does not receive search results.

## Environment

- **Platform**: Telegram (production)
- **Bot**: Deployed on Fly.io
- **Trigger**: `/find` or `/search` command with any query

## Root Cause

Two issues identified in `src/handlers/search.py`:

1. **`get_folders()` not wrapped in try/except**: After `search_notes()` succeeds, `get_folders()` is called without error handling. If Joplin is slow, times out, or returns an error, the exception propagates and crashes the handler.

2. **Telegram Markdown parse errors**: Search results are sent with `parse_mode="Markdown"`. Note titles, folder names, and snippets come from user content (Joplin) and can contain Markdown-special characters (`*`, `_`, `` ` ``, `[`, `]`). Unescaped characters cause:
   - `BadRequest: Can't parse entities: can't find end of the entity starting at byte offset X`
   - Same pattern as BF-010 (greeting), BF-014/BF-016 (dream).

## Solution

1. **Wrap `get_folders()` in try/except**: On failure, use empty `folder_by_id` so folder names show as "Unknown" but search results still display.

2. **Safe message send**: Switch to `parse_mode="HTML"` with `html.escape()` for user content (titles, snippets, folder names). HTML mode avoids underscore/asterisk parse issues. Add plain-text fallback on send error (same pattern as BF-010).

## Affected Code

- `src/handlers/search.py`:
  - `_find()` handler — lines 81–102: `get_folders()` call, message building, `reply_text` with Markdown
  - Usage help at lines 60–66: also uses Markdown (low risk but consistent)

## References

- [BF-010: Greeting Parse Entities Error](BF-010-greeting-parse-entities-error.md) — HTML mode + plain-text fallback
- [BF-014: /dream Parse Entities Error](BF-014-dream-parse-entities-error.md)
- [FR-029: Quick Note Search](../features/FR-029-quick-note-search.md)
- [Telegram Bot API: Formatting options](https://core.telegram.org/bots/api#formatting-options)

## Testing

- [ ] Unit test: search with folder fetch failure returns results with "Unknown" folders
- [ ] Unit test: search with special chars in title/snippet sends without parse error
- [ ] Manual: `/find test` returns results in production (Fly.io)

## Implementation Guide

**Sprint 15**: See [sprint-15-implementation-guide.md](../../sprints/sprint-15-implementation-guide.md) § BF-022 for verification steps and unit test scenarios. Implementation may already exist in `src/handlers/search.py`.

## History

- 2026-03-06 - Created
- 2026-03-06 - Implemented: get_folders try/except, HTML mode with escape, plain-text fallback
