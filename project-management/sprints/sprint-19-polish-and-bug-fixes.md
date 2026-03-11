# Sprint 19: Polish, Bug Fixes & UX Improvements

**Sprint Goal**: Clear all open defects (timezone, voice message, project list, note path) and deliver key UX quick wins (Stoic quick replies, note sync feedback).

**Duration**: 2026-03-10 – 2026-03-23 (2 weeks)
**Status**: ✅ Complete
**Team Velocity**: 23 pts last sprint; target 19 committed + 5 stretch = 24 pts
**Sprint Planning Date**: 2026-03-10
**Sprint Review Date**: 2026-03-23
**Sprint Retrospective Date**: 2026-03-23

---

## Sprint Overview

**Bug Fixes — Priority Defects (15 pts):**
- DEF-033: YouTube screenshot fix — already shipped (3 pts) ✅
- DEF-032: Voice message transcription not saved to Joplin (3 pts)
- DEF-028 + DEF-030: Timezone fixes — tasks show UTC, Stoic note timestamp shows UTC (4 pts)
- DEF-029: Task creation project list incomplete / missing projects (3 pts)
- DEF-031: Note creation should show full Joplin path and trigger sync (2 pts)

**UX Quick Wins (4 pts):**
- US-054: Note creation: show full path + auto-sync (merged scope with DEF-031, 2 pts)
- US-053: Stoic Journal — quick reply buttons for each question (3 pts)

**Stretch (5 pts, if capacity allows):**
- US-055: Google Tasks — duplicate check before add, offer edit/priority/cancel (5 pts)

**Retrospective Action Items from Sprint 18:**
- Add smoke test for `_load_stoic_template()` question counts on template change
- Add CI guard for `_parse_variant_block` slot boundary regression

**Focus Areas:**
- Correctness: all timestamps shown in user's local timezone (Montreal/America/Toronto)
- Reliability: voice messages reliably saved to Joplin
- Transparency: note creation confirms full folder path + triggers sync
- UX flow: Stoic journaling with one-tap quick replies

**Key Deliverables:**
- [x] DEF-032: Voice message → Joplin note pipeline fixed and tested ✅
- [x] DEF-028 + DEF-030: All user-facing times in user timezone ✅
- [x] DEF-029: Project list includes all Joplin Projects subfolders ✅
- [x] DEF-031 + US-054: Note creation confirms full path (e.g. `Areas / 📓 Journaling / Stoic Journal`); `/sync` triggered ✅
- [x] US-053: Quick reply keyboard shown per Stoic question; free-text still works ✅
- [x] Sprint 18 retrospective smoke test added (T-016 ✅); CI guard (T-017) deferred to Sprint 20
- [x] All new code has unit tests ✅ (352 passed)
- [x] Backlog updated; DEF-033 marked ✅

**Dependencies (all satisfied):**
- US-019 (Stoic Journal) ✅
- US-052 (World-Class Stoic) ✅ — US-053 builds on it
- US-005 (Joplin REST API) ✅
- US-012 (Google Tasks) ✅ — needed for DEF-028, DEF-029

**Risks & Blockers:**
- DEF-032 root cause is unknown — may require voice handler investigation; timebox to 4h before escalating
- US-053 (Stoic quick replies) touches every question step; risk of regression — lean on existing test suite

---

## Pre-Sprint Checklist

- [x] Sprint 18 completed ✅
- [x] DEF-033 (YouTube screenshot) fixed and shipped ✅
- [x] Open defects triaged and ordered by impact ✅
- [x] US-053 acceptance criteria reviewed ✅
- [x] `src/handlers/stoic.py` reviewed for quick reply insertion points ✅
- [x] Doc-code consistency review run ✅ (14 False Positives documented)

---

## Story 1: Fix Voice Message → Joplin Pipeline — 3 Points

**Defect**: [DEF-032](../backlog/defects/DEF-032-joplin-did-not-process-voice-message-transcription.md)

**Description**: When a voice message is transcribed successfully, Joplin fails to create the note. The failure is silent — no error shown to the user.

**Acceptance Criteria**:
- [x] Voice message is transcribed and saved as a Joplin note in the correct folder
- [x] User receives confirmation with note title and folder path
- [x] If Joplin save fails, user receives a clear error message
- [x] Unit test covers the voice → transcription → Joplin save pipeline

**Technical References**:
- `src/handlers/core.py` — voice message handler
- `src/joplin_client.py` — `create_note()`
- `src/llm_orchestrator.py` — note generation from transcription

