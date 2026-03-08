# Sprint 11: New Capture Modalities

**Sprint Goal**: Expand capture modalities with photo OCR, read-later queue, Jungian dream analysis, and habit tracking.

**Duration**: 2026-03-24 - 2026-04-06 (2 weeks)
**Status**: ✅ Complete
**Team Velocity**: 31 points (delivered)
**Sprint Planning Date**: 2026-03-05
**Sprint Review Date**: 2026-04-06
**Sprint Retrospective Date**: 2026-04-06

## Sprint Overview

**Focus Areas**:
- Visual capture (photo OCR via Gemini)
- Reading workflow (read-later queue)
- Dream journaling (Jungian analysis + image generation)
- Habit tracking (daily check-ins with streaks)

**Key Deliverables**:
- Photo message handler with Gemini OCR
- `/readlater` and `/reading` commands
- `/dream` guided conversation with image generation
- `/habits` check-in with inline buttons and streak tracking

**Dependencies**:
- Sprint 10 (Greeting - for command list updates)
- Joplin REST API (Complete - US-005)
- Gemini API (Configured - GEMINI_API_KEY)
- URL Enrichment (Complete - for read-later)
- Google Tasks (Complete - US-012, for planning in Sprint 12)

**Risks & Blockers**:
- Gemini rate limits for OCR (mitigated by retry pattern from recipe_image.py)
- Habit SQLite schema (use existing STATE_DB_PATH)

---

## User Stories

### Story 1: Photo/Screenshot OCR Capture - 5 Points

**User Story**: As a user who encounters information in visual form, I want to photograph whiteboards, documents, or handwritten notes and have them saved to Joplin, so that I can capture knowledge without manually transcribing.

**Acceptance Criteria**:
- [ ] Sending a photo triggers OCR processing
- [ ] Extracted text is included in the note body
- [ ] Original image is attached to the Joplin note
- [ ] LLM classifies/routes the content (folder, tags) based on extracted text
- [ ] User can add caption to photo for additional context
- [ ] Works with: screenshots, whiteboard photos, documents, handwritten notes
- [ ] Handles photos with no text gracefully ("No text detected")
- [ ] Processing indicator shown while OCR runs

**Reference Documents**:
- [US-030: Photo/Screenshot OCR Capture](../backlog/user-stories/US-030-photo-ocr-capture.md)
- [API Reference: Gemini](../../docs/api-reference.md)

**Technical References**:
- File: `src/recipe_image.py` - Gemini API pattern to follow
- File: `src/ocr_service.py` (new) - OCR via Gemini 1.5 Flash
- File: `src/joplin_client.py` - Add `create_resource()` for image attachments
- File: `src/handlers/photo.py` (new) - Photo message handler

**Story Points**: 5

**Priority**: 🟡 Medium

**Status**: ✅ Complete

