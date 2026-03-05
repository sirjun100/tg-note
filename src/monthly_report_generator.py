"""
Monthly Review Report Generator (FR-031)

Generates monthly reports aggregating:
- Notes created/updated in the month
- Tasks completed
- Week-over-week trends
- Project activity, top tags
- Productivity patterns
- AI-generated insights
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.joplin_client import JoplinClient
    from src.llm_orchestrator import LLMOrchestrator
    from src.logging_service import LoggingService
    from src.task_service import TaskService

logger = logging.getLogger(__name__)


@dataclass
class MonthlyMetrics:
    """Aggregated metrics for a month."""

    notes_created: int = 0
    notes_updated: int = 0
    tasks_completed: int = 0
    completion_rate: float = 0.0
    decisions_made: int = 0

    notes_change_pct: float = 0.0
    tasks_change_pct: float = 0.0
    completion_change_pct: float = 0.0


@dataclass
class WeeklyBreakdown:
    """Weekly activity within the month."""

    week_number: int
    week_start: datetime
    notes: int
    tasks: int
    total: int


@dataclass
class ProjectActivity:
    """Project/folder activity summary."""

    project_name: str
    notes_count: int
    tasks_count: int
    status: str  # "active", "slowing", "stalled"


@dataclass
class MonthlyReportData:
    """Complete monthly report payload."""

    year: int
    month: int
    metrics: MonthlyMetrics
    weekly_data: list[WeeklyBreakdown]
    project_activity: list[ProjectActivity]
    top_tags: list[tuple[str, int]]
    most_productive_day: str
    least_productive_day: str
    peak_hours: list[int]
    insights: list[str]


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Return (start, end) for the given month (UTC)."""
    start = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
    return start, end


