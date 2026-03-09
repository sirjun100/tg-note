# Sprint 17: Brain Dump & Photo OCR Polish

**Sprint Goal**: Elevate the brain dump experience (US-035) and polish Photo OCR with folder quick-reply, retry logic, and test coverage.

**Duration**: 2026-03-24 – 2026-04-06 (2 weeks)
**Status**: ✅ Complete
**Team Velocity**: 24 points delivered (19 committed + 5 stretch)
**Sprint Planning Date**: 2026-03-08
**Sprint Review Date**: 2026-04-06
**Sprint Retrospective Date**: 2026-04-06

---

## Sprint Overview

**Primary Feature** (13 pts):
- US-035: World-Class Brain Dump Experience — modes, time awareness, recovery, personalization

**Secondary Cluster** (6 pts):
- US-045: Photo OCR — Folder Quick-Reply for NEED_INFO (3 pts)
- US-046: Photo OCR — Test for OCRUnprocessableImageError (1 pt)
- US-047: Photo OCR — Retry on Transient Failures (2 pts)

**Stretch** (5 pts, if capacity allows):
- US-051: /bookmark Command to Save URLs to Joplin

**Focus Areas**:
- UX: richer, multi-modal brain dump with contextual prompts
- Reliability: Photo OCR retry and error handling
- Quality: test coverage for error paths

**Key Deliverables**:
- [ ] US-035: Brain dump modes implemented and working in Telegram
- [ ] US-045: Folder quick-reply inline keyboard on OCR NEED_INFO
- [ ] US-046: Unit test for OCRUnprocessableImageError
- [ ] US-047: Retry logic for transient OCR failures
- [ ] Backlog and RELEASE_NOTES.md updated
- [ ] Doc-code consistency review run

**Dependencies** (all satisfied):
- US-007 (Conversation State) ✅
- US-017 (GTD Expert Persona) ✅
- US-032 (Habit Tracking) ✅
- US-030 (Photo OCR Capture) ✅
- US-005 (Joplin REST API) ✅

**Risks & Blockers**:
- US-035 is 13 pts — largest single item; scope-reduce to 2 modes if needed
- Photo OCR cluster is low-risk; well-contained in `src/handlers/photo.py`

---

## Pre-Sprint Checklist

- [ ] Sprint 16 completed ✅
- [ ] Doc-code consistency review run (`./scripts/doc-code-review.sh`)
- [ ] US-035 acceptance criteria reviewed and understood
- [ ] Photo OCR handler reviewed (`src/handlers/photo.py`)

---

## User Stories

### Story 1: World-Class Brain Dump Experience — 13 Points

**User Story**: As a user, I want a richer brain dump experience with multiple modes, time awareness, and session recovery, so that I can capture more and better organize my thoughts.

**Reference**: [US-035](../backlog/user-stories/US-035-world-class-brain-dump.md)

**Acceptance Criteria**:
- [ ] At least 2 brain dump modes selectable (e.g. GTD-style, freeform)
- [ ] Time/day-phase context included in prompts (morning vs evening tone)
- [ ] Incomplete session can be resumed or discarded
- [ ] Personalization: mode preference remembered across sessions
- [ ] Works end-to-end in Telegram with inline keyboard mode selection

**Technical References**:
- `src/handlers/braindump.py` — core brain dump handler
- `src/conversation_state.py` — session state
- `src/llm_service.py` — prompts
- `tests/test_braindump.py`

**Priority**: 🟠 High
**Story Points**: 13

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-001 | Define brain dump modes (quick/standard/thorough) and parse mode from command args | braindump.py | ✅ | 2 |
| T-002 | Add elapsed time and day-phase context to LLM messages (morning, afternoon, evening) | braindump.py, gtd_expert.txt | ✅ | 2 |
| T-003 | Session recovery: detect incomplete session on /braindump, offer resume or discard | conversation_state.py | ✅ | 3 |
| T-004 | Persist mode preference per user in DB | logging_service.py | ✅ | 2 |
| T-005 | Unit tests: mode selection, time context, session recovery | tests/ | ✅ | 2 |
| T-006 | Update help text and RELEASE_NOTES.md | core.py, RELEASE_NOTES.md | ✅ | 1 |
| T-007 | Mark US-035 ✅ in product backlog | product-backlog.md | ✅ | 0.5 |
| T-008 | Doc-code consistency review for brain dump | scripts/ | ✅ | 0.5 |

