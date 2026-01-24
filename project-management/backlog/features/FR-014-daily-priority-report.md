# Feature Request: FR-014 - Daily Priority Report for Review and Action Items

**Status**: ⭕ Not Started
**Priority**: 🟠 High
**Story Points**: 8
**Created**: 2025-01-23
**Updated**: 2025-01-23
**Assigned Sprint**: Backlog

## Description

Generate and deliver a daily report summarizing the most important items that require review or action. This report provides users with a focused, prioritized view of what needs their attention each day, helping them stay organized and ensuring critical tasks don't get missed.

## User Story

As a busy user managing multiple tasks and notes,
I want to receive a daily summary of the most important items that need my attention,
so that I can prioritize my work and ensure critical actions are not forgotten.

## Acceptance Criteria

- [ ] Daily report is generated automatically (scheduled task)
- [ ] Report includes high-priority backlog items
- [ ] Report includes incomplete tasks from Google Tasks (if configured)
- [ ] Report includes recent notes pending clarification
- [ ] Report ranks items by urgency and impact
- [ ] Report can be delivered via Telegram daily message
- [ ] User can customize report delivery time (timezone-aware)
- [ ] User can configure what types of items are included
- [ ] Report format is clear and actionable
- [ ] Option to generate manual on-demand reports
- [ ] Database logging for report generation and user actions
- [ ] Report includes completion tracking (items completed since last report)

## Business Value

Increases productivity and accountability by providing a daily digest of what matters most. Users get a bird's-eye view of their priorities, reducing cognitive load and helping them focus on high-impact activities. This bridges the gap between note-taking and task management by ensuring insights are acted upon.

## Technical Requirements

- Scheduled task scheduler (APScheduler or similar)
- Report aggregation logic pulling from:
  - Joplin notes with high-priority tags
  - Incomplete Google Tasks
  - Pending clarifications in bot state
  - Recently created notes needing review
- Telegram message formatting for readability
- Database schema for report configuration per user
- Timezone support for report delivery times
- Analytics on report interactions and completions

## Reference Documents

- Backlog Management Process
- Current logging and decision system
- Google Tasks Integration (FR-012)
- Database logging system (FR-010)

## Technical References

- `src/telegram_orchestrator.py` - Message sending
- `src/joplin_client.py` - Fetching notes and tasks
- `src/task_service.py` - Google Tasks integration
- `src/logging_service.py` - Report logging and tracking
- APScheduler documentation for scheduling

## Dependencies

- Joplin integration (FR-005)
- Logging system (FR-010)
- Conversation state management (FR-007)
- Optional: Google Tasks Integration (FR-012)

## Implementation Notes

### Report Components

The daily report should include:

1. **Critical Items** (if any)
   - Overdue items
   - Blocked tasks
   - High-impact incomplete tasks

2. **Today's Focus**
   - High-priority items due today
   - Items with approaching deadlines
   - Recently created items needing action

3. **Progress Summary**
   - Items completed since yesterday
   - Tasks closed in Google Tasks
   - Notes archived or completed

4. **Call to Action**
   - Most urgent item to tackle first
   - Any items requiring clarification
   - Optional: suggestion to review backlog

### Message Format Example

```
📊 Daily Priority Report - Jan 23, 2025

🔴 CRITICAL (1 item)
• Follow up with client - OVERDUE since Jan 20
  → Reply to Telegram: /update-status task-name

🟠 HIGH PRIORITY (3 items)
• Prepare project presentation - Due today
• Review Q1 budget - Due today
• Schedule team meeting - Due Jan 24

✅ COMPLETED TODAY (2 items)
• Design homepage mockup
• Update project documentation

💡 RECOMMENDATION
Start with: "Prepare project presentation"
(2 hours | high impact)

---
React with 📌 to save this report
Reply /details [item-name] for more info
```

### Configuration Options

Users should be able to customize:
- Report delivery time (e.g., 8:00 AM their timezone)
- Days to include in report (weekdays only, daily, custom)
- Items to include (priority levels, tags, folders)
- Report detail level (compact, detailed, comprehensive)
- Include Google Tasks (yes/no)

### Database Schema

```sql
CREATE TABLE daily_reports (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  report_date DATE NOT NULL,
  scheduled_time TIME NOT NULL,
  items_count INTEGER,
  critical_items INTEGER,
  high_items INTEGER,
  completed_since_last INTEGER,
  telegram_message_id INTEGER,
  user_action VARCHAR(50),
  action_timestamp DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE report_configurations (
  user_id INTEGER PRIMARY KEY,
  enabled BOOLEAN DEFAULT TRUE,
  delivery_time TIME DEFAULT '08:00',
  timezone VARCHAR(100) DEFAULT 'UTC',
  include_critical BOOLEAN DEFAULT TRUE,
  include_high BOOLEAN DEFAULT TRUE,
  include_medium BOOLEAN DEFAULT FALSE,
  include_google_tasks BOOLEAN DEFAULT TRUE,
  detail_level VARCHAR(20) DEFAULT 'detailed',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);
```

### Priority Algorithm

Items should be scored and ranked by:
```
Priority Score = (Priority_Level × 10) + (Urgency × 8) + (Impact × 5) - (Days_Overdue × 2)

Priority_Level: Critical=5, High=3, Medium=1, Low=0
Urgency: Due today=3, Due tomorrow=2, Due this week=1, Future=0
Impact: High=3, Medium=2, Low=1
Days_Overdue: number of days past due date
```

## Success Metrics

- User engagement: % of reports opened/read
- Action completion rate: % of report items completed
- Time saved: User feedback on reduced decision time
- Report accuracy: % of reported items still relevant next day

## Notes

This feature significantly enhances the value of the bot by ensuring that notes and tasks don't just get created—they get acted upon. The daily digest pattern is proven to increase follow-through and accountability.

Should be non-intrusive (scheduled, user can disable) but highly visible when delivered (important enough to interrupt).

## History

- 2025-01-23 - Created
