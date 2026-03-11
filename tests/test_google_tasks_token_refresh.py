#!/usr/bin/env python3
"""
Tests for Google Tasks OAuth token refresh behavior.

- GoogleTasksClient.refresh_token() preserves refresh_token when Google's
  refresh response does not include it.
- TaskService persists the refreshed token after API calls that may have refreshed.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# GoogleTasksClient.refresh_token() preserves refresh_token
# ---------------------------------------------------------------------------


class TestGoogleTasksClientRefreshToken:
    """Test that refresh_token() preserves refresh_token when not in response."""

    def test_preserves_refresh_token_when_not_in_response(self):
        """Google's refresh response often only has access_token and expires_in.
        We must keep the previous refresh_token."""
        from src.google_tasks_client import GoogleTasksClient

        client = GoogleTasksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost",
        )
        original_token = {
            "access_token": "old_access_token",
            "refresh_token": "original_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        client.set_token(original_token)

        # Simulate Google's refresh response: no refresh_token
        new_response = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch.object(
            client.session,
            "refresh_token",
            return_value=new_response,
        ):
            result = client.refresh_token()

        assert result is not None
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "original_refresh_token"

    def test_uses_new_refresh_token_when_in_response(self):
        """If the refresh response does include refresh_token, use it."""
        from src.google_tasks_client import GoogleTasksClient

        client = GoogleTasksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost",
        )
        client.set_token({
            "access_token": "old",
            "refresh_token": "old_refresh",
            "token_type": "Bearer",
        })

        new_response = {
            "access_token": "new_at",
            "refresh_token": "new_refresh_from_google",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch.object(client.session, "refresh_token", return_value=new_response):
            result = client.refresh_token()

        assert result["refresh_token"] == "new_refresh_from_google"
        assert result["access_token"] == "new_at"

    def test_returns_none_when_no_session(self):
        """When session is None, refresh_token returns None."""
        from src.google_tasks_client import GoogleTasksClient

        client = GoogleTasksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost",
        )
        # Never call set_token, so session is None
        assert client.refresh_token() is None

    def test_returns_none_when_no_token(self):
        """When token is None, refresh_token returns None."""
        from src.google_tasks_client import GoogleTasksClient

        client = GoogleTasksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost",
        )
        client.set_token({"access_token": "x", "token_type": "Bearer"})
        # No refresh_token in token; then clear token to simulate "no token"
        client.token = None
        assert client.refresh_token() is None


# ---------------------------------------------------------------------------
# TaskService saves token when client refreshed it
# ---------------------------------------------------------------------------


class TestTaskServiceSavesRefreshedToken:
    """Test that TaskService persists the token after a refresh during API use."""

    def test_create_tasks_from_decision_saves_token_when_refreshed(self):
        """When create_tasks_from_decision runs and the client refreshes the token,
        we must save the new token so the DB has the new access_token."""
        from src.google_tasks_client import GoogleTasksClient
        from src.logging_service import LoggingService
        from src.task_service import TaskService

        user_id = "12345"
        original_token = {
            "access_token": "old_at",
            "refresh_token": "refresh_123",
            "token_type": "Bearer",
        }
        refreshed_token = {
            "access_token": "new_at",
            "refresh_token": "refresh_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            logging_service = LoggingService(db_path=db_path)
            logging_service.save_google_token(user_id, original_token)
            logging_service.save_google_tasks_config(
                int(user_id),
                {
                    "enabled": True,
                    "auto_create_tasks": True,
                    "task_list_id": "list_1",
                },
            )

            tasks_client = GoogleTasksClient(
                client_id="c", client_secret="s", redirect_uri="http://localhost"
            )
            task_service = TaskService(tasks_client, logging_service)

            decision = type("Decision", (), {
                "status": "SUCCESS",
                "joplin_note_id": "note_1",
                "note_title": "Test",
                "note_body": "todo: call mom",
                "tags": None,
            })()

            # Simulate: during create_task the client refreshes the token (as on 401)
            def create_task_mock(*args, **kwargs):
                tasks_client.token = refreshed_token.copy()
                return {"id": "task_1"}

            tasks_client.create_task = MagicMock(side_effect=create_task_mock)
            tasks_client.get_default_task_list = MagicMock(return_value="list_1")
            tasks_client.get_task_lists = MagicMock(
                return_value=[{"id": "list_1", "title": "My Tasks"}]
            )

            task_service.create_tasks_from_decision(decision, user_id)

            # Should have saved the refreshed token
            saved = logging_service.load_google_token(user_id)
            assert saved is not None
            assert saved.get("access_token") == "new_at"
            assert saved.get("refresh_token") == "refresh_123"
        finally:
            import contextlib
            with contextlib.suppress(OSError):
                os.unlink(db_path)

    def test_get_user_tasks_saves_token_when_refreshed(self):
        """When get_user_tasks triggers a refresh, the new token is saved."""
        from src.google_tasks_client import GoogleTasksClient
        from src.logging_service import LoggingService
        from src.task_service import TaskService

        user_id = "999"
        original = {"access_token": "old", "refresh_token": "r", "token_type": "Bearer"}
        refreshed = {"access_token": "new", "refresh_token": "r", "token_type": "Bearer"}

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            logging_service = LoggingService(db_path=db_path)
            logging_service.save_google_token(user_id, original)

            tasks_client = GoogleTasksClient(
                client_id="c", client_secret="s", redirect_uri="http://localhost"
            )
            tasks_client.set_token(original)
            call_count = [0]

            def get_tasks_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    tasks_client.token = refreshed.copy()
                return [{"id": "t1", "title": "Task 1"}]

            tasks_client.get_tasks = MagicMock(side_effect=get_tasks_side_effect)
            tasks_client.get_default_task_list = MagicMock(return_value="list_1")

            task_service = TaskService(tasks_client, logging_service)
            result = task_service.get_user_tasks(user_id)

            assert len(result) == 1
            saved = logging_service.load_google_token(user_id)
            assert saved is not None
            assert saved.get("access_token") == "new"
        finally:
            import contextlib
            with contextlib.suppress(OSError):
                os.unlink(db_path)

    def test_get_available_task_lists_saves_token_when_refreshed(self):
        """When get_available_task_lists triggers a refresh, the new token is saved."""
        from src.google_tasks_client import GoogleTasksClient
        from src.logging_service import LoggingService
        from src.task_service import TaskService

        user_id = "888"
        original = {"access_token": "old", "refresh_token": "r", "token_type": "Bearer"}
        refreshed = {"access_token": "new", "refresh_token": "r", "token_type": "Bearer"}

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            logging_service = LoggingService(db_path=db_path)
            logging_service.save_google_token(user_id, original)

            tasks_client = GoogleTasksClient(
                client_id="c", client_secret="s", redirect_uri="http://localhost"
            )
            tasks_client.set_token(original)
            def get_lists():
                tasks_client.token = refreshed.copy()
                return [{"id": "l1", "title": "List 1"}]

            tasks_client.get_task_lists = MagicMock(side_effect=get_lists)

            task_service = TaskService(tasks_client, logging_service)
            result = task_service.get_available_task_lists(user_id)

            assert len(result) == 1
            saved = logging_service.load_google_token(user_id)
            assert saved is not None
            assert saved.get("access_token") == "new"
        finally:
            import contextlib
            with contextlib.suppress(OSError):
                os.unlink(db_path)
