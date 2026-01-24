# Feature Request: FR-015 - Weekly Review and Report

**Status**: ⭕ Not Started
**Priority**: 🟠 High
**Story Points**: 13
**Created**: 2025-01-23
**Updated**: 2025-01-23
**Assigned Sprint**: Backlog

## Description

Generate and deliver a comprehensive weekly review and report that summarizes accomplishments, pending items, trends, and recommendations for the upcoming week. This report provides users with insights into their productivity, helps identify bottlenecks, and informs planning for the next week.

## User Story

As a user managing multiple projects and goals,
I want to receive a comprehensive weekly review of my accomplishments and pending work,
so that I can reflect on progress, identify patterns, and plan more effectively for the next week.

## Acceptance Criteria

- [ ] Weekly report is generated automatically on a scheduled day/time (default: Friday evening or Monday morning)
- [ ] Report includes summary of completed items from the past week
- [ ] Report includes items still pending or overdue
- [ ] Report tracks productivity metrics (velocity, completion rate, average completion time)
- [ ] Report identifies trends (most productive days, common blockers)
- [ ] Report categorizes items by project/folder/tag for deeper insight
- [ ] Report includes Google Tasks completion data (if configured)
- [ ] Report provides actionable recommendations for next week
- [ ] User can customize report day and time (timezone-aware)
- [ ] User can configure report sections included
- [ ] Report includes comparison to previous weeks (trending data)
- [ ] Database logging for all reports and metrics
- [ ] Option to generate manual on-demand reports for any week
- [ ] Export report to Markdown or PDF for external sharing
- [ ] Report includes visual elements (charts/graphs where applicable in Telegram)

## Business Value

Enables data-driven productivity improvement through weekly reflection. Users gain visibility into their work patterns, can identify what's working and what isn't, and make informed decisions about planning. Helps prevent burnout by highlighting overwork, and celebrates accomplishments. Creates accountability and structure around weekly planning.

## Technical Requirements

- Scheduled weekly report generation (APScheduler)
- Aggregation of weekly statistics from:
  - Completed Joplin notes and tasks
  - Completed Google Tasks
  - Notes created vs. completed ratio
  - Time to completion analysis
  - Tags/folders categorization
- Trend analysis and comparison (week-over-week)
- Telegram message formatting with optional embedded charts
- Database schema for metrics storage and historical tracking
- Timezone support for report delivery
- Analytics dashboard queries
- Optional Markdown/PDF export functionality

## Reference Documents

- Backlog Management Process
- Daily Priority Report (FR-014)
- Database logging system (FR-010)
- Google Tasks Integration (FR-012)

## Technical References

- `src/telegram_orchestrator.py` - Message sending
- `src/joplin_client.py` - Fetching notes, tags, and metadata
- `src/task_service.py` - Google Tasks data
- `src/logging_service.py` - Database access for metrics
- APScheduler for scheduling
- Optional: matplotlib/plotly for chart generation

## Dependencies

- Joplin integration (FR-005)
- Logging system (FR-010)
- Daily Priority Report (FR-014) - related but not dependent
- Optional: Google Tasks Integration (FR-012)

## Implementation Notes

### Report Components

The weekly report should include:

1. **Weekly Summary**
   - Date range covered
   - Overall productivity score/percentage
   - Key accomplishments highlighted

2. **Completion Metrics**
   - Total items completed this week
   - Completion rate (completed / total attempted)
   - Items still pending (overdue, in progress, blocked)
   - Average time to completion

3. **Categorized Breakdown**
   - Completed items by project/folder/tag
   - Pending items by category
   - Items created vs. completed ratio

4. **Productivity Insights**
   - Most productive day of the week
   - Most common completion time ranges
   - Distribution of work across the week
   - Identified blockers/slow items

5. **Trends & Comparison**
   - Velocity trend (this week vs. previous 4 weeks)
   - Category trends (which areas improving/declining)
   - Weekly comparison chart
   - Busiest days pattern

6. **Google Tasks Integration** (if configured)
   - Google Tasks completed this week
   - Tasks vs. Joplin notes correlation
   - Cross-platform completion analysis

7. **Recommendations**
   - Top priority areas for next week (based on pending items)
   - Suggested focus areas
   - Pattern-based recommendations (e.g., "You complete more items on Tuesdays")
   - Workload balance suggestions

### Message Format Example

