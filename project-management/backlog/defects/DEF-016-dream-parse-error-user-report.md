# Defect: DEF-016 - /dream Parse Error: User Receives Nothing in Telegram

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

When using `/dream`, the user describes a dream and the bot generates a Jungian analysis. The message send fails with `BadRequest: Can't parse entities: can't find end of the entity starting at byte offset 317`. **Nothing appears in the Telegram client** — the user receives no analysis.

## Steps to Reproduce

1. Send `/dream` to start a session.
2. Describe a dream (20+ characters).
3. Wait for analysis generation.
4. Observe: Server logs show `BadRequest`; user sees nothing in Telegram.

## Logs (User Report)

```
{"event": "User 7256045321 is whitelisted"}
{"event": "Updated state for user 7256045321"}
{"event": "No error handlers are registered, logging exception.", "exc_info": ["<class 'telegram.error.BadRequest'>", "BadRequest('Can't parse entities: can't find end of the entity starting at byte offset 317')", "<traceback object at 0x7f14a21f9740>"]}
```

## Expected Behavior

- User receives the Jungian analysis in Telegram.
- User can reply yes/no to explore life associations.

## Actual Behavior

- Message send fails with parse error.
- User receives nothing in Telegram.
- Exception logged; no fallback message delivered.

## Relation to DEF-014

DEF-014 added a try/except with plain-text fallback. Possible causes for this regression:
1. **Fix not deployed** — Production (Fly.io) may be running an older build.
2. **Fallback not triggered** — Exception may propagate before our handler catches it (e.g. different call path).
3. **Fallback fails** — Plain-text send could raise a different error.

## Proposed Resolution

**Option A (verify)**: Ensure latest code is deployed. Run `fly deploy` if on Fly.io.

**Option B (robust fix)**: Stop using Markdown for the analysis message. LLM output is unpredictable and often contains `*`, `_`, `` ` ``, `[`, `]` which break Telegram's parser. **Always send the analysis as plain text** — no `parse_mode` for the analysis portion. This eliminates the parse error entirely.

```python
# Current: try Markdown, fallback to plain
# Better: always use plain for LLM content
plain_msg = _dream_analysis_to_plain(msg)
await message.reply_text(plain_msg)  # No parse_mode
```

## Affected Code

- `src/handlers/dream.py` — `handle_dream_message()` phase `analyzing`, lines ~165–177

## Resolution (2026-03-05)

Implemented Option B: Always send the analysis as plain text (no `parse_mode`). Removed Markdown formatting for the analysis message so LLM output is never parsed by Telegram. User always receives the analysis.

## References

- [DEF-014: /dream Parse Entities Error](DEF-014-dream-parse-entities-error.md) — initial fix with fallback
