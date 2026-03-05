# Sprint 10: Core UX and Quick Wins

**Sprint Goal**: Improve core user experience with greeting/command help, quick note search, intelligent content routing, and monthly review reports.

**Duration**: 2026-03-10 - 2026-03-23 (2 weeks)
**Team Velocity**: 20 points (target)
**Sprint Planning Date**: 2026-03-05
**Sprint Review Date**: 2026-03-23
**Sprint Retrospective Date**: 2026-03-23

## Sprint Overview

**Focus Areas**:
- Command discovery and onboarding (greeting response)
- Quick retrieval (keyword search)
- Intelligent message routing (notes vs tasks)
- Strategic reporting (monthly review)

**Key Deliverables**:
- Joplin app available 24/7 (machine always running)
- Greeting response with categorized command list
- `/find` and `/search` commands for Joplin note search
- LLM-powered content routing (note, task, or both)
- Monthly report generation with AI insights

**Dependencies**:
- Joplin REST API (Complete - FR-005)
- LLM Integration (Complete - FR-006)
- Google Tasks Integration (Complete - FR-012)
- Weekly Report Generator (Complete - FR-015)

**Risks & Blockers**:
- Content routing classification accuracy (mitigated by confidence threshold and fallback)
- Monthly report data aggregation complexity (mitigated by reusing weekly report patterns)

---

## User Stories

### Story 1: Greeting Response and Command Help - 3 Points

**User Story**: As a new or returning user, I want to say hello and get a friendly response with available commands, so that I can quickly learn what the bot can do and start using it effectively.

**Acceptance Criteria**:
- [ ] LLM recognizes common greetings (hello, hi, hey, good morning, etc.)
- [ ] Bot responds with a friendly greeting
- [ ] Response includes top 5-7 most useful commands with brief descriptions
- [ ] Response is concise (not overwhelming)
- [ ] Does NOT trigger note creation flow
- [ ] Greeting detection has high confidence (avoid false positives)

**Reference Documents**:
- [FR-024: Greeting Response and Command Discovery](../backlog/features/FR-024-greeting-and-command-help.md)

**Technical References**:
- File: `src/handlers/core.py` - `/start` handler, message routing
- File: `src/llm_orchestrator.py` - Content classification

**Story Points**: 3

