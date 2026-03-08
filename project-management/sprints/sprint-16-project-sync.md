# Sprint 16: Joplin ↔ Google Tasks Project Sync

**Sprint Goal**: Unify Joplin project structure with Google Tasks so each project folder maps to a parent task and action items from project notes become subtasks.

**Duration**: 2026-06-02 – 2026-06-15 (2 weeks)
**Status**: ⏳ Planned
**Team Velocity**: 13 points (target)
**Sprint Planning Date**: 2026-03-08
**Sprint Review Date**: 2026-06-15
**Sprint Retrospective Date**: 2026-06-15

---

## Sprint Overview

**Primary Feature** (13 pts):
- FR-034: Joplin Projects ↔ Google Tasks sync — project folder = parent task, notes → subtasks

**Focus Areas**:
- Project-to-task mapping: Joplin folder ↔ Google parent task
- Subtask creation: Action items from project notes → subtasks under parent
- Configuration: Opt-in, projects folder selection, task list
- Stalled projects: Flag in reports when project has no next actions

**Key Deliverables**:
- Project sync enabled via config; "Is this for a project?" flow when creating tasks
- Parent tasks created on-demand; subtasks linked to project
- `joplin_project_sync` mapping (folder_id ↔ google_task_id)
- Stalled projects in daily/weekly/monthly reports
- `/sync_projects` (or equivalent) for initial sync

**Dependencies**:
- FR-012 (Google Tasks) ✅
- FR-044 (/project_new) ✅ — project creation exists
- Joplin `get_folders`, folder structure

**Risks & Blockers**:
- Google Tasks API subtask handling; parent parameter
- Mapping persistence across restarts

---

## Pre-Sprint Checklist

- [ ] Documentation-Code Consistency Review run (`./scripts/doc-code-review.sh`)
- [ ] Sprint 15 completed ✅
- [ ] FR-034 acceptance criteria refined and understood

---

## User Stories

### Story 1: Project Sync Core — 8 Points

**User Story**: As a user with Joplin projects, I want each project folder to map to a parent task in Google Tasks, and action items from project notes to become subtasks, so that my structure stays aligned.

**Acceptance Criteria**:
- [ ] Folder under Projects → parent task in Google Tasks (same name)
- [ ] Note in project + action item → subtask under that project's parent
- [ ] Note in Inbox/non-project → top-level task
- [ ] Mapping stored: `joplin_folder_id` ↔ `google_task_id`
- [ ] Parent tasks created on-demand (lazy)
- [ ] `task_link` preserved (note_id ↔ task_id) for subtasks

**Reference**: [FR-034](../backlog/features/FR-034-joplin-google-tasks-project-sync.md)

**Technical References**:
- `src/task_service.py` — `create_task_with_metadata`, extend for `parent_folder_id`
- `src/logging_service.py` — new table/config for `joplin_project_sync`
- Google Tasks API: `tasks.insert` with `parent` parameter

**Priority**: 🟠 High  
**Story Points**: 8

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-001 | Add `joplin_project_sync` table/config; CRUD for folder↔task mapping | FR-034 | ⭕ | 2 |
| T-002 | Extend task creation to accept `parent_folder_id`; resolve to parent task | task_service.py | ⭕ | 2 |
| T-003 | Create parent task on-demand when first subtask for project | task_service.py | ⭕ | 2 |
| T-004 | Wire routing/note flow: pass folder_id when note is in project | handlers/core.py | ⭕ | 2 |

**Total Task Points**: 8

---

### Story 2: Project Selection UX — 3 Points

**User Story**: As a user creating a task, I want to be asked "Is this for a project?" and pick from my projects, so that I can assign tasks to the right project.

**Acceptance Criteria**:
- [ ] When creating task (without note context): "Is this for a project?" with numbered list
- [ ] User replies with number → create as subtask under that project
- [ ] User replies "no" → create as top-level task
- [ ] Skip prompt when task comes from note already in project folder
- [ ] Inline/reply keyboard for faster selection (optional)

**Reference**: [FR-034](../backlog/features/FR-034-joplin-google-tasks-project-sync.md)

**Technical References**:
- `src/handlers/core.py` — `_handle_new_request` force_task flow, project selection state
- `src/reorg_orchestrator.py` — `get_project_folders`

**Priority**: 🟠 High  
**Story Points**: 3

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-005 | Add "Is this for a project?" flow; state for project selection | handlers/core.py | ⭕ | 1.5 |
| T-006 | Fetch project list; show numbered list; parse reply | handlers/core.py | ⭕ | 1 |
| T-007 | Create subtask with parent when project selected | task_service.py | ⭕ | 0.5 |

**Total Task Points**: 3

---

### Story 3: Config, Sync, Stalled — 2 Points

**User Story**: As a user, I want to enable/disable project sync, run initial sync, and see stalled projects in reports, so that I control the feature and get visibility.

**Acceptance Criteria**:
- [ ] Config: enable/disable project sync; choose projects folder
- [ ] Command or flow for initial sync (create parent tasks for all projects)
- [ ] Stalled projects (no subtasks) flagged in daily/weekly/monthly reports

**Reference**: [FR-034](../backlog/features/FR-034-joplin-google-tasks-project-sync.md)

**Technical References**:
- `src/report_generator.py`, `weekly_report_generator.py`, `monthly_report_generator.py` — stalled projects
- `src/task_service.py` — `get_stalled_project_titles` (may exist)
- `src/handlers/google_tasks.py` — config, sync command

**Priority**: 🟡 Medium  
**Story Points**: 2

**Tasks**:

| Task ID | Task Description | Reference | Status | Points |
|---------|------------------|-----------|--------|--------|
| T-008 | Add project sync config (enabled, projects_folder_id) | logging_service, handlers | ⭕ | 0.5 |
| T-009 | Implement initial sync: create parent tasks for all projects | task_service, handlers | ⭕ | 0.5 |
| T-010 | Add stalled projects to reports (daily, weekly, monthly) | report_generator, etc. | ⭕ | 1 |

**Total Task Points**: 2

---

## Sprint Summary

**Total Story Points**: 13  
**Total Task Points**: 13  
**Estimated Velocity**: 13 points

**Sprint Burndown Plan**:
- **Week 1**: Story 1 (T-001–T-004) — core sync, mapping, parent/subtask creation
- **Week 2**: Story 2 (T-005–T-007) — project selection UX; Story 3 (T-008–T-010) — config, sync, stalled

**Scope Reduction** (if needed):
- Phase 1: Stories 1 + 2 only (11 pts) — core + UX
- Phase 2: Story 3 (2 pts) — config, sync, stalled (next sprint)

**Success Criteria** (Definition of Done):
- [ ] All 3 stories completed; acceptance criteria met
- [ ] Unit tests for mapping, task creation with parent
- [ ] No new linter errors
- [ ] RELEASE_NOTES.md updated
- [ ] Doc-code consistency review run

---

## Optional Stretch: FR-051 Bookmark (5 pts)

If capacity allows, add [FR-051](/bookmark command) — 5 pts. Well-defined, reuses URL enrichment. Would bring sprint to 18 pts (above velocity).

---

## Related Documents

- [Sprint 15–18 Planning](../docs/sprint-15-18-planning.md)
- [FR-034: Joplin ↔ Google Tasks Project Sync](../backlog/features/FR-034-joplin-google-tasks-project-sync.md)
- [Definition of Done](../docs/definition-of-done.md)
- [Product Backlog](../backlog/product-backlog.md)

---

**Last Updated**: 2026-03-08
