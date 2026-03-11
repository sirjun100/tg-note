# Defect: DEF-032 - Joplin did not process voice message transcription

[← Back to Product Backlog](../product-backlog.md)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19

---

## Problem Statement

When a voice message was sent to the Telegram bot, no voice handler was registered — the feature never existed. Voice messages were silently ignored and no note was created in Joplin.

**User impact:** Users could not dictate notes by voice. The bot gave no response to voice messages.

---

## Steps to Reproduce

1. Send a voice note to the bot in Telegram
2. Observe: no response, no note created in Joplin

---

## Expected Behavior

Voice message is transcribed via Whisper, transcript shown to user, and routed through the same pipeline as text messages (note or task creation in Joplin).

---

## Actual Behavior

Bot silently ignored voice messages — no handler was registered for `filters.VOICE | filters.AUDIO`.

---

## Root Cause

No voice/audio message handler was ever implemented. The `filters.VOICE` handler was missing from `telegram_orchestrator.py`.

---

## Fix

Implemented `src/handlers/voice.py`:
- Download voice/audio from Telegram
- Transcribe via OpenAI Whisper (`whisper-1` model)
- Show transcript to user
- Route through `_route_plain_message` (same as text input)
- Registered in `telegram_orchestrator.py` before core handlers

| File | Change |
|------|--------|
| `src/handlers/voice.py` | New file — full voice pipeline |
| `src/handlers/__init__.py` | Export `register_voice_handlers` |
| `src/telegram_orchestrator.py` | Register voice handler on startup |

---

## References

- [US-058](../user-stories/US-058-bot-understands-natural-conversational-intent-from.md)
- [Sprint 19](../../sprints/sprint-19-polish-and-bug-fixes.md)

---

## History

- 2026-03-10 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
