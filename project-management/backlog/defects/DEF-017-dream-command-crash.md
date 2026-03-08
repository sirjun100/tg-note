# Defect: DEF-017 - /dream Command Crashes Agent on Invocation

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 1
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

Sending the `/dream` command alone causes the agent to crash. The user receives no response; the bot appears to fail immediately when the command is invoked (before any dream description is entered).

## Steps to Reproduce

1. Send `/dream` to the bot.
2. Observe: No welcome message; agent crashes.

## Expected Behavior

- Bot responds with the dream analysis welcome message:
  - "🌙 **Welcome to Dream Analysis**"
  - Instructions to describe the dream
  - "Type /dream_cancel to cancel anytime."

## Actual Behavior

- Agent crashes.
- User receives nothing.
- Server logs may show an unhandled exception.

## Possible Causes

1. **Markdown parse error** on the welcome message (similar to DEF-010, DEF-014) — the welcome uses `parse_mode="Markdown"` with `**bold**`.
2. **State manager** — `update_state` or `get_state` failure.
3. **Whitelist check** — unexpected behavior.
4. **Message/update** — missing or malformed update data.

## Resolution (2026-03-05)

- **Added logging** around `/dream` entry, state update, reply, and exception handlers to aid debugging.
- Consider switching welcome message to plain text or HTML if Markdown parse is the cause.

## Affected Code

- `src/handlers/dream.py` — `dream_cmd` handler, `register_dream_handlers`

## References

- [DEF-010: Greeting Parse Entities](DEF-010-greeting-parse-entities-error.md)
- [DEF-014: Dream Parse Entities](DEF-014-dream-parse-entities-error.md)
- [DEF-016: Dream Parse User Report](DEF-016-dream-parse-error-user-report.md)
