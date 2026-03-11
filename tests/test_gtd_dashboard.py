#!/usr/bin/env python3
"""
Unit tests for US-059: GTD Dashboard — get_dashboard_data() in TaskService.

Covers: overdue section, today section, this week, inbox count, empty state,
not-connected state, and next_task field for motivating empty state.
"""

import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytz

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Fixed reference date used across all tests to avoid UTC vs local drift
_TODAY = date(2026, 3, 10)
_TODAY_DT = datetime(_TODAY.year, _TODAY.month, _TODAY.day, 12, 0, 0, tzinfo=pytz.UTC)


def _make_task(title: str, due: str | None = None, status: str = "needsAction",
               task_id: str = "t1", parent: str | None = None) -> dict:
    t: dict = {"id": task_id, "title": title, "status": status}
    if due:
        t["due"] = due
    if parent:
        t["parent"] = parent
    return t


def _due(delta_days: int) -> str:
    """Return a due date string delta_days from the fixed reference date."""
    d = _TODAY + timedelta(days=delta_days)
    return f"{d.isoformat()}T00:00:00.000Z"


class TestGetDashboardDataNotConnected:
    """Dashboard returns None when Google Tasks is not set up."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        return TaskService(tasks_client, logging_service)

    def test_no_token_returns_none(self, service):
        service.logging_service.load_google_token.return_value = None
        assert service.get_dashboard_data("123") is None

    def test_no_config_returns_none(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.logging_service.get_google_tasks_config.return_value = None
        assert service.get_dashboard_data("123") is None

    def test_disabled_config_returns_none(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.logging_service.get_google_tasks_config.return_value = {"enabled": False}
        assert service.get_dashboard_data("123") is None


class TestGetDashboardDataClassification:
    """Overdue / today / this week / inbox classification."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        # Default setup: connected, task list "tl1"
        svc.logging_service.load_google_token.return_value = {"access_token": "x"}
        svc.logging_service.get_google_tasks_config.return_value = {
            "enabled": True, "task_list_id": "tl1", "task_list_name": "My Tasks"
        }
        svc.logging_service.get_all_project_sync_mappings.return_value = []
        svc.logging_service.get_sync_history.return_value = []
        svc.tasks_client.token = None
        return svc

    def test_overdue_task_classified(self, service):
        task = _make_task("Old task", due=_due(-3))
        service.tasks_client.get_all_tasks.return_value = [task]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert len(data["overdue"]) == 1
        assert data["overdue"][0]["title"] == "Old task"
        assert len(data["due_today"]) == 0
        assert len(data["due_week"]) == 0

    def test_due_today_classified(self, service):
        task = _make_task("Today task", due=_due(0))
        service.tasks_client.get_all_tasks.return_value = [task]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert len(data["due_today"]) == 1
        assert data["due_today"][0]["title"] == "Today task"
        assert len(data["overdue"]) == 0

    def test_due_this_week_classified(self, service):
        task = _make_task("Week task", due=_due(3))
        service.tasks_client.get_all_tasks.return_value = [task]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert len(data["due_week"]) == 1
        assert data["due_week"][0]["title"] == "Week task"

    def test_completed_task_excluded(self, service):
        task = _make_task("Done task", due=_due(-1), status="completed")
        service.tasks_client.get_all_tasks.return_value = [task]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert len(data["overdue"]) == 0

    def test_inbox_count_excludes_project_parents(self, service):
        proj_parent = _make_task("My Project", task_id="proj_parent_1")
        inbox_task = _make_task("Random task", task_id="inbox_task_1")
        subtask = _make_task("Subtask", task_id="sub_1", parent="proj_parent_1")
        service.tasks_client.get_all_tasks.return_value = [proj_parent, inbox_task, subtask]
        service.logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "proj_parent_1"}
        ]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        # Only inbox_task counts as inbox (proj_parent excluded, subtask has parent)
        assert data["inbox_count"] == 1

    def test_empty_state_all_clear(self, service):
        """No tasks at all → overdue=[], due_today=[], inbox_count=0."""
        service.tasks_client.get_all_tasks.return_value = []
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert data["overdue"] == []
        assert data["due_today"] == []
        assert data["due_week"] == []
        assert data["inbox_count"] == 0

    def test_next_task_populated_from_upcoming(self, service):
        """next_task is the earliest upcoming task with a due date."""
        soon = _make_task("Next thing", due=_due(2), task_id="t_next")
        later = _make_task("Later thing", due=_due(5), task_id="t_later")
        service.tasks_client.get_all_tasks.return_value = [later, soon]
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert data["next_task"] is not None
        assert data["next_task"]["title"] == "Next thing"

    def test_mixed_tasks_multi_bucket(self, service):
        """Multiple tasks classified into their correct buckets."""
        tasks = [
            _make_task("Old", due=_due(-5), task_id="old"),
            _make_task("Today", due=_due(0), task_id="tod"),
            _make_task("Week", due=_due(4), task_id="wk"),
            _make_task("No due", task_id="nd"),
        ]
        service.tasks_client.get_all_tasks.return_value = tasks
        with patch("src.timezone_utils.get_user_timezone_aware_now") as mock_now, \
             patch("src.timezone_utils.get_user_timezone", return_value="UTC"):
            mock_now.return_value = _TODAY_DT
            data = service.get_dashboard_data("123")
        assert data is not None
        assert len(data["overdue"]) == 1
        assert len(data["due_today"]) == 1
        assert len(data["due_week"]) == 1
        assert data["inbox_count"] == 4  # all 4 are top-level with no project parent
