---
template_version: 1.1.0
last_updated: 2025-01-27
compatible_with: [feature-request, bug-fix, sprint-planning]
requires: [markdown-support]
---

# Product Backlog Table Template

This template provides the structure for your main product backlog tracking table. This table provides a high-level overview of all feature requests and bug fixes.

## Usage

1. Copy this template to create your `product-backlog.md` file
2. Update the table as items are added, modified, or completed
3. Keep the table sorted by priority (Critical → High → Medium → Low)
4. Update "Last Updated" date when making changes

---

# Product Backlog

This is the main product backlog tracking all feature requests and bug fixes.

**Last Updated**: 2025-01-23 (FR-012 Completed, Updated for FR-013, FR-014, FR-015, FR-016)

## Feature Requests

| ID | Title | Priority | Points | Status | Sprint | Created | Updated |
|----|-------|----------|--------|--------|--------|---------|---------|
| [FR-001](features/FR-001-git-commit-template.md) | Add Git Commit Message Template | 🟠 High | 5 | ✅ | Sprint 1 | 2026-01-01 | 2026-01-01 |
| [FR-002](features/FR-002-mermaid-workflow-diagrams.md) | Add Mermaid Workflow Diagrams for Backlog Management | 🟠 High | 5 | ✅ | Sprint 1 | 2026-01-01 | 2026-01-01 |
| [FR-003](features/FR-003-update-quick-start-with-setup-script.md) | Update Quick Start Guide to Use Setup Script | 🟠 High | 3 | ✅ | Sprint 3 | 2026-01-01 | 2025-01-27 |
| [FR-004](features/FR-004-telegram-bot-interface.md) | Telegram Bot Interface | 🟠 High | 8 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-005](features/FR-005-joplin-rest-api-client.md) | Joplin REST API Client | 🟠 High | 5 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-006](features/FR-006-llm-integration-for-note-generation.md) | LLM Integration for Note Generation | 🟠 High | 8 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-007](features/FR-007-conversation-state-management.md) | Conversation State Management | 🟠 High | 3 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-008](features/FR-008-security-and-error-handling.md) | Security and Error Handling | 🟠 High | 3 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-009](features/FR-009-initial-setup-and-configuration.md) | Initial Setup and Configuration | 🟠 High | 5 | ✅ | Sprint 2 | 2026-01-20 | 2026-01-20 |
| [FR-010](features/FR-010-database-logging-telegram-llm-decisions.md) | Database for Logging Telegram Conversations and LLM Decisions | 🟡 Medium | 8 | ⏳ | Sprint 3 | 2025-01-27 | 2025-01-27 |
| [FR-010](features/FR-010-database-logging-telegram-llm-decisions.md) | Database for Logging Telegram Conversations and LLM Decisions | 🟡 Medium | 8 | ✅ | Sprint 3 | 2025-01-27 | 2025-01-27 |
| [FR-011](features/FR-011-comprehensive-project-documentation.md) | Comprehensive Project Documentation for Multiple Audiences | 🟡 Medium | 13 | ✅ | Sprint 3 | 2025-01-27 | 2025-01-27 |
| [FR-012](features/FR-012-google-tasks-integration.md) | Google Tasks Integration for Task Logging | 🟡 Medium | 8 | ✅ | Sprint 4 | 2025-01-27 | 2025-01-23 |
| [FR-013](features/FR-013-display-tags-in-ai-response.md) | Display Tags in AI Response to Telegram | 🟡 Medium | 5 | ⭕ | - | 2025-01-23 | 2025-01-23 |
| [FR-014](features/FR-014-daily-priority-report.md) | Daily Priority Report for Review and Action Items | 🟠 High | 8 | ⭕ | - | 2025-01-23 | 2025-01-23 |
| [FR-015](features/FR-015-weekly-review-report.md) | Weekly Review and Report | 🟠 High | 13 | ⭕ | - | 2025-01-23 | 2025-01-23 |
| [FR-016](features/FR-016-joplin-database-reorganization.md) | Joplin Database Reorganization, Tag Management, and Entry Enrichment | 🟠 High | 21 | ⭕ | - | 2025-01-23 | 2025-01-23 |

## Bug Fixes

