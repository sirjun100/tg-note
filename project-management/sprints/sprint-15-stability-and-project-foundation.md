# Sprint 15: Stability & Project Foundation

**Sprint Goal**: Fix production bugs (/find, /ask) and add project creation command (/project_new), establishing a stable base and project workflow before project sync (FR-034).

**Duration**: 2026-05-19 - 2026-06-01 (2 weeks, after Sprint 14)
**Status**: ✅ Completed
**Team Velocity**: 12 points (BF-022 + BF-023 + FR-044 + FR-039)
**Sprint Planning Date**: 2026-03-06
**Sprint Review Date**: 2026-06-01
**Sprint Retrospective Date**: 2026-06-01

---

## ⚡ Implementation Guide (LLM-Ready)

**Before coding, read**: [sprint-15-implementation-guide.md](sprint-15-implementation-guide.md)

That document contains:
- Exact file paths, line numbers, and code snippets for each story
- Copy-paste patterns from existing fixes (BF-010, BF-022, BF-019)
- API signatures for `JoplinClient`, `ReorgOrchestrator`
- Test scenarios and Definition of Done

---

## Sprint Overview

**Bug Fixes** (4 pts):
- BF-022: /find command — Fly.io errors, Markdown parse; fix with get_folders try/except, HTML escape
- BF-023: /ask command — crashes on certain prompts; fix with HTML escape, plain-text fallback

