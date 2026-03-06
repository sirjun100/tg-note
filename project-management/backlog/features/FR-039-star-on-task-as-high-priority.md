# Feature Request: FR-039 - Treat Star on Task as High Priority

**Status**: ✅ Completed
**Priority**: 🟡 Medium
**Story Points**: 3
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Sprint 15

## Description

Treat tasks with stars at the **beginning** of the title as priority markers across the bot. The Google Tasks API does not expose a native "starred" or "importance" field, but users can add ⭐/★/* to task titles. The bot recognizes this convention and surfaces starred tasks by priority in reports and all task displays.

**Star levels** (beginning of title only):
- `*` or `⭐` or `★` = important (HIGH)
- `**` or `⭐⭐` or `★★` = critical (CRITICAL)
- `***` or `⭐⭐⭐` or `★★★` = urgent (URGENT, highest)

## User Story

As a user who stars important tasks in Google Tasks,
I want the bot to treat starred tasks as high priority in reports and displays,
so that my most important items are prominently shown and ranked correctly.

## Design Decisions (2026-03-06)

- **Star variants**: Support ⭐ (emoji), ★ (Unicode), and `*` (ASCII)
- **Position**: Only at beginning of title
- **Priority mapping**: `*` = HIGH, `**` = CRITICAL, `***` = URGENT (urgent > critical)
- **Star vs due date**: Star always wins—starred tasks rank above non-starred regardless of due date
- **Scope**: All task displays (daily/weekly reports, `/task`, `/find`, `/list`, etc.)
- **Documentation**: In `/help` and when user runs `/task` (inform about the feature)
- **Planning handler**: Keep as-is—adds ⭐ (HIGH) for top weekly priority; no change to `***`
- **Display labels**: URGENT = 🔥, CRITICAL = 🔴, HIGH = 🟠, MEDIUM = 🟡, LOW = 🟢

## Acceptance Criteria

- [ ] Add `PriorityLevel.URGENT` (value 6) to enum; existing CRITICAL=5, HIGH=3
- [ ] Tasks with `*`/`**`/`***` (or ⭐/★ variants) at **beginning** of title get corresponding priority
- [ ] Starred tasks rank above non-starred in all displays (star always wins over due date)
- [ ] `/task * Buy milk` or `/task ⭐ Buy milk` creates task with star at beginning (preserved)
- [ ] Content routing: recognize star prefix and preserve it in task title
- [ ] Apply to: daily reports, weekly reports, `/task`, `/find`, `/list`, any task list
- [ ] Documentation: `/help` and `/task` usage hint about star priority feature

## Business Value

- Aligns with Google Tasks UI convention (users can star tasks in the app; we use ⭐ in title as API workaround)
- Ensures user intent (high priority) is reflected in reports
- Low effort: title-based detection, no API changes required

## Technical Requirements

### 1. PriorityLevel Enum

Add `URGENT = 6` to `PriorityLevel` in `src/report_generator.py`:

```python
class PriorityLevel(Enum):
    URGENT = 6      # *** (highest)
    CRITICAL = 5    # **
    HIGH = 3        # *
    MEDIUM = 1
    LOW = 0
```

Add `_priority_label` mapping for URGENT: "🔥 Urgent"

### 2. Star Detection Utility

Create helper to detect star prefix and map to `PriorityLevel`:

- Support: `*`, `**`, `***` (ASCII) and ⭐/★ (emoji/Unicode) at **beginning** of title only
- Return: `PriorityLevel.URGENT`, `CRITICAL`, or `HIGH`; else `None` (use existing logic)

### 3. Report Generator

In `create_google_task_item()` (`src/report_generator.py`):

- Call star-detection helper on `task.get("title", "")`
- If star prefix found, set `priority_level` from star (star **always wins** over due-date inference)
- Otherwise keep existing logic (overdue → HIGH, etc.)

### 4. Task Creation & Content Routing

- `/task` handler and content routing: preserve star prefix if user includes it
- `task_service.create_task_with_metadata()`: pass through title as-is
- Routing prompt: "Star at **beginning** of task text means priority: * = important, ** = critical, *** = urgent; include it in the task title"

### 5. All Task Displays

Ensure star-based priority is applied wherever tasks are listed: reports, `/find`, `/list`, `/task` output, etc.

## API Limitation

The Google Tasks API does not have a `starred` or `importance` field. The native Google Tasks app allows users to star tasks, but this is not exposed via the API. Using ⭐ in the task title is a practical workaround that:
- Works with the current API
- Is visible in Google Tasks UI (user sees the star in the title)
- Can be added/removed by editing the task title

## Reference Documents

- [FR-014: Daily Priority Report](FR-014-daily-priority-report.md)
- [FR-012: Google Tasks Integration](FR-012-google-tasks-integration.md)
- [FR-023: Intelligent Content Routing](FR-023-intelligent-content-routing.md)
- [Google Tasks API - Task resource](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks) (no star field)

## Technical References

- `src/report_generator.py` — `create_google_task_item()`, `PriorityLevel`, `_priority_label`
- `src/task_service.py` — `create_task_with_metadata()`
- `src/handlers/core.py` — `/task` command, content routing, `/find`, `/list`
- `src/llm_orchestrator.py` — `_build_routing_system_prompt()`, ContentDecision
- `src/handlers/planning.py` — adds `⭐` for top weekly priority; no change needed

## Dependencies

- Google Tasks integration (FR-012) ✅
- Daily/Weekly reports (FR-014, FR-015) ✅

## Notes

- Planning handler (`/plan`) already adds ⭐ for top weekly priority; keep as-is. FR-039 makes that star respected everywhere.
- `PriorityLevel` is internal to the bot (report sorting, labels); Google Tasks has no native priority field.

## Implementation Guide

**Sprint 15**: See [sprint-15-implementation-guide.md](../../sprints/sprint-15-implementation-guide.md) § FR-039 for exact code: `PriorityLevel.URGENT`, `_detect_star_priority`, `create_google_task_item` change, routing prompt update.

## History

- 2026-03-06 - Created
- 2026-03-06 - Design decisions: star at beginning only, three levels (*/**/***), all variants (⭐/★/*), star wins over due date, URGENT > CRITICAL
- 2026-03-06 - Story points increased to 3 (expanded scope)
