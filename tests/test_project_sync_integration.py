#!/usr/bin/env python3
"""
Integration test for US-034 project sync: project note + action → subtask under parent.

Uses real LoggingService (tmp DB), real TaskService; mocks only Google Tasks API.
Verifies that when a project note (folder with project sync mapping) triggers task creation,
the created task appears as a subtask under the project parent in Google Tasks.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


class TestProjectNoteActionSubtaskIntegration:
    """Integration test: project note + action → subtask under parent."""

    @pytest.fixture
    def tmp_db_path(self, tmp_path: Path) -> str:
        """Temporary SQLite database path."""
        return str(tmp_path / "integration_test.db")

    @pytest.fixture
    def logging_service(self, tmp_db_path: str):
        """Real LoggingService with tmp DB."""
        from src.logging_service import LoggingService

        return LoggingService(db_path=tmp_db_path)

    @pytest.fixture
    def tasks_client(self):
        """GoogleTasksClient with mocked create_task (no real API calls)."""
        from src.google_tasks_client import GoogleTasksClient

        client = GoogleTasksClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost",
        )
        return client

    @pytest.fixture
    def task_service(self, tasks_client, logging_service):
        """Real TaskService with mocked Google API client."""
        from src.task_service import TaskService

        return TaskService(tasks_client, logging_service)

    def test_project_note_action_creates_subtask_under_parent(
        self, task_service, tasks_client, logging_service, tmp_db_path
    ):
        """Project note (folder with sync mapping) + action → task created as subtask under parent."""
        from src.logging_service import Decision

        user_id = "999"
        project_folder_id = "joplin_folder_proj_abc"
        project_folder_title = "Q1 Planning"
        google_parent_task_id = "gt_parent_xyz"
        task_list_id = "list_main"

        # Set up real DB: token, config with project_sync_enabled, project sync mapping
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.save_google_token(user_id, token)
        logging_service.save_google_tasks_config(
            int(user_id),
            {
                "enabled": True,
                "auto_create_tasks": True,
                "task_list_id": task_list_id,
                "project_sync_enabled": True,
            },
        )
        logging_service.save_project_sync_mapping(
            user_id=int(user_id),
            joplin_folder_id=project_folder_id,
            joplin_folder_title=project_folder_title,
            google_task_id=google_parent_task_id,
            google_task_list_id=task_list_id,
        )

        # Mock Google API: create_task returns the created subtask
        created_subtask = {"id": "gt_subtask_1", "title": "Review proposal", "parent": google_parent_task_id}
        tasks_client.create_task = MagicMock(return_value=created_subtask)

        # Decision from a note in the project folder (action item in body)
        decision = Decision(
            user_id=int(user_id),
            status="SUCCESS",
            folder_chosen=project_folder_id,
            note_title="Meeting Notes",
            note_body="todo: Review proposal",
            joplin_note_id="note_123",
        )

        # Process: create_tasks_from_decision with parent_folder_id (as braindump does)
        created = task_service.create_tasks_from_decision(
            decision,
            user_id,
            parent_folder_id=project_folder_id,
            parent_folder_title=project_folder_title,
        )

        assert len(created) == 1
        assert created[0]["id"] == "gt_subtask_1"
        assert created[0]["title"] == "Review proposal"

        # Key assertion: task was created as subtask under project parent (not top-level)
        tasks_client.create_task.assert_called_once()
        call_kwargs = tasks_client.create_task.call_args[1]
        assert call_kwargs.get("parent_task_id") == google_parent_task_id
        assert call_kwargs.get("title") == "Review proposal"
