# Feature Request: FR-027 - Weekly Planning Session

**Status**: ⭕ Not Started
**Priority**: 🟡 Medium
**Story Points**: 8
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 12

## Description

Add a guided weekly planning session (`/plan`) that complements the GTD brain dump (`/braindump`). While brain dump focuses on capturing everything on your mind, the planning session focuses on intentional prioritization: reviewing the upcoming week, setting 3-5 key priorities, identifying potential obstacles, and creating a structured plan.

This closes the GTD loop: capture (braindump) → organize (auto-routing) → review & plan (weekly planning).

## User Story

As a productivity-focused user,
I want a guided weekly planning session,
so that I can start each week with clear priorities and intentions rather than reactive chaos.

## Acceptance Criteria

- [ ] `/plan` starts a guided planning session
- [ ] Bot asks structured questions about the week ahead
- [ ] User can review incomplete tasks from Google Tasks
- [ ] User sets 3-5 priorities for the week
- [ ] User identifies potential obstacles and mitigation strategies
- [ ] Session generates structured planning note in Joplin
- [ ] Tasks created for each priority in Google Tasks
- [ ] `/plan_done` ends session early with summary
- [ ] `/plan_cancel` exits without saving
- [ ] Session timeout after 30 minutes of inactivity

## Business Value

Weekly planning is a cornerstone of GTD and most productivity systems. Without intentional planning:
- Users stay reactive, responding to whatever is urgent
- Important but not urgent work gets neglected
- Weeks blur together without progress on goals

A guided session ensures users actually do weekly planning (not just intend to) and captures the output in their system.

## Technical Requirements

### 1. Planning Session Flow

```
/plan
   │
   ▼
┌─────────────────────────────────┐
│ 1. Review: "Let me show you    │
│    your incomplete tasks and   │
│    upcoming commitments..."    │
└─────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────┐
│ 2. Reflect: "How did last week │
│    go? What worked, what       │
│    didn't?"                    │
└─────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────┐
│ 3. Priorities: "What are the   │
│    3-5 most important things   │
│    to accomplish this week?"   │
└─────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────┐
│ 4. Obstacles: "What might get  │
│    in the way? How will you    │
│    handle it?"                 │
└─────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────┐
│ 5. Commitment: "Looking at     │
│    your priorities, what's     │
│    your #1 focus?"             │
└─────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────┐
│ Generate planning note +       │
│ Create priority tasks          │
└─────────────────────────────────┘
```

### 2. Planning Persona Prompt

```python
PLANNING_PERSONA = """You are a Weekly Planning Coach helping users plan their week intentionally.

Your role:
- Guide the user through a structured weekly planning process
- Help them clarify priorities (not just list tasks)
- Encourage realistic commitments (3-5 priorities max)
- Surface potential obstacles proactively
- Keep the session focused and time-boxed

Conversation style:
- Warm but focused
- Ask one question at a time
- Summarize what you hear before moving on
- Challenge vague priorities ("What specifically would 'make progress on project X' look like?")

Session phases:
1. REVIEW - Show pending tasks, ask about last week
2. REFLECT - What worked, what didn't
3. PRIORITIES - Set 3-5 key outcomes for the week
4. OBSTACLES - Identify blockers and mitigation
5. COMMIT - Confirm #1 priority, end session
"""
```

### 3. State Management

```python
class PlanningSessionState(BaseModel):
    phase: str  # "review", "reflect", "priorities", "obstacles", "commit"
    started_at: datetime
    last_week_reflection: str | None = None
    priorities: list[str] = []
    obstacles: list[dict] = []  # {"obstacle": str, "mitigation": str}
    top_priority: str | None = None
    conversation_history: list[dict] = []
```

### 4. Review Phase - Task Fetching

Pull data for context:

```python
async def _gather_review_context(user_id: int, orch: TelegramOrchestrator) -> str:
    """Gather pending tasks and recent activity for review."""

    # Get incomplete Google Tasks
    tasks = await orch.google_tasks_client.list_tasks(user_id, show_completed=False)

    # Get notes created this week
    week_start = get_week_start(user_id)
    recent_notes = await orch.joplin_client.search_notes(
        query=f"created:{week_start.isoformat()}"
    )

    # Get overdue items
    overdue = [t for t in tasks if t.due_date and t.due_date < datetime.now()]

    return format_review_context(tasks, recent_notes, overdue)
```

### 5. Output Note Template

```markdown
# Weekly Plan - Week of March 3, 2026

## Last Week Reflection
{last_week_reflection}

## This Week's Priorities

### 🎯 #1 Priority
{top_priority}

### Other Priorities
1. {priority_1}
2. {priority_2}
3. {priority_3}

## Potential Obstacles

| Obstacle | Mitigation Strategy |
|----------|---------------------|
| {obstacle_1} | {mitigation_1} |
| {obstacle_2} | {mitigation_2} |

## Pending Tasks Carried Over
{pending_tasks_list}

---
*Generated via /plan on {timestamp}*
```

### 6. Task Creation

Create Google Tasks for each priority:

```python
async def _create_priority_tasks(
    priorities: list[str],
    top_priority: str,
    user_id: int,
    orch: TelegramOrchestrator
) -> None:
    """Create tasks for weekly priorities."""

    for priority in priorities:
        is_top = priority == top_priority
        await orch.google_tasks_client.create_task(
            user_id=user_id,
            title=f"{'⭐ ' if is_top else ''}{priority}",
            notes="Weekly priority from /plan session",
            due_date=get_friday()  # Due end of week
        )
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/handlers/planning.py` | Planning session handlers |
| `src/prompts/planning_coach.txt` | Persona prompt |
| `tests/test_planning.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/__init__.py` | Register planning handlers |
| `src/state_manager.py` | Add PlanningSessionState |
| `config.py` | Add planning config options |

### Commands

| Command | Description |
|---------|-------------|
| `/plan` | Start weekly planning session |
| `/plan_done` | End session early, generate summary |
| `/plan_cancel` | Exit without saving |

## Testing

### Unit Tests

- [ ] Test session state transitions
- [ ] Test context gathering (tasks, notes)
- [ ] Test note generation format
- [ ] Test task creation for priorities
- [ ] Test session timeout handling
- [ ] Test cancel flow

### Manual Testing Scenarios

| Scenario | Expected |
|----------|----------|
| Start `/plan` with no pending tasks | Skip review, go to reflect |
| Set 6 priorities | Bot suggests narrowing to 5 |
| Vague priority "work on project" | Bot asks for specifics |
| `/plan_cancel` mid-session | No note created, confirmation |
| Session idle 30+ minutes | Auto-timeout with partial save |

## Dependencies

- FR-012: Google Tasks Integration (required - for task list)
- FR-017: Brain Dump Session (reference - similar conversation flow)
- FR-007: Conversation State Management (required)
- FR-014: Daily Report (optional - can reference report data)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session too long | Time-box to 15-20 min, show progress |
| Users skip planning | Send weekly reminder (optional) |
| Priorities too vague | Coach persona challenges vagueness |
| Overwhelmed by review data | Summarize, don't dump raw lists |

## Future Enhancements

- [ ] Calendar integration (show upcoming events)
- [ ] Weekly reminder notification (Sunday evening)
- [ ] Template customization
- [ ] Review previous week's plan completion
- [ ] Suggest priorities based on overdue/high-priority items
- [ ] Integration with monthly/quarterly goals

## Notes

- Keep session under 20 minutes - respect user's time
- Coach should push back on > 5 priorities
- Consider offering "quick plan" (just priorities) vs "full plan"
- Sunday evening or Monday morning are ideal times

## History

- 2026-03-05 - Feature request created