**Total Task Points**: 13

---

### Story 2: Photo OCR — Folder Quick-Reply for NEED_INFO — 3 Points

**User Story**: As a user, when the bot needs me to choose a folder for a photo note, I want an inline keyboard with folder options instead of a free-text prompt, so that I can respond faster.

**Reference**: [US-045](../backlog/user-stories/US-045-photo-folder-quick-reply.md)

**Acceptance Criteria**:
- [ ] When OCR returns NEED_INFO for folder, bot replies with inline keyboard listing top Joplin folders
- [ ] Selecting a folder saves the note to the correct location
- [ ] Falls back to text input if folder list unavailable

**Technical References**:
- `src/handlers/photo.py` — OCR handler, NEED_INFO path
- `src/joplin_client.py` — folder listing

**Priority**: 🟡 Medium
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-009 | Fetch top Joplin folders and build inline keyboard on NEED_INFO | photo.py, joplin_client.py | ✅ | 2 |
| T-010 | Handle callback: save OCR note to selected folder | photo.py | ✅ | 1 |

**Total Task Points**: 3

---

### Story 3: Photo OCR — Test for OCRUnprocessableImageError — 1 Point

**User Story**: As a developer, I want a unit test for the OCRUnprocessableImageError path, so that we don't regress on error handling.

**Reference**: [US-046](../backlog/user-stories/US-046-photo-ocr-unprocessable-test.md)

**Acceptance Criteria**:
- [ ] Unit test exists that triggers OCRUnprocessableImageError and verifies correct user message

**Technical References**:
- `src/handlers/photo.py`
- `tests/test_photo.py`

**Priority**: 🟡 Medium
**Story Points**: 1

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-011 | Add unit test: OCRUnprocessableImageError → user-facing error message | test_photo.py | ✅ | 1 |

**Total Task Points**: 1

---

### Story 4: Photo OCR — Retry on Transient Failures — 2 Points

**User Story**: As a user, I want the bot to automatically retry OCR when it fails due to transient API errors, so that I don't have to resend images.

**Reference**: [US-047](../backlog/user-stories/US-047-photo-ocr-retry-transient.md)

**Acceptance Criteria**:
- [ ] Transient API errors (timeout, 5xx) trigger up to 2 retries with backoff
- [ ] Permanent errors (unprocessable, auth) do not retry
- [ ] User is not notified of retries (transparent)

**Technical References**:
- `src/handlers/photo.py`
- `src/llm_service.py` — OCR API call

**Priority**: 🟡 Medium
**Story Points**: 2

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-012 | Add retry decorator/logic for transient OCR errors (2 retries, exponential backoff) | photo.py / llm_service.py | ✅ | 1 |
| T-013 | Unit test: retry fires on transient, not on permanent errors | test_photo.py | ✅ | 1 |

**Total Task Points**: 2

---

### Stretch Story: /bookmark Command — 5 Points

**User Story**: As a user, I want to send a URL to the bot with `/bookmark` and have it saved as a Joplin note with title and summary, so that I can build a read-later list.

**Reference**: [US-051](../backlog/user-stories/US-051-bookmark-command.md)

**Acceptance Criteria**:
- [ ] `/bookmark <url>` fetches page title and summary via URL enrichment
- [ ] Saves note to a "Bookmarks" notebook in Joplin
- [ ] Confirms success with title in Telegram reply
- [ ] Handles invalid/unreachable URLs gracefully

**Technical References**:
- `src/handlers/core.py` — new /bookmark command
- `src/joplin_client.py` — note creation
- URL enrichment logic (reuse from screenshot/recipe flow)

**Priority**: 🟡 Medium
**Story Points**: 5

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-014 | Register /bookmark command; extract URL, fetch title+summary | core.py | ✅ | 2 |
| T-015 | Create Joplin note in Bookmarks notebook; reply with title | joplin_client.py | ✅ | 2 |
| T-016 | Error handling: invalid URL, fetch failure, Joplin unreachable | core.py | ✅ | 1 |

