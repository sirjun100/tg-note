"""Sync Joplin REST API client for MCP. No dependency on telegram-joplin."""

from __future__ import annotations

import json
from urllib.parse import quote

import httpx


class JoplinError(Exception):
    """Raised when Joplin API returns an error (403, 404, 4xx)."""

    pass


def _items(result: dict | list) -> list:
    if isinstance(result, dict) and "items" in result:
        return result["items"]
    if isinstance(result, list):
        return result
    return []


class JoplinClient:
    """Sync client for Joplin Web Clipper API."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()

    def _url(self, endpoint: str) -> str:
        url = f"{self.base_url}{endpoint}"
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}token={self.token}"

    def _request(self, method: str, endpoint: str, **kwargs) -> dict | list | None:
        client = self._get_client()
        url = self._url(endpoint)
        try:
            resp = client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise JoplinError(f"Cannot connect to {self.base_url}") from exc
        if resp.status_code == 403:
            raise JoplinError("Joplin: invalid or expired token")
        if resp.status_code == 404:
            raise JoplinError("Not found")
        if resp.status_code >= 400:
            raise JoplinError(f"Joplin returned {resp.status_code}: {resp.text[:200]}")
        if resp.content:
            return resp.json()
        return None

    def _paginated_items(self, endpoint: str, max_items: int = 1000) -> list[dict]:
        page = 1
        items: list[dict] = []
        while len(items) < max_items:
            sep = "&" if "?" in endpoint else "?"
            result = self._request("GET", f"{endpoint}{sep}page={page}")
            page_items = _items(result) if result else []
            items.extend(page_items)
            if not isinstance(result, dict) or not result.get("has_more"):
                break
            page += 1
        return items[:max_items]

    # --- Folders ---

    def get_folders(self, parent_id: str | None = None) -> list[dict]:
        """List folders. If parent_id is set, filter by parent (empty string = root)."""
        all_folders = self._paginated_items("/folders")
        active = [f for f in all_folders if not (f.get("deleted_time") or 0)]
        if parent_id is not None:
            want = parent_id or ""
            active = [f for f in active if (f.get("parent_id") or "") == want]
        return active

    def get_folder(self, folder_id: str) -> dict:
        result = self._request("GET", f"/folders/{folder_id}")
        if result is None:
            raise JoplinError(f"Folder {folder_id} not found")
        return result

    def create_folder(self, title: str, parent_id: str | None = None) -> dict:
        payload = {"title": title}
        if parent_id:
            payload["parent_id"] = parent_id
        result = self._request("POST", "/folders", json=payload)
        if result is None:
            raise JoplinError(f"Failed to create folder '{title}'")
        return result

    # --- Notes (with offset/limit) ---

    def list_notes(
        self,
        folder_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int | None, bool]:
        """List notes in folder. Returns (items, next_offset, has_more)."""
        all_in_folder = self._paginated_items(f"/folders/{folder_id}/notes", max_items=offset + limit + 1)
        items = all_in_folder[offset : offset + limit]
        next_offset = offset + len(items) if len(all_in_folder) > offset + limit else None
        has_more = next_offset is not None
        return items, next_offset, has_more

    def get_note(self, note_id: str) -> dict:
        result = self._request("GET", f"/notes/{note_id}?fields=id,title,body,parent_id,updated_time")
        if result is None:
            raise JoplinError(f"Note {note_id} not found")
        return result

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int | None, bool]:
        """Full-text search. Returns (items, next_offset, has_more)."""
        if not (query or "").strip():
            return [], None, False
        # Joplin search has limit but no offset; we request more and slice
        request_limit = min(offset + limit + 1, 100)
        endpoint = f"/search?query={quote(query.strip())}&type=note&fields=id,title,body,parent_id,updated_time&limit={request_limit}"
        result = self._request("GET", endpoint)
        items_list = _items(result) if isinstance(result, dict) else []
        items = items_list[offset : offset + limit]
        next_offset = offset + len(items) if len(items_list) > offset + limit else None
        has_more = next_offset is not None
        return items, next_offset, has_more

    def create_note(
        self,
        folder_id: str,
        title: str,
        body: str,
        image_data_url: str | None = None,
    ) -> dict:
        payload = {"title": title, "body": body, "parent_id": folder_id}
        if image_data_url:
            payload["image_data_url"] = image_data_url
        result = self._request("POST", "/notes", json=payload)
        if result is None or "id" not in result:
            raise JoplinError(f"Failed to create note '{title}'")
        return result

    def update_note(self, note_id: str, updates: dict) -> None:
        self._request("PUT", f"/notes/{note_id}", json=updates)

    def delete_note(self, note_id: str) -> None:
        self._request("DELETE", f"/notes/{note_id}")

    def move_note(self, note_id: str, parent_id: str) -> None:
        self._request("PUT", f"/notes/{note_id}", json={"parent_id": parent_id})
