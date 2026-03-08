# Defect: DEF-019 - Dream Analysis: "Message is too long" Error Despite Image Generated

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 2
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog

## Description

When using `/dream`, the image is generated and sent successfully, but the user receives "Something went wrong" instead of the Jungian analysis. The dream analysis text is never delivered because it exceeds Telegram's message length limit (4096 characters).

## Steps to Reproduce

1. Send `/dream` to start a dream analysis session.
2. Describe a vivid, detailed dream.
3. Wait for the symbolic image to be generated and sent.
4. Observe: Image appears, then "Something went wrong" — no analysis text.

## Expected Behavior

- User receives the symbolic image.
- User receives the Jungian analysis text (or a truncated/split version).
- User can proceed to "yes/no" for life associations.

## Actual Behavior (User Report)

- Image is generated and sent successfully.
- Error: `Message is too long` (Telegram API)
- User sees generic "Something went wrong" instead of the analysis.
- Logs show: `Error handling message from user X: Message is too long`

## Logs (User Report)

```
{"event": "Generated dream image"}
{"event": "Updated state for user 7256045321"}
{"event": "Error handling message from user 7256045321: Message is too long"}
{"event": "Unhandled error in message handling: Message is too long"}
```

## Root Cause

**Telegram message limit:** 4096 characters for `sendMessage` / `reply_text`.

In `src/handlers/dream.py` (lines 159–164), the analysis is sent in a single message:

```python
msg = f"📖 Jungian Analysis\n\n{analysis}\n\n---\n\n"
msg += "Would you like to explore how this dream connects to your current life? (yes/no)"
msg += DREAM_DISCLAIMER
await message.reply_text(msg)
```

The LLM-generated Jungian analysis can easily exceed 2000–4000+ characters. Combined with the header, prompt, and disclaimer, the total exceeds 4096 → Telegram raises `Message is too long`.

## Affected Code

- `src/handlers/dream.py` — `handle_dream_message()`, lines 159–164 (phase `analyzing`)

## Resolution (2026-03-06)

Implemented **split long messages**:
- Added `split_message_for_telegram()` in `src/security_utils.py` — splits at newlines/spaces when possible
- Added `TELEGRAM_MESSAGE_MAX_LENGTH = 4096` in `src/constants.py`
- Dream handler sends analysis in multiple messages when it exceeds 4096 chars

## References

- [US-025: Jungian Dream Analysis](../user-stories/US-025-jungian-dream-analysis.md)
- [DEF-014: Dream Parse Entities](DEF-014-dream-parse-entities-error.md)
- [DEF-016: Dream Parse User Report](DEF-016-dream-parse-error-user-report.md)
- [DEF-017: Dream Command Crash](DEF-017-dream-command-crash.md)
- [Telegram API: sendMessage](https://core.telegram.org/method/messages.sendMessage) — max length 4096
