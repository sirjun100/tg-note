# Bug Fix: BF-020 - Daily Report: Column Overlap, SOURCE Column Not Required

**Status**: ✅ Completed  
**Priority**: 🟡 Medium  
**Story Points**: 1  
**Created**: 2026-03-06  
**Updated**: 2026-03-06  
**Assigned Sprint**: Backlog

## Description

The Daily Priority Report table shows "PRIORITY" and "SOURCE" as column headers. On narrow screens (e.g. Telegram mobile), "PRIORITY SOURCE" wraps poorly and columns overlap. The SOURCE column (📝 Note / ✅ Task) is not required for the user and adds visual clutter.

## Steps to Reproduce

1. Have tasks and notes in Joplin and Google Tasks.
2. Run `/daily_report` or receive the scheduled daily report.
3. View the report in Telegram (especially on mobile).
4. Observe: "PRIORITY" and "SOURCE" headers wrap awkwardly; columns appear overlapped.

## Expected Behavior

- Two-column table: PRIORITY | ITEM
- No SOURCE column
- Clean alignment on all screen sizes

## Actual Behavior

- Three-column table: PRIORITY | ITEM | SOURCE
- SOURCE column shows "📝 Note" or "✅ Task" — redundant for most users
- Narrow column widths cause header overlap

## Resolution (2026-03-06)

- Removed SOURCE column from daily report priority tasks table
- Updated headers to ["PRIORITY", "ITEM"]
- Adjusted col_widths to [12, 42] for better item title space

## Affected Code

- `src/report_generator.py` — `format_report_message()`, priority tasks table

## References

- FR-037: Reports Look Great on Telegram