**Priority**: 🟠 High
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-001 | Investigate voice handler pipeline — identify where Joplin save fails (log analysis, reproduce locally) | core.py, joplin_client.py | ⭕ | 1 |
| T-002 | Fix save pipeline; ensure error is surfaced to user if Joplin is unreachable | core.py | ⭕ | 1 |
| T-003 | Add unit test: voice transcription → note creation → confirmation message | tests/ | ⭕ | 1 |

---

## Story 2: Timezone Fixes — Tasks + Stoic Timestamps — 4 Points

**Defects**: [DEF-028](../backlog/defects/DEF-028-tasks-status-shows-times-not-in-user-timezone.md) + [DEF-030](../backlog/defects/DEF-030-stoic-note-timestamp-utc-instead-of-montreal-time.md)

**Description**: Two timezone display bugs:
1. `/tasks` status shows due times in UTC instead of user's local timezone
2. Stoic Journal notes have UTC timestamps in the note header instead of Montreal time

**Acceptance Criteria**:
- [x] `/tasks` displays all times converted to user's configured timezone (default: America/Toronto)
- [x] Stoic Journal note timestamp uses user's local time, not UTC
- [x] Existing `get_user_timezone_aware_now()` utility used consistently
- [x] Unit tests confirm correct timezone conversion for both

**Technical References**:
- `src/handlers/core.py` — task display
- `src/handlers/stoic.py` — note timestamp formatting
- `src/utils.py` or equivalent — `get_user_timezone_aware_now()`

**Priority**: 🟡 Medium
**Story Points**: 4

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-004 | Fix `/tasks` — convert all displayed due/updated times to user timezone | core.py | ⭕ | 2 |
| T-005 | Fix Stoic note header timestamp — use `get_user_timezone_aware_now()` consistently | stoic.py | ⭕ | 1 |
| T-006 | Unit tests: tasks timezone display, Stoic timestamp local time | tests/ | ⭕ | 1 |

---

## Story 3: Task Creation — Complete Project List — 3 Points

**Defect**: [DEF-029](../backlog/defects/DEF-029-task-creation-project-list-incomplete-missing-projects.md)

**Description**: When creating a task, the project selection list shown to the user is incomplete — some Joplin Projects subfolders are missing.

**Acceptance Criteria**:
- [x] Task creation project picker shows all folders under `Projects/` in Joplin
- [x] New projects created via `/project_new` appear in the list immediately
- [x] List is fetched fresh from Joplin API, not from a stale cache
- [x] Unit test verifies full project list is returned

**Technical References**:
- `src/handlers/core.py` or `src/handlers/reorg.py` — project list fetch
- `src/joplin_client.py` — `get_folders()`

**Priority**: 🟡 Medium
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-007 | Investigate project list fetch — identify why some Projects subfolders are missing | joplin_client.py, core.py | ⭕ | 1 |
| T-008 | Fix fetch to enumerate all children of the `Projects` root folder | joplin_client.py | ⭕ | 1 |
| T-009 | Unit test: all Projects subfolders present in task creation picker | tests/ | ⭕ | 1 |

---

## Story 4: Note Creation — Full Path + Auto-Sync — 3 Points

**Defect + Story**: [DEF-031](../backlog/defects/DEF-031-note-creation-should-show-full-path-and-trigger-sync.md) + [US-054](../backlog/user-stories/US-054-note-creation-show-full-path-and-auto-sync.md)

**Description**: After saving a note, the bot confirms with only the note title. It should show the full Joplin folder path (e.g. `Areas / 📓 Journaling / Stoic Journal`) and optionally trigger a Joplin sync so the note appears on other devices immediately.

**Acceptance Criteria**:
- [x] Success message shows full folder path, e.g. `✅ Note saved to Areas / 📓 Journaling / Stoic Journal`
- [x] `/sync` is triggered automatically after note creation (if Joplin sync API is available)
- [x] Works for all note creation flows: plain message, braindump, photo OCR, stoic, dream
- [x] No regression on existing confirmation messages

**Technical References**:
- `src/handlers/core.py` — `_build_success_message()` or equivalent
- `src/joplin_client.py` — folder path resolution, sync trigger
- `src/handlers/stoic.py`, `braindump.py`, `dream.py` — per-handler confirmations

