"""MCP tools: Google Tasks and Joplin. All tools return JSON-serializable dicts or strings for the LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .config import load_config, get_pagination
from .joplin_client import JoplinClient, JoplinError
from .tasks_client import TasksClient, TasksClientError
from .semantic_search import search as semantic_search_impl

mcp = FastMCP(name="Tasks and Joplin", version="0.1.0")

_config: dict[str, Any] | None = None
_joplin: JoplinClient | None = None
_tasks: TasksClient | None = None


def _get_config() -> dict[str, Any]:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def _get_joplin() -> JoplinClient:
    global _joplin
    if _joplin is None:
        cfg = _get_config()["joplin"]
        url = (cfg.get("url") or "").strip()
        token = (cfg.get("token") or "").strip()
        if not url or not token:
            raise ValueError("Joplin not configured: set JOPLIN_URL and JOPLIN_TOKEN")
        timeout = float(cfg.get("request_timeout_seconds", 30))
        _joplin = JoplinClient(base_url=url, token=token, timeout=timeout)
    return _joplin


def _get_tasks() -> TasksClient:
    global _tasks
    if _tasks is None:
        cfg = _get_config()["google_tasks"]
        cid = (cfg.get("client_id") or "").strip()
        secret = (cfg.get("client_secret") or "").strip()
        token_json = cfg.get("token_json")
        token_path = cfg.get("token_path")
        if not cid or not secret:
            raise ValueError("Google Tasks not configured: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
        token = None
        if token_json:
            token = json.loads(token_json) if isinstance(token_json, str) else token_json
        elif token_path:
            token = json.loads(Path(token_path).read_text(encoding="utf-8"))
        if not token:
            raise ValueError("Google Tasks token missing: set GOOGLE_TASKS_TOKEN_JSON or GOOGLE_TASKS_TOKEN_PATH")
        _tasks = TasksClient(
            client_id=cid,
            client_secret=secret,
            token=token,
            redirect_uri=cfg.get("redirect_uri", "urn:ietf:wg:oauth:2.0:oob"),
        )
    return _tasks


def _cap_limit(limit: int | None, default: int, max_limit: int) -> int:
    if limit is None:
        return default
    return min(max(1, int(limit)), max_limit)


# --- Tasks tools ---


@mcp.tool
def tasks_list_lists() -> str:
    """List all Google Tasks task lists. Returns JSON array of lists (id, title)."""
    try:
        client = _get_tasks()
        items = client.list_lists()
        return json.dumps([{"id": x.get("id"), "title": x.get("title")} for x in items])
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_list_tasks(
    task_list_id: str,
    show_completed: bool = True,
    show_hidden: bool = False,
    due_min: str | None = None,
    due_max: str | None = None,
    limit: int | None = None,
    page_token: str | None = None,
) -> str:
    """List tasks in a task list. Returns JSON with items and next_page_token if more results exist."""
    try:
        default_limit, max_limit = get_pagination(_get_config())
        limit = _cap_limit(limit, default_limit, max_limit)
        client = _get_tasks()
        items, next_token = client.list_tasks(
            task_list_id=task_list_id,
            show_completed=show_completed,
            show_hidden=show_hidden,
            max_results=limit,
            page_token=page_token,
            due_min=due_min,
            due_max=due_max,
        )
        out = {"items": items, "next_page_token": next_token}
        return json.dumps(out)
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_get_task(task_list_id: str, task_id: str) -> str:
    """Get a single task by id. Returns JSON task object."""
    try:
        client = _get_tasks()
        task = client.get_task(task_list_id, task_id)
        return json.dumps(task)
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_create(
    task_list_id: str,
    title: str,
    notes: str = "",
    due: str | None = None,
    status: str | None = None,
) -> str:
    """Create a new task. Returns JSON task object."""
    try:
        client = _get_tasks()
        task = client.create_task(task_list_id, title=title, notes=notes, due=due, status=status)
        return json.dumps(task)
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_update(
    task_list_id: str,
    task_id: str,
    title: str | None = None,
    notes: str | None = None,
    due: str | None = None,
    status: str | None = None,
) -> str:
    """Update a task (patch). Returns JSON task object."""
    try:
        client = _get_tasks()
        task = client.update_task(task_list_id, task_id, title=title, notes=notes, due=due, status=status)
        return json.dumps(task)
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_complete(task_list_id: str, task_id: str) -> str:
    """Mark a task as completed. Returns JSON task object."""
    try:
        client = _get_tasks()
        task = client.complete_task(task_list_id, task_id)
        return json.dumps(task)
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def tasks_delete(task_list_id: str, task_id: str) -> str:
    """Delete a task."""
    try:
        client = _get_tasks()
        client.delete_task(task_list_id, task_id)
        return "OK"
    except TasksClientError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


# --- Joplin structure and keyword ---


@mcp.tool
def joplin_list_folders(parent_id: str | None = None) -> str:
    """List Joplin notebooks/folders. Optional parent_id (empty = root). Returns JSON array."""
    try:
        client = _get_joplin()
        folders = client.get_folders(parent_id=parent_id or None)
        return json.dumps([{"id": f.get("id"), "title": f.get("title"), "parent_id": f.get("parent_id")} for f in folders])
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_get_folder(folder_id: str) -> str:
    """Get one folder by id. Returns JSON folder object."""
    try:
        client = _get_joplin()
        folder = client.get_folder(folder_id)
        return json.dumps(folder)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_list_notes(
    folder_id: str,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    """List notes in a folder. Returns JSON with items, next_offset, has_more."""
    try:
        default_limit, max_limit = get_pagination(_get_config())
        limit = _cap_limit(limit, default_limit, max_limit)
        client = _get_joplin()
        items, next_offset, has_more = client.list_notes(folder_id, limit=limit, offset=offset)
        out = {"items": items, "limit": limit, "offset": offset, "next_offset": next_offset, "has_more": has_more}
        return json.dumps(out)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_get_note(note_id: str) -> str:
    """Get full note (id, title, body, parent_id, etc.). Returns JSON."""
    try:
        client = _get_joplin()
        note = client.get_note(note_id)
        return json.dumps(note)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_search(
    query: str,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    """Full-text search in Joplin. Returns JSON with items, next_offset, has_more."""
    try:
        default_limit, max_limit = get_pagination(_get_config())
        limit = _cap_limit(limit, default_limit, max_limit)
        client = _get_joplin()
        items, next_offset, has_more = client.search(query, limit=limit, offset=offset)
        out = {"items": items, "limit": limit, "offset": offset, "next_offset": next_offset, "has_more": has_more}
        return json.dumps(out)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


# --- Joplin semantic search ---


@mcp.tool
def joplin_semantic_search(
    query: str,
    limit: int = 8,
    min_score: float | None = None,
) -> str:
    """Vector/semantic search over note chunks. Requires index to be built (see README)."""
    cfg = _get_config()
    index_path = cfg.get("semantic_search", {}).get("index_db_path") or ""
    top_k = int(cfg.get("semantic_search", {}).get("top_k_default", 8))
    limit = min(max(1, limit), 50)
    results, err = semantic_search_impl(query, limit=limit, min_score=min_score, index_db_path=index_path or None)
    if err:
        return f"Error: {err}"
    return json.dumps({"items": results})


# --- Joplin write ---


@mcp.tool
def joplin_create_note(
    folder_id: str,
    title: str,
    body: str,
    image_data_url: str | None = None,
) -> str:
    """Create a note in a folder. Returns JSON note (id, title, ...)."""
    try:
        client = _get_joplin()
        note = client.create_note(folder_id, title=title, body=body, image_data_url=image_data_url)
        return json.dumps(note)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_update_note(
    note_id: str,
    title: str | None = None,
    body: str | None = None,
    parent_id: str | None = None,
) -> str:
    """Update a note (partial). Pass only fields to change. Returns OK or error."""
    try:
        client = _get_joplin()
        updates = {}
        if title is not None:
            updates["title"] = title
        if body is not None:
            updates["body"] = body
        if parent_id is not None:
            updates["parent_id"] = parent_id
        if not updates:
            return "OK (no changes)"
        client.update_note(note_id, updates)
        return "OK"
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_delete_note(note_id: str) -> str:
    """Delete a note."""
    try:
        client = _get_joplin()
        client.delete_note(note_id)
        return "OK"
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_move_note(note_id: str, parent_id: str) -> str:
    """Move a note to another folder."""
    try:
        client = _get_joplin()
        client.move_note(note_id, parent_id)
        return "OK"
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool
def joplin_create_folder(title: str, parent_id: str | None = None) -> str:
    """Create a notebook/folder. Returns JSON folder object."""
    try:
        client = _get_joplin()
        folder = client.create_folder(title, parent_id=parent_id)
        return json.dumps(folder)
    except JoplinError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Error: {e}"
