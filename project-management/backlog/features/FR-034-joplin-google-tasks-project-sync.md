# Feature Request: FR-034 - Joplin Projects ↔ Google Tasks Sync (Project = Task, Tasks = Subtasks)

**Status**: ⭕ Not Started
**Priority**: 🟠 High
**Story Points**: 13
**Created**: 2026-03-05
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog (Sprint 13+ candidate)

## Description

Keep Joplin projects (folders under Projects) and Google Tasks in sync. Each Joplin project folder becomes a parent task in Google Tasks with the same name. When the user adds a task for a project (via note or action item), it is created as a **subtask** under that project's task. This mirrors the project structure in both systems and keeps actionable items organized by project.

**Scope:** Tasks are created **only in Google Tasks**, never in Joplin. Joplin stores notes; action items extracted from notes become Google Tasks. This feature does not change that — it only affects *where* and *how* those tasks are organized in Google Tasks (by project/subtask).

## User Story

As a user with multiple Joplin projects (e.g. Projects/Work, Projects/Home Reno),
I want each project to have a corresponding task in Google Tasks with the same name,
and when I add tasks for a project they appear as subtasks under that project,
so that my Joplin projects and Google Tasks stay aligned and I can see all project tasks in one place.

## Current Behavior

- All tasks go to a single configured Google Task list.
- No link between Joplin folder/project and Google Tasks structure.
- Project context is lost when tasks are created.

## Proposed Behavior

| Joplin | Google Tasks |
|--------|--------------|
| Projects/Work | Parent task "Work" |
| Projects/Home Reno | Parent task "Home Reno" |
| Note in Projects/Work with action "Call client" | Subtask "Call client" under "Work" |
| Note in Projects/Home Reno with action "Buy paint" | Subtask "Buy paint" under "Home Reno" |

## Acceptance Criteria

### Task Creation UX

- [ ] When creating a Google Task, ask the user: **"Is this task for a project?"** (skip if task comes from note already in a project folder — auto-assign)
- [ ] If yes → show numbered list of Joplin projects (folders under Projects); prefer **inline/reply keyboard** for faster selection
  ```
  1. Work
  2. Home Reno
  3. Volunteer
  Reply with the number, or "no" to create as top-level task.
  ```
- [ ] User replies with number → create Google Task as subtask under that project's parent
- [ ] User replies "no" or skips → create Google Task as top-level task

### Core Sync

- [ ] Each folder under **Projects** (or configurable parent) in Joplin → one parent task in Google Tasks with the same name
- [ ] Note in project folder + action item extracted → create **Google Task** as subtask under that project's parent (Joplin has no tasks; only notes)
- [ ] Note in Inbox or non-project folder + action item extracted → create **Google Task** as top-level task in Google Tasks
- [ ] Project parent tasks are created on-demand when first task for that project is added (lazy creation)
- [ ] Mapping stored: `joplin_folder_id` ↔ `google_task_id` (parent task) for sync
- [ ] When subtask created from note → preserve `task_link` (joplin_note_id ↔ google_task_id) so user can jump from task to note context

### Sync Direction & Triggers

- [ ] **Joplin → Google Tasks** (primary): New project folder → create parent task in Google Tasks; action item extracted from note in project → create subtask in Google Tasks (never create tasks in Joplin)
- [ ] **Initial sync**: Command or config to create parent tasks for all existing Joplin projects
- [ ] **Rename**: Hybrid — `/sync_projects` for manual sync; on next task creation, detect stale folder title and update Google Task
- [ ] **Delete**: When Joplin project folder deleted → delete parent task in Google Tasks (subtasks become top-level); remove mapping
- [ ] **New project**: When user creates a new Joplin project folder → create parent task in Google Tasks (or on first task creation)

### Configuration

