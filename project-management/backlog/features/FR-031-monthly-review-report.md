# Feature Request: FR-031 - Monthly Review Report

**Status**: ⭕ Not Started
**Priority**: 🟢 Low
**Story Points**: 5
**Created**: 2026-03-05
**Updated**: 2026-03-05
**Assigned Sprint**: Sprint 10

## Description

Extend the reporting system with a monthly review report (`/monthly_report`) that aggregates productivity metrics, goal progress, and insights across a full month. While daily and weekly reports focus on tactical execution, the monthly report enables strategic reflection on trends, patterns, and longer-term progress.

## User Story

As a user focused on long-term growth and productivity,
I want a monthly report summarizing my progress and patterns,
so that I can reflect on what's working, adjust my systems, and track progress toward goals.

## Acceptance Criteria

- [ ] `/monthly_report` generates report for current/previous month
- [ ] `/monthly_report 2026-02` generates report for specific month
- [ ] Report aggregates data from daily/weekly reports
- [ ] Shows: notes created, tasks completed, completion rates
- [ ] Shows: week-over-week trends
- [ ] Shows: most active projects/areas
- [ ] Shows: most used tags
- [ ] Shows: productivity patterns (day of week, time of day)
- [ ] Includes AI-generated insights and recommendations
- [ ] Optional: Scheduled monthly delivery (1st of month)

## Business Value

Monthly reflection is a cornerstone of continuous improvement. Without stepping back to see the big picture:
- Users miss trends (gradual decline or improvement)
- Good habits go unrecognized and unreinforced
- Problem patterns persist unnoticed
- Goal progress is unclear

A monthly report creates a natural checkpoint for reflection and adjustment.

## Technical Requirements

### 1. Report Sections

```markdown
# Monthly Review - February 2026

## 📊 Overview

| Metric | This Month | Last Month | Change |
|--------|------------|------------|--------|
| Notes Created | 47 | 52 | -10% 📉 |
| Tasks Completed | 23 | 19 | +21% 📈 |
| Completion Rate | 78% | 72% | +6% 📈 |
| Brain Dumps | 4 | 3 | +1 |
| Journal Entries | 12 | 8 | +4 |

## 📈 Weekly Trends

Week 1: ████████░░ 32 items
Week 2: ██████████ 41 items  ⬆ Peak week
Week 3: ███████░░░ 28 items
Week 4: ████████░░ 35 items

## 🎯 Project Activity

| Project | Notes | Tasks | Status |
|---------|-------|-------|--------|
| Product Launch | 12 | 8 | 🟢 Active |
| Q1 Planning | 6 | 3 | 🟡 Slowing |
| Personal Site | 2 | 1 | 🔴 Stalled |

## 🏷️ Top Tags

1. #work (34 items)
2. #planning (18 items)
3. #ideas (12 items)
4. #learning (8 items)
5. #health (5 items)

## ⏰ Productivity Patterns

**Most Productive Day**: Tuesday (avg 8.2 items)
**Least Productive Day**: Saturday (avg 1.8 items)

**Peak Hours**: 9-11 AM, 2-4 PM
**Quiet Hours**: 12-1 PM (lunch), after 6 PM

## 💡 AI Insights

Based on your activity this month:

1. **Strong start, mid-month dip**: Your productivity peaked in week 2, then declined. Consider what changed - energy, external factors, or overcommitment?

2. **Project balance**: "Product Launch" dominated your attention. Two other projects show minimal activity - are they still priorities?

3. **Tag insight**: #learning appeared 8 times but declined week-over-week. If learning is a goal, consider scheduling dedicated time.

4. **Completion rate improved**: +6% vs last month. Your task sizing or commitment accuracy is improving.

## 🎯 Suggested Focus for Next Month

- Re-engage with "Personal Site" project or archive it
- Maintain the Tuesday momentum - what makes Tuesdays work?
- Consider a mid-month check-in to catch dips early

---
*Generated on 2026-03-01*
```

### 2. Data Aggregation

```python
class MonthlyReportGenerator:
    """Generate monthly review reports."""

    async def generate(
        self,
        user_id: int,
        year: int,
        month: int
    ) -> MonthlyReport:
        """Generate monthly report."""

        # Get date range
        start_date = datetime(year, month, 1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Aggregate from multiple sources
        notes = await self._get_notes_in_range(start_date, end_date)
        tasks = await self._get_tasks_in_range(start_date, end_date)
        decisions = await self._get_decisions_in_range(user_id, start_date, end_date)

        # Previous month for comparison
        prev_month = start_date - timedelta(days=1)
        prev_data = await self._get_previous_month_data(user_id, prev_month)

        # Calculate metrics
        metrics = self._calculate_metrics(notes, tasks, decisions, prev_data)

        # Weekly breakdown
        weekly_data = self._calculate_weekly_breakdown(notes, tasks, start_date)

        # Project activity
        project_activity = self._analyze_project_activity(notes, tasks)

        # Tag analysis
        tag_analysis = self._analyze_tags(notes)

        # Productivity patterns
        patterns = self._analyze_patterns(decisions)

        # AI insights
        insights = await self._generate_insights(metrics, weekly_data, project_activity)

        return MonthlyReport(
            year=year,
            month=month,
            metrics=metrics,
            weekly_data=weekly_data,
            project_activity=project_activity,
            tag_analysis=tag_analysis,
            patterns=patterns,
            insights=insights
        )
```