**Backlog Reference**: [US-030](../backlog/user-stories/US-030-photo-ocr-capture.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create ocr_service with Gemini vision extraction | `ocr_service.py:extract_text_from_image()` | US-030 Gemini OCR | ✅ | 1.5 | — |
| T-002 | Add create_resource() to JoplinClient | `JoplinClient.create_resource()` | US-030 Joplin Resources | ✅ | 1 | — |
| T-003 | Create photo handler with progress indicator | `handlers/photo.py` | US-030 Handler | ✅ | 1.5 | — |
| T-004 | Integrate caption, classification, note creation | `handlers/photo.py` | US-030 Flow | ✅ | 1 | — |

**Total Task Points**: 5

---

### Story 2: Read Later Queue - 5 Points

**User Story**: As a user who encounters interesting articles throughout the day, I want to quickly save them for later reading, so that I don't lose track of content I want to consume without interrupting my current work.

**Acceptance Criteria**:
- [ ] `/readlater <url>` saves URL to reading queue
- [ ] Automatic title and summary extraction (using existing URL enrichment)
- [ ] `/reading` shows queue with titles and short summaries
- [ ] `/reading done <id>` marks item as read
- [ ] Queue stored in Joplin folder: `03 - Resources/📚 Reading List/`
- [ ] Each item is a note with metadata (source, date saved, read status)
- [ ] Optional: `/reading random` picks a random unread item

**Reference Documents**:
- [US-028: Read Later Queue](../backlog/user-stories/US-028-read-later-queue.md)

**Technical References**:
- File: `src/url_enrichment.py` - Reuse for title/summary
- File: `src/reading_service.py` (new) - Queue management
- File: `src/handlers/reading.py` (new) - Commands
- File: `src/joplin_client.py` - `get_or_create_folder_by_path()`

**Story Points**: 5

**Priority**: 🟡 Medium

**Status**: ✅ Complete

**Backlog Reference**: [US-028](../backlog/user-stories/US-028-read-later-queue.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create reading_service for queue CRUD | `reading_service.py` | US-028 Service | ✅ | 1.5 | — |
| T-002 | Implement /readlater with URL enrichment | `handlers/reading.py` | US-028 Save | ✅ | 1 | — |
| T-003 | Implement /reading and /reading done | `handlers/reading.py` | US-028 Queue Display | ✅ | 1.5 | — |
| T-004 | Add Reading List folder setup | `reading_service.py` | US-028 Folder Structure | ✅ | 1 | — |

**Total Task Points**: 5

---

### Story 3: Jungian Dream Analysis - 8 Points

**User Story**: As a user interested in self-discovery and dream work, I want to describe my dreams and receive Jungian analysis with visual representation, so that I can understand my unconscious mind and apply insights to my waking life.

**Acceptance Criteria**:
- [ ] `/dream` command starts a dream analysis session
- [ ] Bot prompts user to describe their dream in detail
- [ ] LLM generates a symbolic image representing the dream
- [ ] LLM provides Jungian interpretation of key symbols and themes
- [ ] Bot asks if user wants to explore life associations
- [ ] Session saved to Joplin with image, interpretation, and associations
- [ ] `/dream_done` ends session and saves the analysis
- [ ] `/dream_cancel` cancels without saving

**Reference Documents**:
- [US-025: Jungian Dream Analysis](../backlog/user-stories/US-025-jungian-dream-analysis.md)
- [US-019: Stoic Journal](../backlog/user-stories/US-019-stoic-journal.md) - Conversation flow pattern

**Technical References**:
- File: `src/handlers/stoic.py` - Conversation state pattern
- File: `src/recipe_image.py` - Gemini image generation pattern
- File: `src/handlers/dream.py` (new) - Dream session handlers

**Story Points**: 8

**Priority**: 🟡 Medium

**Status**: ✅ Complete

**Backlog Reference**: [US-025](../backlog/user-stories/US-025-jungian-dream-analysis.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create dream handler with /dream, /dream_done, /dream_cancel | `handlers/dream.py` | US-025 Commands | ✅ | 1.5 | — |
| T-002 | Add DREAM_ANALYST persona state and routing | `core.py`, `state_manager.py` | US-025 State | ✅ | 1.5 | — |
| T-003 | Implement dream description and Jungian analysis prompts | `prompts/` | US-025 Analysis | ✅ | 2 | — |
| T-004 | Add dream image generation via Gemini | `handlers/dream.py` | US-025 Image Gen | ✅ | 2 | — |
| T-005 | Save dream note to Joplin (Dream Journal folder) | `handlers/dream.py` | US-025 Output | ✅ | 1 | — |

**Total Task Points**: 8

---

### Story 4: Habit Check-ins and Tracking - 5 Points

**User Story**: As a user building better habits, I want to quickly log my daily habits in Telegram, so that I can track consistency without needing a separate habit app.

**Acceptance Criteria**:
- [ ] `/habits add <habit>` adds a new habit to track
- [ ] `/habits` shows today's habits with quick check-in buttons
- [ ] Inline buttons for Yes/No each habit
- [ ] Current streak displayed for each habit
- [ ] `/habits stats` shows weekly/monthly completion rates
- [ ] `/habits remove <habit>` removes a habit
- [ ] `/habits list` shows all defined habits with streaks
- [ ] Habits reset daily at user's configured timezone midnight

**Reference Documents**:
- [US-032: Habit Check-ins and Tracking](../backlog/user-stories/US-032-habit-tracking.md)

**Technical References**:
- File: `src/habit_service.py` (new) - SQLite CRUD, streak calculation
- File: `src/handlers/habits.py` (new) - Commands and callback handler
- Database: `STATE_DB_PATH` - habits, habit_entries tables

**Story Points**: 5

**Priority**: 🟢 Low

**Status**: ✅ Complete

**Backlog Reference**: [US-032](../backlog/user-stories/US-032-habit-tracking.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create habit_service with SQLite schema | `habit_service.py` | US-032 Data Model | ✅ | 1.5 | — |
| T-002 | Implement streak calculation | `HabitService.calculate_streak()` | US-032 Streaks | ✅ | 1 | — |
| T-003 | Create habits handler with /habits, add, remove, list, stats | `handlers/habits.py` | US-032 Commands | ✅ | 1.5 | — |
| T-004 | Add inline keyboard and callback handler | `handlers/habits.py` | US-032 Buttons | ✅ | 1 | — |

**Total Task Points**: 5

---

## Sprint Summary

**Total Story Points**: 31 (includes US-027 from Sprint 12)
**Total Task Points**: 23
**Status**: ✅ Complete

**Sprint Burndown Plan**:
- Week 1: Stories 1-2 (Photo OCR, Read Later) - 10 points
- Week 2: Stories 3-4 (Dream Analysis, Habit Tracking) - 13 points
- US-027 (Weekly Planning) implemented in Sprint 11 scope

**Sprint Review Notes**:
- All 5 features delivered: US-025, US-027, US-028, US-030, US-032

**Sprint Retrospective Notes**:
- **What went well?**
  - [To be filled]
- **What could be improved?**
  - [To be filled]
- **Action items for next sprint**
  - [To be filled]

---

**Last Updated**: 2026-03-05 (Sprint complete - status synced with code)
