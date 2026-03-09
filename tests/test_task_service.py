#!/usr/bin/env python3
"""
Unit tests for TaskService (US-034 project sync).

Covers get_or_create_project_parent_task: create, reuse, rename detection.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


class TestGetOrCreateProjectParentTask:
    """Unit tests for get_or_create_project_parent_task (FR-034)."""

    @pytest.fixture
    def logging_service(self):
        """Mock LoggingService for asserting calls."""
        mock = MagicMock()
        mock.get_project_sync_mapping = MagicMock(return_value=None)
        mock.load_google_token = MagicMock(return_value=None)
        mock.save_project_sync_mapping = MagicMock()
        return mock

    @pytest.fixture
    def tasks_client(self):
        from src.google_tasks_client import GoogleTasksClient

        return GoogleTasksClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost",
        )

    @pytest.fixture
    def task_service(self, tasks_client, logging_service):
        from src.task_service import TaskService

        return TaskService(tasks_client, logging_service)

    def test_create_first_call_creates_parent_task_in_google_tasks(
        self, task_service, tasks_client, logging_service
    ):
        """First call with no mapping creates parent task in Google Tasks."""
        user_id = "123"
        folder_id = "folder_abc"
        folder_title = "My Project"
        task_list_id = "list_xyz"

        logging_service.get_project_sync_mapping.return_value = None
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token
        task_service._set_client_token(user_id, token)

        created_task = {"id": "google_task_1", "title": folder_title}
        tasks_client.create_task = MagicMock(return_value=created_task)

        result = task_service.get_or_create_project_parent_task(
            user_id, folder_id, folder_title, task_list_id
        )

        assert result == "google_task_1"
        tasks_client.create_task.assert_called_once_with(
            title=folder_title,
            notes=f"Joplin project: {folder_title}",
            task_list_id=task_list_id,
        )
        logging_service.save_project_sync_mapping.assert_called_once_with(
            user_id=int(user_id),
            joplin_folder_id=folder_id,
            joplin_folder_title=folder_title,
            google_task_id="google_task_1",
            google_task_list_id=task_list_id,
        )

    def test_reuse_second_call_with_same_folder_id_returns_existing_task_id(
        self, task_service, tasks_client, logging_service
    ):
        """Second call with same folder_id returns existing task_id without creating."""
        user_id = "456"
        folder_id = "folder_def"
        folder_title = "Existing Project"
        task_list_id = "list_abc"

        logging_service.get_project_sync_mapping.return_value = {
            "google_task_id": "existing_gt_123",
            "joplin_folder_title": folder_title,
        }

        tasks_client.create_task = MagicMock()

        result = task_service.get_or_create_project_parent_task(
            user_id, folder_id, folder_title, task_list_id
        )

        assert result == "existing_gt_123"
        tasks_client.create_task.assert_not_called()

    def test_rename_detection_folder_title_changed_updates_google_task_title(
        self, task_service, tasks_client, logging_service
    ):
        """When folder title changed in Joplin, updates Google Task title."""
        user_id = "789"
        folder_id = "folder_ghi"
        old_title = "Old Project Name"
        new_title = "Renamed Project"
        task_list_id = "list_def"

        logging_service.get_project_sync_mapping.return_value = {
            "google_task_id": "gt_456",
            "joplin_folder_title": old_title,
        }
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token
        task_service._set_client_token(user_id, token)

        tasks_client.update_task = MagicMock(return_value={"id": "gt_456", "title": new_title})
        tasks_client.create_task = MagicMock()

        result = task_service.get_or_create_project_parent_task(
            user_id, folder_id, new_title, task_list_id
        )

        assert result == "gt_456"
        tasks_client.create_task.assert_not_called()
        tasks_client.update_task.assert_called_once_with(
            "gt_456", task_list_id, {"title": new_title}
        )
        logging_service.save_project_sync_mapping.assert_called_once_with(
            user_id=int(user_id),
            joplin_folder_id=folder_id,
            joplin_folder_title=new_title,
            google_task_id="gt_456",
            google_task_list_id=task_list_id,
        )

    def test_returns_none_when_no_token_and_no_mapping(
        self, task_service, logging_service
    ):
        """Returns None when user has no token and no existing mapping."""
        user_id = "999"
        folder_id = "folder_jkl"
        folder_title = "No Token Project"
        task_list_id = "list_ghi"

        logging_service.get_project_sync_mapping.return_value = None
        logging_service.load_google_token.return_value = None

        result = task_service.get_or_create_project_parent_task(
            user_id, folder_id, folder_title, task_list_id
        )

        assert result is None

    def test_returns_existing_task_id_when_no_token_but_mapping_exists(
        self, task_service, logging_service
    ):
        """Returns existing google_task_id from mapping even when token is missing (reuse path)."""
        user_id = "111"
        folder_id = "folder_mno"
        folder_title = "Mapped Project"
        task_list_id = "list_jkl"

        logging_service.get_project_sync_mapping.return_value = {
            "google_task_id": "gt_from_mapping",
            "joplin_folder_title": folder_title,
        }

        result = task_service.get_or_create_project_parent_task(
            user_id, folder_id, folder_title, task_list_id
        )

        assert result == "gt_from_mapping"


class TestSyncProjectParentTasks:
    """Unit tests for sync_project_parent_tasks (FR-034)."""

    @pytest.fixture
    def logging_service(self):
        mock = MagicMock()
        mock.get_project_sync_mapping = MagicMock(return_value=None)
        mock.get_google_tasks_config = MagicMock(
            return_value={"task_list_id": "list_xyz", "project_sync_enabled": True}
        )
        mock.load_google_token = MagicMock(return_value=None)
        mock.save_project_sync_mapping = MagicMock()
        return mock

    @pytest.fixture
    def tasks_client(self):
        from src.google_tasks_client import GoogleTasksClient

        return GoogleTasksClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost",
        )

    @pytest.fixture
    def task_service(self, tasks_client, logging_service):
        from src.task_service import TaskService

        return TaskService(tasks_client, logging_service)

    def test_create_new_when_folder_has_no_mapping_creates_parent_and_saves_mapping(
        self, task_service, tasks_client, logging_service
    ):
        """When folder has no mapping, creates parent task in Google Tasks and saves mapping."""
        user_id = "123"
        project_folders = [("folder_abc", "My Project")]

        logging_service.get_project_sync_mapping.return_value = None
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token

        created_task = {"id": "google_task_1", "title": "My Project"}
        tasks_client.create_task = MagicMock(return_value=created_task)

        created, existing = task_service.sync_project_parent_tasks(user_id, project_folders)

        assert created == 1
        assert existing == 0
        tasks_client.create_task.assert_called_once_with(
            title="My Project",
            notes="Joplin project: My Project",
            task_list_id="list_xyz",
        )
        logging_service.save_project_sync_mapping.assert_called_once_with(
            user_id=int(user_id),
            joplin_folder_id="folder_abc",
            joplin_folder_title="My Project",
            google_task_id="google_task_1",
            google_task_list_id="list_xyz",
        )

    def test_skip_existing_when_folder_has_mapping_does_not_create_duplicate(
        self, task_service, tasks_client, logging_service
    ):
        """When folder already has mapping, does not create duplicate, returns without error."""
        user_id = "456"
        project_folders = [("folder_def", "Existing Project")]

        logging_service.get_project_sync_mapping.return_value = {
            "google_task_id": "existing_gt_123",
            "joplin_folder_title": "Existing Project",
        }
        tasks_client.create_task = MagicMock()

        created, existing = task_service.sync_project_parent_tasks(user_id, project_folders)

        assert created == 0
        assert existing == 1
        tasks_client.create_task.assert_not_called()
        logging_service.save_project_sync_mapping.assert_not_called()


class TestGetStalledProjectTitles:
    """Unit tests for get_stalled_project_titles (FR-034)."""

    @pytest.fixture
    def logging_service(self):
        mock = MagicMock()
        mock.get_google_tasks_config = MagicMock(
            return_value={"task_list_id": "list_xyz", "project_sync_enabled": True}
        )
        mock.get_all_project_sync_mappings = MagicMock(return_value=[])
        mock.load_google_token = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def tasks_client(self):
        from src.google_tasks_client import GoogleTasksClient

        return GoogleTasksClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost",
        )

    @pytest.fixture
    def task_service(self, tasks_client, logging_service):
        from src.task_service import TaskService

        return TaskService(tasks_client, logging_service)

    def test_empty_when_no_parent_tasks_returns_empty_list(
        self, task_service, logging_service
    ):
        """No parent tasks (no mappings) → returns empty list."""
        user_id = "123"
        logging_service.get_all_project_sync_mappings.return_value = []

        result = task_service.get_stalled_project_titles(user_id)

        assert result == []

    def test_empty_when_all_parents_have_subtasks_returns_empty_list(
        self, task_service, tasks_client, logging_service
    ):
        """All parent tasks have incomplete subtasks → returns empty list."""
        user_id = "456"
        logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "gt_1", "joplin_folder_title": "Project A"},
            {"google_task_id": "gt_2", "joplin_folder_title": "Project B"},
        ]
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token
        # Tasks with parent=gt_1 and parent=gt_2 → both parents have subtasks
        tasks_client.get_all_tasks = MagicMock(
            return_value=[
                {"id": "sub1", "parent": "gt_1", "title": "Subtask 1"},
                {"id": "sub2", "parent": "gt_2", "title": "Subtask 2"},
            ]
        )

        result = task_service.get_stalled_project_titles(user_id)

        assert result == []

    def test_returns_titles_when_parents_have_zero_subtasks(
        self, task_service, tasks_client, logging_service
    ):
        """Parent tasks with zero subtasks (or all completed) → returns their titles."""
        user_id = "789"
        logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "gt_stalled_1", "joplin_folder_title": "Stalled Project A"},
            {"google_task_id": "gt_stalled_2", "joplin_folder_title": "Stalled Project B"},
        ]
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token
        # No tasks, or no tasks with parent=gt_stalled_1/gt_stalled_2
        tasks_client.get_all_tasks = MagicMock(return_value=[])

        result = task_service.get_stalled_project_titles(user_id)

        assert set(result) == {"Stalled Project A", "Stalled Project B"}

    def test_returns_only_stalled_titles_mixed_parents(
        self, task_service, tasks_client, logging_service
    ):
        """Mixed: some parents have subtasks, some don't → returns only stalled titles."""
        user_id = "999"
        logging_service.get_all_project_sync_mappings.return_value = [
            {"google_task_id": "gt_has_sub", "joplin_folder_title": "Has Subtasks"},
            {"google_task_id": "gt_stalled", "joplin_folder_title": "Stalled Only"},
        ]
        token = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        logging_service.load_google_token.return_value = token
        # Only gt_has_sub has a subtask
        tasks_client.get_all_tasks = MagicMock(
            return_value=[{"id": "sub1", "parent": "gt_has_sub", "title": "Do something"}]
        )

        result = task_service.get_stalled_project_titles(user_id)

        assert result == ["Stalled Only"]


