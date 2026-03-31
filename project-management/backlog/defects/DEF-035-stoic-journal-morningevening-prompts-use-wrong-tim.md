# Defect: DEF-035 - Bot uses UTC instead of configurable user timezone

[← Back to Product Backlog](../product-backlog.md)

**Status**: ⭕ To Do
**Priority**: 🟠 High
**Story Points**: 5
**Created**: 2026-03-29
**Updated**: 2026-03-30
**Assigned Sprint**: Backlog

## Description

The bot uses UTC for all time-related operations instead of the user's timezone. This affects the entire bot globally — Stoic Journal, flashcards, habits, health imports, and any other feature that displays or relies on time. The timezone should be configurable in settings, defaulting to `America/Montreal`.

## Steps to Reproduce

1. Complete a Stoic evening reflection at ~22:00 Montreal time
2. Check the saved note in Joplin
3. Observe the header shows "Evening (02:04)" instead of "Evening (22:04)"
4. Observe the note title is "2026-03-31 - Daily Stoic Reflection" instead of "2026-03-30"

## Expected Behavior

- All times displayed by the bot use the configured timezone (default: America/Montreal)
- Note titles use the configured timezone's date
- Morning = before 12:00 noon local time, Evening = noon to midnight local time
- DST transitions (EST/EDT) are handled automatically

## Actual Behavior

- Time shows UTC: "Evening (02:04)" — 4 hours ahead of Montreal
- Note date shows UTC date: "2026-03-31" — tomorrow's date because UTC has crossed midnight
- Both morning and evening reflections have wrong times inside the note
- Affects all features globally, not just Stoic Journal

## Root Cause

The bot uses `datetime.utcnow()` or similar UTC-based time functions instead of converting to the user's timezone before formatting times and dates.

## Solution

1. Add a configurable `timezone` setting in `src/settings.py` (default: `America/Montreal`)
2. Create a utility function that returns the current time in the configured timezone using `zoneinfo.ZoneInfo`
3. Replace all `datetime.utcnow()` / `datetime.now()` calls globally with the timezone-aware utility
4. Morning/evening cutoff: before 12:00 noon = morning, noon to midnight = evening
5. Leave existing notes as-is — do not retroactively fix past entries
6. Ensure DST transitions (EST ↔ EDT) are handled correctly

## Technical References

- Stoic handler code that formats the time and creates note titles
- `src/settings.py` — add timezone setting
- All files using `datetime.utcnow()` or `datetime.now()` for display/logic

## Testing

- [ ] Unit test: evening reflection at 22:00 ET shows correct Montreal time
- [ ] Unit test: morning reflection at 08:00 ET shows correct Montreal time
- [ ] Unit test: note date uses Montreal date, not UTC
- [ ] Unit test: morning/evening cutoff at noon local time
- [ ] Unit test: DST transition handled correctly
- [ ] Unit test: timezone setting is configurable
- [ ] Manual test: complete evening reflection after 20:00 ET, verify correct time/date

## Acceptance Verification

- [ ] Actual Behavior now matches Expected Behavior
- [ ] Steps to Reproduce no longer produce the defect
- [ ] All features globally use configured timezone, not UTC

## Clarifying Questions

- **Q**: Is this only about Stoic Journal, or global?
- **A**: Fix globally across the whole bot.
- **Q**: Morning vs evening cutoff?
- **A**: Morning = before noon, Evening = noon to midnight.
- **Q**: Note title date should use Montreal time?
- **A**: Yes, always use Montreal date.
- **Q**: Morning reflections also affected?
- **A**: Yes, the time inside the note is wrong for morning too.
- **Q**: Hardcode Montreal or configurable?
- **A**: Make it configurable in settings, default to America/Montreal.
- **Q**: Fix existing notes?
- **A**: No, leave existing notes as-is.
- **Q**: Handle DST?
- **A**: Yes.

## History

- 2026-03-29 - Created
- 2026-03-30 - Updated with user screenshot evidence, expanded scope to global fix, bumped to 5 SP
