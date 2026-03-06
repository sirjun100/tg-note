# Feature Request: FR-042 - Stoic Journal: "What I Learned Today" Section

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 4
**Created**: 2026-03-06
**Updated**: 2026-03-06
**Assigned Sprint**: Backlog

## Description

Add a **"What I learned today"** section to the Stoic journal evening reflection. This prompt captures daily insights, lessons, and takeaways that can be repurposed for weekly content (e.g. YouTube videos, blog posts). It fits naturally at the end of the evening flow, after gratitude and before "one thing tomorrow," as a reflective capstone on the day's learnings.

## User Story

As a user who creates weekly YouTube or blog content,
I want to capture "what I learned today" in my Stoic evening reflection,
so that I have a daily stream of insights to draw from when creating content.

## Acceptance Criteria

### Evening Section

- [ ] New question added to evening flow: "What did you learn today? (e.g. A new approach that worked, A mistake to avoid, An insight about yourself or others)"
- [ ] Question appears after "Grateful For," before "Tomorrow"
- [ ] Question is **skippable** (user can leave blank)
- [ ] Answer is saved under section: `### 📚 What I Learned Today`
- [ ] Apply both `#learnings` and `#content-ideas` tags when answer is non-empty
- [ ] Template (`stoic_journal_template.md`) updated with the new EVENING_QUESTIONS entry

### Weekly Aggregation

- [ ] New command `/learnings` aggregates "What I Learned Today" from past 7 days
- [ ] Output formatted for content drafting (YouTube/blog)

## Business Value

- **Content pipeline**: Daily learnings become raw material for weekly YouTube/blog — no need to recall insights later
- **Stoic alignment**: Reflection on lessons learned supports the Stoic practice of learning from experience
- **Low friction**: Captured in the same flow as the existing evening reflection; no extra step

## Technical Requirements

### 1. Template Update

In `src/prompts/stoic_journal_template.md`, add to EVENING_QUESTIONS (after gratitude, before tomorrow):

```
What did you learn today? (e.g. A new approach that worked, A mistake to avoid, An insight about yourself or others)
```

### 2. Evening Content Formatting

In `src/handlers/stoic.py`, `_format_evening_content()`:
- Add new answer slot (index 7 for "learned"; "tomorrow" shifts to index 8)
- Add section to output (between Grateful For and Tomorrow):
  ```
  - **📚 What I Learned Today:**
    {learned}
  ```

### 3. Answer Index Updates

- `_extract_tomorrow_answer()`: Update from index 7 to index 8 (evening answers list)
- `_create_tomorrow_task_from_stoic()`: Uses `_extract_tomorrow_answer` — no change if that's updated

### 4. Content-Friendly Tags

- Apply both `#learnings` and `#content-ideas` when the "learned" answer is non-empty
- Enables `/find learnings` or `/find content-ideas` for search

### 5. Weekly Aggregation Command

- New command: `/learnings`
- Query Stoic Journal notes from past 7 days (user timezone)
- Extract "What I Learned Today" sections from each note
- Output format: **Chronological by date** (most recent first), e.g.:
  ```
  📚 Learnings from the past 7 days

  **Mar 6, 2026**
  • Learning about X...
  • Another insight...

  **Mar 5, 2026**
  • Today's lesson...
  ```

## Design Decisions (2026-03-06)

- **Phrasing**: Option A (with examples)
- **Skippable**: Yes
- **Tags**: Both `#learnings` and `#content-ideas`
- **Section format**: `### 📚 What I Learned Today` ✓
- **Weekly aggregation**: Include in this FR
- **Command**: `/learnings`
- **Output format**: Chronological by date (Design A)

## Reference Documents

- [FR-019: Stoic Journal](FR-019-stoic-journal.md)
- [Stoic Journal Template](../../../src/prompts/stoic_journal_template.md)
- [BF-009: Stoic Questions Template Mismatch](../bugs/BF-009-stoic-questions-template-mismatch.md) — ensure template and code stay aligned

## Technical References

- `src/handlers/stoic.py` — `_format_evening_content()`, `_extract_tomorrow_answer()`, `_load_stoic_template()`
- `src/prompts/stoic_journal_template.md` — EVENING_QUESTIONS, body template
- `src/llm_orchestrator.py` — `format_stoic_reflection()` (if it uses answer indices)

## Dependencies

- Stoic Journal (FR-019) ✅

## Notes

- User use case: weekly YouTube/blog content creation
- Placing after gratitude and before tomorrow keeps the flow: reflect on the day → capture learning → look ahead
- Consider adding `{{LEARNED_CONTENT}}` to the body template if we want flexibility in section placement

## History

- 2026-03-06 - Created
- 2026-03-06 - Design decisions: phrasing A, skippable, both tags, weekly aggregation included; story points 4
