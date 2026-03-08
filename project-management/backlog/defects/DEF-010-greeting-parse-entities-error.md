# Defect: DEF-010 - Greeting Response Causes "Something Went Wrong" (Parse Entities Error)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

When a user sends a greeting (e.g., "Hello"), the bot attempts to send the greeting response with command list. Telegram rejects the message due to invalid Markdown entities, causing an unhandled exception. The user sees "Something went wrong, try again" instead of the greeting.

## Steps to Reproduce

1. Ensure user is whitelisted and has no pending state (or state was just cleared).
2. Send "Hello" (or "hi", "hey", etc.) to the bot.
3. Observe: User receives "Something went wrong, try again" instead of the greeting with command list.

## Expected Behavior

- Bot responds with a friendly time-aware greeting and the categorized command list (Capture, Search, Productivity, Review).
- No error is shown to the user.

## Actual Behavior

- User sees "Something went wrong, try again."
- Server logs show: `Can't parse entities: can't find end of the entity starting at byte offset 554`
- Exception: `Error handling message from user 7256045321: Can't parse entities: can't find end of the entity starting at byte offset 554`
- `Unhandled error in message handling: Can't parse entities: can't find end of the entity starting at byte offset 554`

## Environment

- **Platform**: Telegram (production)
- **Bot**: Deployed on Fly.io
- **User ID**: 7256045321 (from logs)
- **Trigger**: Plain text greeting ("Hello") after Stoic flow completed (state cleared)

## Screenshots/Logs

```
15:12:35 {"event": "User 7256045321 is whitelisted"}
15:12:35 {"event": "Processing message from user 7256045321: 'Hello'"}
15:12:35 {"event": "Error handling message from user 7256045321: Can't parse entities: can't find end of the entity starting at byte offset 554"}
15:12:35 {"event": "Unhandled error in message handling: Can't parse entities: can't find end of the entity starting at byte offset 554"}
15:12:40 {"event": "User 7256045321 is whitelisted"}
15:12:40 {"event": "Processing message from user 7256045321: 'Hello'"}
15:12:40 {"event": "Error handling message from user 7256045321: Can't parse entities: can't find end of the entity starting at byte offset 554"}
15:12:40 {"event": "Unhandled error in message handling: Can't parse entities: can't find end of the entity starting at byte offset 554"}
```

## Technical Details

- The greeting response is built by `_build_greeting_response()` in `core.py` and sent with `parse_mode="Markdown"`.
- Telegram's Markdown parser requires properly paired entities (`*`, `_`, `` ` ``, `[`/`]`). An unescaped or unpaired character at byte offset 554 causes the parse to fail.
- The greeting text includes: time salutation, command categories with `**bold**` headers, bullet points (`•`), and emoji. Byte 554 is likely in the middle of the message (e.g., near "Review" or "monthly_report" section).
- Possible causes: unescaped `*` or `_` in plain text, odd number of asterisks, or special characters that Telegram interprets as entity delimiters.

## Root Cause

Underscores in command names (`/daily_report`, `/weekly_report`, `/monthly_report`) are interpreted by Telegram's Markdown parser as the start of italic entities. With no matching closing `_`, the parser fails at byte ~554.

## Solution (Implemented)

1. **HTML parse mode**: Switched from Markdown to `parse_mode="HTML"`. In HTML, underscores in `/daily_report`, `/weekly_report`, `/monthly_report` are not special, so no parse error. Category headers use `<b>bold</b>` for formatting. Angle brackets in `/task <text>` are escaped as `&lt;text&gt;`.
2. **Defensive fallback**: `_send_greeting_safe()` tries HTML first; on parse error, falls back to plain text (stripped of tags) so the user always receives the greeting.

## Reference Documents

- [US-024: Greeting Response and Command Discovery](../user-stories/US-024-greeting-and-command-help.md)
- [Telegram Bot API: Formatting options](https://core.telegram.org/bots/api#formatting-options)

## Technical References

- File: `src/handlers/core.py`
  - `_build_greeting_response()` — builds greeting with HTML `<b>` tags and `&lt;&gt;` escapes
  - `_greeting_to_plain()` — strips HTML for fallback
  - `_send_greeting_safe()` — sends with `parse_mode="HTML"`, falls back to plain on parse error
  - `_is_greeting()` — detects greeting
  - `/start` and message handler — use `_send_greeting_safe()` for greeting replies

## Testing

- [x] Unit tests: `tests/test_greeting_bf010.py` — greeting uses HTML, `_greeting_to_plain` strips correctly
- [ ] Send "Hello" → greeting displayed correctly (manual)
- [ ] `/start` → welcome message displayed correctly (manual)
- [ ] Verify in production (Fly.io) after deploy

## Notes

- Error occurs consistently on "Hello" (reproduced at 15:12:35 and 15:12:40).
- User had just completed Stoic flow (state cleared at 15:05:38); greeting was the next interaction.
- Additional logs available on Fly.io if needed for debugging.

## History

- 2026-03-05 - Created
- 2026-03-05 - Completed: Greeting sent as plain text (no parse_mode) to avoid underscore parse errors
- 2026-03-05 - Improved: Switched to HTML parse mode for bold headers; added `_send_greeting_safe()` with plain-text fallback; added unit tests
