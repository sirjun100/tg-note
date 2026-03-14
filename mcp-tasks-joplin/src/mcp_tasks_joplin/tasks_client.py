"""Google Tasks API client for MCP. Sync, with token load from JSON/path and refresh on 401."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from requests_oauthlib import OAuth2Session

BASE_URL = "https://www.googleapis.com/tasks/v1"
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = ["https://www.googleapis.com/auth/tasks"]


class TasksClientError(Exception):
    """Auth or API error from Google Tasks."""

    pass


def _load_token_from_json_string(data: str) -> dict[str, Any]:
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise TasksClientError(f"Invalid GOOGLE_TASKS_TOKEN_JSON: {e}") from e


def _load_token_from_file(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise TasksClientError(f"Token file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise TasksClientError(f"Failed to read token from {path}: {e}") from e


class TasksClient:
    """Sync Google Tasks API client. Token from env (JSON string or file path); auto-refresh on 401."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token: dict[str, Any] | None = None,
        token_path: str | None = None,
        token_json: str | None = None,
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token: dict[str, Any] | None = token
        self._session: OAuth2Session | None = None

        if self.token is None and token_json:
            self.token = _load_token_from_json_string(token_json)
        if self.token is None and token_path:
            self.token = _load_token_from_file(token_path)
        if self.token:
            self._ensure_session()

    def _ensure_session(self) -> None:
        if not self.token:
            return
        if "expires_in" not in self.token and "expires_at" not in self.token:
            self.token["expires_in"] = 3600
        self._session = OAuth2Session(
            client_id=self.client_id,
            token=self.token,
            auto_refresh_url=TOKEN_URL,
            auto_refresh_kwargs={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            token_updater=self._token_updater,
        )

    def _token_updater(self, new_token: dict[str, Any]) -> None:
        if self.token and self.token.get("refresh_token") and not new_token.get("refresh_token"):
            new_token = {**new_token, "refresh_token": self.token["refresh_token"]}
        self.token = new_token

    def is_authenticated(self) -> bool:
        return self._session is not None

    def list_lists(self) -> list[dict[str, Any]]:
        """List all task lists. Raises TasksClientError on auth failure."""
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        try:
            resp = self._session.get(f"{BASE_URL}/users/@me/lists")
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            resp.raise_for_status()
            return resp.json().get("items", [])
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e

    def list_tasks(
        self,
        task_list_id: str,
        show_completed: bool = True,
        show_hidden: bool = False,
        max_results: int = 20,
        page_token: str | None = None,
        due_min: str | None = None,
        due_max: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Returns (items, next_page_token)."""
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        params: dict[str, Any] = {
            "maxResults": max_results,
            "showCompleted": show_completed,
            "showHidden": show_hidden,
        }
        if page_token:
            params["pageToken"] = page_token
        if due_min:
            params["dueMin"] = due_min
        if due_max:
            params["dueMax"] = due_max
        try:
            resp = self._session.get(f"{BASE_URL}/lists/{task_list_id}/tasks", params=params)
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            if resp.status_code == 404:
                raise TasksClientError("Task list not found")
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", []), data.get("nextPageToken")
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e

    def get_task(self, task_list_id: str, task_id: str) -> dict[str, Any]:
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        try:
            resp = self._session.get(f"{BASE_URL}/lists/{task_list_id}/tasks/{task_id}")
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            if resp.status_code == 404:
                raise TasksClientError("Task not found")
            resp.raise_for_status()
            return resp.json()
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e

    def create_task(
        self,
        task_list_id: str,
        title: str,
        notes: str = "",
        due: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        payload: dict[str, Any] = {"title": title}
        if notes:
            payload["notes"] = notes
        if due:
            payload["due"] = due
        if status:
            payload["status"] = status
        try:
            resp = self._session.post(f"{BASE_URL}/lists/{task_list_id}/tasks", json=payload)
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            if resp.status_code == 404:
                raise TasksClientError("Task list not found")
            resp.raise_for_status()
            return resp.json()
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e

    def update_task(
        self,
        task_list_id: str,
        task_id: str,
        title: str | None = None,
        notes: str | None = None,
        due: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        updates: dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if notes is not None:
            updates["notes"] = notes
        if due is not None:
            updates["due"] = due
        if status is not None:
            updates["status"] = status
        if not updates:
            return self.get_task(task_list_id, task_id)
        try:
            resp = self._session.patch(f"{BASE_URL}/lists/{task_list_id}/tasks/{task_id}", json=updates)
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            if resp.status_code == 404:
                raise TasksClientError("Task not found")
            resp.raise_for_status()
            return resp.json()
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e

    def complete_task(self, task_list_id: str, task_id: str) -> dict[str, Any]:
        return self.update_task(task_list_id, task_id, status="completed")

    def delete_task(self, task_list_id: str, task_id: str) -> None:
        if not self._session:
            raise TasksClientError("Google Tasks: not authenticated (missing token)")
        try:
            resp = self._session.delete(f"{BASE_URL}/lists/{task_list_id}/tasks/{task_id}")
            if resp.status_code == 401:
                raise TasksClientError("Google Tasks: invalid or expired token")
            if resp.status_code == 404:
                raise TasksClientError("Task not found")
            resp.raise_for_status()
        except TasksClientError:
            raise
        except Exception as e:
            raise TasksClientError(f"Google Tasks: {e}") from e
