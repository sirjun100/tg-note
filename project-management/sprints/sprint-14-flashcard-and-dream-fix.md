# Sprint 14: Flashcard Practice & Dream Fix

**Sprint Goal**: Fix the /dream command crash (BF-017) and deliver flashcard practice from Joplin notes (FR-033), turning the Second Brain into a memory-building practice gym.

**Duration**: 2026-05-05 - 2026-05-18 (2 weeks)
**Status**: ⏳ Planned
**Team Velocity**: 9 points (BF-017 + FR-033)
**Sprint Planning Date**: 2026-03-06
**Sprint Review Date**: 2026-05-18
**Sprint Retrospective Date**: 2026-05-18

## Sprint Overview

**Focus Areas**:
- Dream command stability (parse/markdown, state, error handling)
- Flashcard system: card extraction from notes, SM-2 scheduling, session flow in Telegram

**Key Deliverables**:
- BF-017: /dream command responds reliably with welcome message (no crash)
- FR-033: /flashcard command with spaced repetition, card extraction from #flashcard notes, session flow

**Dependencies**:
- FR-005 (Joplin REST API) ✅
- FR-006 (LLM Integration) ✅
- FR-007 (Conversation State Management) ✅
- `src/handlers/dream.py` (existing)
- `src/joplin_client.py`, `src/llm_orchestrator.py` (existing)

**Risks & Blockers**:
- BF-017: May be Markdown parse issue (similar to BF-010, BF-014) — switch to HTML or plain text if needed
- FR-033: LLM card extraction quality — allow manual cards, skip option

**Alternative Scope** (if preferring brain dump focus):
- BF-017 (1 pt) + FR-035 World-Class Brain Dump (13 pts) = 14 pts — replaces FR-033 with brain dump enhancements

---

## Pre-Sprint Checklist

- [x] Documentation-Code Consistency Review run (2026-03-06)
- [ ] Report reviewed: `project-management/reports/doc-code-consistency-latest.md`
- [ ] High-priority contradictions resolved or triaged

---

## User Stories

### Story 1: Dream Command Crash Fix - 1 Point

**User Story**: As a user who uses /dream for Jungian dream analysis, I want the command to show the welcome message without crashing, so that I can start a dream session reliably.

**Acceptance Criteria**:
- [ ] Sending `/dream` alone shows welcome message: "🌙 **Welcome to Dream Analysis**"
- [ ] Instructions to describe the dream and "Type /dream_cancel to cancel anytime" are displayed
- [ ] No crash, no unhandled exception
- [ ] If Markdown parse is the cause, switch to HTML or plain text

**Reference Documents**:
- [BF-017: Dream Command Crashes Agent](../backlog/bugs/BF-017-dream-command-crash.md)
- [BF-010: Greeting Parse Entities](../backlog/bugs/BF-010-greeting-parse-entities-error.md)
- [BF-014: Dream Parse Entities](../backlog/bugs/BF-014-dream-parse-entities-error.md)

**Technical References**:
- File: `src/handlers/dream.py` — `dream_cmd`, `register_dream_handlers`
- Fix pattern: BF-010, BF-014 (parse_mode, entity escaping)

**Story Points**: 1

**Priority**: 🟠 High

**Status**: ⭕ Not Started

