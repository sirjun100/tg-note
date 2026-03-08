# User Story: US-013 - Display Tags in AI Response to Telegram

**Status**: ⏳ In Progress
**Priority**: 🟡 Medium
**Story Points**: 5
**Created**: 2025-01-23
**Updated**: 2025-01-24
**Assigned Sprint**: Sprint 5

## Description

Display the tags that were used or created by the AI when generating a note. When the bot successfully creates a note in Joplin, it should inform the user which tags were assigned or created as part of the note creation process.

## User Story

As a Telegram user creating notes through the bot,
I want to see which tags were applied or created for my note,
so that I can understand how my notes are being organized and ensure the AI is categorizing correctly.

## Acceptance Criteria

- [ ] Tags are displayed in the success message after note creation
- [ ] Distinguishes between existing tags and newly created tags
- [ ] Shows tags in a clear, readable format
- [ ] Handles multiple tags gracefully
- [ ] Works with notes that have no tags
- [ ] Tag display is concise and doesn't clutter the response
- [ ] Information is logged to database for audit trail
- [ ] Edge cases handled (very long tag names, special characters)

## Business Value

Improves user transparency and confidence in the AI's decision-making process. Users can quickly verify that their notes are being organized correctly and understand the categorization logic. This also helps identify if tags need refinement.

## Technical Requirements

- Extract tag information from LLM response
- Format tag display in Telegram message response
- Differentiate between:
  - Tags that already existed in Joplin
  - Tags newly created by the AI
- Update telegram_orchestrator.py response formatting
- Update LLMInteraction logging to include tag information
- Handle Unicode characters and special characters in tag names

## Reference Documents

- Current note creation response format
- LLM response structure
- Logging service for audit trail

## Technical References

- `src/telegram_orchestrator.py` - Response formatting (around line 278)
- `src/llm_orchestrator.py` - LLM response handling
- `src/logging_service.py` - Database logging
- `src/joplin_client.py` - Tag application

## Dependencies

- Core note creation functionality (US-006)
- Joplin tag system (US-005)
- Logging system (US-010)

## Implementation Notes

### Current Response Format
Current success message shows:
```
✅ Note created: '[title]' in folder '[folder_name]'
```

### Proposed Enhancement
Enhanced message could show:
```
✅ Note created: '[title]' in folder '[folder_name]'
🏷️ Tags: existing-tag, new-tag (new)
```

Or with more detail:
```
✅ Note created: '[title]' in folder '[folder_name]'
🏷️ Applied tags:
  • existing-tag (existing)
  • new-tag (new)
```

### Database Extension
- Log which tags were created vs. reused in LLMInteraction table
- Track tag creation for analytics

## Notes

This is a quality-of-life feature that increases transparency. Users appreciate knowing how the AI categorized their content, especially when it's creating new tags. This feedback loop also helps identify if the tagging strategy needs adjustment.

The feature should be non-intrusive but visible—perhaps using a tag emoji 🏷️ for visual clarity.

## History

- 2025-01-23 - Created
