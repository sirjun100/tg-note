# Bug Fix: BF-009 - Stoic Journal: Questions Do Not Match Template Generated in Joplin

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 3
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Backlog

## Description

The `/stoic` command asks questions that do not align with the template structure generated in the Joplin journal. The information is captured in Joplin, but the questions asked during the conversation do not match the sections in the final note. This creates confusion and makes it harder for users to provide meaningful reflections.

## Steps to Reproduce

1. Run `/stoic morning` at any time.
2. Answer the questions as they appear (professional objective, personal objective, obstacle, greater goals).
3. Run `/stoic_done`.
4. Open the generated note in Joplin.
5. Observe: The note structure (Professional Objective, Personal Objective, Obstacle & Response, Greater Goals) does not match what users expect for a morning reflection focused on priorities.
6. Run `/stoic evening` later.
7. Answer the questions (what went well, what went wrong, etc.).
8. Run `/stoic_done`.
9. Observe: The evening section does not ask whether the morning's 3 priorities were completed, nor does it ask for the 3 priorities for tomorrow.

## Expected Behavior

### Morning
- Questions should ask: **What are your 3 top priorities for today?**
- The Joplin template should reflect this: a section for "Top 3 Priorities" with the user's answers.

### Evening
- Questions should ask: **Were your 3 priorities from this morning completed?** (with space to reflect on each).
- Questions should ask: **What are your 3 top priorities for tomorrow?**
- The Joplin template should include sections for: completion status of morning priorities, and tomorrow's 3 priorities.

## Actual Behavior

- **Morning**: Questions ask about professional objective, personal objective, obstacle, and greater goals. No explicit "3 top priorities" question.
- **Evening**: Questions ask about professional/personal wins, what went wrong, control, progress, gratitude, and "one thing tomorrow." No question about whether the morning's priorities were completed, and no explicit "3 priorities for tomorrow."

The template in `stoic.py` (`_format_morning_content`, `_format_evening_content`) and the questions in `stoic_journal_template.md` are misaligned with the intended use case: prioritising the day around 3 top items and checking completion in the evening.

## Root Cause

1. **Template file** (`src/prompts/stoic_journal_template.md`): Defines MORNING_QUESTIONS and EVENING_QUESTIONS that do not include "3 top priorities" for morning or "3 priorities completed" / "3 priorities for tomorrow" for evening.
2. **Formatting logic** (`src/handlers/stoic.py`): `_format_morning_content` and `_format_evening_content` use hardcoded sections (Professional Objective, Personal Objective, etc.) that do not map to a priority-focused flow.
3. **LLM formatter** (`src/llm_orchestrator.py`): `format_stoic_reflection` uses yet another structure (Intention, Focus, Virtue, Gratitude, Top 3 Tasks for morning) that may not align with the questions asked.

## Proposed Solution

Adapt the template and questions so they match:

1. **Update `stoic_journal_template.md`**:
   - **MORNING_QUESTIONS**: Replace with questions that ask for the 3 top priorities of the day
   - **EVENING_QUESTIONS**: Add questions about:
     - Whether the 3 morning priorities were completed (and brief reflection)
     - What are the 3 top priorities for tomorrow

2. **Update `_format_morning_content` and `_format_evening_content`** in `src/handlers/stoic.py`:
   - Morning: Section for "Top 3 Priorities" populated from answers
   - Evening: Section for "Morning Priorities Completed?" and "Top 3 Priorities for Tomorrow"

3. **Ensure consistency** between `stoic_journal_template.md`, the formatting functions, and any LLM-based formatting (if used).

## Technical References

- File: `src/prompts/stoic_journal_template.md` — Questions and body template
- File: `src/handlers/stoic.py` — `_load_stoic_template()`, `_format_morning_content()`, `_format_evening_content()`
- File: `src/llm_orchestrator.py` — `format_stoic_reflection()` (if used for stoic formatting)

## Testing

- [ ] Morning: Questions ask for 3 top priorities; Joplin note shows "Top 3 Priorities" section
- [ ] Evening: Questions ask if 3 priorities were completed and what are 3 priorities for tomorrow
- [ ] Joplin note evening section matches evening questions
- [ ] Full morning → evening flow produces coherent note with correct sections

## Dependencies

- None (self-contained in stoic journal feature)

## Notes

- This fix aligns the stoic journal with a clear priority-based workflow: set 3 priorities in the morning, check completion in the evening, plan 3 for tomorrow.
- Consider whether the LLM format in `format_stoic_reflection` is still used; if so, it must be updated to match the new structure.

## History

- 2026-03-05 - Created (user-reported: questions don't match template, need 3 priorities for morning/evening/tomorrow)
- 2026-03-05 - Completed: Updated template, formatters, and LLM structure to Top 3 Priorities flow
- 2026-03-05 - Improved: Per user choices—kept objectives, obstacle, goals; added Top 3 Priorities; kept morning priorities completion reflection; kept separate prof/personal wins; kept "one thing tomorrow"
