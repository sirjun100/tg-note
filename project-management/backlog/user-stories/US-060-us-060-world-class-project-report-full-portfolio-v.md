# User Story: US-060 - World-Class Project Report: Full Portfolio View Across Joplin + Google Tasks

[← Back to Product Backlog](../product-backlog.md)

**Status**: ⭕ To Do
**Priority**: 🟠 High
**Story Points**: 8
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Assigned Sprint**: Sprint 20

---

## Description

The current `/project_status` command counts how many Joplin notes carry `status/planning`, `status/building`, `status/blocked`, or `status/done` tags inside the Projects folder:

```
📊 Project Status Tags

🟡 Planning: 2
🔵 Building: 3
🟠 Blocked: 1
✅ Done: 12
⚪ Untagged: 5
```

This is a tag audit, not a report. It cannot answer the fundamental GTD question: *"Am I moving forward on what matters?"*

### Philosophy

The GTD + Second Brain system places every project in two systems simultaneously:
- **Joplin** = the project cockpit — goals, research, decisions, progress log
- **Google Tasks** = the project engine — the concrete next actions that move it forward

A meaningful project report reads both and synthesizes them. It mirrors the GTD Weekly Review: *"Do I have a next action for every active project? Is anything stalled? What did I finish this week?"*

The report should feel like a briefing from a trusted chief-of-staff, not a database printout.

### Current vs. World-Class

| Current `/project_status` | World-Class `/project_report` |
|--------------------------|-------------------------------|
| Planning: 2 | **Learn to Sing Harmonies** 🔵 Building |
| Building: 3 | Next: "Practice 3rds over Let It Be" |
| Blocked: 1 | Last activity: 2 days ago · 8 notes · 3 tasks |
| Done: 12 | |
| Untagged: 5 | **Kitchen Renovation** 🟠 Blocked |
| | ⚠️ No next action — project is stuck! |
| | ⚠️ Stalled: no activity in 18 days |

### What the Report Shows

**Portfolio Header**
- Active: N · Blocked: N · Planning: N · ⚠️ No next action: N
- Warning if total active > 15: *"You have 17 active projects — GTD recommends keeping under 15"*

**Needs Attention Section** *(appears only when applicable)*
- Stalled projects (no note updated + no task completed in 14+ days)
- Projects with no open Google Task linked (GTD anti-pattern: invisible project)

**Per-Project Block** *(one per active project, blocked/stalled first)*
1. Name + status badge — `Learn to Sing Harmonies 🔵 Building`
2. Next action from Google Tasks — `Next: "Text Mike about harmony tips"`
   — or — `⚠️ No next action — use /task to add one`
3. Activity signal — `Last activity: 2 days ago` or `⚠️ Stalled: 18 days`
4. Scale — `8 notes · 3 open tasks`

**Completed This Week** *(collapsed summary)*
- `✅ 2 completed this week: Kitchen Reno, Tax Return`
- Not expanded — focus stays on what's active

**Drill-Down Mode**
- `/project_report learn` — fuzzy match to one project, shows all open tasks, last 3 notes updated, status history

---

## User Story

As a GTD practitioner managing multiple active projects,
I want `/project_report` to show me a per-project breakdown with next actions, activity signals, and stall detection,
so that I can answer *"Am I moving forward on everything that matters?"* in a single Telegram message without opening Joplin or Google Tasks separately.

---

## Acceptance Criteria

- [ ] **Portfolio header**: Shows count of active, blocked, planning, and "no next action" projects; warns if total active > 15
- [ ] **Per-project block**: Each active project shows name, status badge, next Google Task (or "⚠️ No next action"), last activity date, note count, open task count
- [ ] **Stall detection**: Projects with no note update AND no task completion in 14+ days are flagged `⚠️ Stalled` and surfaced in a "Needs Attention" section
- [ ] **No-next-action alert**: Projects with no open Google Task are flagged with a nudge to `/task`; these appear before healthy projects
- [ ] **Status order**: Blocked → Stalled → Building → Planning; completed last (collapsed)
- [ ] **Completed this week**: Single summary line for projects completed in the past 7 days — not expanded by default
- [ ] **Drill-down**: `/project_report <name>` (fuzzy match) shows full project detail: all open tasks, 3 most recently updated notes, tag/status history
- [ ] **Weekly report integration**: Project portfolio included as an optional section in `/weekly_report`
- [ ] **Timezone-correct**: "Last activity N days ago" calculated in user's configured timezone
- [ ] **Graceful empty state**: When no active projects, shows an encouraging message + prompt to create one via `/project_new`
- [ ] **Performance**: Full report for up to 20 projects in < 3 seconds

---

## Business Value

The weekly review is the heartbeat of a GTD system. Without a project report that shows stalls, missing next actions, and portfolio size, the system slowly loses trust — tasks fall through the cracks, projects go dark. A world-class project report makes the weekly review effortless and keeps the trusted system actually trusted.

---

## Technical References

- `src/handlers/core.py` — `_project_status()` handler (replace/extend → `_project_report()`)
- `src/joplin_client.py` — `get_notes_with_tag()`, `get_all_notes()`, `get_folders()` — note activity per project
- `src/task_service.py` — fetch open tasks per linked Google Tasks project list
- `src/handlers/report.py` — weekly report integration point
- `src/timezone_utils.py` — `get_user_timezone_aware_now()` for "N days ago" calculation

---

## Dependencies

- US-012 (Google Tasks integration) ✅
- US-034 (Joplin ↔ Google Tasks project sync) ✅
- US-044 (/project_new command) ✅
- US-015 (Weekly Report — integration) ✅
- DEF-028 (timezone fix for timestamps) ✅ Sprint 19
- US-059 (GTD Dashboard) — shares task-fetching logic; implement together or after

---

## History

- 2026-03-10 - Created
- 2026-03-10 - Assigned to Sprint 20