- [ ] User can enable/disable project sync (opt-in)
- [ ] User can choose which Joplin parent folder maps to "projects" (default: folder named "Projects" or "Project")
- [ ] **One task list for all projects** — all parent tasks and subtasks live in a single Google Task list (e.g. "Joplin Projects" or user's default)
- [ ] Fallback: If note has no project folder (e.g. Inbox), tasks go to that same task list as top-level tasks

### Edge Cases

- [ ] **Stalled projects** (parent tasks with zero subtasks) flagged in **all reports**: daily, weekly, monthly. E.g. "⚠️ Projects with no next actions: Work, Home Reno"
- [ ] Project folder deleted in Joplin → see Rename/Delete Sync below
- [ ] Task completed in Google Tasks → optionally sync back to Joplin note (future enhancement)
- [ ] Duplicate project names → disambiguate with folder path or ID

## Technical Requirements

### Google Tasks API

- Use `parent` query parameter when inserting subtasks: `POST .../tasks?parent={parentTaskId}`
- Parent tasks are regular tasks with no parent; subtasks have `parent` set
- [Google Tasks API: tasks.insert](https://developers.google.com/tasks/reference/rest/v1/tasks/insert)

### Data Model

- New table or config: `joplin_project_sync` — `(user_id, joplin_folder_id, joplin_folder_title, google_task_id, google_task_list_id)`
- Extend `create_tasks_from_decision` to accept `parent_folder_id` and resolve to `google_parent_task_id`

### Flow

1. User creates note in Projects/Work with action "Call client"
2. LLM returns `parent_id` = folder ID of "Work"
3. Task service: lookup `joplin_project_sync` for (user_id, folder_id)
4. If no mapping: create parent task "Work", store mapping
5. Create subtask "Call client" with `parent=Work_task_id`

### Dependencies

- FR-012 (Google Tasks Integration) ✅
- Joplin folder structure (PARA or custom)
- `get_folders`, `get_all_notes` for project discovery

## Business Value

- **Unified view**: Projects in Joplin and tasks in Google Tasks stay aligned
- **Reduced cognitive load**: No manual mapping; structure follows naturally
- **GTD alignment**: Projects as containers for next actions (subtasks)
- **Differentiation**: Most task apps don't sync with note-taking structure

---

## Philosophy Alignment (from docs)

Based on [GTD + Second Brain workflow](../../../docs/for-users/gtd-second-brain-workflow.md), [PARA](../../../docs/para-where-to-put.md), and [README](../../../README.md):

| Principle | How FR-034 supports it |
|-----------|------------------------|
| **Tasks only in Google Tasks** | Joplin = notes; action items → Google Tasks. No tasks in Joplin. |
| **Project = cockpit (Joplin) + engine (Tasks)** | Joplin project folder = knowledge; Google parent task + subtasks = next actions. Same structure in both. |
| **Every active project has ≥1 next action** | Parent tasks with no subtasks = stalled projects. Flag in daily, weekly, and monthly reports. |
| **Areas ≠ Projects** | Tasks from Areas (Health, Finance) stay top-level — no parent. Aligns with "Areas don't get project-style task lists." |
| **Archive, don't delete** | When Joplin project moves to Archive → complete (not delete) the parent task in Google Tasks? Preserves history. |
| **Low friction / capture first** | See suggestions below. |

---

## Suggested Improvements (from philosophy review)

### 1. Reduce friction when we have context

**Current:** Always ask "Is this for a project?" + numbered list.

**Suggestion:** When task comes from a **note already in a project folder** → auto-assign to that project, no prompt. Only ask when context is missing (e.g. `/task Call client` with no note). Aligns with "capture first, don't decide."

### 2. Inline keyboard instead of typing numbers

**Suggestion:** Show projects as **reply keyboard buttons** or **inline buttons** (e.g. `[Work] [Home Reno] [Skip]`) instead of "Reply with 1, 2, or 3." Faster than typing a number.

### 3. Archive → complete, not delete

**Current:** Delete parent task when Joplin project folder deleted.

**Suggestion:** When Joplin project is **moved to Archive** (not deleted) → **complete** the parent task in Google Tasks instead of deleting. Subtasks become top-level; parent stays as historical record. Aligns with "Archive, don't delete."

### 4. Stalled project detection ✅ (accepted)

**Decision:** Parent task with **zero subtasks** = stalled project (Golden Rule: "Every active project should have at least one task"). Flag in **all reports**:
- **Daily report** — section or line: "⚠️ Projects with no next actions: Work, Home Reno"
- **Weekly report** — in recommendations or "BY THE NUMBERS": stalled projects list
- **Monthly report** — in insights or summary: stalled projects for the month

### 5. Link task → note context

**Suggestion:** When creating subtask from a note, preserve `task_link` (joplin_note_id ↔ google_task_id) so user can jump from task to note. "Tasks point you to action, notes give you the context to act."

### 6. Deferred project assignment

**Suggestion:** Allow "create task first, assign project later" — e.g. `/move_task 3 Work` to move task #3 under project "Work". For users who want to capture fast and organize later.

---

## Decisions (2026-03-05)

| Question | Decision |
|----------|----------|
| Task list strategy | **One task list** for all projects |
| Areas vs. Projects | **Projects only** — Areas (Work, Health, etc.) do not get parent tasks |

## Rename/Delete Sync — Suggestions

**Rename (Joplin project folder renamed):**

| Option | Pros | Cons |
|--------|------|------|
| **A. On-demand command** `/sync_projects` | Simple, no background jobs; user controls when | User must remember to run it |
| **B. On next task creation** | Automatic; no extra command | Rename not reflected until next task for that project |
| **C. Periodic sync** (e.g. daily) | Eventually consistent | Adds complexity; may miss renames if Joplin API doesn't expose rename events |
| **D. Hybrid: A + B** | Best of both: `/sync_projects` for immediate sync; fallback: detect stale title on next task creation and update | Slightly more logic |

**Recommendation:** **D (Hybrid)** — `/sync_projects` for manual sync; when creating a subtask, compare stored `joplin_folder_title` with current folder title and update Google Task if changed.

---

**Delete (Joplin project folder deleted):**

| Option | Pros | Cons |
|--------|------|------|
| **A. Move subtasks to top-level** | No data loss; tasks remain visible | Loses project grouping |
| **B. Move to "Uncategorized" parent** | Keeps structure; easy to find orphans | Need to create/maintain "Uncategorized" parent |
| **C. Leave as-is** | Simplest | Orphaned subtasks under deleted parent (Google may hide completed parents) |
| **D. Delete parent task only** | Clean | Subtasks become top-level in Google Tasks automatically |

**Recommendation:** **D** — When Joplin project is deleted, delete the parent task in Google Tasks. Google Tasks API: deleting a parent moves its subtasks to top-level. Remove mapping from `joplin_project_sync`. Optionally notify user: "Project X deleted in Joplin; 3 tasks moved to top-level."

**Note:** When project is **moved to Archive** (not deleted), consider **completing** the parent task instead of deleting — aligns with "Archive, don't delete." Requires detecting Archive move (folder parent_id change).

## References

- [FR-012: Google Tasks Integration](FR-012-google-tasks-integration.md)
- [FR-016: Joplin Reorganization (PARA)](FR-016-joplin-database-reorganization.md)
- [Google Tasks API - tasks.insert](https://developers.google.com/tasks/reference/rest/v1/tasks/insert)
