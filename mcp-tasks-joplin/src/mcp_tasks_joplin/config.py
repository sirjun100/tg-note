"""Load config from env and optional config file. Env overrides file."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _find_config_path() -> Path | None:
    path = os.environ.get("MCP_CONFIG_PATH")
    if path:
        return Path(path)
    cwd = Path.cwd()
    for candidate in (cwd / "config.json", cwd / "mcp-tasks-joplin" / "config.json"):
        if candidate.exists():
            return candidate
    return None


def load_config() -> dict[str, Any]:
    """Load config: optional config file merged with env overrides."""
    out: dict[str, Any] = {
        "joplin": {
            "url": os.environ.get("JOPLIN_URL", ""),
            "token": os.environ.get("JOPLIN_TOKEN", ""),
            "request_timeout_seconds": 30,
            "ping_timeout_seconds": 5,
        },
        "google_tasks": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "token_json": os.environ.get("GOOGLE_TASKS_TOKEN_JSON"),
            "token_path": os.environ.get("GOOGLE_TASKS_TOKEN_PATH"),
            "default_list_id": None,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        },
        "semantic_search": {
            "enabled": False,
            "top_k_default": 8,
            "index_db_path": os.environ.get("MCP_NOTE_INDEX_DB_PATH"),
        },
        "pagination": {
            "default_limit": _DEFAULT_LIMIT,
            "max_limit": _MAX_LIMIT,
        },
    }

    config_path = _find_config_path()
    if config_path:
        try:
            with open(config_path, encoding="utf-8") as f:
                file_cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            file_cfg = {}

        if "joplin" in file_cfg:
            j = file_cfg["joplin"]
            out["joplin"]["request_timeout_seconds"] = j.get("request_timeout_seconds", out["joplin"]["request_timeout_seconds"])
            out["joplin"]["ping_timeout_seconds"] = j.get("ping_timeout_seconds", out["joplin"]["ping_timeout_seconds"])
            if "url" in j:
                out["joplin"]["url"] = out["joplin"]["url"] or j["url"]
            if "token" in j:
                out["joplin"]["token"] = out["joplin"]["token"] or j["token"]
        if "google_tasks" in file_cfg:
            g = file_cfg["google_tasks"]
            out["google_tasks"]["default_list_id"] = g.get("default_list_id")
            out["google_tasks"]["redirect_uri"] = g.get("redirect_uri", out["google_tasks"]["redirect_uri"])
        if "semantic_search" in file_cfg:
            s = file_cfg["semantic_search"]
            out["semantic_search"]["enabled"] = s.get("enabled", False)
            out["semantic_search"]["top_k_default"] = s.get("top_k_default", 8)
            if "index_db_path" in s:
                out["semantic_search"]["index_db_path"] = s["index_db_path"]
        if "pagination" in file_cfg:
            p = file_cfg["pagination"]
            out["pagination"]["default_limit"] = p.get("default_limit", _DEFAULT_LIMIT)
            out["pagination"]["max_limit"] = p.get("max_limit", _MAX_LIMIT)

    # Env overrides for secrets (again so env always wins)
    if os.environ.get("JOPLIN_URL"):
        out["joplin"]["url"] = os.environ["JOPLIN_URL"]
    if os.environ.get("JOPLIN_TOKEN"):
        out["joplin"]["token"] = os.environ["JOPLIN_TOKEN"]
    if os.environ.get("GOOGLE_CLIENT_ID"):
        out["google_tasks"]["client_id"] = os.environ["GOOGLE_CLIENT_ID"]
    if os.environ.get("GOOGLE_CLIENT_SECRET"):
        out["google_tasks"]["client_secret"] = os.environ["GOOGLE_CLIENT_SECRET"]
    if os.environ.get("GOOGLE_TASKS_TOKEN_JSON"):
        out["google_tasks"]["token_json"] = os.environ["GOOGLE_TASKS_TOKEN_JSON"]
    if os.environ.get("GOOGLE_TASKS_TOKEN_PATH"):
        out["google_tasks"]["token_path"] = os.environ["GOOGLE_TASKS_TOKEN_PATH"]

    return out


def get_pagination(config: dict[str, Any]) -> tuple[int, int]:
    """Return (default_limit, max_limit)."""
    p = config.get("pagination", {})
    return (
        int(p.get("default_limit", _DEFAULT_LIMIT)),
        int(p.get("max_limit", _MAX_LIMIT)),
    )