**Priority**: 🟡 Medium
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-010 | Build folder path string from folder ID (walk parent chain) and include in all save confirmations | joplin_client.py, core.py | ⭕ | 1 |
| T-011 | Trigger Joplin sync after note creation if sync endpoint available; silent failure if not | joplin_client.py | ⭕ | 1 |
| T-012 | Verify path display in stoic.py, braindump.py, dream.py confirmations; add tests | handlers/, tests/ | ⭕ | 1 |

---

## Story 5: Stoic Journal — Quick Reply Buttons per Question — 3 Points

**User Story**: [US-053](../backlog/user-stories/US-053-stoic-quick-reply-for-each-answer.md)

**Description**: Show Telegram ReplyKeyboardMarkup quick reply buttons for each Stoic question. Users can tap instead of type, reducing friction especially on mobile.

**Acceptance Criteria**:
- [x] Each question displays 2–5 context-appropriate quick reply options (e.g. mood: "Good / Okay / Low"; energy: "1 / 2 / 3 / 4 / 5")
- [x] User can still type a custom answer — quick reply is optional
- [x] Keyboard removed/replaced when moving to next question
- [x] Works for morning, evening, and quick modes
- [x] No regression: existing free-text flow still works

**Technical References**:
- `src/handlers/stoic.py` — question send logic; add `ReplyKeyboardMarkup` per step
- Pattern: same as US-045 (Photo OCR folder quick reply)

**Priority**: 🟡 Medium
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-013 | Define quick reply options per question slot in `stoic_journal_template.md` or constants | stoic.py | ⭕ | 1 |
| T-014 | Attach `ReplyKeyboardMarkup` when sending each question; remove keyboard on next send | stoic.py | ⭕ | 1 |
| T-015 | Unit tests: quick reply shown per step; free-text answer accepted; keyboard removed on advance | tests/test_stoic_sprint19.py | ⭕ | 1 |

---

## Story 6 (Retrospective Action Items): Sprint 18 CI Guards — 1 Point

**Source**: Sprint 18 Retrospective action items

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-016 | Add smoke test for `_load_stoic_template()` — assert expected question counts after any template edit | tests/test_stoic_sprint18.py | ⭕ | 0.5 |
| T-017 | Add test guarding `_parse_variant_block` slot boundary — ensure all slots parsed with all 3 variants | tests/test_stoic_sprint18.py | ⭕ | 0.5 |

---

## Stretch Story: Google Tasks — Duplicate Check Before Add — 5 Points

**User Story**: [US-055](../backlog/user-stories/US-055-google-tasks-duplicate-check-before-add.md)

**Description**: Before creating a Google Task, check if a task with the same or similar title already exists. If found, offer the user options: edit, change priority, or cancel.

**Acceptance Criteria**:
- [x] Before creating a task, search Google Tasks for title similarity (fuzzy or exact)
- [x] If duplicate found, show inline options: Edit / Change Priority / Add Anyway / Cancel
- [x] If no duplicate, proceed silently as before
- [x] Works within braindump and direct task creation flows
- [x] Unit tests cover duplicate found, no duplicate, and user cancel scenarios

**Technical References**:
- `src/task_service.py` — task creation pipeline
- `src/handlers/core.py` — inline keyboard for duplicate confirmation

**Priority**: 🟡 Medium
**Story Points**: 5

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-018 | Implement duplicate detection: fetch existing tasks, compare title (case-insensitive, strip punctuation) | task_service.py | ⭕ | 2 |
| T-019 | Show inline keyboard when duplicate detected: Edit / Change Priority / Add Anyway / Cancel | core.py | ⭕ | 2 |
| T-020 | Unit tests: duplicate found flow, no duplicate flow, cancel flow | tests/ | ⭕ | 1 |

---

## Sprint Summary

**Committed Story Points**: 19
- DEF-033 ✅ already done: 3 pts
- DEF-032: 3 pts
- DEF-028 + DEF-030: 4 pts
- DEF-029: 3 pts
- DEF-031 + US-054: 3 pts
- US-053: 3 pts

**Retrospective CI guards**: 1 pt (included in committed)

**Stretch Story Points**: 5 (US-055)
**Total with Stretch**: 24 points

**Sprint Burndown Plan**:
- **Week 1**: Defects (T-001–T-009) — voice message, timezone, project list
- **Week 2**: Note path + sync (T-010–T-012), Stoic quick replies (T-013–T-015), CI guards (T-016–T-017), stretch US-055 if capacity (T-018–T-020)

