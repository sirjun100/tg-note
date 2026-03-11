# User Story: US-059 - World-Class GTD Dashboard: /tasks_status as Personal Productivity Cockpit

[← Back to Product Backlog](../product-backlog.md)

**Status**: ⭕ To Do
**Priority**: 🟠 High
**Story Points**: 5
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Assigned Sprint**: Backlog

---

## Description

The current `/tasks_status` shows internal sync diagnostics — total synced, success/fail counts, raw timestamps. It is a developer troubleshooting tool, not a user-facing feature. Running it gives the user zero actionable information about their day or their commitments.

The project's core philosophy (GTD + Second Brain docs) is clear:
- **Google Tasks** answers *"What's my next step?"*
- **Joplin** answers *"What do I know about this?"*
- The bot eliminates friction so capture is instant and review is effortless

A world-class `/tasks_status` is a **personal productivity cockpit** that answers *"What is my situation right now?"* in under 10 seconds, without leaving Telegram. It is the bot's equivalent of a morning briefing from a trusted assistant: concise, prioritized, and actionable.

### Current vs. World-Class

| Current `/tasks_status` | World-Class Dashboard |
|------------------------|-----------------------|
| Total synced: 47 | ⚠️ **2 overdue** — needs action now |
| ✅ Successful: 45 | 📅 **3 due today** — your day at a glance |
| ❌ Failed: 2 | 📆 **5 due this week** — planning horizon |
| Recent syncs: sync - 09:42 | 📥 **Inbox: 4 uncategorized tasks** |
| ⚠️ Failed syncs: 2 | ✅ Google Tasks connected · last sync 3 min ago |

### Dashboard Layout (5 sections)

**Section 1 — Action Required** *(always first)*
- Overdue tasks: count + top 3 titles with days overdue
  > `• Call dentist · 2 days overdue`
- If nothing overdue: `✅ All clear — nothing overdue`

**Section 2 — Today**
- Tasks due today with project context
  > `• Submit expense report · Finance`
- If empty: `Nothing scheduled for today — /task to add one`

**Section 3 — This Week**
- Tasks due in the next 7 days, grouped by project
  > `• Buy guitar strings · Long & McQuade project`
- Shows count if list is long (> 5): `+3 more this week`

**Section 4 — Inbox**
- Count of tasks with no project assigned
- Nudge if > 5: `Your inbox has 7 items — time for a quick review`
- If empty: shown as part of the all-clear message

**Section 5 — System Health** *(one line, always last)*
- `✅ Google Tasks connected · Last sync: 3 min ago`
- Expands only if action needed: `⚠️ 2 sync errors — /tasks_sync_detail for more`

### Motivating Empty State

When everything is clear (nothing overdue, nothing today, inbox clean):
> ✅ **You're on top of everything.**
> Nothing overdue · Nothing due today · Inbox clear
> 📆 Next: Call dentist (Friday)

---

## User Story

As a GTD practitioner using the bot as my trusted system,
I want `/tasks_status` to show me a clear, prioritized dashboard of my task situation,
so that I can answer *"What's my next step?"* and *"Is anything slipping?"* in under 10 seconds without leaving Telegram.

---

## Acceptance Criteria

- [ ] **Overdue section**: Shows count + top 3 overdue task titles with days overdue; shows "✅ All clear" if none
- [ ] **Today section**: Shows tasks due today with project name context; shows "Nothing scheduled" with a nudge to `/task` if empty
- [ ] **This week section**: Shows task titles grouped by project for the next 7 days; truncates with `+N more` if > 5
- [ ] **Inbox section**: Shows count of tasks with no project; nudges user to review if > 5; hidden or part of all-clear if empty
- [ ] **System health line**: Single line at bottom — connected status + last sync time; only expands to show errors if action is needed
- [ ] **Motivating empty state**: When nothing overdue and inbox clean, shows an encouraging "You're on top of everything" message with the next upcoming task
- [ ] **Timezone-correct**: All dates and times use the user's configured timezone (set via `/report_set_timezone`)
- [ ] **Fast**: Full response in < 2 seconds
- [ ] **Not-connected state**: If Google Tasks not linked, shows a single friendly one-liner prompt — not a wall of technical error text
- [ ] **Old sync diagnostics preserved**: Raw sync stats available via `/tasks_sync_detail` for debugging; removed from `/tasks_status`

---

## Business Value

The `/tasks_status` command is the user's most natural touchpoint for checking in on their task system. Making it a true GTD dashboard transforms it from a maintenance command into a daily habit — the "open loop check" that GTD practitioners do every morning and evening. This directly reinforces the bot's value as a trusted second brain rather than a technical tool.

---

## Technical References

- `src/handlers/google_tasks.py` — `_tasks_status()` handler (replace body; move sync diagnostics to `_tasks_sync_detail()`)
- `src/task_service.py` — add `get_dashboard_data(user_id)`: returns overdue, due_today, due_this_week, inbox_count
- `src/handlers/google_tasks.py` — `_utc_str_to_local()` already exists for timezone conversion
- `src/timezone_utils.py` — `get_user_timezone_aware_now()` for today/week boundary calculation

---

## Dependencies

- US-012 (Google Tasks integration) ✅
- US-034 (Joplin ↔ Google Tasks project sync) ✅
- DEF-028 (timezone fix for task timestamps) ✅ Sprint 19

---

## History

- 2026-03-10 - Created
