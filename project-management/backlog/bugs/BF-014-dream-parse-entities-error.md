# Bug Fix: BF-014 - /dream Parse Entities Error (BadRequest)

**Status**: ⭕ Open
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

When the `/dream` flow sends the Jungian analysis to the user, Telegram rejects the message due to invalid Markdown entities. The error is logged as:

```
Error handlers are registered, logging exception.
exc_info: ["<class 'telegram.error.BadRequest'>", "BadRequest('Can't parse entities: can't find end of the entity starting at byte offset 317')", "<traceback object at 0x7febd6f2f580>"]
```

The user likely receives no reply or a generic error instead of the analysis.

## Steps to Reproduce

1. Start a dream session: `/dream`
2. Describe a dream with sufficient detail (20+ characters).
3. Wait for the bot to generate the Jungian analysis.
4. Observe: Message send fails; user may see no analysis or an error. Server logs show `BadRequest: Can't parse entities`.

## Expected Behavior

- Bot sends the Jungian analysis with formatting (bold headers, etc.) and the follow-up prompt.
- User receives the full analysis and can choose yes/no for life associations.

## Actual Behavior

- `telegram.error.BadRequest` is raised when sending the analysis message.
- Error: `Can't parse entities: can't find end of the entity starting at byte offset 317`
- User does not receive the analysis.

## Root Cause

The analysis message is built in `handle_dream_message()` (phase `analyzing`):

```python
msg = f"📖 **Jungian Analysis**\n\n{analysis}\n\n---\n\n"
msg += "Would you like to explore how this dream connects to your current life? (yes/no)"
msg += DREAM_DISCLAIMER
await message.reply_text(msg, parse_mode="Markdown")
```

The `analysis` text comes from the LLM (Jungian analyst) and is inserted **without escaping**. LLM output often contains Markdown-special characters (`*`, `_`, `` ` ``, `[`, `]`, etc.) that Telegram interprets as entity delimiters. Unpaired or malformed sequences cause the parser to fail at the offending byte offset (e.g. 317).

## Proposed Resolution

1. **Escape Markdown in LLM output**: Escape special characters in `analysis` before inserting into the message (e.g. `*` → `\*`, `_` → `\_`, etc.), or use a helper like `telegram.helpers.escape_markdown()`.
2. **Alternative: Switch to HTML**: Use `parse_mode="HTML"` and escape `&`, `<`, `>` in the analysis; headers use `<b>...</b>`.
3. **Fallback**: On `BadRequest` from `reply_text`, retry without `parse_mode` (plain text) so the user always receives the analysis.

## Affected Code

- `src/handlers/dream.py`:
  - `handle_dream_message()` — line ~154–158: builds and sends analysis with `parse_mode="Markdown"`
  - The `analysis` variable (from LLM) is the unescaped source of the parse error

## References

- [BF-010: Greeting Parse Entities Error](BF-010-greeting-parse-entities-error.md) — similar fix: HTML mode + plain-text fallback
- [Telegram Bot API: Formatting options](https://core.telegram.org/bots/api#formatting-options)
- [python-telegram-bot: escape_markdown](https://docs.python-telegram-bot.org/en/stable/telegram.helpers.html#telegram.helpers.escape_markdown)
