# Sprint 12: Advanced Intelligence

**Sprint Goal**: Add semantic search/Q&A over notes and guided weekly planning session.

**Duration**: 2026-04-07 - 2026-04-20 (2 weeks)
**Team Velocity**: 21 points (target)
**Sprint Planning Date**: 2026-03-05
**Sprint Review Date**: 2026-04-20
**Sprint Retrospective Date**: 2026-04-20

## Sprint Overview

**Focus Areas**:
- Semantic search with vector embeddings (Gemini)
- Q&A synthesis over note context
- Guided weekly planning (GTD complement to braindump)

**Key Deliverables**:
- `/ask <question>` semantic Q&A with source citations
- `/reindex` for note index rebuild
- `/plan` guided weekly planning session
- Note index with Gemini embeddings and SQLite storage

**Dependencies**:
- Sprint 10 (Quick Search - extends search.py)
- Sprint 10 (Greeting - command list update)
- Joplin REST API (Complete - FR-005)
- Google Tasks (Complete - FR-012)
- Gemini API (Complete - for embeddings)
- Braindump pattern (Complete - FR-017) for planning flow

**Risks & Blockers**:
- First-time indexing may be slow for large note collections (mitigated by progress indicator)
- Embedding API rate limits (Gemini free tier - mitigated by batching)

---

## User Stories

### Story 1: Semantic Search and Q&A Over Notes - 13 Points

**User Story**: As a user with hundreds of notes in Joplin, I want to ask questions in natural language and get answers from my notes, so that I can quickly retrieve knowledge without manually searching and reading.

**Acceptance Criteria**:
- [ ] `/ask <question>` searches notes and returns AI-synthesized answer
- [ ] Search uses semantic similarity (not just keyword matching)
- [ ] Answer includes source note references (titles)
- [ ] Works across all Joplin folders (respects PARA structure)
- [ ] Handles "I don't know" gracefully when no relevant notes found
- [ ] Response time < 10 seconds for typical queries
- [ ] Results limited to user's own notes (security)
- [ ] `/reindex` rebuilds the note index

**Reference Documents**:
- [FR-026: Semantic Search and Q&A](../backlog/features/FR-026-semantic-search-qa.md)
- [API Reference: Gemini Embeddings](../../docs/api-reference.md)

**Technical References**:
- File: `src/note_index.py` (new) - Vector embeddings, SQLite storage
- File: `src/qa_service.py` (new) - Q&A orchestration
- File: `src/handlers/search.py` - Extend with `/ask`, `/reindex`
- Gemini: `text-embedding-004` for embeddings

**Story Points**: 13

**Priority**: 🟠 High

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-026](../backlog/features/FR-026-semantic-search-qa.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create NoteIndex with SQLite embedding storage | `note_index.py:NoteIndex` | FR-026 Indexing | ⭕ | 3 | — |
| T-002 | Implement chunking and Gemini embedding | `NoteIndex.index_note()` | FR-026 Embeddings | ⭕ | 2 | — |
| T-003 | Implement cosine similarity search | `NoteIndex.search()` | FR-026 Vector Search | ⭕ | 2 | — |
| T-004 | Create reindex_all() from Joplin notes | `NoteIndex.reindex_all()` | FR-026 Reindex | ⭕ | 1.5 | — |
| T-005 | Create QAService with context + DeepSeek synthesis | `qa_service.py` | FR-026 Q&A | ⭕ | 2 | — |
| T-006 | Add /ask and /reindex to search handler | `handlers/search.py` | FR-026 Commands | ⭕ | 2 | — |
| T-007 | Add basic unit tests | `tests/test_semantic_search.py` | FR-026 Testing | ⭕ | 0.5 | — |

**Total Task Points**: 13

---

### Story 2: Weekly Planning Session - 8 Points

**User Story**: As a productivity-focused user, I want a guided weekly planning session, so that I can start each week with clear priorities and intentions rather than reactive chaos.

**Acceptance Criteria**:
- [ ] `/plan` starts a guided planning session
- [ ] Bot asks structured questions about the week ahead
- [ ] User can review incomplete tasks from Google Tasks
- [ ] User sets 3-5 priorities for the week
- [ ] User identifies potential obstacles and mitigation strategies
- [ ] Session generates structured planning note in Joplin
- [ ] Tasks created for each priority in Google Tasks
- [ ] `/plan_done` ends session early with summary
- [ ] `/plan_cancel` exits without saving
- [ ] Session timeout after 30 minutes of inactivity

**Reference Documents**:
- [FR-027: Weekly Planning Session](../backlog/features/FR-027-weekly-planning-session.md)
- [FR-017: GTD Expert](../backlog/features/FR-017-gtd-expert-persona.md) - Braindump flow pattern

**Technical References**:
- File: `src/handlers/braindump.py` - Conversation flow pattern
- File: `src/handlers/planning.py` (new) - Planning session
- File: `src/task_service.py` - Google Tasks for priority tasks
- File: `src/joplin_client.py` - Planning note creation

**Story Points**: 8

**Priority**: 🟡 Medium

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-027](../backlog/features/FR-027-weekly-planning-session.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create planning handler with /plan, /plan_done, /plan_cancel | `handlers/planning.py` | FR-027 Commands | ⭕ | 1.5 | — |
| T-002 | Add PLANNING_COACH persona state and routing | `core.py`, `state_manager.py` | FR-027 State | ⭕ | 1 | — |
| T-003 | Create planning coach prompt and phase flow | `prompts/planning_coach.txt` | FR-027 Flow | ⭕ | 2 | — |
| T-004 | Implement review phase (fetch tasks + notes) | `handlers/planning.py` | FR-027 Review | ⭕ | 1.5 | — |
| T-005 | Generate planning note and create priority tasks | `handlers/planning.py` | FR-027 Output | ⭕ | 2 | — |

**Total Task Points**: 8

---

## Sprint Summary

**Total Story Points**: 21
**Total Task Points**: 21
**Estimated Velocity**: 21 points (based on story points)

**Sprint Burndown Plan**:
- Week 1: Story 1 (Semantic Search/Q&A) - 13 points
- Week 2: Story 2 (Weekly Planning) - 8 points

**Sprint Review Notes**:
- [To be filled at sprint review]

**Sprint Retrospective Notes**:
- **What went well?**
  - [To be filled]
- **What could be improved?**
  - [To be filled]
- **Action items for next sprint**
  - [To be filled]

---

**Last Updated**: 2026-03-05
