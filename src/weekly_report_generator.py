"""
Weekly Review and Report Generator (FR-015)

Generates comprehensive weekly reports aggregating:
- Completed items from the past week (Joplin notes created, Google Tasks completed)
- Pending/overdue items
- Productivity metrics (velocity, completion rate)
- Trends vs. previous weeks
- Categorised breakdown by folder/tag
- Actionable recommendations for next week
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.joplin_client import JoplinClient
    from src.logging_service import LoggingService
    from src.task_service import TaskService

logger = logging.getLogger(__name__)


@dataclass
class WeeklyMetrics:
    """Aggregated metrics for a single week."""

    week_start: datetime
    week_end: datetime

    notes_created: int = 0
    notes_modified: int = 0
    tasks_completed: int = 0
    tasks_pending: int = 0
    tasks_overdue: int = 0

    messages_sent: int = 0
    decisions_made: int = 0

    completion_rate: float = 0.0
    velocity: int = 0  # completed items total

    items_by_folder: dict[str, int] = field(default_factory=dict)
    items_by_tag: dict[str, int] = field(default_factory=dict)
    items_by_day: dict[str, int] = field(default_factory=dict)

    most_productive_day: str = ""
    avg_items_per_day: float = 0.0


@dataclass
class WeeklyReportData:
    """Complete weekly report payload."""

    user_id: int
    current: WeeklyMetrics
    previous: WeeklyMetrics | None = None

    completed_note_titles: list[str] = field(default_factory=list)
    pending_task_titles: list[str] = field(default_factory=list)
    overdue_task_titles: list[str] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)


def _week_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Sunday 23:59:59) for the week containing *reference*."""
    ref = reference or datetime.now()
    start = (ref - timedelta(days=ref.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


class WeeklyReportGenerator:
    """Builds weekly review reports from Joplin, Google Tasks, and the logging DB."""

    def __init__(
        self,
        joplin_client: JoplinClient | None = None,
        task_service: TaskService | None = None,
        logging_service: LoggingService | None = None,
    ):
        self.joplin_client = joplin_client
        self.task_service = task_service
        self.logging_service = logging_service

    # ------------------------------------------------------------------
    # Data collection helpers
    # ------------------------------------------------------------------

    async def _collect_joplin_metrics(
        self, start: datetime, end: datetime
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (created_notes, modified_notes) within the window."""
        if not self.joplin_client:
            return [], []

        try:
            notes = self.joplin_client._make_request("GET", "/notes")
            if isinstance(notes, dict) and "items" in notes:
                notes = notes["items"]
            if not isinstance(notes, list):
                return [], []

            folders = self.joplin_client.get_folders()
            folder_map = {f["id"]: f.get("title", "Unknown") for f in (folders or [])}

            created: list[dict[str, Any]] = []
            modified: list[dict[str, Any]] = []

            start_ts = start.timestamp() * 1000
            end_ts = end.timestamp() * 1000

            for note in notes:
                note["folder_name"] = folder_map.get(note.get("parent_id", ""), "Unknown")

                created_ts = note.get("created_time", note.get("user_created_time", 0))
                updated_ts = note.get("updated_time", note.get("user_updated_time", 0))

                if start_ts <= created_ts <= end_ts:
                    created.append(note)
                elif start_ts <= updated_ts <= end_ts:
                    modified.append(note)

            return created, modified
        except Exception as exc:
            logger.error("Failed to collect Joplin metrics: %s", exc)
            return [], []

    async def _collect_google_tasks_metrics(
        self, user_id: int, start: datetime, end: datetime
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (completed, pending, overdue) tasks."""
        if not self.task_service:
            return [], [], []

        try:
            task_lists = self.task_service.get_available_task_lists(str(user_id))
            if not task_lists:
                return [], [], []

            completed: list[dict[str, Any]] = []
            pending: list[dict[str, Any]] = []
            overdue: list[dict[str, Any]] = []
            now = datetime.now()

            for tl in task_lists:
                tasks = self.task_service.get_user_tasks(str(user_id), tl.get("id")) or []
                for task in tasks:
                    if task.get("status") == "completed":
                        completed.append(task)
                    else:
                        due_str = task.get("due")
                        if due_str:
                            try:
                                due = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                                if due.replace(tzinfo=None) < now:
                                    overdue.append(task)
                                    continue
                            except (ValueError, TypeError):
                                pass
                        pending.append(task)

            return completed, pending, overdue
        except Exception as exc:
            logger.error("Failed to collect Google Tasks metrics: %s", exc)
            return [], [], []

    def _collect_db_metrics(
        self, user_id: int, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """Return (messages_sent, decisions_made) from the logging DB."""
        if not self.logging_service:
            return 0, 0
        try:
            import sqlite3

            with sqlite3.connect(self.logging_service.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM telegram_messages WHERE user_id = ? AND timestamp BETWEEN ? AND ?",
                    (user_id, start.isoformat(), end.isoformat()),
                )
                messages = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM decisions WHERE user_id = ? AND timestamp BETWEEN ? AND ?",
                    (user_id, start.isoformat(), end.isoformat()),
                )
                decisions = cursor.fetchone()[0]

            return messages, decisions
        except Exception as exc:
            logger.error("Failed to collect DB metrics: %s", exc)
            return 0, 0

    # ------------------------------------------------------------------
    # Metric building
    # ------------------------------------------------------------------

    async def _build_metrics(
        self, user_id: int, start: datetime, end: datetime
    ) -> WeeklyMetrics:
        created_notes, modified_notes = await self._collect_joplin_metrics(start, end)
        completed_tasks, pending_tasks, overdue_tasks = (
            await self._collect_google_tasks_metrics(user_id, start, end)
        )
        messages, decisions = self._collect_db_metrics(user_id, start, end)

        total_attempted = len(created_notes) + len(completed_tasks) + len(pending_tasks) + len(overdue_tasks)
        total_done = len(created_notes) + len(completed_tasks)

        items_by_folder: dict[str, int] = {}
        items_by_tag: dict[str, int] = {}
        items_by_day: dict[str, int] = {}

        for note in created_notes:
            folder = note.get("folder_name", "Unknown")
            items_by_folder[folder] = items_by_folder.get(folder, 0) + 1

            tags = note.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in tags:
                items_by_tag[tag] = items_by_tag.get(tag, 0) + 1

            created_ts = note.get("created_time", note.get("user_created_time", 0))
            if created_ts:
                ts = created_ts / 1000 if created_ts > 1e12 else created_ts
                day_name = datetime.fromtimestamp(ts).strftime("%A")
                items_by_day[day_name] = items_by_day.get(day_name, 0) + 1

        for task in completed_tasks:
            day_name = "Unknown"
            completed_str = task.get("completed")
            if completed_str:
                with contextlib.suppress(ValueError, TypeError):
                    day_name = datetime.fromisoformat(
                        completed_str.replace("Z", "+00:00")
                    ).strftime("%A")
            items_by_day[day_name] = items_by_day.get(day_name, 0) + 1

        most_productive = max(items_by_day, key=items_by_day.get) if items_by_day else ""

        metrics = WeeklyMetrics(
            week_start=start,
            week_end=end,
            notes_created=len(created_notes),
            notes_modified=len(modified_notes),
            tasks_completed=len(completed_tasks),
            tasks_pending=len(pending_tasks),
            tasks_overdue=len(overdue_tasks),
            messages_sent=messages,
            decisions_made=decisions,
            completion_rate=(total_done / total_attempted * 100) if total_attempted else 0.0,
            velocity=total_done,
            items_by_folder=items_by_folder,
            items_by_tag=items_by_tag,
            items_by_day=items_by_day,
            most_productive_day=most_productive,
            avg_items_per_day=round(total_done / 7, 1) if total_done else 0.0,
        )
        return metrics

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    async def generate_weekly_report(
        self, user_id: int, reference_date: datetime | None = None
    ) -> WeeklyReportData:
        """Generate a full weekly report for the week containing *reference_date*."""
        current_start, current_end = _week_bounds(reference_date)
        prev_start, prev_end = _week_bounds(current_start - timedelta(days=1))

        current = await self._build_metrics(user_id, current_start, current_end)
        previous = await self._build_metrics(user_id, prev_start, prev_end)

        created_notes, _ = await self._collect_joplin_metrics(current_start, current_end)
        _, pending_tasks, overdue_tasks = await self._collect_google_tasks_metrics(
            user_id, current_start, current_end
        )

        report = WeeklyReportData(
            user_id=user_id,
            current=current,
            previous=previous,
            completed_note_titles=[n.get("title", "Untitled") for n in created_notes[:15]],
            pending_task_titles=[t.get("title", "Untitled") for t in pending_tasks[:10]],
            overdue_task_titles=[t.get("title", "Untitled") for t in overdue_tasks[:10]],
            recommendations=self._generate_recommendations(current, previous),
        )

        if self.logging_service:
            self._log_weekly_report(user_id, report)

        return report

    # ------------------------------------------------------------------
    # Recommendations engine
    # ------------------------------------------------------------------

    def _generate_recommendations(
        self, current: WeeklyMetrics, previous: WeeklyMetrics | None
    ) -> list[str]:
        recs: list[str] = []

        if current.tasks_overdue > 0:
            recs.append(
                f"Clear {current.tasks_overdue} overdue task(s) — they accumulate cognitive load."
            )

        if previous and current.velocity < previous.velocity:
            diff = previous.velocity - current.velocity
            recs.append(
                f"Velocity dropped by {diff} items vs. last week. Consider blocking focused time."
            )

        if current.most_productive_day:
            recs.append(
                f"Your most productive day was {current.most_productive_day} — "
                "schedule deep-work sessions on that day next week."
            )

        if current.completion_rate < 60:
            recs.append(
                "Completion rate is below 60 %. Try breaking large items into smaller tasks."
            )

        if previous and current.velocity > previous.velocity:
            recs.append("Great momentum! Keep it up by maintaining your current rhythm.")

        if not recs:
            recs.append("Solid week! Review your goals and set intentions for next week.")

        return recs

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_weekly_report(self, report: WeeklyReportData) -> str:
        """Format the weekly report as a Telegram message."""
        c = report.current
        p = report.previous
        lines: list[str] = []

        date_range = f"{c.week_start.strftime('%b %d')} – {c.week_end.strftime('%b %d, %Y')}"
        lines.append(f"📊 WEEKLY REVIEW — {date_range}")
        lines.append("")

        # Productivity score
        score = min(100, round(c.completion_rate))
        grade = (
            "A+" if score >= 90 else
            "A" if score >= 80 else
            "B" if score >= 70 else
            "C" if score >= 60 else
            "D"
        )
        trend = ""
        if p:
            prev_score = min(100, round(p.completion_rate))
            delta = score - prev_score
            if delta > 0:
                trend = f" (⬆️ +{delta}% vs last week)"
            elif delta < 0:
                trend = f" (⬇️ {delta}% vs last week)"
            else:
                trend = " (➡️ same as last week)"
        lines.append(f"✅ PRODUCTIVITY SCORE: {score}% [{grade}]{trend}")
        lines.append("")

        # Key numbers
        lines.append("📈 BY THE NUMBERS")
        lines.append(f"  Notes created: {c.notes_created}")
        lines.append(f"  Notes modified: {c.notes_modified}")
        lines.append(f"  Tasks completed: {c.tasks_completed}")
        lines.append(f"  Tasks pending: {c.tasks_pending}")
        if c.tasks_overdue:
            lines.append(f"  ⚠️ Tasks overdue: {c.tasks_overdue}")
        lines.append(f"  Velocity: {c.velocity} items")
        if p:
            v_delta = c.velocity - p.velocity
            symbol = "⬆️" if v_delta > 0 else ("⬇️" if v_delta < 0 else "➡️")
            lines.append(f"  vs last week: {symbol} {abs(v_delta)} items")
        lines.append(f"  Messages sent: {c.messages_sent}")
        lines.append("")

        # Breakdown by folder
        if c.items_by_folder:
            lines.append("📂 BY FOLDER")
            for folder, count in sorted(
                c.items_by_folder.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  • {folder}: {count}")
            lines.append("")

        # Breakdown by day
        if c.items_by_day:
            lines.append("📅 BY DAY")
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for day in day_order:
                count = c.items_by_day.get(day, 0)
                bar = "█" * count + "░" * max(0, 5 - count)
                if count:
                    lines.append(f"  {day[:3]}: {bar} {count}")
            if c.most_productive_day:
                lines.append(f"  🔥 Most productive: {c.most_productive_day}")
            lines.append("")

        # Completed notes
        if report.completed_note_titles:
            lines.append(f"✨ NOTES CREATED ({c.notes_created})")
            for title in report.completed_note_titles[:8]:
                lines.append(f"  • {title}")
            if c.notes_created > 8:
                lines.append(f"  ... and {c.notes_created - 8} more")
            lines.append("")

        # Overdue tasks
        if report.overdue_task_titles:
            lines.append(f"🔴 OVERDUE TASKS ({c.tasks_overdue})")
            for title in report.overdue_task_titles[:5]:
                lines.append(f"  • {title}")
            lines.append("")

        # Pending tasks
        if report.pending_task_titles:
            lines.append(f"⏳ PENDING TASKS ({c.tasks_pending})")
            for title in report.pending_task_titles[:5]:
                lines.append(f"  • {title}")
            if c.tasks_pending > 5:
                lines.append(f"  ... and {c.tasks_pending - 5} more")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("🎯 RECOMMENDATIONS")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        # Footer
        lines.append("—" * 40)
        lines.append("🔗 /weekly_report — regenerate")
        lines.append("⚙️ /show_report_config — settings")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_weekly_report(self, user_id: int, report: WeeklyReportData) -> None:
        if not self.logging_service:
            return
        try:
            self.logging_service.log_system_event(
                level="INFO",
                module="weekly_report",
                message=f"Generated weekly report for user {user_id}",
                extra_data={
                    "week_start": report.current.week_start.isoformat(),
                    "week_end": report.current.week_end.isoformat(),
                    "velocity": report.current.velocity,
                    "completion_rate": report.current.completion_rate,
                    "notes_created": report.current.notes_created,
                    "tasks_completed": report.current.tasks_completed,
                    "tasks_overdue": report.current.tasks_overdue,
                },
            )
        except Exception as exc:
            logger.error("Failed to log weekly report: %s", exc)