### 3. Metrics Model

```python
class MonthlyMetrics(BaseModel):
    notes_created: int
    notes_updated: int
    tasks_created: int
    tasks_completed: int
    completion_rate: float
    brain_dumps: int
    journal_entries: int

    # Comparison to previous month
    notes_change_pct: float
    tasks_change_pct: float
    completion_change_pct: float

class WeeklyBreakdown(BaseModel):
    week_number: int
    week_start: date
    notes: int
    tasks: int
    total_items: int

class ProjectActivity(BaseModel):
    project_name: str
    folder_id: str
    notes_count: int
    tasks_count: int
    status: str  # "active", "slowing", "stalled"

class ProductivityPattern(BaseModel):
    most_productive_day: str
    least_productive_day: str
    peak_hours: list[int]
    quiet_hours: list[int]
    day_averages: dict[str, float]
```

### 4. Insight Generation

```python
async def _generate_insights(
    self,
    metrics: MonthlyMetrics,
    weekly_data: list[WeeklyBreakdown],
    projects: list[ProjectActivity]
) -> list[str]:
    """Generate AI insights about the month."""

    prompt = f"""Analyze this monthly productivity data and provide 3-4 actionable insights:

## Metrics
- Notes: {metrics.notes_created} (change: {metrics.notes_change_pct:+.0%})
- Tasks completed: {metrics.tasks_completed} (change: {metrics.tasks_change_pct:+.0%})
- Completion rate: {metrics.completion_rate:.0%}

## Weekly Trend
{self._format_weekly_trend(weekly_data)}

## Project Activity
{self._format_project_activity(projects)}

Provide specific, actionable insights. Focus on:
- Trends and patterns
- Potential issues to address
- Wins to celebrate and reinforce
- Suggestions for next month

Keep each insight to 2-3 sentences."""

    response = await self.llm.generate(prompt)
    return self._parse_insights(response)
```

### 5. Commands

| Command | Description |
|---------|-------------|
| `/monthly_report` | Current month (or previous if < 7 days in) |
| `/monthly_report 2026-02` | Specific month |
| `/monthly_report last` | Previous month |
| `/configure_monthly_report` | Set up scheduled delivery |

### 6. Scheduled Delivery (Optional)

```python
async def schedule_monthly_report(user_id: int, day_of_month: int = 1):
    """Schedule monthly report delivery."""

    scheduler.add_job(
        send_monthly_report,
        CronTrigger(day=day_of_month, hour=9, minute=0),
        args=[user_id],
        id=f"monthly_report_{user_id}"
    )
```

## Implementation

### Key Files to Create

| File | Purpose |
|------|---------|
| `src/monthly_report_generator.py` | Report generation logic |
| `src/handlers/monthly_report.py` | Command handlers |
| `tests/test_monthly_report.py` | Unit tests |

### Key Files to Modify

| File | Changes |
|------|---------|
| `src/handlers/__init__.py` | Register handlers |
| `src/scheduler_service.py` | Add monthly schedule support |
| `src/logging_service.py` | Ensure data available for aggregation |

### Data Sources

| Data | Source |
|------|--------|
| Notes created/updated | Joplin API (`/notes?order_by=created_time`) |
| Tasks completed | Google Tasks API (completed status) |
| Decision history | SQLite logging database |
| Brain dumps | Notes in brain dump folder or with tag |
| Journal entries | Notes in journaling folder |

## Testing

### Unit Tests

- [ ] Test metrics calculation
- [ ] Test week-over-week comparison
- [ ] Test project activity detection
- [ ] Test tag aggregation
- [ ] Test pattern analysis
- [ ] Test insight generation
- [ ] Test month boundary handling

### Manual Testing Scenarios

| Scenario | Expected |
|----------|----------|
| `/monthly_report` on March 5 | Shows February report |
| `/monthly_report 2026-01` | Shows January report |
| Month with no data | Graceful handling, "No activity" |
| Compare to previous month | Changes calculated correctly |

## Dependencies

- FR-014: Daily Report (reference - similar structure)
- FR-015: Weekly Report (required - aggregates weekly data)
- FR-005: Joplin REST API Client (required)
- FR-012: Google Tasks Integration (required)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Insufficient data for patterns | Require minimum activity threshold |
| Report generation slow | Cache intermediate calculations |
| Insight quality varies | Review and tune prompts |
| Month boundaries confusing | Clear date labels |

## Future Enhancements

- [ ] Quarterly report aggregation
- [ ] Year-in-review annual report
- [ ] Goal tracking integration
- [ ] Export to PDF
- [ ] Comparison charts (visual)
- [ ] Custom metric tracking
- [ ] Team/shared reports

## Notes

- Run report generation at night to avoid API rate limits
- Consider caching weekly aggregates to speed up monthly
- Insights should be specific and actionable, not generic
- Allow users to set which day of month for scheduled delivery

## History

- 2026-03-05 - Feature request created
