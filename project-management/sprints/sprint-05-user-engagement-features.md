# Sprint 5: Display Tags in AI Response

**Sprint Goal**: Display tags applied by AI when creating notes, improving transparency and helping users understand how their content is being organized.

**Status**: ⭕ Planning

**Duration**: 2025-01-27 - 2025-01-31 (1 week - accelerated)
**Team Velocity**: 5 points (base feature) + bug fixes/cleanup
**Sprint Planning Date**: 2025-01-24
**Sprint Start Date**: 2025-01-27
**Sprint Review Date**: 2025-01-31
**Sprint Retrospective Date**: 2025-01-31

## Sprint Overview

**Focus Areas**:
- Tag display in note creation success messages
- Tag creation history logging
- Simple, clear user communication
- Bug fixes and cleanup

**Key Deliverables**:
- Enhanced success messages with tags
- Tag creation history logging to database
- Updated database schema for tag history
- Comprehensive testing

**Dependencies**:
- Core note creation (✅ Complete - FR-006)
- Joplin tagging system (✅ Complete - FR-005)
- Logging service (✅ Complete - FR-010)

**Risks & Blockers**:
- None identified - low complexity feature
- All dependencies are complete and stable

---

## User Stories

### Story 1: Display Tags in AI Response to Telegram - 5 Points

**User Story**: As a Telegram user creating notes through the bot, I want to see which tags were applied for my note, so that I can understand how the AI is organizing my content.

**Acceptance Criteria**:
- [x] Tags are displayed in the success message after note creation
- [x] Distinguishes between existing tags and newly created tags
- [x] Shows tags in simple, readable format
- [x] Handles multiple tags gracefully
- [x] Works with notes that have no tags
- [x] Tag creation history is logged to database
- [x] Only shows tags for new notes (not retroactive)
- [x] Edge cases handled (long tag names, special characters)

**Reference Documents**:
- FR-013: Display Tags in AI Response to Telegram
- Current note creation response format in telegram_orchestrator.py
- Joplin tag system documentation

**Technical References**:
- File: `src/telegram_orchestrator.py` - Response formatting
- File: `src/llm_orchestrator.py` - LLM response handling
- File: `src/logging_service.py` - Database logging for tags
- File: `src/joplin_client.py` - Tag retrieval
- Database: `tag_creation_history` table (new)

**Story Points**: 5

**Priority**: 🟡 Medium

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-013](../backlog/features/FR-013-display-tags-in-ai-response.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Extract tag information from LLM response | `llm_orchestrator.py:parse_response()` | FR-013 Technical Requirements | ⭕ | 1 | Claude Code |
| T-002 | Differentiate existing vs new tags | `joplin_client.py:get_tags()` + compare logic | FR-013 Technical Requirements | ⭕ | 1 | Claude Code |
| T-003 | Format tag display in response message | `telegram_orchestrator.py:format_success_message()` | FR-013 - Simple format | ⭕ | 2 | Claude Code |
| T-004 | Create database schema for tag history | `database_schema.sql` - new table | FR-013 Database Schema | ⭕ | 1 | Claude Code |
| T-005 | Update logging to track tag creation | `logging_service.py:log_tag_creation()` (new) | FR-013 Technical Requirements | ⭕ | 1 | Claude Code |

**Total Task Points**: 5

---

## Bug Fixes & Cleanup

In addition to FR-013, Sprint 5 will address:
- Any critical bugs discovered in recent testing
- Code cleanup and refactoring as needed
- Documentation updates
- Test coverage improvements

**Estimated Effort**: ~1-2 additional points

---

## Sprint Summary

**Total Story Points**: 5
**Total Task Points**: 5
**Additional Work**: Bug fixes/cleanup (estimated 1-2 points)
**Estimated Total Effort**: 6-7 points
**Sprint Duration**: 1 week (highly accelerated)

**Sprint Burndown Plan**:
- Jan 27-28: Tasks T-001 through T-003 (3 points)
- Jan 29-30: Tasks T-004, T-005 + bug fixes (2-3 points)
- Jan 31: Testing, documentation, review

---

## Technical Implementation Plan

### Files to Modify

1. **`src/telegram_orchestrator.py`**
   - Update `_process_llm_response()` to extract and format tags
   - Update success message formatting
   - Pass tag information to logging service

2. **`src/logging_service.py`**
   - Add `log_tag_creation(user_id, note_id, tags, new_tags)` method
   - Add `get_tag_creation_history(user_id)` method (optional, for analytics)

3. **`src/llm_orchestrator.py`**
   - Ensure LLM response includes tag information
   - Extract existing vs new tags from response

4. **`database_schema.sql`**
   - Add `tag_creation_history` table
   - Add index on (user_id, created_at) for performance

### Database Schema Addition

```sql
CREATE TABLE tag_creation_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  joplin_note_id VARCHAR(100) NOT NULL,
  tag_name VARCHAR(100) NOT NULL,
  is_new_tag BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE INDEX idx_tag_creation_user_date ON tag_creation_history(user_id, created_at);
```

### Tag Display Format (Simple)

**Current Format**:
```
✅ Note created: 'Buy milk' in folder '00 - Inbox'
```

**Enhanced Format with Tags**:
```
✅ Note created: 'Buy milk' in folder '00 - Inbox'
Tags: shopping, groceries (new)
```

**Example with Mix of Tags**:
```
✅ Note created: 'Project meeting notes' in folder 'Work'
Tags: meetings, project-alpha (new), Q1-planning
```

**Explanation**:
- Simple colon-separated format: `Tags: tag1, tag2, tag3 (new)`
- Only new tags get "(new)" suffix
- No emojis, just clear readable text
- Single line, mobile-friendly
- Gracefully handles zero tags (line omitted)

---

## Success Criteria for Sprint 5

- ✅ Tags display in all note creation responses
- ✅ New tags are marked with "(new)" suffix
- ✅ Tag creation history logged to database
- ✅ Works for notes with 0, 1, or many tags
- ✅ All edge cases tested (long names, special chars)
- ✅ Database schema updated with proper indexing
- ✅ Documentation complete
- ✅ Unit tests passing (100% coverage on new code)
- ✅ Bug fixes and cleanup complete

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LLM doesn't return tag info | Low | Medium | Fallback: show tags from Joplin lookup |
| Performance on large tag lists | Very Low | Very Low | No known performance issues |
| Edge cases in tag names | Low | Low | Comprehensive testing of special characters |

**Overall Risk**: VERY LOW - Simple feature, low complexity, stable dependencies

---

## References

- **Feature FR-013**: [Display Tags in AI Response](../backlog/features/FR-013-display-tags-in-ai-response.md)
- **Sprint 4 Completion**: [Sprint 4 Results](sprint-04-google-tasks-integration.md)
- **Product Backlog**: [Product Backlog](../backlog/product-backlog.md)
- **Sprint & Backlog Planning**: [Sprint & Backlog Planning](../docs/sprint-and-backlog-planning.md)

---

**Last Updated**: 2025-01-24
**Version**: 2.0
**Status**: Sprint Planning - Revised Scope (5 points, 1 week, FR-013 only)