class MonthlyReportGenerator:
    """Builds monthly review reports from Joplin, Google Tasks, and the logging DB."""

    def __init__(
        self,
        joplin_client: JoplinClient | None = None,
        task_service: TaskService | None = None,
        logging_service: LoggingService | None = None,
        llm_orchestrator: LLMOrchestrator | None = None,
    ):
        self.joplin_client = joplin_client
        self.task_service = task_service
        self.logging_service = logging_service
        self.llm_orchestrator = llm_orchestrator

    async def _get_notes_in_range(
        self, start: datetime, end: datetime
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (created_notes, updated_notes) in the date range."""
        if not self.joplin_client:
            return [], []

        try:
            notes = await self.joplin_client.get_all_notes(
                fields="id,title,parent_id,created_time,updated_time,user_created_time,user_updated_time"
            )
            folders = await self.joplin_client.get_folders()
            folder_map = {f.get("id"): f.get("title", "Unknown") for f in folders}

            start_ts = int(start.timestamp() * 1000)
            end_ts = int(end.timestamp() * 1000)

            created: list[dict[str, Any]] = []
            updated: list[dict[str, Any]] = []

            for note in notes:
                note["folder_name"] = folder_map.get(note.get("parent_id", ""), "Unknown")
                created_ts = note.get("created_time") or note.get("user_created_time", 0)
                updated_ts = note.get("updated_time") or note.get("user_updated_time", 0)

                if start_ts <= created_ts <= end_ts:
                    created.append(note)
                elif start_ts <= updated_ts <= end_ts and created_ts < start_ts:
                    updated.append(note)

            return created, updated
        except Exception as exc:
            logger.error("Failed to get notes for monthly report: %s", exc)
            return [], []

    async def _get_completed_tasks_in_range(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Return tasks completed within the date range."""
        if not self.task_service:
            return []

        try:
            task_lists = self.task_service.get_available_task_lists(str(user_id))
            if not task_lists:
                return []

            completed: list[dict[str, Any]] = []
            for tl in task_lists:
                # BF-018: show_completed=True — API returns only incomplete by default
                tasks = self.task_service.get_user_tasks(
                    str(user_id), tl.get("id"), show_completed=True
                ) or []
                for task in tasks:
                    if task.get("status") == "completed":
                        completed_str = task.get("completed")
                        if completed_str:
                            try:
                                completed_dt = datetime.fromisoformat(
                                    completed_str.replace("Z", "+00:00")
                                )
                                if start <= completed_dt.replace(tzinfo=None) <= end:
                                    completed.append(task)
                            except (ValueError, TypeError):
                                pass
            return completed
        except Exception as exc:
            logger.error("Failed to get tasks for monthly report: %s", exc)
            return []

    def _get_decisions_in_range(
        self, user_id: int, start: datetime, end: datetime
    ) -> int:
        """Return count of decisions in the date range."""
        if not self.logging_service:
            return 0
        try:
            import sqlite3

            with sqlite3.connect(self.logging_service.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM decisions WHERE user_id = ? AND timestamp BETWEEN ? AND ?",
                    (user_id, start.isoformat(), end.isoformat()),
                )
                return cursor.fetchone()[0]
        except Exception as exc:
            logger.error("Failed to get decisions for monthly report: %s", exc)
            return 0

    def _analyze_weekly_breakdown(
        self,
        created_notes: list[dict[str, Any]],
        completed_tasks: list[dict[str, Any]],
        start: datetime,
    ) -> list[WeeklyBreakdown]:
        """Break down activity by week within the month."""
        weeks: list[WeeklyBreakdown] = []
        current = start
        week_num = 1

        while current.month == start.month:
            week_end = current + timedelta(days=6, hours=23, minutes=59, seconds=59)
            week_start_ts = int(current.timestamp() * 1000)
            week_end_ts = int(week_end.timestamp() * 1000)

            notes_count = sum(
                1
                for n in created_notes
                if week_start_ts
                <= (n.get("created_time") or n.get("user_created_time", 0))
                <= week_end_ts
            )

            tasks_count = 0
            for t in completed_tasks:
                completed_str = t.get("completed")
                if completed_str:
                    try:
                        completed_dt = datetime.fromisoformat(
                            completed_str.replace("Z", "+00:00")
                        )
                        if current <= completed_dt.replace(tzinfo=None) <= week_end:
                            tasks_count += 1
                    except (ValueError, TypeError):
                        pass

            weeks.append(
                WeeklyBreakdown(
                    week_number=week_num,
                    week_start=current,
                    notes=notes_count,
                    tasks=tasks_count,
                    total=notes_count + tasks_count,
                )
            )
            current += timedelta(days=7)
            week_num += 1

        return weeks

    def _analyze_project_activity(
        self,
        created_notes: list[dict[str, Any]],
        completed_tasks: list[dict[str, Any]],
    ) -> list[ProjectActivity]:
        """Aggregate activity by folder (project)."""
        folder_notes: dict[str, int] = {}

        for note in created_notes:
            folder = note.get("folder_name", "Unknown")
            folder_notes[folder] = folder_notes.get(folder, 0) + 1

        projects: list[ProjectActivity] = []
        for folder, count in sorted(folder_notes.items(), key=lambda x: -x[1])[:10]:
            status = "active" if count >= 3 else ("slowing" if count >= 1 else "stalled")
            projects.append(
                ProjectActivity(
                    project_name=folder,
                    notes_count=count,
                    tasks_count=0,
                    status=status,
                )
            )

        if completed_tasks:
            projects.append(
                ProjectActivity(
                    project_name="Google Tasks",
                    notes_count=0,
                    tasks_count=len(completed_tasks),
                    status="active",
                )
            )

        return projects

    def _analyze_tags(
        self,
        notes: list[dict[str, Any]],
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, int]]:
        """Count tags from decisions (notes don't include tags in API response)."""
        tag_counts: dict[str, int] = {}
        if not self.logging_service:
            return []

        try:
            import json
            import sqlite3

            with sqlite3.connect(self.logging_service.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT tags FROM decisions WHERE user_id = ? AND timestamp BETWEEN ? AND ? AND tags IS NOT NULL",
                    (user_id, start.isoformat(), end.isoformat()),
                )
                for row in cursor.fetchall():
                    try:
                        tags = json.loads(row[0]) if row[0] else []
                        for tag in tags:
                            if isinstance(tag, str) and tag.strip():
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception as exc:
            logger.warning("Failed to get tags from decisions: %s", exc)
        return sorted(tag_counts.items(), key=lambda x: -x[1])[:10]

    def _analyze_patterns(
        self,
        created_notes: list[dict[str, Any]],
        completed_tasks: list[dict[str, Any]],
    ) -> tuple[str, str, list[int]]:
        """Return (most_productive_day, least_productive_day, peak_hours)."""
        day_counts: dict[str, int] = {}
        hour_counts: dict[int, int] = {}

        for note in created_notes:
            ts = note.get("created_time") or note.get("user_created_time", 0)
            if ts:
                ts_sec = ts / 1000 if ts > 1e12 else ts
                dt = datetime.fromtimestamp(ts_sec)
                day_name = dt.strftime("%A")
                day_counts[day_name] = day_counts.get(day_name, 0) + 1
                hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1

        for task in completed_tasks:
            completed_str = task.get("completed")
            if completed_str:
                try:
                    dt = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                    day_name = dt.strftime("%A")
                    day_counts[day_name] = day_counts.get(day_name, 0) + 1
                    hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1
                except (ValueError, TypeError):
                    pass

        most = max(day_counts, key=day_counts.get) if day_counts else "N/A"
        least = min(day_counts, key=day_counts.get) if day_counts else "N/A"
        top_hours = sorted(hour_counts.items(), key=lambda x: -x[1])[:3]
        peak_hours: list[int] = [h for h, _ in top_hours]

        return most, least, peak_hours

    async def _generate_insights(
        self,
        metrics: MonthlyMetrics,
        weekly_data: list[WeeklyBreakdown],
        projects: list[ProjectActivity],
    ) -> list[str]:
        """Generate AI insights about the month."""
        if not self.llm_orchestrator:
            return []

        try:
            weekly_lines = "\n".join(
                f"Week {w.week_number}: {w.total} items (notes: {w.notes}, tasks: {w.tasks})"
                for w in weekly_data
            )
            project_lines = "\n".join(
                f"- {p.project_name}: {p.notes_count} notes, {p.tasks_count} tasks ({p.status})"
                for p in projects[:5]
            )

            prompt = f"""Analyze this monthly productivity data and provide 3-4 actionable insights (2-3 sentences each):

## Metrics
- Notes created: {metrics.notes_created} (change vs last month: {metrics.notes_change_pct:+.0f}%)
- Tasks completed: {metrics.tasks_completed} (change: {metrics.tasks_change_pct:+.0f}%)
- Completion rate: {metrics.completion_rate:.0f}%

## Weekly Trend
{weekly_lines or "No data"}

## Project Activity
{project_lines or "No data"}

Focus on: trends, potential issues, wins to celebrate, suggestions for next month. Be specific and actionable."""

            messages = [
                {"role": "system", "content": "You are a productivity coach. Provide concise, actionable insights."},
                {"role": "user", "content": prompt},
            ]

            provider = self.llm_orchestrator.provider
            response = await provider.generate_response(
                messages=messages,
                temperature=0.5,
                max_tokens=500,
            )
            content = (response.get("content") or "").strip()
            if not content:
                return []

            insights: list[str] = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                    line = line.lstrip("0123456789.-* ")
                    if len(line) > 20:
                        insights.append(line)
            return insights[:4] if insights else [content[:300]]
        except Exception as exc:
            logger.error("Failed to generate monthly insights: %s", exc)
            return []

    async def generate(
        self, user_id: int, year: int, month: int
    ) -> MonthlyReportData:
        """Generate a full monthly report."""
        start, end = _month_bounds(year, month)
        prev_start, prev_end = _month_bounds(
            year if month > 1 else year - 1,
            month - 1 if month > 1 else 12,
        )

        created, updated = await self._get_notes_in_range(start, end)
        prev_created, prev_updated = await self._get_notes_in_range(prev_start, prev_end)
        completed = await self._get_completed_tasks_in_range(user_id, start, end)
        prev_completed = await self._get_completed_tasks_in_range(user_id, prev_start, prev_end)
        decisions = self._get_decisions_in_range(user_id, start, end)

        total_items = len(created) + len(completed)
        completion_rate = (
            (len(completed) / total_items * 100) if total_items else 0.0
        )
        prev_total_items = len(prev_created) + len(prev_completed)
        prev_completion = (
            (len(prev_completed) / prev_total_items * 100) if prev_total_items else 0.0
        )

        notes_change = (
            ((len(created) - len(prev_created)) / len(prev_created) * 100)
            if prev_created
            else 0.0
        )
        tasks_change = (
            ((len(completed) - len(prev_completed)) / len(prev_completed) * 100)
            if prev_completed
            else 0.0
        )
        completion_change = completion_rate - prev_completion

        metrics = MonthlyMetrics(
            notes_created=len(created),
            notes_updated=len(updated),
            tasks_completed=len(completed),
            completion_rate=completion_rate,
            decisions_made=decisions,
            notes_change_pct=notes_change,
            tasks_change_pct=tasks_change,
            completion_change_pct=completion_change,
        )

        weekly_data = self._analyze_weekly_breakdown(created, completed, start)
        projects = self._analyze_project_activity(created, completed)
        top_tags = self._analyze_tags(created, user_id, start, end)
        most_day, least_day, peak_hours = self._analyze_patterns(created, completed)
        insights = await self._generate_insights(metrics, weekly_data, projects)

        return MonthlyReportData(
            year=year,
            month=month,
            metrics=metrics,
            weekly_data=weekly_data,
            project_activity=projects,
            top_tags=top_tags,
            most_productive_day=most_day,
            least_productive_day=least_day,
            peak_hours=peak_hours,
            insights=insights,
        )

    def format_report(self, report: MonthlyReportData) -> str:
        """Format the monthly report as a Telegram message."""
        m = report.metrics
        month_name = datetime(report.year, report.month, 1).strftime("%B %Y")

        lines = [
            f"# 📊 Monthly Review — {month_name}",
            "",
            "## Overview",
            "| Metric | This Month | Change |",
            "|--------|------------|--------|",
            f"| Notes Created | {m.notes_created} | {m.notes_change_pct:+.0f}% |",
            f"| Tasks Completed | {m.tasks_completed} | {m.tasks_change_pct:+.0f}% |",
            f"| Completion Rate | {m.completion_rate:.0f}% | {m.completion_change_pct:+.0f}% |",
            "",
        ]

        if report.weekly_data:
            lines.append("## 📈 Weekly Trends")
            for w in report.weekly_data:
                bar = "█" * min(10, w.total // 3) + "░" * (10 - min(10, w.total // 3))
                lines.append(f"Week {w.week_number}: {bar} {w.total} items")
            lines.append("")

        if report.project_activity:
            lines.append("## 🎯 Project Activity")
            for p in report.project_activity[:5]:
                lines.append(f"• {p.project_name}: {p.notes_count} notes, {p.tasks_count} tasks ({p.status})")
            lines.append("")

        if report.top_tags:
            lines.append("## 🏷️ Top Tags")
            for tag, count in report.top_tags[:5]:
                lines.append(f"• #{tag} ({count})")
            lines.append("")

        lines.append("## ⏰ Productivity Patterns")
        lines.append(f"• Most productive day: {report.most_productive_day}")
        lines.append(f"• Least productive day: {report.least_productive_day}")
        if report.peak_hours:
            lines.append(f"• Peak hours: {', '.join(str(h) for h in report.peak_hours)}")
        lines.append("")

        if report.insights:
            lines.append("## 💡 AI Insights")
            for i, insight in enumerate(report.insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        lines.append(f"—_Generated on {datetime.now().strftime('%Y-%m-%d')}_")
        return "\n".join(lines)