class TestCreateTasksFromDecisionWithParentFolder:
    """Unit tests for create_tasks_from_decision with parent_folder_id (FR-034)."""

    @pytest.fixture
    def logging_service(self):
        mock = MagicMock()
        mock.get_project_sync_mapping = MagicMock(return_value=None)
        mock.get_google_tasks_config = MagicMock(
            return_value={
                "enabled": True,
                "auto_create_tasks": True,
                "task_list_id": "list_xyz",
                "project_sync_enabled": True,
            }
        )
        mock.load_google_token = MagicMock(
            return_value={"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        )
        mock.save_project_sync_mapping = MagicMock()
        mock.create_task_link = MagicMock(return_value=1)
        mock.log_task_sync = MagicMock()
        return mock

    @pytest.fixture
    def tasks_client(self):
        from src.google_tasks_client import GoogleTasksClient

        return GoogleTasksClient(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost",
        )

    @pytest.fixture
    def task_service(self, tasks_client, logging_service):
        from src.task_service import TaskService

        return TaskService(tasks_client, logging_service)

    def test_with_parent_folder_id_creates_subtask_under_parent(
        self, task_service, tasks_client, logging_service
    ):
        """When parent_folder_id and parent_folder_title are provided with project_sync_enabled,
        created task is a subtask of the parent (parent_task_id passed to create_task)."""
        from src.logging_service import Decision

        user_id = "123"
        parent_folder_id = "folder_proj"
        parent_folder_title = "My Project"
        parent_google_task_id = "google_parent_123"

        logging_service.get_project_sync_mapping.return_value = {
            "google_task_id": parent_google_task_id,
            "joplin_folder_title": parent_folder_title,
        }
        task_service._set_client_token(user_id, logging_service.load_google_token.return_value)

        created_task = {"id": "google_subtask_1", "title": "Review proposal"}
        tasks_client.create_task = MagicMock(return_value=created_task)

        decision = Decision(
            user_id=int(user_id),
            status="SUCCESS",
            note_title="Meeting Notes",
            note_body="todo: Review proposal",
            joplin_note_id="note_1",
        )

        result = task_service.create_tasks_from_decision(
            decision,
            user_id,
            parent_folder_id=parent_folder_id,
            parent_folder_title=parent_folder_title,
        )

        assert len(result) == 1
        assert result[0]["id"] == "google_subtask_1"
        assert result[0]["title"] == "Review proposal"
        # Key assertion: create_task was called with parent_task_id (subtask under parent)
        tasks_client.create_task.assert_called_once()
        call_kwargs = tasks_client.create_task.call_args[1]
        assert call_kwargs.get("parent_task_id") == parent_google_task_id

    def test_without_parent_folder_id_creates_top_level_task(
        self, task_service, tasks_client, logging_service
    ):
        """When parent_folder_id is not provided, created task is top-level (no parent_task_id)."""
        from src.logging_service import Decision

        user_id = "456"
        task_service._set_client_token(user_id, logging_service.load_google_token.return_value)

        created_task = {"id": "google_task_1", "title": "Call client"}
        tasks_client.create_task = MagicMock(return_value=created_task)

        decision = Decision(
            user_id=int(user_id),
            status="SUCCESS",
            note_title="Quick note",
            note_body="todo: Call client",
        )

        result = task_service.create_tasks_from_decision(decision, user_id)

        assert len(result) == 1
        call_kwargs = tasks_client.create_task.call_args[1]
        assert call_kwargs.get("parent_task_id") is None
