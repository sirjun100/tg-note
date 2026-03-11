# Defect: DEF-028 - Tasks Status Shows Times Not in User Timezone

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 2
**Created**: 2026-03-09
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 19

---

## Problem Statement

When users run `/tasks_status` (or `/google_tasks_status`), the timestamps displayed for sync history, failed syncs, or other time-based information are not converted to the user's configured timezone. Users see UTC or server time instead of their local time, making it harder to correlate events with their actual workflow.

**User impact:** Confusion when reviewing sync history. User sets timezone via `/report_set_timezone` (e.g. US/Eastern) for reports, but `/tasks_status` still shows times in UTC, requiring mental conversion.

---

## Steps to Reproduce

1. Configure a timezone via `/report_set_timezone` (e.g. US/Eastern)
2. Run `/tasks_status`
3. Observe timestamps in sync history or failed sync list
4. Compare with local time — timestamps do not match user timezone

---

## Expected Behavior

Times in `/tasks_status` should be displayed in the user's configured timezone (same as reports use).

---

## Actual Behavior

Times appear in UTC or server timezone, not the user's timezone.

---

## Affected Code

| File | Notes |
|------|-------|
| `src/handlers/google_tasks.py` | `_tasks_status` handler formats and displays sync history |
| `src/task_service.py` | `get_task_sync_status` returns raw timestamps |
| `src/timezone_utils.py` | `get_user_timezone_aware_now`, timezone conversion helpers |

---

## References

- [DEF-005: Stoic Journal Timezone](DEF-005-stoic-journal-timezone-and-data-loss.md) — similar timezone fix; reports use `report_configurations.timezone`
- [US-014: Daily Report](user-stories/US-014-daily-priority-report.md) — report delivery timezone configuration

## History

- 2026-03-09 - Created
- 2026-03-10 - Assigned to Sprint 19; Status changed to ✅ Completed
