# User Story: US-023 - Intelligent Content Routing (Notes vs Tasks)

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 8
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 10

## Description

Enable the LLM to intelligently decide whether user input should be saved as a Joplin note, a Google Task, or both. Currently, the system uses simple heuristics (`is_action_item()`) to detect tasks. This feature upgrades to LLM-powered classification that considers context, language patterns, deadlines, and content type to make smarter routing decisions.

Users can also force a specific content type using existing `/tasks` and `/notes` commands, overriding LLM classification.

## User Story

As a user who captures both knowledge and action items through Telegram,
I want the bot to automatically determine whether my message is a note or a task,
so that I don't have to manually specify the type for every message.

## Acceptance Criteria

- [ ] LLM classifies each message as `note`, `task`, or `both`
- [ ] Classification uses semantic analysis (not just keyword matching)
- [ ] Tasks are created in Google Tasks with extracted due dates when present
- [ ] Notes are created in Joplin with appropriate folder/tags
- [ ] "Both" creates a linked note and task
- [ ] `/tasks <text>` forces task creation (bypasses LLM classification)
- [ ] `/notes <text>` forces note creation (bypasses LLM classification)
- [ ] Plain text messages use LLM classification
- [ ] Confidence threshold configurable (default: 0.8)
- [ ] Fallback to NEED_INFO when classification is ambiguous
- [ ] Logging captures classification decisions for analysis

## Business Value

Users capture mixed content throughout the day — some items need action tracking (tasks), others need knowledge preservation (notes), and some need both. Manual classification adds friction. By letting the LLM understand intent, users can simply send messages naturally, and the system routes them correctly.

This reduces:
- Cognitive load (no need to remember /tasks vs /notes)
- Missed tasks (action items that get saved as notes and forgotten)
- Lost context (tasks without supporting documentation)

## Technical Requirements

### 1. Extended Response Schema

Replace `JoplinNoteSchema` with `ContentDecision`:

```python
class TaskData(BaseModel):
    title: str
    due_date: str | None = None  # ISO format or natural language
    notes: str | None = None
    task_list: str | None = None  # Google Tasks list name

class NoteData(BaseModel):
    title: str
    body: str
    parent_id: str  # Joplin folder ID
    tags: list[str] = []

class ContentDecision(BaseModel):
    status: str  # "SUCCESS" or "NEED_INFO"
    content_type: str  # "note", "task", or "both"
    confidence_score: float
    question: str | None = None
    log_entry: str

    note: NoteData | None = None
    task: TaskData | None = None
```

### 2. Updated System Prompt

Add classification guidelines to `_build_system_prompt()`:

```
## Content Type Classification

Analyze user messages and determine the appropriate content type:

### Create a TASK when:
- Contains action verbs (buy, call, send, schedule, book, fix, submit, review)
- Has time references (tomorrow, by Friday, next week, in 2 hours)
- Is a reminder or to-do item
- Uses imperative mood ("Do X", "Remember to Y", "Don't forget to Z")
- Short, actionable (typically < 50 words)
- Explicitly mentions "task", "todo", "reminder"

### Create a NOTE when:
- Contains information to preserve (meeting notes, ideas, research)
- Reference material, documentation, or learning
- Long-form content (> 100 words)
- URLs/links with context to save
- Journal entries, reflections, thoughts
- Recipes, instructions, how-tos
- Explicitly mentions "note", "save this", "remember this"

### Create BOTH when:
- Action item with extensive context worth preserving
- Project-related item needing tracking AND documentation
- Task with research, links, or reference material
- "Do X and here's the background: ..."

### Examples:
- "Buy milk tomorrow" → TASK
- "Meeting notes from client call about the Q3 roadmap..." → NOTE
- "Call John about the proposal - here are the key points to discuss: 1. Budget..." → BOTH
- "Schedule dentist appointment for next Tuesday" → TASK
- "Interesting article about productivity: [URL]" → NOTE
```

### 3. Process Flow