**Total Task Points**: 5

---

## Sprint Summary

**Committed Story Points**: 19 (Stories 1–4)
**Stretch Story Points**: 5 (US-051)
**Total with Stretch**: 24 points

**Sprint Burndown Plan**:
- **Week 1**: Story 1 (T-001–T-005) — brain dump modes, time context, session recovery, tests
- **Week 2**: Story 1 finish (T-006–T-008) + Stories 2–4 (T-009–T-013) — Photo OCR cluster; stretch (T-014–T-016) if capacity

**Scope Reduction** (if needed):
- Phase 1 (Week 1): Story 1 only — 13 pts
- Phase 2 (Week 2): Stories 2–4 — 6 pts → next sprint if overrun

**Success Criteria** (Definition of Done):
- [x] US-035 all acceptance criteria met and marked ✅
- [x] US-045, US-046, US-047 marked ✅
- [x] All new code has unit tests
- [x] RELEASE_NOTES.md updated
- [x] Doc-code consistency review run; no high-priority gaps (5 false positives, 1 resolved)
- [x] Lint passes (`./project-management/scripts/lint-project-management.sh`)

---

## Sprint Review Notes

**Date**: 2026-03-08

### Delivered
- **US-035 Brain Dump Experience** (13 pts): Three modes (quick/standard/thorough), day-phase context injection, idle session recovery, mode preference persistence in SQLite.
- **US-045 Photo OCR Folder Quick-Reply** (3 pts): Inline keyboard with top Joplin folders on NEED_INFO; callback saves note to selected folder; fallback to text input.
- **US-046 OCR Unprocessable Test** (1 pt): Unit test confirms `OCRUnprocessableImageError` path sends friendly user message.
- **US-047 OCR Transient Retry** (2 pts): Up to 2 retries with exponential backoff on timeout/5xx; permanent errors (400) do not retry.
- **US-051 /bookmark Command** (5 pts, stretch): `/bookmark <url>` fetches title+summary, saves to Bookmarks folder in Joplin, confirms with title. Handles invalid URLs and Joplin failures.

### Metrics
- **273 tests passing, 2 skipped, 0 failures**
- **24 story points delivered** (19 committed + 5 stretch)
- Velocity: 24 pts (above baseline ~14 pts/week; sprint was efficient)

### Notes
- Stretch story US-051 completed within sprint capacity — no scope reduction needed.
- `StateManager.user_preferences` table is reusable for future personalization.
- Brain dump context injection works via message prefix (not persona prompt injection), which is simpler and more testable.

---

## Sprint Retrospective

**Date**: 2026-03-08

### What Went Well
- All 5 stories delivered including stretch; zero rework on tests.
- InMemoryStateManager made brain dump tests fast and isolated.
- Photo OCR cluster was low-risk as planned; well-contained in `photo.py`.
- Doc-code consistency check caught one real issue (US-051 file ref) that was immediately resolved.

### What Could Be Improved
- Sprint planning doc referenced non-existent module names (`conversation_state.py`, `llm_service.py`) — use actual filenames from the codebase during planning to avoid false positives in consistency checks.
- US-051 was implemented inside `core.py` rather than a dedicated handler file; for a 5-pt story this is acceptable, but a dedicated `src/handlers/bookmark.py` would improve discoverability.

### Action Items
- None — no blocking retrospective items. The `src/handlers/bookmark.py` separation can be addressed if the feature grows (e.g. when `/bookmarks list` is added).

---

## Related Documents

- [US-035](../backlog/user-stories/US-035-world-class-brain-dump.md)
- [US-045](../backlog/user-stories/US-045-photo-folder-quick-reply.md)
- [US-046](../backlog/user-stories/US-046-photo-ocr-unprocessable-test.md)
- [US-047](../backlog/user-stories/US-047-photo-ocr-retry-transient.md)
- [US-051](../backlog/user-stories/US-051-bookmark-command.md)
- [Definition of Done](../criteria/definition-of-done.md)
- [Product Backlog](../backlog/product-backlog.md)

---

**Last Updated**: 2026-03-08