**Backlog Reference**: [BF-017](../backlog/bugs/BF-017-dream-command-crash.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Diagnose crash (logging, parse_mode, state) | `handlers/dream.py:dream_cmd` | BF-017 | ⭕ | 0.25 | — |
| T-002 | Fix welcome message (HTML or plain text if Markdown fails) | `handlers/dream.py` | BF-017 | ⭕ | 0.5 | — |
| T-003 | Add exception handling and user-facing error message | `handlers/dream.py` | BF-017 | ⭕ | 0.25 | — |

**Total Task Points**: 1

---

### Story 2: Flashcard Practice from Notes - 8 Points

**User Story**: As a user with notes I want to remember—concepts, decisions, quotes—I want to practice them as flashcards in Telegram using spaced repetition, so that I strengthen my memory without it feeling like homework.

**Acceptance Criteria**:

**Core Flow**:
- [ ] `/flashcard` starts a session (default 5–10 cards)
- [ ] `/flashcard N` starts session with up to N cards
- [ ] Cards show question first; user reveals answer, then rates: Easy | Good | Hard | Again (or 👍/👎 simplified)
- [ ] Session ends with brief summary (e.g., "🎯 7/8 today. Nice work!")
- [ ] `/flashcard_done` or "stop"/"done" ends session early

**Card Source**:
- [ ] Cards extracted from Joplin notes via LLM (question–answer pairs)
- [ ] Notes tagged `#flashcard` or `#practice` included in pool
- [ ] Option: `/flashcard from <note title>` to generate from specific note
- [ ] Cards link back to source note

**Spaced Repetition**:
- [ ] SM-2–style scheduling (interval, easiness factor)
- [ ] "Again" → reschedule 1 day; "Good"/"Easy" → increase interval
- [ ] New cards introduced gradually (3–5 per session default)

**Filtering**:
- [ ] `/flashcard tag <tag>` — filter by tag
- [ ] `/flashcard folder <path>` — filter by folder (PARA-aware)
- [ ] Default: all #flashcard/#practice notes

**Stats & Help**:
- [ ] `/flashcard stats` — due count, streak, session history
- [ ] `/flashcard help` — usage guide

**Reference Documents**:
- [FR-033: Flashcard Practice from Notes](../backlog/features/FR-033-flashcard.md)

**Technical References**:
- File: `src/flashcard_service.py` (new) — Card CRUD, SM-2, session logic
- File: `src/handlers/flashcard.py` (new) — Command handlers, inline keyboards
- File: `src/prompts/flashcard_extractor.txt` (new) — LLM prompt for Q&A extraction
- Database: `flashcards`, `card_reviews`, `flashcard_sessions` tables

**Story Points**: 8

**Priority**: 🟠 High

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-033](../backlog/features/FR-033-flashcard.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-004 | Create DB schema (flashcards, card_reviews, flashcard_sessions) | Migration / schema | FR-033 | ⭕ | 1 | — |
| T-005 | Implement FlashcardService (CRUD, SM-2 scheduling, due selection) | `flashcard_service.py` | FR-033 | ⭕ | 2 | — |
| T-006 | Add LLM card extraction (prompt, extract_flashcards_from_note) | `llm_orchestrator.py`, prompt | FR-033 | ⭕ | 1.5 | — |
| T-007 | Create flashcard handlers (/flashcard, session flow, inline keyboards) | `handlers/flashcard.py` | FR-033 | ⭕ | 2 | — |
| T-008 | Implement tag/folder filtering, stats, help | `flashcard_service.py`, handlers | FR-033 | ⭕ | 1 | — |
| T-009 | Register handlers, add to greeting/help, unit tests | `handlers/__init__.py`, tests | FR-033 | ⭕ | 0.5 | — |

**Total Task Points**: 8

---

## Sprint Summary

**Total Story Points**: 9 (BF-017: 1, FR-033: 8)
**Total Task Points**: 9
**Estimated Velocity**: 9 points

**Sprint Burndown Plan**:
- Week 1: Story 1 (BF-017) — 1 pt; Story 2 start (T-004, T-005, T-006)
- Week 2: Story 2 (FR-033) — 8 pts; T-007, T-008, T-009

**Buffer**: 5 points under ~14 pt velocity — allows for FR-016/FR-018 progress or Sprint 13 spillover.

**Sprint Review Notes**:
- [ ] [RELEASE_NOTES.md](../../../RELEASE_NOTES.md) updated (see [release-notes-process.md](../docs/processes/release-notes-process.md))
- [To be filled at sprint review]

**Sprint Retrospective Notes**:
- **What went well?**
  - [To be filled]
- **What could be improved?**
  - [To be filled]
- **Action items for next sprint**
  - [To be filled]

---

**Last Updated**: 2026-03-06
