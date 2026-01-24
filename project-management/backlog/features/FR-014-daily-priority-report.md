# Feature Request: FR-014 - Daily Priority Report for Review and Action Items

**Status**: ✅ Completed
**Priority**: 🟠 High
**Story Points**: 8
**Created**: 2025-01-23
**Updated**: 2026-01-24
**Assigned Sprint**: Sprint 6

## Description

Generate and deliver a daily report summarizing the most important items that require review or action. The report aggregates data from both Joplin notes (with priority tags) and Google Tasks (if configured) to provide users with a unified, prioritized view of what needs their attention each day. This helps them stay organized and ensures critical tasks and notes don't get missed.

**Key Sources for Report**:
- High-priority Joplin notes (based on tags: #urgent, #important, #critical)
- Incomplete Google Tasks (status: needsAction, when configured)
- Notes pending user clarification (waiting for follow-up response)
- Recently created items requiring action

## User Story

As a busy user managing multiple tasks and notes,
I want to receive a daily summary of the most important items that need my attention,
so that I can prioritize my work and ensure critical actions are not forgotten.

## Acceptance Criteria

- [x] Daily report is generated automatically (scheduled task)
- [x] Report includes high-priority backlog items
- [x] Report includes incomplete tasks from Google Tasks (if configured)
- [x] Report includes recent notes pending clarification
- [x] Report ranks items by urgency and impact
- [x] Report can be delivered via Telegram daily message
- [x] User can customize report delivery time (timezone-aware)
- [x] User can configure what types of items are included
- [x] Report format is clear and actionable
- [x] Option to generate manual on-demand reports
- [x] Database logging for report generation and user actions
- [x] Report includes completion tracking (items completed since last report)

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

The daily report should include data from **both Joplin notes and Google Tasks**:

1. **Critical Items** (if any)
   - Overdue Joplin notes
   - Overdue Google Tasks
   - Blocked tasks
   - High-impact incomplete items

2. **Today's Focus**
   - High-priority Joplin notes due today (by tag)
   - Google Tasks due today
   - Items with approaching deadlines (from either source)
   - Recently created items needing action

3. **Progress Summary**
   - Joplin notes completed since yesterday
   - Google Tasks completed since yesterday
   - Notes archived or completed
   - Combined completion count

4. **Breakdown by Source**
   - Count of Joplin items in report
   - Count of Google Tasks in report
   - Count of notes pending clarification

5. **Call to Action**
   - Most urgent item to tackle first (ranked across both sources)
   - Any notes requiring user clarification
   - Optional: suggestion to review backlog

### Message Format Example

```
📊 Daily Priority Report - Jan 23, 2025
📊 9 items total (5 from Joplin + 4 from Google Tasks)

🔴 CRITICAL (2 items)
• Follow up with client - OVERDUE since Jan 20 (Google Task)
  → Status: needsAction | Complete at: /update-status
• Complete Q1 report - OVERDUE (Joplin note #urgent)

🟠 HIGH PRIORITY (4 items)
📝 Joplin Notes (2):
  • Prepare project presentation - Due today (#important)
  • Review Q1 budget - Due today (#work)

✅ Google Tasks (2):
  • Schedule team meeting - Due today
  • Finalize contract review - Due Jan 24

⏳ PENDING CLARIFICATION (2 items)
• Meeting notes from yesterday - awaiting your response
• Project plan draft - waiting for feedback

✅ COMPLETED TODAY (3 items)
• Design homepage mockup (Joplin)
• Update project documentation (Joplin)
• Approve vendor quote (Google Task)

💡 RECOMMENDATION
Start with: "Follow up with client" (OVERDUE + high impact)
Then: "Complete Q1 report" (OVERDUE + blocking other work)

---
🔗 /daily_report - Generate another report now
⚙️ /show_report_config - View your settings
📌 React with 📌 to save this report
💬 Reply /details to see full breakdown
```

### Configuration Options

Users should be able to customize:
- **Report delivery time** (e.g., 8:00 AM their timezone)
- **Timezone** (important for scheduling accurate delivery)
- **Days to include in report** (weekdays only, daily, custom)
- **Priority levels to include** (critical, high, medium, low)
- **Report detail level** (compact, detailed, comprehensive)
- **Include Google Tasks** (yes/no) - aggregates incomplete tasks
- **Include Joplin notes** (yes/no) - prioritized by tags
- **Include clarification items** (yes/no) - notes awaiting response
- **Custom tags to monitor** (which tags trigger inclusion)

### Database Schema

```sql
CREATE TABLE daily_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  report_date DATE NOT NULL,
  scheduled_time TIME NOT NULL,
  joplin_items_count INTEGER,
  google_tasks_count INTEGER,
  clarification_items_count INTEGER,
  critical_items INTEGER,
  high_items INTEGER,
  completed_since_last INTEGER,
  telegram_message_id INTEGER,
  generated_by VARCHAR(20) DEFAULT 'scheduled',  -- 'scheduled' or 'manual' (/daily_report command)
  user_action VARCHAR(50),
  action_timestamp DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
  UNIQUE(user_id, report_date)
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
  include_clarification_pending BOOLEAN DEFAULT TRUE,
  detail_level VARCHAR(20) DEFAULT 'detailed',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

-- Add indexes for performance
CREATE INDEX idx_daily_reports_user_date ON daily_reports(user_id, report_date);
CREATE INDEX idx_daily_reports_created ON daily_reports(created_at);
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

### Telegram Commands

Users interact with daily reports through these commands:

**Generate Report On-Demand**:
```
/daily_report
  → Immediately generates and sends the daily report
  → Pulls current Joplin notes and Google Tasks
  → Respects user configuration settings
  → Logs the manual trigger in database
```

**Configuration Commands**:
```
/configure_report_time 08:00
  → Set delivery time for automatic reports
  → Format: HH:MM (24-hour)

/configure_report_timezone US/Eastern
  → Set timezone for report scheduling
  → Examples: US/Eastern, Europe/London, Asia/Tokyo

/configure_report_content high
  → Set priority filter: critical, high, medium, all
  → Default: high (includes critical and high items)

/toggle_daily_report on
  → Enable/disable automatic daily reports
  → Options: on/off, yes/no, true/false

/show_report_config
  → Display current configuration
  → Shows: delivery time, timezone, content level, enabled status

/report_help
  → Show help for report commands
  → List all available commands with descriptions
```

## Success Metrics

- User engagement: % of reports opened/read
- Action completion rate: % of report items completed
- Time saved: User feedback on reduced decision time
- Report accuracy: % of reported items still relevant next day
- Feature adoption: % of users with automated reports enabled
- Google Tasks integration: % of users including Google Tasks in reports

## Notes

This feature significantly enhances the value of the bot by ensuring that notes and tasks don't just get created—they get acted upon. The daily digest pattern is proven to increase follow-through and accountability.

Should be non-intrusive (scheduled, user can disable) but highly visible when delivered (important enough to interrupt).

## History

- 2025-01-23 - Created
- 2025-01-24 - Updated to include Google Tasks aggregation and /daily_report command
  - Added explicit mention that daily reports include Google Tasks (incomplete tasks)
  - Added /daily_report command for on-demand report generation
  - Enhanced message format examples to show both Joplin notes and Google Tasks
  - Added timezone configuration for accurate scheduled delivery
  - Added command documentation section