```
📊 WEEKLY REVIEW - Jan 15-21, 2025

✅ PRODUCTIVITY SCORE: 82% (vs 74% last week ⬆️)

🎯 KEY ACCOMPLISHMENTS
• Completed 12 items (up from 8 last week)
• Closed 5 Google Tasks
• Created project plan document
• Reviewed and archived 8 old notes

📈 BY THE NUMBERS
Completed: 12/15 items (80%)
In Progress: 2 items (blocking 1 item)
Overdue: 1 item (escalate: "Finish Q1 report")
Average Time: 2.3 days to completion (↓ 0.5 days)

📂 BREAKDOWN BY CATEGORY
✅ Projects: 6 completed
✅ Research: 4 completed
✅ Admin: 2 completed
⏳ Projects: 2 pending
⏳ Research: 1 pending (3 days overdue)

📊 TRENDS THIS WEEK
🔥 Most Productive: Tuesday (5 items)
⏰ Peak Time: 10am-12pm window
📈 Velocity: 12 items (↑ 50% vs avg of 8)

🎯 RECOMMENDED NEXT WEEK
1. Complete "Finish Q1 report" (overdue)
2. Focus on Research category (trending slow)
3. Leverage Tuesday momentum (highest output)
4. Break down larger items (avg 2+ days)

💡 PATTERNS OBSERVED
• You're most productive on Tuesdays-Thursdays
• Smaller items completed in <1 day (>80% success)
• Larger items (5+ day estimate) need earlier starts
• Mix of quick wins + deep work improves morale

📌 WEEK OVERVIEW
```
Items    ████████░░░ 80% Complete
Velocity ██████░░░░░ 50% Above Avg
Quality  ███████░░░░ 70% On Time
Focus    ████████░░░ 80% Concentrated
```

---
React with 👍 if you're happy with progress
React with 📌 to save this report
Reply /details to see full breakdown
```

### Configuration Options

Users should be able to customize:
- Report day (e.g., Friday 6 PM, Monday 8 AM)
- Report sections (which to include)
- Timezone
- Category grouping (by folder, tag, or project)
- Include trending data (yes/no)
- Include Google Tasks (yes/no)
- Export format (Telegram message only, or include Markdown/PDF)
- Detail level (summary, detailed, comprehensive)

### Database Schema

```sql
CREATE TABLE weekly_reports (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  week_start_date DATE NOT NULL,
  week_end_date DATE NOT NULL,
  scheduled_time TIME NOT NULL,
  items_completed INTEGER,
  items_pending INTEGER,
  items_overdue INTEGER,
  completion_rate DECIMAL(5,2),
  productivity_score DECIMAL(5,2),
  avg_completion_days DECIMAL(5,2),
  most_productive_day VARCHAR(10),
  telegram_message_id INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE weekly_metrics (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  report_id INTEGER,
  metric_name VARCHAR(100) NOT NULL,
  metric_value VARCHAR(255),
  category VARCHAR(50),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
  FOREIGN KEY (report_id) REFERENCES weekly_reports(id)
);

CREATE TABLE weekly_trends (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  week_number INTEGER,
  year INTEGER,
  velocity INTEGER,
  completion_rate DECIMAL(5,2),
  productivity_score DECIMAL(5,2),
  most_productive_day VARCHAR(10),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE TABLE report_configurations (
  user_id INTEGER PRIMARY KEY,
  weekly_enabled BOOLEAN DEFAULT TRUE,
  weekly_delivery_day VARCHAR(10) DEFAULT 'Friday',
  weekly_delivery_time TIME DEFAULT '18:00',
  weekly_timezone VARCHAR(100) DEFAULT 'UTC',
  weekly_sections VARCHAR(500),
  include_trends BOOLEAN DEFAULT TRUE,
  include_google_tasks BOOLEAN DEFAULT TRUE,
  weekly_detail_level VARCHAR(20) DEFAULT 'detailed',
  export_format VARCHAR(50) DEFAULT 'telegram',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);
```

### Productivity Score Algorithm

```
Weekly Productivity Score = (Completion Rate × 40) + (Velocity vs Avg × 30) + (On-Time Ratio × 20) + (Category Balance × 10)

Completion Rate: (Completed / Total Attempted) × 100
Velocity vs Avg: (This Week Items / Average Items) × 100
On-Time Ratio: (Completed On Time / Completed) × 100
Category Balance: Measure of diversity (0-100, higher = better balanced)

Final Score = (Score / 100) × 100
Grade: 90-100 = A+, 80-89 = A, 70-79 = B, 60-69 = C, <60 = D
```

### Trending Analysis

Track and compare:
- Weekly velocity (items completed per week)
- Completion rate % (trending up/down)
- Average cycle time (trending faster/slower)
- Most productive day consistency
- Category performance over time
- Overdue item frequency

### Export Options

1. **Telegram Message** (default)
   - Formatted for mobile viewing
   - Inline charts/visualizations

2. **Markdown Export**
   - Full detailed format
   - Can be saved, shared, or imported to note-taking apps
   - Includes charts as ASCII or embedded descriptions

3. **PDF Export** (optional future enhancement)
   - Professional format for sharing with stakeholders
   - Visual charts and graphs
   - Print-ready

## Success Metrics

- User engagement: % of reports opened/read weekly
- Action rate: % of users implementing recommendations
- Trend visibility: User feedback on insight value
- Productivity improvement: Tracking score improvements over time
- Data accuracy: Verification of reported metrics

## Notes

This is a powerful feature that transforms the bot from a task-creator into a personal productivity coach. Weekly reviews are proven to increase goal achievement and self-awareness.

Should be complementary to daily reports (FR-014) but more retrospective than prospective. Together they create a feedback loop: daily reports for execution, weekly reports for reflection and planning.

The trending component is critical—users need to see if they're improving or declining in specific areas. This drives engagement and motivation.

## History

- 2025-01-23 - Created