| ID | Title | Priority | Points | Status | Sprint | Created | Updated |
|----|-------|----------|--------|--------|--------|---------|---------|
| [BF-001](bugs/BF-001-bug-description.md) | [Bug Description] | 🔴 Critical | [X] | ⭕ | - | 2026-01-01 | 2026-01-01 |
| [BF-002](bugs/BF-002-bug-description.md) | [Bug Description] | 🟠 High | [X] | ⭕ | - | 2026-01-01 | 2026-01-01 |
| [BF-003](bugs/BF-003-bug-description.md) | [Bug Description] | 🟡 Medium | [X] | ⭕ | - | 2026-01-01 | 2026-01-01 |

---

## Status Values

- ⭕ **Not Started**: Item not yet started
- ⏳ **In Progress**: Item currently being worked on
- ✅ **Completed**: Item finished and verified

## Priority Levels

- 🔴 **Critical**: Blocks core functionality, must be fixed/implemented immediately
- 🟠 **High**: Important feature/bug, should be addressed soon
- 🟡 **Medium**: Nice to have, can wait
- 🟢 **Low**: Future consideration, low priority

## Column Definitions

- **ID**: Unique identifier (FR-XXX for features, BF-XXX for bugs)
  - Link to detailed item: `[FR-001](features/FR-001-feature-name.md)`
- **Title**: Short, descriptive title (50 characters or less recommended)
- **Priority**: Visual priority indicator (🔴 🟠 🟡 🟢)
- **Points**: Story points (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Status**: Current status (⭕ ⏳ ✅)
- **Sprint**: Assigned sprint number or "-" if not assigned
- **Created**: Date when item was created (YYYY-MM-DD)
- **Updated**: Date when item was last updated (YYYY-MM-DD)

## Notes

- Feature request details: See `features/FR-XXX-*.md` files
- Bug fix details: See `bugs/BF-XXX-*.md` files
- Sprint assignments: See `../sprints/sprint-XX-*.md` files (if using sprint planning)

## Backlog Statistics

**Total Items**: 16 (Features)

**By Status**:
- ⭕ Not Started: 4
- ⏳ In Progress: 0
- ✅ Completed: 12

**By Priority**:
- 🔴 Critical: 0
- 🟠 High: 7
- 🟡 Medium: 9
- 🟢 Low: 0

**Total Story Points**: 86
  - Completed: 66 points (FR-001 through FR-012)
  - Pending: 20 points (FR-013 through FR-016)

**Completion Rate**: 77% (66/86 story points)

---

## Tips for Maintaining the Backlog

1. **Keep it Updated**: Update status and dates when items change
2. **Sort by Priority**: Keep Critical items at top of each section
3. **Link to Details**: Always link IDs to detailed markdown files
4. **Regular Review**: Review and refine backlog regularly (weekly/bi-weekly)
5. **Update Dates**: Keep "Created" and "Updated" dates current
6. **Clear Titles**: Use descriptive, concise titles (update if needed as understanding evolves)

## Example Table Entry

| ID | Title | Priority | Points | Status | Sprint | Created | Updated |
|----|-------|----------|--------|--------|--------|---------|---------|
| [FR-042](features/FR-042-user-authentication.md) | User Authentication | 🟠 High | 13 | ⏳ | Sprint 5 | 2024-01-10 | 2024-01-15 |

This entry indicates:
- Feature Request #42 about User Authentication
- High priority
- Estimated at 13 story points
- Currently in progress
- Assigned to Sprint 5
- Created on January 10, 2024
- Last updated on January 15, 2024
- Clicking FR-042 links to detailed document

---

## Template Validation Checklist

Before finalizing backlog table, ensure:

- [ ] "Last Updated" date is current
- [ ] All feature requests from backlog are included
- [ ] All bug fixes from backlog are included
- [ ] IDs link correctly to detailed files
- [ ] Priorities are assigned (🔴 🟠 🟡 🟢)
- [ ] Story points are estimated
- [ ] Status is current (⭕ ⏳ ✅)
- [ ] Sprint assignments are accurate
- [ ] Created and Updated dates are correct
- [ ] Table is sorted by priority (Critical → High → Medium → Low)
- [ ] Statistics are updated (if using)
- [ ] File is saved as `product-backlog.md`

