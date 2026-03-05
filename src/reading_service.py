"""
Read Later queue service.

Manages reading list notes in Joplin: add URLs, list queue, mark as read,
delete, random pick, stats. Uses URL enrichment for title/summary extraction.
Sprint 11 Story 2 - FR-028.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from src.url_enrichment import fetch_url_context

if TYPE_CHECKING:
    from src.joplin_client import JoplinClient

logger = logging.getLogger(__name__)

READING_FOLDER_PATH = ["03 - Resources", "📚 Reading List"]
TAG_READING = "reading"
TAG_UNREAD = "reading/unread"
TAG_READ = "reading/read"
_PAGE_SIZE = 5


def _parse_saved_at(body: str) -> datetime | None:
    """Parse **Saved**: YYYY-MM-DD HH:MM from note body."""
    import re
    m = re.search(r"\*\*Saved\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", body)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _parse_domain(body: str) -> str:
    """Parse **Source**: URL from note body and extract domain."""
    import re
    m = re.search(r"\*\*Source\*\*:\s*(https?://[^\s]+)", body)
    if not m:
        return ""
    parsed = urlparse(m.group(1).strip())
    domain = (parsed.netloc or "").replace("www.", "")
    return domain


def _build_note_body(url: str, title: str, summary: str, key_points: list[str], saved_at: datetime) -> str:
    """Build reading list note body per FR-028 spec."""
    saved_str = saved_at.strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {title}",
        "",
        f"**Source**: {url}",
        f"**Saved**: {saved_str}",
        "**Status**: 📖 Unread",
        "",
        "## Summary",
        summary or "(No summary available)",
        "",
    ]
    if key_points:
        lines.append("## Key Points")
        for p in key_points[:5]:
            if p and str(p).strip():
                lines.append(f"- {str(p).strip()}")
        lines.append("")
    lines.append("---")
    lines.append("*Saved via /readlater*")
    return "\n".join(lines)


def _extract_key_points(extracted_text: str, max_chars: int = 500) -> list[str]:
    """Extract first few sentences or bullet points as key points."""
    if not extracted_text or not extracted_text.strip():
        return []
    text = extracted_text.strip()[:max_chars]
    points: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("-") or line.startswith("*") or line.startswith("•"):
            line = line.lstrip("-*• ").strip()
        if len(line) > 20:
            points.append(line)
        if len(points) >= 5:
            break
    if not points and text:
        first_sentence = text.split(".")[0].strip()
        if first_sentence:
            points.append(first_sentence + ("." if not first_sentence.endswith(".") else ""))
    return points[:5]


async def add_to_queue(
    joplin: JoplinClient,
    url: str,
    saved_at: datetime,
) -> dict[str, Any]:
    """
    Add URL to reading queue. Fetches title/summary via URL enrichment.
    Returns dict with note_id, title, domain, error (if any).
    """
    folder_id = await joplin.get_or_create_folder_by_path(READING_FOLDER_PATH)

    # Check for duplicate URL
    notes = await joplin.get_notes_in_folder(folder_id)
    for n in notes:
        body = n.get("body") or ""
        if url in body and "**Source**:" in body:
            return {
                "note_id": n.get("id"),
                "title": n.get("title") or "Untitled",
                "domain": _parse_domain(body),
                "duplicate": True,
            }

    ctx = await fetch_url_context(url)
    title = (ctx.get("title") or "").strip() or "Untitled Article"
    description = (ctx.get("description") or "").strip()
    extracted = (ctx.get("extracted_text") or "").strip()
    summary = description or extracted[:300] or "(No summary available)"
    key_points = _extract_key_points(extracted)

    body = _build_note_body(url, title, summary, key_points, saved_at)
    note_id = await joplin.create_note(folder_id, title, body)
    await joplin.apply_tags(note_id, [TAG_READING, TAG_UNREAD])

    domain = ctx.get("domain") or urlparse(url).netloc or ""
    return {"note_id": note_id, "title": title, "domain": domain, "duplicate": False}


async def _get_reading_notes(joplin: JoplinClient, unread_only: bool) -> list[dict[str, Any]]:
    """Get notes in reading folder, optionally filtered by unread tag."""
    folder_id = await joplin.get_or_create_folder_by_path(READING_FOLDER_PATH)
    notes = await joplin.get_notes_in_folder(folder_id)

    if unread_only:
        unread_tag_id = await joplin.get_tag_id_by_name(TAG_UNREAD)
        if not unread_tag_id:
            return []
        unread_note_ids = {n["id"] for n in await joplin.get_notes_with_tag(unread_tag_id)}
        notes = [n for n in notes if n.get("id") in unread_note_ids]

    # Sort by created_time descending (most recent first)
    notes.sort(key=lambda n: int(n.get("created_time", 0) or 0), reverse=True)
    return notes


async def get_queue(
    joplin: JoplinClient,
    unread_only: bool = True,
    page: int = 1,
) -> tuple[list[dict[str, Any]], int]:
    """
    Get reading queue items. Returns (items_for_page, total_count).
    Each item has id, title, domain, summary, saved_at, body (truncated).
    """
    notes = await _get_reading_notes(joplin, unread_only)
    total = len(notes)
    items: list[dict[str, Any]] = []
    for n in notes[(page - 1) * _PAGE_SIZE : page * _PAGE_SIZE]:
        body = n.get("body") or ""
        summary = ""
        if "## Summary" in body:
            parts = body.split("## Summary", 1)[1].split("##", 1)[0].strip()
            summary = parts[:200] + ("..." if len(parts) > 200 else "")
        items.append({
            "id": n.get("id"),
            "title": n.get("title") or "Untitled",
            "domain": _parse_domain(body),
            "summary": summary or "(No summary)",
            "saved_at": _parse_saved_at(body),
        })
    return items, total


async def mark_as_read(joplin: JoplinClient, note_id: str) -> bool:
    """Mark note as read: update body status, swap tags."""
    try:
        note = await joplin.get_note(note_id)
    except Exception:
        return False
    body = note.get("body") or ""
    if "**Status**: 📖 Unread" in body:
        body = body.replace("**Status**: 📖 Unread", "**Status**: ✅ Read")
        await joplin.update_note(note_id, {"body": body})
    await joplin.apply_tags(note_id, [TAG_READING, TAG_READ])
    unread_tag_id = await joplin.get_tag_id_by_name(TAG_UNREAD)
    if unread_tag_id:
        await joplin.unlink_tag_from_note(unread_tag_id, note_id)
    return True


async def delete_from_queue(joplin: JoplinClient, note_id: str) -> bool:
    """Delete note from reading queue."""
    try:
        await joplin.delete_note(note_id)
        return True
    except Exception:
        return False


async def get_random_unread(joplin: JoplinClient) -> dict[str, Any] | None:
    """Pick a random unread item from the queue."""
    notes = await _get_reading_notes(joplin, unread_only=True)
    if not notes:
        return None
    n = random.choice(notes)
    body = n.get("body") or ""
    return {
        "id": n.get("id"),
        "title": n.get("title") or "Untitled",
        "domain": _parse_domain(body),
        "summary": "",
    }


async def get_stats(joplin: JoplinClient) -> dict[str, int]:
    """Return unread_count, read_count, total."""
    folder_id = await joplin.get_or_create_folder_by_path(READING_FOLDER_PATH)
    all_notes = await joplin.get_notes_in_folder(folder_id)
    unread_tag_id = await joplin.get_tag_id_by_name(TAG_UNREAD)
    unread_ids = set()
    if unread_tag_id:
        unread_notes = await joplin.get_notes_with_tag(unread_tag_id)
        unread_ids = {n["id"] for n in unread_notes}
    unread = sum(1 for n in all_notes if n.get("id") in unread_ids)
    return {"unread": unread, "total": len(all_notes), "read": len(all_notes) - unread}
