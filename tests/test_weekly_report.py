"""Tests for the weekly report generator (FR-015)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.weekly_report_generator import (
    WeeklyMetrics,
    WeeklyReportData,
    WeeklyReportGenerator,
    _week_bounds,
)


class TestWeekBounds:
    def test_monday_returns_full_week(self):
        monday = datetime(2026, 3, 2, 10, 0)  # Monday
        # Pass user_id=123 and logging_service=None for tests
        start, end = _week_bounds(123, None, monday)
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert start.hour == 0
        assert end.hour == 23

    def test_sunday_stays_in_same_week(self):
        sunday = datetime(2026, 3, 8, 18, 0)  # Sunday
        start, end = _week_bounds(123, None, sunday)
        assert start.date() == datetime(2026, 3, 2).date()  # Previous Monday
        assert end.date() == sunday.date()

    def test_none_uses_now(self):
        start, end = _week_bounds(123, None, None)
        # _week_bounds returns timezone-aware datetimes, so use naive comparison
        now = datetime.now()
        # Convert to naive for comparison (strip tzinfo)
        start_naive = start.replace(tzinfo=None)
        end_naive = end.replace(tzinfo=None)
        assert start_naive <= now <= end_naive


class TestRecommendations:
    def setup_method(self):
        self.gen = WeeklyReportGenerator()

    def test_overdue_tasks_recommendation(self):
        current = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), tasks_overdue=3
        )
        recs = self.gen._generate_recommendations(current, None)
        assert any("overdue" in r.lower() for r in recs)

    def test_velocity_drop_recommendation(self):
        current = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), velocity=5
        )
        previous = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), velocity=10
        )
        recs = self.gen._generate_recommendations(current, previous)
        assert any("velocity" in r.lower() or "dropped" in r.lower() for r in recs)

    def test_velocity_increase_congratulation(self):
        current = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), velocity=15
        )
        previous = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), velocity=8
        )
        recs = self.gen._generate_recommendations(current, previous)
        assert any("momentum" in r.lower() for r in recs)

    def test_productive_day_recommendation(self):
        current = WeeklyMetrics(
            week_start=datetime.now(),
            week_end=datetime.now(),
            most_productive_day="Tuesday",
        )
        recs = self.gen._generate_recommendations(current, None)
        assert any("Tuesday" in r for r in recs)

    def test_low_completion_rate(self):
        current = WeeklyMetrics(
            week_start=datetime.now(), week_end=datetime.now(), completion_rate=40
        )
        recs = self.gen._generate_recommendations(current, None)
        assert any("60" in r or "completion" in r.lower() for r in recs)


class TestFormatWeeklyReport:
    def setup_method(self):
        self.gen = WeeklyReportGenerator()

    def test_format_contains_key_sections(self):
        current = WeeklyMetrics(
            week_start=datetime(2026, 3, 2),
            week_end=datetime(2026, 3, 8),
            notes_created=5,
            notes_modified=3,
            tasks_completed=4,
            tasks_pending=2,
            tasks_overdue=1,
            messages_sent=20,
            velocity=9,
            completion_rate=75.0,
            items_by_folder={"Inbox": 3, "Projects": 2},
            items_by_day={"Monday": 3, "Wednesday": 4, "Friday": 2},
            most_productive_day="Wednesday",
        )
        report = WeeklyReportData(
            user_id=123,
            current=current,
            previous=None,
            completed_note_titles=["Note 1", "Note 2"],
            pending_task_titles=["Task A"],
            overdue_task_titles=["Overdue X"],
            recommendations=["Do something great"],
        )
        msg = self.gen.format_weekly_report(report)

        assert "WEEKLY REVIEW" in msg
        assert "PRODUCTIVITY SCORE" in msg
        assert "BY THE NUMBERS" in msg
        assert "BY FOLDER" in msg
        assert "BY DAY" in msg
        assert "NOTES CREATED" in msg
        assert "OVERDUE TASKS" in msg
        assert "PENDING TASKS" in msg
        assert "RECOMMENDATIONS" in msg
        assert "Wednesday" in msg

    def test_format_with_previous_week_shows_trend(self):
        current = WeeklyMetrics(
            week_start=datetime(2026, 3, 2),
            week_end=datetime(2026, 3, 8),
            velocity=12,
            completion_rate=80,
        )
        previous = WeeklyMetrics(
            week_start=datetime(2026, 2, 23),
            week_end=datetime(2026, 3, 1),
            velocity=8,
            completion_rate=70,
        )
        report = WeeklyReportData(
            user_id=123, current=current, previous=previous
        )
        msg = self.gen.format_weekly_report(report)

        assert "⬆️" in msg
        assert "vs last week" in msg

    def test_empty_report_still_formats(self):
        current = WeeklyMetrics(
            week_start=datetime(2026, 3, 2), week_end=datetime(2026, 3, 8)
        )
        report = WeeklyReportData(user_id=123, current=current)
        msg = self.gen.format_weekly_report(report)
        assert "WEEKLY REVIEW" in msg
        assert "0%" in msg or "PRODUCTIVITY SCORE: 0%" in msg


class TestDbMetrics:
    def test_collect_db_metrics_no_service(self):
        gen = WeeklyReportGenerator(logging_service=None)
        messages, decisions = gen._collect_db_metrics(123, datetime.now(), datetime.now())
        assert messages == 0
        assert decisions == 0


@pytest.mark.asyncio
class TestGenerateWeeklyReport:
    async def test_generate_report_no_data_sources(self):
        gen = WeeklyReportGenerator()
        report = await gen.generate_weekly_report(user_id=123)
        assert report.user_id == 123
        assert report.current.velocity == 0
        assert report.current.notes_created == 0

    async def test_generate_with_mocked_joplin(self):
        """Verify Joplin note collection filters by date window."""
        now = datetime.now()
        this_week_ts = now.timestamp() * 1000
        old_ts = (now - timedelta(days=30)).timestamp() * 1000

        mock_joplin = MagicMock()
        mock_joplin._make_request.return_value = [
            {"id": "n1", "title": "Recent Note", "parent_id": "f1",
             "created_time": this_week_ts, "updated_time": this_week_ts,
             "tags": "work,urgent"},
            {"id": "n2", "title": "Old Note", "parent_id": "f1",
             "created_time": old_ts, "updated_time": old_ts},
        ]
        mock_joplin.get_folders.return_value = [
            {"id": "f1", "title": "Inbox"}
        ]

        gen = WeeklyReportGenerator(joplin_client=mock_joplin)
        report = await gen.generate_weekly_report(user_id=123)

        assert report.current.notes_created == 1
        assert "Recent Note" in report.completed_note_titles
        assert "Old Note" not in report.completed_note_titles

    async def test_generate_with_mocked_google_tasks(self):
        """Verify Google Tasks split into completed/pending/overdue."""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat() + "Z"

        mock_task_service = MagicMock()
        mock_task_service.get_available_task_lists.return_value = [
            {"id": "list1", "title": "My Tasks"}
        ]
        mock_task_service.get_user_tasks.return_value = [
            {"id": "t1", "title": "Done Task", "status": "completed",
             "completed": datetime.now().isoformat() + "Z"},
            {"id": "t2", "title": "Pending Task", "status": "needsAction"},
            {"id": "t3", "title": "Overdue Task", "status": "needsAction",
             "due": yesterday},
        ]

        gen = WeeklyReportGenerator(task_service=mock_task_service)
        report = await gen.generate_weekly_report(user_id=123)

        assert report.current.tasks_completed == 1
        assert report.current.tasks_pending == 1
        assert report.current.tasks_overdue == 1
        assert "Pending Task" in report.pending_task_titles
        assert "Overdue Task" in report.overdue_task_titles

    async def test_generate_with_db_metrics(self):
        """Verify DB metrics (messages, decisions) are collected."""
        import sqlite3
        import tempfile
        import os

        db_path = os.path.join(tempfile.mkdtemp(), "test_logs.db")

        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE telegram_messages (
                id INTEGER PRIMARY KEY, user_id INTEGER, message_text TEXT,
                response_text TEXT, timestamp DATETIME, message_type TEXT)""")
            conn.execute("""CREATE TABLE decisions (
                id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT,
                timestamp DATETIME)""")
            now = datetime.now()
            for i in range(5):
                conn.execute(
                    "INSERT INTO telegram_messages (user_id, message_text, timestamp, message_type) VALUES (?, ?, ?, ?)",
                    (123, f"msg {i}", now.isoformat(), "user"),
                )
            for i in range(3):
                conn.execute(
                    "INSERT INTO decisions (user_id, status, timestamp) VALUES (?, ?, ?)",
                    (123, "SUCCESS", now.isoformat()),
                )
            conn.commit()

        mock_logging = MagicMock()
        mock_logging.db_path = db_path

        gen = WeeklyReportGenerator(logging_service=mock_logging)
        report = await gen.generate_weekly_report(user_id=123)

        assert report.current.messages_sent == 5
        assert report.current.decisions_made == 3

    async def test_previous_week_comparison(self):
        """Verify the report includes previous week data for trends."""
        gen = WeeklyReportGenerator()
        report = await gen.generate_weekly_report(user_id=123)

        assert report.previous is not None
        assert report.previous.week_end < report.current.week_start

    async def test_weekly_report_last_week_arg(self):
        """Verify /weekly_report last generates for the previous week."""
        gen = WeeklyReportGenerator()
        last_week = datetime.now() - timedelta(days=7)
        report = await gen.generate_weekly_report(user_id=123, reference_date=last_week)

        assert report.current.week_end < datetime.now()

    async def test_full_pipeline_format(self):
        """End-to-end: mock data → generate → format → verify all sections present."""
        now = datetime.now()
        this_week_ts = now.timestamp() * 1000
        yesterday = (now - timedelta(days=1)).isoformat() + "Z"

        mock_joplin = MagicMock()
        mock_joplin._make_request.return_value = [
            {"id": "n1", "title": "Project Plan", "parent_id": "f1",
             "created_time": this_week_ts, "updated_time": this_week_ts,
             "tags": "work"},
            {"id": "n2", "title": "Meeting Notes", "parent_id": "f2",
             "created_time": this_week_ts, "updated_time": this_week_ts,
             "tags": "meetings"},
        ]
        mock_joplin.get_folders.return_value = [
            {"id": "f1", "title": "Projects"},
            {"id": "f2", "title": "Meetings"},
        ]

        mock_tasks = MagicMock()
        mock_tasks.get_available_task_lists.return_value = [
            {"id": "list1", "title": "Tasks"}
        ]
        mock_tasks.get_user_tasks.return_value = [
            {"id": "t1", "title": "Review PR", "status": "completed",
             "completed": now.isoformat() + "Z"},
            {"id": "t2", "title": "Write docs", "status": "needsAction",
             "due": yesterday},
        ]

        gen = WeeklyReportGenerator(
            joplin_client=mock_joplin,
            task_service=mock_tasks,
        )
        report = await gen.generate_weekly_report(user_id=42)
        msg = gen.format_weekly_report(report)

        assert "WEEKLY REVIEW" in msg
        assert "PRODUCTIVITY SCORE" in msg
        assert "BY THE NUMBERS" in msg
        assert "Notes created: 2" in msg
        assert "Tasks completed: 1" in msg
        assert "Tasks overdue: 1" in msg or "OVERDUE TASKS" in msg
        assert "Project Plan" in msg or "Meeting Notes" in msg
        assert "RECOMMENDATIONS" in msg
        assert report.current.velocity == 3  # 2 notes + 1 completed task
        assert report.current.completion_rate > 0


class TestLogging:
    def test_log_weekly_report_calls_logging_service(self):
        mock_logging = MagicMock()
        gen = WeeklyReportGenerator(logging_service=mock_logging)

        report = WeeklyReportData(
            user_id=123,
            current=WeeklyMetrics(
                week_start=datetime(2026, 3, 2),
                week_end=datetime(2026, 3, 8),
                velocity=10,
                completion_rate=80.0,
                notes_created=5,
                tasks_completed=3,
                tasks_overdue=1,
            ),
        )
        gen._log_weekly_report(123, report)

        mock_logging.log_system_event.assert_called_once()
        call_kwargs = mock_logging.log_system_event.call_args
        assert call_kwargs[1]["level"] == "INFO"
        assert call_kwargs[1]["module"] == "weekly_report"
        assert "velocity" in call_kwargs[1]["extra_data"]
        assert call_kwargs[1]["extra_data"]["velocity"] == 10