**Priority**: 🟡 Medium

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-024](../backlog/features/FR-024-greeting-and-command-help.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Add greeting detection (regex or pre-classification) | `core.py` | FR-024 Greeting Detection | ⭕ | 0.5 | — |
| T-002 | Create greeting response template with command list | `core.py:_start()` | FR-024 Response Template | ⭕ | 1 | — |
| T-003 | Modify `/start` and add `/help` alias | `core.py` | FR-024 Commands | ⭕ | 0.5 | — |
| T-004 | Integrate greeting into message routing (skip note flow) | `core.py:_message()` | FR-024 Routing | ⭕ | 1 | — |

**Total Task Points**: 3

---

### Story 2: Quick Note Search - 3 Points

**User Story**: As a user who has captured many notes, I want to quickly search my notes from Telegram, so that I can find information without opening Joplin.

**Acceptance Criteria**:
- [ ] `/find <query>` searches note titles and bodies
- [ ] Returns up to 5-10 matching notes
- [ ] Shows note title, folder, and content snippet
- [ ] Snippet highlights matching text
- [ ] Results sorted by relevance or recency
- [ ] Search is case-insensitive
- [ ] Empty results shows helpful message
- [ ] `/find` without query shows usage help

**Reference Documents**:
- [FR-029: Quick Note Search](../backlog/features/FR-029-quick-note-search.md)

**Technical References**:
- File: `src/joplin_client.py` - Add `search_notes()` method
- File: `src/handlers/search.py` (new) - Search command handlers

**Story Points**: 3

**Priority**: 🟡 Medium

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-029](../backlog/features/FR-029-quick-note-search.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Add `search_notes(query, limit)` to JoplinClient | `JoplinClient.search_notes()` | FR-029 Joplin Search API | ⭕ | 1 | — |
| T-002 | Create search handler with `/find` and `/search` commands | `handlers/search.py` | FR-029 Commands | ⭕ | 1 | — |
| T-003 | Implement snippet extraction and folder resolution | `handlers/search.py` | FR-029 Result Format | ⭕ | 0.5 | — |
| T-004 | Add state for interactive result selection (reply with number) | `state_manager.py` | FR-029 Interactive Results | ⭕ | 0.5 | — |

**Total Task Points**: 3

---

### Story 3: Intelligent Content Routing - 8 Points

**User Story**: As a user who captures both knowledge and action items through Telegram, I want the bot to automatically determine whether my message is a note or a task, so that I don't have to manually specify the type for every message.

**Acceptance Criteria**:
- [ ] LLM classifies each message as `note`, `task`, or `both`
- [ ] Classification uses semantic analysis (not just keyword matching)
- [ ] Tasks are created in Google Tasks with extracted due dates when present
- [ ] Notes are created in Joplin with appropriate folder/tags
- [ ] "Both" creates a linked note and task
- [ ] `/tasks <text>` forces task creation (bypasses LLM classification)
- [ ] `/notes <text>` forces note creation (bypasses LLM classification)
- [ ] Plain text messages use LLM classification
- [ ] Fallback to NEED_INFO when classification is ambiguous
- [ ] Logging captures classification decisions

**Reference Documents**:
- [FR-023: Intelligent Content Routing](../backlog/features/FR-023-intelligent-content-routing.md)

**Technical References**:
- File: `src/llm_orchestrator.py` - ContentDecision schema, routing prompt
- File: `src/handlers/core.py` - Message routing, `/tasks` and `/notes` handlers

**Story Points**: 8

**Priority**: 🟠 High

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-023](../backlog/features/FR-023-intelligent-content-routing.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Define ContentDecision schema (note, task, both) | `llm_orchestrator.py` | FR-023 Extended Schema | ⭕ | 1 | — |
| T-002 | Add content type classification to system prompt | `llm_orchestrator.py` | FR-023 Classification | ⭕ | 2 | — |
| T-003 | Modify `_message()` to dispatch based on content_type | `core.py:_message()` | FR-023 Routing Logic | ⭕ | 2 | — |
| T-004 | Implement task-only flow (create Google Task, no note) | `core.py` | FR-023 Task Flow | ⭕ | 1 | — |
| T-005 | Implement both flow (note + task) | `core.py` | FR-023 Both Flow | ⭕ | 1 | — |
| T-006 | Ensure `/tasks` and `/notes` override classification | `core.py` | FR-023 Force Commands | ⭕ | 0.5 | — |
| T-007 | Add classification logging | `logging_service.py` | FR-023 Logging | ⭕ | 0.5 | — |

**Total Task Points**: 8

---

### Story 4: Monthly Review Report - 5 Points

**User Story**: As a user focused on long-term growth and productivity, I want a monthly report summarizing my progress and patterns, so that I can reflect on what's working, adjust my systems, and track progress toward goals.

**Acceptance Criteria**:
- [ ] `/monthly_report` generates report for current/previous month
- [ ] `/monthly_report 2026-02` generates report for specific month
- [ ] Report aggregates: notes created, tasks completed, completion rates
- [ ] Shows week-over-week trends
- [ ] Shows most active projects/areas
- [ ] Shows most used tags
- [ ] Shows productivity patterns (day of week, time of day)
- [ ] Includes AI-generated insights and recommendations

**Reference Documents**:
- [FR-031: Monthly Review Report](../backlog/features/FR-031-monthly-review-report.md)
- [FR-015: Weekly Report](../backlog/features/FR-015-weekly-review-report.md) - Pattern reference

**Technical References**:
- File: `src/monthly_report_generator.py` (new) - Report generation
- File: `src/weekly_report_generator.py` - Pattern to follow
- File: `src/handlers/reports.py` - Add `/monthly_report` command

**Story Points**: 5

**Priority**: 🟢 Low

**Status**: ⭕ Not Started

**Backlog Reference**: [FR-031](../backlog/features/FR-031-monthly-review-report.md)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Create MonthlyReportGenerator class | `monthly_report_generator.py` | FR-031 Data Aggregation | ⭕ | 2 | — |
| T-002 | Implement metrics calculation (notes, tasks, trends) | `MonthlyReportGenerator._calculate_metrics()` | FR-031 Metrics | ⭕ | 1.5 | — |
| T-003 | Add AI insight generation via DeepSeek | `MonthlyReportGenerator._generate_insights()` | FR-031 AI Insights | ⭕ | 1 | — |
| T-004 | Add `/monthly_report` command handler | `handlers/reports.py` | FR-031 Command | ⭕ | 0.5 | — |

**Total Task Points**: 5

---

### Story 5: Joplin 24/7 Availability - 1 Point

**User Story**: As a user, I want the Joplin app to stay up 24/7, so that the bot can always access my notes and I never have to wait for a cold start.

**Acceptance Criteria**:
- [ ] Fly.io machine runs continuously (min_machines_running = 1)
- [ ] Joplin server is always available (no cold-start delay on first message)
- [ ] Bot responds immediately on first message of the day

**Reference Documents**:
- [Fly.io Joplin Deployment](../../docs/fly-io-joplin-deployment.md)

**Technical References**:
- File: `fly.toml` - `min_machines_running`, `auto_stop_machines`

**Story Points**: 1

**Priority**: 🟠 High

**Status**: ⭕ Not Started

**Backlog Reference**: Operational requirement (no FR)

**Tasks**:

| Task ID | Task Description | Class/Method Reference | Document Reference | Status | Points | Assignee |
|---------|------------------|------------------------|---------------------|--------|--------|----------|
| T-001 | Set min_machines_running = 1 in fly.toml | `fly.toml` | Fly.io config | ⭕ | 0.5 | — |
| T-002 | Deploy and verify machine stays running | `fly deploy` | Deployment | ⭕ | 0.5 | — |

**Total Task Points**: 1

**Note**: This increases Fly.io cost (~$5–7/month for 24/7 shared-cpu-1x) vs ~$0 when idle. See [fly-scheduled-scaling.md](../../docs/fly-scheduled-scaling.md) for hybrid options (e.g., 24/7 during day, sleep at night).

---

## Sprint Summary

**Total Story Points**: 20
**Total Task Points**: 20
**Estimated Velocity**: 20 points (based on story points)

**Sprint Burndown Plan**:
- Week 1: Story 5 (24/7) + Stories 1-2 (Greeting, Quick Search) - 7 points
- Week 2: Stories 3-4 (Content Routing, Monthly Report) - 13 points

**Sprint Review Notes**:
- [To be filled at sprint review]

**Sprint Retrospective Notes**:
- **What went well?**
  - [To be filled]
- **What could be improved?**
  - [To be filled]
- **Action items for next sprint**
  - [To be filled]

---

**Last Updated**: 2026-03-05
