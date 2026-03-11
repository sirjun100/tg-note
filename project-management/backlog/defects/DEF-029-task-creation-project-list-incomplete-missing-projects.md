# Defect: DEF-029 - Task Creation Project List Incomplete — Missing Projects

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 3
**Created**: 2026-03-09
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19

---

## Problem Statement

When creating a task (e.g. via `/task <item>` or braindump flow with project sync enabled), the user is prompted to select a project from a list. The list is hard-limited to 10 projects (8 in inline buttons). Users with more projects cannot select projects beyond the limit — they are not shown and cannot be chosen.

**User impact:** Users with many Joplin project folders cannot assign tasks to projects that fall outside the truncated list. Workaround: create task as top-level, then move manually — poor UX.

---

## Root Cause

In `src/handlers/core.py` (lines ~1120–1133):

- `projects[:10]` — numbered list shows first 10 only
- `projects[:8]` — inline buttons show first 8 only
- State stores `projects[:10]` — selection only works for first 10

No pagination or "show more" exists. Same pattern may apply in braindump flow when `get_project_folder_for_sync` returns project options.

---

## Steps to Reproduce

1. Have 15+ Joplin project folders under the configured Projects root
2. Enable project sync: `/tasks_toggle_project_sync` on
3. Run `/task Call client` (or complete braindump that triggers project selection)
4. Observe project list — only first 8–10 projects shown
5. Projects 11+ are not visible and cannot be selected

---

## Expected Behavior (Industry Standard)

**Option A — Pagination (recommended):**
- Show first page (e.g. 8–10 items per page)
- Add "Next" / "Previous" or "Show more" buttons
- Telegram inline keyboards support callback_data; use `project_sel_page_1`, `project_sel_page_2`, etc.
- Common pattern: 8–15 items per page, with page nav

**Option B — Full list:**
- If project count is small (e.g. ≤20), show all with scrollable message
- Telegram message limit ~4096 chars; 20 projects × ~40 chars ≈ 800 — feasible

**Option C — Search/filter:**
- For very large lists (50+), add search: "Type project name to filter"
- Defer if scope is large

---

## Actual Behavior

List truncated to 10 (display) / 8 (buttons). No pagination, no "show more", no search. Projects beyond the limit are invisible.

---

## Affected Code

| File | Location | Change |
|------|----------|--------|
| `src/handlers/core.py` | ~1118–1137 | Project selection for `/task` — add paging or full list |
| `src/handlers/braindump.py` | `get_project_folder_for_sync` usage | Same project list; verify if truncated |
| `src/reorg_orchestrator.py` | `get_project_folders` | May need to support pagination params |

---

## Implementation Notes

- **Telegram constraint:** Inline keyboards have row/button limits; 8 buttons per page is reasonable
- **State:** Store `projects` full list + `page` index; callback `project_sel_page_N` or `project_sel_more`
- **Industry reference:** Slack, Discord, GitHub use paginated selectors; 10–15 items per page common

---

## References

- [US-034: Joplin ↔ Google Tasks Project Sync](../user-stories/US-034-joplin-google-tasks-project-sync.md)
- [FR-034](https://github.com/martinfou/telegram-joplin/blob/main/project-management/backlog/features/) — project sync feature

## History

- 2026-03-09 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
