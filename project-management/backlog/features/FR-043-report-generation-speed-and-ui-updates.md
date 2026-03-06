# Feature Request: FR-043 - Report Generation: Speed Up with Async and Chat UI Updates

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog

## Description

Speed up daily, weekly, and monthly report generation by maximizing async/parallel data fetching and providing progress updates in the chat UI. Currently reports can feel slow (especially weekly and monthly), and users see only "typing..." with no feedback until the full report arrives. This FR improves both perceived and actual performance.

## User Story

As a user who runs `/daily_report`, `/weekly_report`, or `/monthly_report`,
I want reports to generate faster and see progress updates in the chat,
so that I don't wonder if the bot is stuck and the wait feels shorter.

## Acceptance Criteria

### Async / Parallelization

- [ ] **Daily report**: Maximize parallel fetches; ensure no blocking sync calls in the hot path (Joplin `fetch_joplin_notes_for_report` may use sync `_make_request`/`get_folders` — convert or run in executor)
- [ ] **Weekly report**: Run `_build_metrics` for current and previous week in parallel (`asyncio.gather`); run `_collect_joplin_metrics`, `_collect_google_tasks_metrics`, `_collect_inbox_notes_count` in parallel within `_build_metrics`
- [ ] **Monthly report**: Run `_get_notes_in_range` (current + previous month), `_get_completed_tasks_in_range` (current + previous), `_get_inbox_notes_count`, `_get_pending_tasks_count` in parallel where independent
- [ ] No new sequential awaits where data fetches can run concurrently

### Chat UI Updates

- [ ] Send an initial "📊 Generating report..." message (or edit a status message) when the user triggers a report
- [ ] Update with progress steps, e.g.:
  - "📊 Fetching Joplin notes..."
  - "📊 Fetching Google Tasks..."
  - "📊 Building report..."
- [ ] Progress: **Separate messages** for each step (simpler; user sees a short stream)
- [ ] Final: **Send report as new message, delete progress messages** (industry best practice—clean chat)
- [ ] Progress updates apply to **on-demand** reports only; **scheduled reports**: no progress (user isn't waiting)

### Performance

- [ ] Weekly report: measurable improvement (e.g. current + previous metrics in parallel → ~2x faster for that phase)
- [ ] Monthly report: measurable improvement from parallel fetches
- [ ] No regression: reports remain correct; parallelization does not introduce race conditions or wrong data

## Business Value

- **Perceived speed**: Progress messages make the wait feel shorter and reduce "is it broken?" anxiety
- **Actual speed**: Parallel fetches reduce wall-clock time, especially for weekly/monthly (multiple date ranges, multiple sources)
- **UX**: Aligns with modern expectations (loading indicators, progress feedback)

## Technical Requirements

### 1. Daily Report

- `report_generator.py`: `fetch_joplin_notes_for_report` — if it uses sync Joplin calls, either:
  - Convert Joplin client methods to async, or
  - Run sync calls in `asyncio.to_thread()` / `loop.run_in_executor()` so they don't block
- `generate_report_async` already uses `asyncio.gather` for 5 fetches — verify all are truly async

### 2. Weekly Report

- `weekly_report_generator.py`:
  - `generate_weekly_report`: `current = await _build_metrics(...)` then `previous = await _build_metrics(...)` → change to `asyncio.gather(current_task, previous_task)`
  - `_build_metrics`: `_collect_joplin_metrics`, `_collect_google_tasks_metrics`, `_collect_inbox_notes_count` run sequentially → change to `asyncio.gather`
  - `created_notes, _ = await _collect_joplin_metrics(...)` and `_collect_google_tasks_metrics` after current/previous — can be parallel with current/previous or folded into `_build_metrics`

### 3. Monthly Report

- `monthly_report_generator.py`:
  - `_get_notes_in_range`: `notes = await get_all_notes()` then `folders = await get_folders()` — can run in parallel with `asyncio.gather`
  - `generate`: Multiple `await _get_notes_in_range`, `_get_completed_tasks_in_range`, etc. — group independent calls in `asyncio.gather`
  - `_generate_insights` (LLM) runs after data is ready — keep sequential; it's the slowest part

### 4. Progress Updates

- New helper: `async def _send_report_progress(chat, step: str)` — sends a new message for each step; returns message IDs for later deletion
- Handlers pass chat/message to generator, or generators accept optional callback: `on_progress(step: str)`
- Steps: configurable per report type (e.g. `"fetching_joplin"`, `"fetching_tasks"`, `"building"`)
- Telegram: Use `chat.send_message` for each step; store message IDs; delete all when report is sent

### 5. Progress Implementation

- **Granularity**: Configurable or different per report type (daily vs weekly vs monthly)
- **Progress messages**: Send as **separate messages** for each step
- **Final report**: Send as **new message**, **delete** all progress messages (industry best practice)
- **Scheduled reports**: No progress updates
- **Callback**: Either callback passed to generators or handler-owned; implementation choice

## Reference Documents

- [FR-014: Daily Priority Report](FR-014-daily-priority-report.md)
- [FR-015: Weekly Review Report](FR-015-weekly-review-report.md)
- [FR-031: Monthly Review Report](FR-031-monthly-review-report.md)
- [FR-037: Reports Look Great on Telegram](FR-037-reports-great-on-telegram.md)

## Technical References

- `src/report_generator.py` — `generate_report_async`, `fetch_joplin_notes_for_report`, `fetch_google_tasks_for_report`
- `src/weekly_report_generator.py` — `generate_weekly_report`, `_build_metrics`, `_collect_joplin_metrics`, `_collect_google_tasks_metrics`
- `src/monthly_report_generator.py` — `generate`, `_get_notes_in_range`, `_get_completed_tasks_in_range`
- `src/handlers/reports.py` — `_daily_report`, `_weekly_report`, `_monthly_report`
- `src/joplin_client.py` — `get_folders`, `get_all_notes`, `_make_request` (sync vs async)

## Dependencies

- Reports (FR-014, FR-015, FR-031) ✅
- Ensure Joplin client and task service support async where needed

## Design Decisions (2026-03-06)

- **Progress granularity**: Configurable or different per report type
- **Progress display**: Separate messages for each step
- **Scheduled reports**: No progress updates
- **Final report**: New message + delete progress messages (industry best practice)
- **Callback design**: Either approach fine

## Notes

- Daily report already uses `asyncio.gather` for 5 fetches; the main gain may be from fixing any sync Joplin calls
- Weekly and monthly have the most sequential awaits and will benefit most from parallelization
- Progress updates are high-value for perceived performance even if actual speed gain is modest

## History

- 2026-03-06 - Created
- 2026-03-06 - Design decisions: configurable granularity, separate progress messages, no progress for scheduled, new message + delete progress for final