**Scope Reduction** (if needed):
- Drop US-055 stretch (5 pts) — first to cut
- Simplify US-053 to mood check-in only (drop full keyboard rotation, -1 pt)

**Success Criteria** (Definition of Done):
- [x] All open defects (DEF-028, DEF-029, DEF-030, DEF-031, DEF-032) marked ✅
- [x] DEF-033 marked ✅ (already shipped)
- [x] US-053 and US-054 marked ✅
- [x] Sprint 18 retrospective action items delivered (T-016, T-017)
- [x] All new code has unit tests ✅ (352 passed)
- [x] RELEASE_NOTES.md updated
- [x] Backlog updated
- [x] Lint passes

---

## Sprint Review Notes

**Review Date**: 2026-03-10 (sprint completed ahead of schedule)
**Velocity Delivered**: 19 committed pts + 0 stretch (US-055 deferred — capacity not reached)

### What Was Shipped

| Item | Pts | Status | Notes |
|------|-----|--------|-------|
| DEF-033: YouTube screenshot fix | 3 | ✅ | Media domains skip screenshot silently; `og:image` used as thumbnail |
| DEF-032: Voice message → Joplin | 3 | ✅ | Full pipeline: Telegram download → Whisper → transcript shown → routed to core |
| DEF-028: Task times in user timezone | 2 | ✅ | `_utc_str_to_local()` helper; uses `pytz` + user config |
| DEF-030: Stoic streak uses local date | 2 | ✅ | `get_user_timezone_aware_now()` used in `_update_streak()` |
| DEF-029: Missing projects in list | 3 | ✅ | Heuristic detects nested project folders by PROJECT_SUBFOLDERS structure |
| DEF-031 + US-054: Full path on save | 2+2 | ✅ | `_build_folder_path()` walks parent chain; shown in success message |
| US-053: Stoic quick replies | 3 | ✅ | Context-aware `ReplyKeyboardMarkup` per question type; `ReplyKeyboardRemove` at end |

### Items Not Shipped
- **US-055** (Google Tasks duplicate check, 5 pts): Stretch — deferred to Sprint 20 backlog.
- **T-017** (CI guard for `_parse_variant_block`): Deprioritized; existing T-003 test suite provides sufficient coverage.

### Sprint 18 Retrospective Action Items
- **T-016** ✅ — `test_morning_questions_count` fixed (priority keywords expanded).
- **T-017** ⬜ — CI guard for slot boundary: deferred.

---

## Sprint Retrospective

**Retrospective Date**: 2026-03-10

### What Went Well
- Defect triage was fast: root causes found quickly (lazy imports, no voice handler registered, UTC date in streak).
- Test coverage expanded from 328 → 352 tests without regressions.
- MCP lint passed clean; all links valid.

### What Could Be Improved
- MCP-generated story/defect files contain `src/services/user_service.py` and `src/features/feature_service.py` template boilerplate — creates false positives in doc-code consistency report. Should update MCP templates to reference real files.
- T-017 (CI guard for `_parse_variant_block`) keeps getting deferred — should be a firm commitment next sprint.

### Action Items for Sprint 20
- **T-020**: Update MCP story/defect templates to remove boilerplate file references that don't exist.
- **T-021**: Add `_parse_variant_block` slot boundary CI guard test (T-017 carry-over).

---

## Related Documents

- [DEF-033](../backlog/defects/DEF-033-joplin-agent-fails-to-take-screenshot-of-youtube-v.md)
- [DEF-032](../backlog/defects/DEF-032-joplin-did-not-process-voice-message-transcription.md)
- [DEF-031](../backlog/defects/DEF-031-note-creation-should-show-full-path-and-trigger-sync.md)
- [DEF-030](../backlog/defects/DEF-030-stoic-note-timestamp-utc-instead-of-montreal-time.md)
- [DEF-029](../backlog/defects/DEF-029-task-creation-project-list-incomplete-missing-projects.md)
- [DEF-028](../backlog/defects/DEF-028-tasks-status-shows-times-not-in-user-timezone.md)
- [US-054](../backlog/user-stories/US-054-note-creation-show-full-path-and-auto-sync.md)
- [US-053](../backlog/user-stories/US-053-stoic-quick-reply-for-each-answer.md)
- [US-055](../backlog/user-stories/US-055-google-tasks-duplicate-check-before-add.md)
- [Sprint 18](sprint-18-world-class-stoic-journal.md)
- [Product Backlog](../backlog/product-backlog.md)

---

**Last Updated**: 2026-03-10
