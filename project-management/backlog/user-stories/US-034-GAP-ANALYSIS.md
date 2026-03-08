# US-034 Gap Analysis: Acceptance Criteria vs Implementation

**Date**: 2026-03-06  
**Branch**: feat/US-034-joplin-google-tasks-project-sync  
**Updated**: 2026-03-06 — Implemented gaps 1–4, 6

## Summary

| Category | Implemented | Partial | Not Done |
|----------|-------------|---------|----------|
| Task Creation UX | 3 | 1 | 0 |
| Core Sync | 5 | 1 | 0 |
| Sync Direction & Triggers | 4 | 0 | 0 |
| Configuration | 3 | 0 | 0 |
| Edge Cases | 2 | 0 | 0 |

---

## Task Creation UX

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Ask "Is this task for a project?" when context missing | ✅ Done | `/task <text>` with project_sync_enabled prompts user. |
| 2 | Show numbered list / inline keyboard of projects | ✅ Done | Inline keyboard + numbered list for selection. |
| 3 | User replies with number → create as subtask | ✅ Done | Text reply or button click creates subtask under project. |
| 4 | User replies "no" or skips → top-level task | ✅ Done | "No (top-level)" button or text "no"/"skip" creates top-level. |

---

## Core Sync

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Each folder under Projects → one parent task in Google Tasks | ✅ Partial | Parent created on-demand (lazy), not proactively for all folders. |
| 2 | Note in project folder + action item → subtask under project parent | ✅ Done | Routing "both" and braindump. |
| 3 | Note in Inbox/non-project → top-level task | ✅ Done | When not under Projects, no parent. |
| 4 | Project parent tasks created on-demand (lazy) | ✅ Done | `get_or_create_project_parent_task`. |
| 5 | Mapping stored: joplin_folder_id ↔ google_task_id | ✅ Done | `joplin_project_sync` table. |
| 6 | Preserve task_link (joplin_note_id ↔ google_task_id) | ✅ Done | create_tasks_from_decision + routing "both" now create task_link. |

---

## Sync Direction & Triggers

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Joplin → Google Tasks (primary) | ✅ Done | Subtasks from project notes. |
| 2 | Initial sync: create parent tasks for all projects | ✅ Done | `/sync_projects` command. |
| 3 | Rename: /sync_projects + detect stale on task creation | ✅ Done | Rename detection in get_or_create_project_parent_task. |
| 4 | Delete: remove parent task when folder deleted | ✅ Done | Option A: daily cleanup 03:00 UTC. Option C: cleanup in `/sync_projects`. |
| 5 | New project: create parent on first task | ✅ Done | Lazy creation. |

---

## Configuration

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Enable/disable project sync (opt-in) | ✅ Done | `/toggle_project_sync`. |
| 2 | Choose which Joplin folder maps to "projects" | ✅ Done | Option D: `/set_projects_folder` override; default = name-based. |
| 3 | One task list for all projects | ✅ Done | Same task_list_id. |
| 4 | Fallback: Inbox/non-project → top-level in same list | ✅ Done | |

---

## Edge Cases

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Stalled projects in daily/weekly/monthly reports | ✅ Done | "⚠️ Projects with no next actions" in all reports. |
| 2 | Project folder deleted → handle mapping | ✅ Done | Option A: daily cleanup. Option C: cleanup in `/sync_projects`. |
| 3 | Task completed → sync back to Joplin (future) | — | Out of scope. |
| 4 | Duplicate project names → disambiguate | ✅ N/A | We use folder_id; different folders have different IDs. |

---

## Recommended Next Steps (Priority Order)

1. ~~**Stalled project detection**~~ — ✅ Done. Added to daily, weekly, monthly reports.
2. ~~**"Is this for a project?" flow**~~ — ✅ Done. Inline keyboard + text reply for `/task`.
3. ~~**`/sync_projects`**~~ — ✅ Done. Creates parent tasks for all project folders.
4. ~~**Rename detection**~~ — ✅ Done. In get_or_create_project_parent_task.
5. ~~**Configurable Projects parent**~~ — ✅ Done. `/set_projects_folder` (Option D).
6. ~~**Delete handling**~~ — ✅ Done. Option A (daily 03:00 UTC) + Option C (in `/sync_projects`).
