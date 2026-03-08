# Defect: DEF-021 - Weekly Report Ugly Formatting

**Status**: ✅ Completed  
**Priority**: 🟡 Medium  
**Story Points**: 2  
**Created**: 2026-03-06  
**Updated**: 2026-03-06  
**Assigned Sprint**: Backlog

## Description

The weekly report uses plain bullet lists and ASCII bars that look ugly on Telegram. It lacks the polished monospace table formatting used in the daily report (US-037). Users want a pretty, scannable weekly report consistent with the daily report design.

## Steps to Reproduce

1. Run `/weekly_report` or receive the scheduled weekly report.
2. View the report in Telegram.
3. Observe: Plain bullets for folders, notes, tasks; ASCII bars (█░) for by-day; inconsistent visual hierarchy.

## Expected Behavior

- Monospace tables with Unicode box-drawing (┌─┬─┐, │, └─┴─┘) for all structured sections
- Consistent with daily report (US-037) design
- Clean, scannable layout on mobile

## Actual Behavior

- BY FOLDER: Plain bullet list
- BY DAY: Inline ASCII bars, inconsistent alignment
- NOTES CREATED, OVERDUE TASKS, PENDING TASKS: Plain bullet lists
- RECOMMENDATIONS: Numbered list

## Resolution (2026-03-06)

- Converted all sections to monospace tables using `build_table` and `wrap_pre`
- **By Folder**: Table (Folder | Count)
- **By Day**: Table (Day | Count | Bar) with scaled bar chart
- **Notes Created**: Table (# | Title)
- **Overdue Tasks**: Table (# | Task)
- **Pending Tasks**: Table (# | Task)
- **Recommendations**: Table (# | Recommendation)
- Updated tests to accept new section headers

## Affected Code

- `src/weekly_report_generator.py` — `format_weekly_report()`
- `tests/test_weekly_report.py` — section header assertions

## References

- US-037: Reports Look Great on Telegram
- US-015: Weekly Review and Report