```
User sends message
        │
        ▼
┌───────────────────┐
│ Check for /tasks  │──Yes──▶ Force task creation (skip LLM)
│ or /notes prefix  │
└───────────────────┘
        │ No
        ▼
┌───────────────────┐
│ LLM Classification│
│ (content_type)    │
└───────────────────┘
        │
        ▼
┌─────────┬─────────┬─────────┐
│  note   │  task   │  both   │
└────┬────┴────┬────┴────┬────┘
     │         │         │
     ▼         ▼         ▼
  Create    Create    Create
  Joplin    Google    Both +
   Note     Task      Link them
```

### 4. "Both" Linking Strategy

When `content_type == "both"`:
1. Create Joplin note first
2. Create Google Task with note link in task notes field
3. Add task reference to Joplin note body

Example note body:
```markdown
# Project Proposal Review

[Content here...]

---
📋 **Linked Task**: Review proposal by Friday
```

Example task notes:
```
📝 See Joplin note: Project Proposal Review
```

### 5. Due Date Extraction

For tasks, extract due dates from natural language:
- "tomorrow" → next day
- "by Friday" → upcoming Friday
- "next week" → Monday of next week
- "in 2 hours" → current time + 2 hours
- "March 15" → specific date

Use LLM to parse and return ISO format in `task.due_date`.

## Implementation

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/llm_orchestrator.py` | Add `ContentDecision` schema, update `process_message()`, update system prompt |
| `src/handlers/core.py` | Update `_handle_text_message()` to handle all three content types |
| `src/handlers/core.py` | Add linking logic for "both" case |
| `src/task_service.py` | Add `create_task_with_due_date()` method |
| `tests/test_content_routing.py` | New test file for classification scenarios |

### New Files

| File | Purpose |
|------|---------|
| `tests/test_content_routing.py` | Unit tests for classification |
| `src/prompts/content_classifier.txt` | Optional: Standalone classifier prompt |

### Commands (Existing)

| Command | Behavior |
|---------|----------|
| `/tasks <text>` | Force task creation, bypass LLM |
| `/notes <text>` | Force note creation, bypass LLM |
| `/t <text>` | Shortcut for /tasks |
| `/n <text>` | Shortcut for /notes |
| (plain text) | LLM decides content type |

## Testing

### Unit Tests

- [ ] Test "note" classification (long content, URLs, meeting notes)
- [ ] Test "task" classification (action verbs, deadlines)
- [ ] Test "both" classification (action + context)
- [ ] Test NEED_INFO when ambiguous
- [ ] Test `/tasks` force override
- [ ] Test `/notes` force override
- [ ] Test due date extraction
- [ ] Test linking in "both" case

### Manual Testing Scenarios

| Input | Expected |
|-------|----------|
| "Buy milk tomorrow" | TASK with due date |
| "Meeting notes from today's standup..." | NOTE |
| "Call the client about renewal - here's their contract details..." | BOTH |
| "Interesting article: https://..." | NOTE |
| "Schedule dentist for Tuesday 3pm" | TASK |
| "/tasks Remember to call mom" | TASK (forced) |
| "/notes Buy milk" | NOTE (forced, even though looks like task) |

## Dependencies

- US-006: LLM Integration (required)
- US-012: Google Tasks Integration (required)
- US-005: Joplin REST API Client (required)
- US-007: Conversation State Management (required)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM misclassifies content | Allow user correction, log decisions for tuning |
| Due date extraction errors | Default to no due date, ask for clarification |
| "Both" creates clutter | Make linking optional via config |
| Increased token usage | Classification can use smaller/cheaper model |

## Future Enhancements

- [ ] User feedback loop ("Was this classified correctly?")
- [ ] Per-user classification preferences
- [ ] Auto-learn from corrections
- [ ] Support for recurring tasks
- [ ] Calendar event creation (third type)

## Notes

- This feature builds on top of existing `/tasks` and `/notes` commands
- The LLM classification replaces the simple `is_action_item()` heuristic
- Consider A/B testing: some users get LLM routing, others get manual only

## History

- 2026-03-05 - Feature request created
