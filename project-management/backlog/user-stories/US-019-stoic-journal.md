# User Story: US-019 - Stoic Journal with Morning/Evening Guided Reflection

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 5
**Created**: 2026-02-15
**Updated**: 2026-03-01
**Assigned Sprint**: Sprint 7

## Description

Provide a guided Stoic journaling experience through Telegram with separate morning and evening flows. The morning session focuses on intention-setting and preparing for the day, while the evening session focuses on reflection, gratitude, and self-assessment. Sessions are multi-turn conversations driven by an LLM persona, saved as structured notes in Joplin.

## User Story

As a user who wants to build a daily journaling practice,
I want guided morning and evening Stoic reflection prompts through Telegram,
so that I can develop self-awareness and a consistent journaling habit without friction.

## Acceptance Criteria

- [x] `/stoic` command starts a journaling session (defaults to time-appropriate morning/evening)
- [x] `/stoic morning` starts a morning intention-setting session
- [x] `/stoic evening` starts an evening reflection session
- [x] `/stoic_done` ends the session and saves the reflection
- [x] Multi-turn guided conversation with LLM-driven follow-up questions
- [x] Morning flow covers: intentions, priorities, potential obstacles, mindset
- [x] Evening flow covers: gratitude, accomplishments, challenges, lessons learned
- [x] Final reflection is formatted using a structured Stoic journal template
- [x] Note saved to Joplin under `Areas/Journaling/Stoic Journal/`
- [x] Appropriate tags applied (e.g. `stoic-journal`, `morning`/`evening`)
- [x] Session state managed via `StateManager` (conversation persists across messages)
- [x] Session can be cancelled or restarted

## Business Value

Journaling is one of the highest-leverage habits for personal growth. By integrating it into Telegram — where the user already captures thoughts — friction is minimized. The Stoic framework provides structure without being prescriptive, and the LLM adapts to the user's responses for a personalized experience.

## Technical Requirements

- Multi-turn conversation handling via `StateManager`
- LLM persona for Stoic journaling (`stoic_journal` persona)
- Stoic journal template (`src/prompts/stoic_journal_template.md`)
- Note creation in Joplin with folder resolution
- Tag application
- Session timeout/cleanup

## Implementation

### Key Files
- `src/handlers/stoic.py` — Command handlers (`/stoic`, `/stoic_done`), session management, note saving
- `src/prompts/stoic_journal_template.md` — Structured template for final reflection output
- `src/llm_orchestrator.py` — `format_stoic_reflection()` for generating the final note
- `tests/test_stoic.py` — Unit tests

### Commands
| Command | Description |
|---------|-------------|
| `/stoic` | Start session (auto-detects morning/evening based on time) |
| `/stoic morning` | Start morning intention-setting session |
| `/stoic evening` | Start evening reflection session |
| `/stoic_done` | End session, generate reflection, save to Joplin |

### Flow
1. User sends `/stoic evening`
2. Bot sets active persona to `stoic_journal`, stores session type (morning/evening)
3. Bot asks first guided question based on session type
4. User responds → LLM generates follow-up based on conversation history
5. Multi-turn continues until user sends `/stoic_done`
6. LLM formats final reflection using `stoic_journal_template.md`
7. Note created in Joplin (`Areas/Journaling/Stoic Journal/`)
8. Tags applied, confirmation sent to user

## Reference Documents

- `docs/stoic-journal-command-brainstorm.md` — Original design brainstorm
- `src/prompts/stoic_journal_template.md` — Output template

## Dependencies

- Conversation State Management (US-007)
- LLM Integration (US-006)
- Joplin REST API Client (US-005)

## Testing

- [x] Unit tests (`tests/test_stoic.py`)
- [x] Template loading test
- [x] Message handling test
- [x] Session finish test
- [x] Manual testing completed

## Notes

- This feature was implemented alongside US-017 (GTD Expert Persona) during Sprint 7 but was not tracked as a separate backlog item.
- Added retroactively as US-019 during the 2026-03-01 status audit.

## History

- 2026-02-15 - Implemented during Sprint 7
- 2026-03-01 - Added to backlog as US-019 (retroactive tracking)
