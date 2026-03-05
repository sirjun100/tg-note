"""
Async Joplin REST API Client.

Uses httpx for non-blocking HTTP and raises domain exceptions
instead of returning None on failure.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx

from src.constants import JOPLIN_PING_TIMEOUT, JOPLIN_REQUEST_TIMEOUT
from src.exceptions import JoplinAuthError, JoplinConnectionError, JoplinError
from src.settings import JoplinSettings, get_settings

logger = logging.getLogger(__name__)


class JoplinClient:
    """Async client for the Joplin Web Clipper API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        settings: JoplinSettings | None = None,
    ):
        cfg = settings or get_settings().joplin
        self.base_url = (base_url or cfg.url).rstrip("/")
        self.token = token or cfg.token
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle --

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=JOPLIN_REQUEST_TIMEOUT)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # -- low-level helpers --

    def _url(self, endpoint: str) -> str:
        url = f"{self.base_url}{endpoint}"
        if self.token:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}token={self.token}"
        return url

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        client = await self._get_client()
        url = self._url(endpoint)
        try:
            resp = await client.request(method, url, **kwargs)
        except httpx.ConnectError as exc:
            raise JoplinConnectionError(f"Cannot connect to {self.base_url}") from exc
        except httpx.TimeoutException as exc:
            raise JoplinConnectionError(f"Timeout connecting to {self.base_url}") from exc

        if resp.status_code == 403:
            raise JoplinAuthError()
        if resp.status_code >= 400:
            raise JoplinError(f"Joplin returned {resp.status_code}: {resp.text[:200]}")

        if resp.content:
            return resp.json()
        return None

    # -- health --

    async def ping(self) -> bool:
        client = await self._get_client()
        try:
            resp = await client.get(
                f"{self.base_url}/ping", timeout=JOPLIN_PING_TIMEOUT
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # -- notes --

    async def create_note(
        self,
        folder_id: str,
        title: str,
        body: str,
        image_data_url: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "parent_id": folder_id,
        }
        if image_data_url:
            payload["image_data_url"] = image_data_url
        result = await self._request("POST", "/notes", json=payload)
        if result and "id" in result:
            logger.info("Created note '%s' (%s)", title, result["id"])
            return result["id"]
        raise JoplinError(f"Failed to create note '{title}'")

    async def get_note(self, note_id: str) -> dict[str, Any]:
        # Explicitly request body field to ensure it's included in response
        result = await self._request("GET", f"/notes/{note_id}?fields=id,title,body,parent_id")
        if result is None:
            raise JoplinError(f"Note {note_id} not found")
        return result

    async def update_note(self, note_id: str, updates: dict[str, Any]) -> None:
        await self._request("PUT", f"/notes/{note_id}", json=updates)
        logger.info("Updated note %s", note_id)

    async def delete_note(self, note_id: str) -> None:
        await self._request("DELETE", f"/notes/{note_id}")
        logger.info("Deleted note %s", note_id)

    async def move_note(self, note_id: str, parent_id: str) -> None:
        await self._request("PUT", f"/notes/{note_id}", json={"parent_id": parent_id})

    async def get_all_notes(self, fields: str | None = None) -> list[dict[str, Any]]:
        endpoint = "/notes"
        if fields:
            endpoint = f"/notes?fields={fields}"
        return await self._paginated_items(endpoint)

    async def get_notes_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        return await self._paginated_items(f"/folders/{folder_id}/notes")

    # -- folders --

    async def get_folders(self) -> list[dict[str, Any]]:
        folders = await self._paginated_items("/folders")
        # Ignore soft-deleted folders; they can still be returned by API but
        # should not be considered valid destinations for new notes.
        active_folders: list[dict[str, Any]] = []
        for folder in folders:
            deleted_time = folder.get("deleted_time", 0) or 0
            if deleted_time:
                continue
            active_folders.append(folder)
        return active_folders

    async def get_folder(self, folder_id: str) -> dict[str, Any]:
        result = await self._request("GET", f"/folders/{folder_id}")
        if result is None:
            raise JoplinError(f"Folder {folder_id} not found")
        return result

    async def create_folder(
        self, title: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if parent_id:
            payload["parent_id"] = parent_id
        result = await self._request("POST", "/folders", json=payload)
        if result is None:
            raise JoplinError(f"Failed to create folder '{title}'")
        return result

    async def get_or_create_folder_by_path(self, path_parts: list[str]) -> str:
        current_parent = ""
        for part in path_parts:
            folders = await self.get_folders()
            # Normalize parent_id: Joplin may use None or "" for root
            want_parent = current_parent or ""
            found = next(
                (
                    f
                    for f in folders
                    if f.get("title") == part
                    and (f.get("parent_id") or "") == want_parent
                ),
                None,
            )
            if found:
                current_parent = found["id"]
            else:
                new = await self.create_folder(
                    part, parent_id=current_parent or None
                )
                current_parent = new["id"]
        return current_parent

    # -- tags --

    async def fetch_tags(self) -> list[dict[str, Any]]:
        tags = await self._paginated_items("/tags")
        logger.info("Fetched %d tags", len(tags))
        return tags

    async def get_notes_with_tag(self, tag_id: str) -> list[dict[str, Any]]:
        return await self._paginated_items(f"/tags/{tag_id}/notes")

    async def get_note_tags(self, note_id: str) -> list[dict[str, Any]]:
        """Return the list of tags attached to a note (each dict has at least 'id' and 'title')."""
        return await self._paginated_items(f"/notes/{note_id}/tags")

    async def get_tag_id_by_name(self, tag_name: str) -> str | None:
        """Return tag id if a tag with this name (case-insensitive) exists; else None. Does not create."""
        tags = await self.fetch_tags()
        for tag in tags:
            if self._tag_title_matches(tag, tag_name):
                return tag["id"]
        return None

    async def apply_tags(self, note_id: str, tag_names: list[str]) -> bool:
        success = True
        for name in tag_names:
            tag_id = await self._get_or_create_tag(name)
            if tag_id:
                if not await self._link_tag_to_note(tag_id, note_id):
                    success = False
            else:
                success = False
        return success

    async def apply_existing_tags_only(self, note_id: str, tag_names: list[str]) -> bool:
        """Apply only tags that already exist in Joplin (reuse, never create)."""
        if not tag_names:
            return True
        tags = await self.fetch_tags()
        success = True
        for name in tag_names:
            tag_id = None
            for tag in tags:
                if self._tag_title_matches(tag, name):
                    tag_id = tag["id"]
                    break
            if tag_id and not await self._link_tag_to_note(tag_id, note_id):
                success = False
        return success

    async def apply_tags_and_track_new(
        self, note_id: str, tag_names: list[str]
    ) -> dict[str, Any]:
        existing_titles = {t.get("title") for t in await self.fetch_tags()}
        new_tags: list[str] = []
        existing_tags: list[str] = []
        success = True

        for name in tag_names:
            is_new = name not in existing_titles
            tag_id = await self._get_or_create_tag(name)
            if tag_id:
                if not await self._link_tag_to_note(tag_id, note_id):
                    success = False
                (new_tags if is_new else existing_tags).append(name)
            else:
                success = False

        return {
            "success": success,
            "new_tags": new_tags,
            "existing_tags": existing_tags,
            "all_tags": tag_names,
        }

    async def rename_tag(self, tag_id: str, new_name: str) -> bool:
        result = await self._request(
            "PUT", f"/tags/{tag_id}", json={"title": new_name}
        )
        return result is not None

    def _tag_title_matches(self, tag: dict[str, Any], name: str) -> bool:
        """Match tag title to name case-insensitively (avoids duplicate 'AI' vs 'ai' etc.)."""
        t = (tag.get("title") or "").strip()
        n = (name or "").strip()
        return t.lower() == n.lower()

    async def _get_or_create_tag(self, tag_name: str) -> str | None:
        tags = await self.fetch_tags()
        for tag in tags:
            if self._tag_title_matches(tag, tag_name):
                return tag["id"]
        try:
            result = await self._request("POST", "/tags", json={"title": tag_name})
            if result and "id" in result:
                logger.info("Created tag '%s' (%s)", tag_name, result["id"])
                return result["id"]
        except JoplinError as exc:
            err = str(exc).lower()
            if "already exists" in err or "choose a different name" in err:
                # Tag exists but wasn't found (e.g. case/pagination); fetch again and use it
                tags = await self.fetch_tags()
                for tag in tags:
                    if self._tag_title_matches(tag, tag_name):
                        logger.debug("Using existing tag '%s' after create conflict", tag_name)
                        return tag["id"]
            raise  # re-raise if not "already exists" or tag still not found
        logger.error("Failed to create tag '%s'", tag_name)
        return None

    async def _link_tag_to_note(self, tag_id: str, note_id: str) -> bool:
        try:
            await self._request("POST", f"/tags/{tag_id}/notes", json={"id": note_id})
            return True
        except JoplinError:
            return False

    PROJECT_STATUS_TAG_NAMES = (
        "status/planning",
        "status/building",
        "status/blocked",
        "status/done",
    )

    async def ensure_project_status_tags(self) -> None:
        """Create the four project status tags in Joplin if they do not exist."""
        for name in self.PROJECT_STATUS_TAG_NAMES:
            try:
                await self._get_or_create_tag(name)
            except Exception as exc:
                logger.warning("Failed to ensure tag '%s': %s", name, exc)

    async def _paginated_items(self, endpoint: str) -> list[dict[str, Any]]:
        """
        Fetch all pages from a Joplin list endpoint.

        Joplin may paginate folders/tags with `has_more` and `page`.
        """
        page = 1
        items: list[dict[str, Any]] = []
        while True:
            sep = "&" if "?" in endpoint else "?"
            result = await self._request("GET", f"{endpoint}{sep}page={page}")
            page_items = _items(result)
            items.extend(page_items)
            if not isinstance(result, dict) or not result.get("has_more"):
                break
            page += 1
        return items

    # -- decision log --

    async def append_log(self, log_entry: str) -> bool:
        try:
            with open("joplin_config.json") as f:
                config = json.load(f)
                log_note_id = config.get("ai_decision_log_note_id")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("AI-Decision-Log note ID not found in config")
            return False

        if not log_note_id:
            return False

        note = await self.get_note(log_note_id)
        body = note.get("body", "")
        ts = datetime.now().isoformat()
        updated = f"{body}\n\n---\n**{ts}**\n{log_entry}\n"
        await self.update_note(log_note_id, {"body": updated})
        return True


def _items(result: Any) -> list:
    """Extract items list from Joplin's paginated or flat responses."""
    if isinstance(result, dict) and "items" in result:
        return result["items"]
    if isinstance(result, list):
        return result
    return []