**Features** (8 pts):
- FR-044: /project_new — create project with default PARA folders
- FR-039: Star on task — treat ⭐/* as high priority in reports

**Focus Areas**:
- Production stability: /find and /ask commands working reliably
- Project creation: One-command project setup with default PARA folders
- Task priority: Star prefix recognized across reports and displays

**Key Deliverables**:
- BF-022: /find returns search results without Fly.io errors
- BF-023: /ask returns AI answers without crashing on Markdown-special characters
- FR-044: `/project_new <name>` creates project with Overview, Backlog, Execution, Decisions, Assets, References
- FR-039: Tasks with ⭐/* at start ranked as high priority in reports

**Dependencies**:
- FR-005 (Joplin REST API) ✅
- FR-026 (Semantic Search) ✅ for /ask
- FR-029 (Quick Note Search) ✅ for /find
- ReorgOrchestrator (FR-016) ✅ for FR-044

**Risks & Blockers**:
- BF-022, BF-023: Same Markdown parse pattern as BF-010, BF-014 — HTML mode + escape + plain-text fallback

---

## Pre-Sprint Checklist

- [ ] **Documentation-Code Consistency Review** run (`./scripts/doc-code-review.sh`) — see [Definition of Done](../docs/definition-of-done.md)
- [ ] Report reviewed: `project-management/reports/doc-code-consistency-latest.md`; high-priority contradictions resolved
- [ ] Sprint 14 completed or in progress
- [ ] All backlog items (BF-022, BF-023, FR-044, FR-039) refined and ready for development

---

## User Stories

### Story 1: /find Command Fix - 2 Points

**Implementation Note**: The fix may already exist in `src/handlers/search.py` (BF-022 comments, `_send_search_results_safe`, `html.escape`). **Verify** in production and add unit tests. See [sprint-15-implementation-guide.md § BF-022](sprint-15-implementation-guide.md#1-bf-022-find-command-fix--verify-implementation-may-exist).

**User Story**: As a user, I want /find to return search results without errors, so that I can quickly find notes in production.

**Acceptance Criteria**:
- [ ] `get_folders()` wrapped in try/except; on failure, use empty folder map
- [ ] Search results sent with `parse_mode="HTML"` and `html.escape()` for user content
- [ ] Plain-text fallback on send error
- [ ] `/find test` returns results in production (Fly.io)

**Reference**: [BF-022](../backlog/bugs/BF-022-find-command-flyio-error.md)

**Technical References**:
- `src/handlers/search.py` — `_find()` (lines 84–164), `get_folders()` (118–124), `_send_search_results_safe` (53–76)
- Copy pattern from: `src/handlers/core.py` `_send_greeting_safe` (BF-010)

**Priority**: 🟠 High  
**Status**: ⏳ In Progress (implementation may already exist)  
**Story Points**: 2

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Wrap get_folders() in try/except; use empty folder map on failure | `handlers/search.py:_find` | BF-022 | ⭕ | 0.5 | — |
| T-002 | Switch to parse_mode="HTML" with html.escape() for titles, snippets, folder names | `handlers/search.py` | BF-022 | ⭕ | 1 | — |
| T-003 | Add plain-text fallback on send error; verify in production | `handlers/search.py` | BF-022 | ⭕ | 0.5 | — |

**Total Task Points**: 2

---

### Story 2: /ask Command Fix - 2 Points

**Implementation Note**: `src/handlers/ask.py` lines 60–66 use `parse_mode="Markdown"` with unescaped LLM/Joplin content. **Fix**: Switch to HTML + `html.escape()`, add `_send_ask_response_safe` (like `_send_search_results_safe`), use `split_message_for_telegram` for >4096 chars. Full code in [sprint-15-implementation-guide.md § BF-023](sprint-15-implementation-guide.md#2-bf-023-ask-command-fix--implement).

**User Story**: As a user, I want /ask to return AI-synthesized answers without crashing, so that I can query my notes reliably.

**Acceptance Criteria**:
- [ ] Response built with `parse_mode="HTML"` and `html.escape()` for answer and source titles
- [ ] Plain-text fallback on send error (same pattern as BF-010, BF-022)
- [ ] Long responses split if > 4096 chars (BF-019 pattern)
- [ ] `/ask how did I learn how to cook` returns answer without crash

**Reference**: [BF-023](../backlog/bugs/BF-023-ask-command-crash.md)

**Technical References**:
- `src/handlers/ask.py` — `_ask()` lines 29–74; `ask_question` from `src/qa_service.py`
- Copy pattern: `src/handlers/search.py` `_send_search_results_safe`, `src/security_utils.py` `split_message_for_telegram`

**Priority**: 🟠 High  
**Story Points**: 2

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-004 | Switch to HTML mode with html.escape() for answer and source titles | `handlers/ask.py:_ask` | BF-023 | ⭕ | 1 | — |
| T-005 | Add plain-text fallback on send error; split long messages (>4096 chars) | `handlers/ask.py` | BF-023 | ⭕ | 0.5 | — |
| T-006 | Verify `/ask how did I learn how to cook` in production | — | BF-023 | ⭕ | 0.5 | — |

**Total Task Points**: 2

---

### Story 3: /project_new Command - 5 Points

**Implementation Note**: Add `create_project(project_name)` to `ReorgOrchestrator`; add `_project_new` handler in `reorg.py`; register `project_new` and `pn`. Use `get_or_create_folder_by_path(["Projects", normalized])` and `PROJECT_SUBFOLDERS`. Create Overview note via `create_note`. Full implementation in [sprint-15-implementation-guide.md § FR-044](sprint-15-implementation-guide.md#3-fr-044-project_new-command--implement).

**User Story**: As a user who starts new projects frequently, I want to run `/project_new name` and get a project folder with all default subfolders, so that I can start capturing notes immediately.

**Acceptance Criteria**:
- [ ] `/project_new <name>` and `/pn <name>` create project under Projects/
- [ ] Default subfolders: Overview, Backlog, Execution, Decisions, Assets, References
- [ ] Initial Overview note with template (project name, date, Goals, Key Decisions, Next Steps)
- [ ] Duplicate handling: show "Project X already exists" + list subfolders
- [ ] Name normalized to kebab-case

**Reference**: [FR-044](../backlog/features/FR-044-project-new-command.md)

**Technical References**:
- `src/reorg_orchestrator.py` — `PROJECT_SUBFOLDERS` (line 52), `initialize_structure` pattern; `joplin_client.get_or_create_folder_by_path`
- `src/joplin_client.py` — `get_or_create_folder_by_path(path_parts)` (223), `create_note(folder_id, title, body)` (132), `get_folders()`

**Priority**: 🟡 Medium  
**Story Points**: 5

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-007 | Add create_project_with_default_folders() or extend ReorgOrchestrator | `reorg_orchestrator.py` | FR-044 | ⭕ | 2 | — |
| T-008 | Register /project_new and /pn handlers; whitelist check | `handlers/reorg.py` or new handler | FR-044 | ⭕ | 1 | — |
| T-009 | Create initial Overview note with template; duplicate handling | `reorg_orchestrator.py`, handler | FR-044 | ⭕ | 1.5 | — |
| T-010 | Add to greeting/help; unit tests | `handlers/__init__.py`, tests | FR-044 | ⭕ | 0.5 | — |

**Total Task Points**: 5

---

### Story 4: Star on Task as High Priority - 3 Points

**Implementation Note**: Add `PriorityLevel.URGENT = 6`; add `_detect_star_priority(title)`; in `create_google_task_item` call it first — star wins over due date; update `_build_routing_system_prompt` in llm_orchestrator. Full code in [sprint-15-implementation-guide.md § FR-039](sprint-15-implementation-guide.md#4-fr-039-star-on-task-as-high-priority--implement).

**User Story**: As a user who stars important tasks, I want the bot to treat starred tasks as high priority in reports and displays, so that my most important items are prominently shown.

**Acceptance Criteria**:
- [ ] `*`/`⭐`/`★` at beginning of title → HIGH; `**` → CRITICAL; `***` → URGENT
- [ ] Starred tasks rank above non-starred in daily/weekly reports, /task, /find, /list
- [ ] `/task * Buy milk` preserves star in title
- [ ] Content routing recognizes star prefix
- [ ] Documentation in /help and /task usage

**Reference**: [FR-039](../backlog/features/FR-039-star-on-task-as-high-priority.md)

**Technical References**:
- `src/report_generator.py` — `PriorityLevel` (39), `create_google_task_item` (372), `_priority_label` (1007), `categorize_items` (429)
- `src/llm_orchestrator.py` — `_build_routing_system_prompt` (857)

**Priority**: 🟡 Medium  
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-011 | Add PriorityLevel.URGENT; create star-detection helper | `report_generator.py` | FR-039 | ⭕ | 0.5 | — |
| T-012 | Apply star priority in create_google_task_item(); star wins over due date | `report_generator.py` | FR-039 | ⭕ | 1 | — |
| T-013 | Preserve star in /task and content routing; update routing prompt | `handlers/core.py`, `llm_orchestrator.py` | FR-039 | ⭕ | 1 | — |
| T-014 | Apply to all task displays; add /help and /task docs | `report_generator.py`, handlers | FR-039 | ⭕ | 0.5 | — |

**Total Task Points**: 3

---

## Sprint Summary

**Total Story Points**: 12
**Total Task Points**: 12
**Estimated Velocity**: 12 points

**Sprint Burndown Plan** (bugs first):
- **Week 1**: Story 1 (BF-022) — verify/finish T-001–T-003; Story 2 (BF-023) — T-004–T-006; Story 3 start (T-007)
- **Week 2**: Story 3 (FR-044) — T-007–T-010; Story 4 (FR-039) — T-011–T-014

**Success Criteria** (Definition of Done):
- [ ] All 4 stories completed; acceptance criteria met
- [ ] Unit tests added/updated; no new linter errors
- [ ] Documentation updated (README, /help)
- [ ] [RELEASE_NOTES.md](../../RELEASE_NOTES.md) updated — see [release-notes-process.md](../docs/processes/release-notes-process.md)
- [ ] Doc-code consistency review run; no unresolved high-priority contradictions

**Sprint Review Notes**:
- [ ] [RELEASE_NOTES.md](../../RELEASE_NOTES.md) updated
- [To be filled at sprint review]

**Sprint Retrospective Notes**:
- **What went well?** [To be filled]
- **What could be improved?** [To be filled]
- **Action items for next sprint** [To be filled]

---

## Related Documents

- **[sprint-15-implementation-guide.md](sprint-15-implementation-guide.md)** — LLM-ready implementation reference (read first)
- [Sprint 15–18 Planning](../docs/sprint-15-18-planning.md) — Feature order and rationale
- [Definition of Done](../docs/definition-of-done.md) — Quality gate
- [Release Notes Process](../docs/processes/release-notes-process.md)
- [Product Backlog](../backlog/product-backlog.md)

---

**Last Updated**: 2026-03-06
