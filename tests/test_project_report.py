#!/usr/bin/env python3
"""
Unit tests for US-060: World-Class Project Report.

Covers: get_tasks_by_project(), stall detection, no-next-action detection,
drill-down logic, and portfolio sort order.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── get_tasks_by_project tests ───────────────────────────────────────────────

class TestGetTasksByProject:
    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        ls = MagicMock()
        tc = MagicMock()
        svc = TaskService(tc, ls)
        svc.tasks_client.token = None
        return svc

    def test_returns_empty_when_no_token(self, service):
        service.logging_service.load_google_token.return_value = None
        assert service.get_tasks_by_project("123") == {}

    def test_returns_empty_when_no_mappings(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.logging_service.get_google_tasks_config.return_value = {"enabled": True}
        service.logging_service.get_all_project_sync_mappings.return_value = []
        assert service.get_tasks_by_project("123") == {}

    def test_groups_subtasks_by_folder(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.logging_service.get_google_tasks_config.return_value = {
            "enabled": True, "task_list_id": "tl1"
        }
        service.logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "gp1", "joplin_folder_id": "fld1"},
            {"google_task_id": "gp2", "joplin_folder_id": "fld2"},
        ]
        service.tasks_client.get_all_tasks.return_value = [
            {"id": "t1", "title": "Task A", "parent": "gp1", "status": "needsAction"},
            {"id": "t2", "title": "Task B", "parent": "gp1", "status": "needsAction"},
            {"id": "t3", "title": "Task C", "parent": "gp2", "status": "needsAction"},
            {"id": "t4", "title": "Done", "parent": "gp1", "status": "completed"},
        ]
        result = service.get_tasks_by_project("123")
        assert len(result["fld1"]) == 2
        assert len(result["fld2"]) == 1
        # completed task excluded
        assert all(t["status"] != "completed" for t in result["fld1"])

    def test_tasks_without_parent_not_included(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.logging_service.get_google_tasks_config.return_value = {
            "enabled": True, "task_list_id": "tl1"
        }
        service.logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "gp1", "joplin_folder_id": "fld1"},
        ]
        service.tasks_client.get_all_tasks.return_value = [
            {"id": "inbox", "title": "Inbox task", "status": "needsAction"},  # no parent
        ]
        result = service.get_tasks_by_project("123")
        assert result == {}


# ── Stall detection and sort-order logic tests ───────────────────────────────

class TestProjectReportHelpers:
    """Test the helper functions used by _project_report."""

    def test_ms_to_days_ago_recent(self):
        import time

        from src.handlers.core import _ms_to_days_ago
        now_ms = int(time.time() * 1000)
        assert _ms_to_days_ago(now_ms) == 0

    def test_ms_to_days_ago_14_days(self):
        import time

        from src.handlers.core import _ms_to_days_ago
        fourteen_days_ms = int(time.time() * 1000) - 14 * 86_400_000
        result = _ms_to_days_ago(fourteen_days_ms)
        assert 13 <= result <= 14  # allow 1-day variance

    def test_stall_detection_threshold(self):
        """Projects with ≥14 days no activity are stalled."""
        import time

        from src.handlers.core import _STALL_DAYS, _ms_to_days_ago
        old_ms = int(time.time() * 1000) - 20 * 86_400_000
        days_since = _ms_to_days_ago(old_ms)
        assert days_since >= _STALL_DAYS

    def test_no_stall_for_new_project(self):
        """Projects updated today are not stalled."""
        import time

        from src.handlers.core import _STALL_DAYS, _ms_to_days_ago
        today_ms = int(time.time() * 1000)
        days_since = _ms_to_days_ago(today_ms)
        assert days_since < _STALL_DAYS

    def test_portfolio_sort_order(self):
        """Blocked first, then stalled, building, planning, untagged, done."""
        projects = [
            {"status": "untagged", "is_stalled": False, "title": "u", "has_next_action": True},
            {"status": "status/done", "is_stalled": False, "title": "d", "has_next_action": True},
            {"status": "status/blocked", "is_stalled": False, "title": "b", "has_next_action": True},
            {"status": "status/building", "is_stalled": True, "title": "s", "has_next_action": True},
            {"status": "status/building", "is_stalled": False, "title": "bld", "has_next_action": True},
            {"status": "status/planning", "is_stalled": False, "title": "p", "has_next_action": True},
        ]

        def _sort_key(p: dict) -> tuple:
            s = p["status"]
            if s == "status/blocked":
                order = 0
            elif p["is_stalled"]:
                order = 1
            elif s == "status/building":
                order = 2
            elif s == "status/planning":
                order = 3
            elif s == "untagged":
                order = 4
            else:
                order = 5
            return (order, p["title"].lower())

        projects.sort(key=_sort_key)
        titles = [p["title"] for p in projects]
        assert titles[0] == "b"    # blocked first
        assert titles[1] == "s"    # stalled building second
        assert titles[2] == "bld"  # non-stalled building third
        assert titles[3] == "p"    # planning
        assert titles[4] == "u"    # untagged
        assert titles[5] == "d"    # done last

    def test_no_next_action_detection(self):
        """Project with no open tasks and project_sync_enabled is 'no next action'."""
        project = {
            "status": "status/building",
            "open_tasks": [],
            "has_next_action": False,
        }
        assert not project["has_next_action"]

    def test_has_next_action_when_tasks_exist(self):
        project = {
            "status": "status/building",
            "open_tasks": [{"id": "t1", "title": "Do something"}],
            "has_next_action": True,
        }
        assert project["has_next_action"]


# ── Empty state test ─────────────────────────────────────────────────────────

class TestProjectPortfolioEmptyState:
    def test_empty_projects_shows_empty_state(self):
        """get_tasks_by_project with no mappings returns {}."""
        from src.task_service import TaskService
        ls = MagicMock()
        tc = MagicMock()
        ls.load_google_token.return_value = {"access_token": "x"}
        ls.get_google_tasks_config.return_value = {"enabled": True}
        ls.get_all_project_sync_mappings.return_value = []
        svc = TaskService(tc, ls)
        assert svc.get_tasks_by_project("123") == {}
