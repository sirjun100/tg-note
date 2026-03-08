# Defect: DEF-018 - Weekly Report Shows Incorrect Numbers (0 Notes/Tasks Despite Activity)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-05
**Updated**: 2026-03-06

## Resolution (2026-03-06)

- **Tasks completed:** Added `show_completed` param to `task_service.get_user_tasks()`; weekly and monthly reports now pass `show_completed=True`. Filter completed tasks by completion date (only count those completed within the report window).
- **Notes created/modified:** `get_all_notes()` now requests explicit fields `created_time, updated_time, user_created_time, user_updated_time`. Normalized timestamp handling (int conversion, `created_ts < start_ts` for modified to avoid double-counting).
**Assigned Sprint**: Backlog

## Description

The weekly report shows zeros for notes created, notes modified, and tasks completed, even when the user has created many notes and tasks during the week. The productivity score and velocity are therefore wrong.

## Steps to Reproduce

1. Create notes and tasks via the bot during the current week.
2. Run `/weekly_report` or wait for the scheduled weekly report.
3. Observe: Notes created: 0, Notes modified: 0, Tasks completed: 0, Velocity: 0.

## Expected Behavior

- Notes created: count of Joplin notes created in the report week.
- Notes modified: count of Joplin notes updated in the report week.
- Tasks completed: count of Google Tasks completed in the report week.
- Velocity and productivity score reflect actual activity.

## Actual Behavior (User Report)

```
WEEKLY REVIEW — Mar 02 – Mar 08, 2026

✅ PRODUCTIVITY SCORE: 0% [D] (➡️ same as last week)

📈 BY THE NUMBERS
  Notes created: 0
  Notes modified: 0
  Tasks completed: 0
  Tasks pending: 83
  ⚠️ Tasks overdue: 22
  Velocity: 0 items
  vs last week: ➡️ 0 items
  Messages sent: 90
```

User reports having created "lots of notes and tasks this week" — the numbers make no sense.

## Root Cause (Code Review 2026-03-06)

- **Tasks completed = 0:** `task_service.get_user_tasks()` calls `get_tasks(task_list_id)` without `show_completed=True`. Google Tasks API returns only incomplete tasks by default, so completed tasks are never counted.
- **Notes created/modified:** `get_all_notes()` may not request `created_time`/`updated_time`; `monthly_report_generator` explicitly requests these fields. Verify `weekly_report_generator` gets full note data.

## Possible Causes (Other)

1. **Joplin timestamp format** — `created_time` / `updated_time` may be returned in a different format (e.g. string vs ms) or under different keys (`user_created_time`, `user_updated_time`).
2. **Timezone mismatch** — Week bounds are computed in user timezone; Joplin timestamps are UTC. Conversion or comparison may be wrong.
3. **Tasks completed not filtered by date** — `_collect_google_tasks_metrics` includes all completed tasks, not only those completed within the week. If the logic is inverted or misused, counts could be wrong.
4. **`get_all_notes`** — Pagination or field selection might omit timestamps or return incomplete data.
5. **Week bounds** — `_week_bounds` may compute Mon–Sun incorrectly for the user's timezone.

## Affected Code

- `src/weekly_report_generator.py` — `_collect_joplin_metrics`, `_collect_google_tasks_metrics`, `_week_bounds`, `_build_metrics`
- `src/joplin_client.py` — `get_all_notes` (fields returned)

## References

- [US-015: Weekly Review Report](../user-stories/US-015-weekly-review-report.md)
- [DEF-005: Stoic Timezone](DEF-005-stoic-journal-timezone-and-data-loss.md) — similar timezone/data mismatch
