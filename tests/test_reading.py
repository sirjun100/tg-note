"""Tests for Read Later queue (FR-028)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.reading_service import (
    _build_note_body,
    _extract_key_points,
    _parse_domain,
    _parse_saved_at,
    add_to_queue,
    delete_from_queue,
    get_queue,
    get_stats,
    mark_as_read,
)


class TestReadingServiceHelpers:
    def test_parse_saved_at(self):
        body = "**Saved**: 2026-03-05 14:32\n**Status**: Unread"
        assert _parse_saved_at(body) == datetime(2026, 3, 5, 14, 32)

    def test_parse_saved_at_missing(self):
        assert _parse_saved_at("No date here") is None

    def test_parse_domain(self):
        body = "**Source**: https://example.com/article?q=1"
        assert _parse_domain(body) == "example.com"

    def test_parse_domain_www(self):
        body = "**Source**: https://www.techcrunch.com/post"
        assert _parse_domain(body) == "techcrunch.com"

    def test_build_note_body(self):
        body = _build_note_body(
            "https://example.com/a",
            "Test Article",
            "A short summary.",
            ["Point 1", "Point 2"],
            datetime(2026, 3, 5, 14, 30),
        )
        assert "# Test Article" in body
        assert "**Source**: https://example.com/a" in body
        assert "**Saved**: 2026-03-05 14:30" in body
        assert "**Status**: 📖 Unread" in body
        assert "## Summary" in body
        assert "A short summary." in body
        assert "## Key Points" in body
        assert "- Point 1" in body
        assert "*Saved via /readlater*" in body

    def test_extract_key_points_from_bullets(self):
        text = "- First point here with enough chars\n- Second point also long enough\n- Third point with sufficient length"
        result = _extract_key_points(text)
        assert "First point here with enough chars" in result
        assert "Second point also long enough" in result

    def test_extract_key_points_empty(self):
        assert _extract_key_points("") == []


@pytest.mark.asyncio
class TestAddToQueue:
    async def test_add_creates_note_and_tags(self):
        joplin = MagicMock()
        joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder123")
        joplin.get_notes_in_folder = AsyncMock(return_value=[])
        joplin.create_note = AsyncMock(return_value="note456")
        joplin.apply_tags = AsyncMock(return_value=True)

        with patch("src.reading_service.fetch_url_context", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "title": "Test Article",
                "description": "A summary",
                "extracted_text": "",
                "domain": "example.com",
            }
            result = await add_to_queue(joplin, "https://example.com/article", datetime.now(UTC))

        assert result["note_id"] == "note456"
        assert result["title"] == "Test Article"
        assert result["domain"] == "example.com"
        assert result.get("duplicate") is False
        joplin.create_note.assert_called_once()
        joplin.apply_tags.assert_called_once()
        call_args = joplin.apply_tags.call_args[0]
        assert "reading" in call_args[1]
        assert "reading/unread" in call_args[1]

    async def test_add_detects_duplicate(self):
        joplin = MagicMock()
        joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder123")
        joplin.get_notes_in_folder = AsyncMock(
            return_value=[
                {
                    "id": "existing",
                    "body": "**Source**: https://example.com/same\nOther content",
                }
            ]
        )

        result = await add_to_queue(joplin, "https://example.com/same", datetime.now(UTC))

        assert result["duplicate"] is True
        assert result["note_id"] == "existing"
        joplin.create_note.assert_not_called()


@pytest.mark.asyncio
class TestGetQueue:
    async def test_get_queue_returns_items(self):
        joplin = MagicMock()
        joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder123")
        joplin.get_notes_in_folder = AsyncMock(
            return_value=[
                {
                    "id": "n1",
                    "title": "Article 1",
                    "body": "**Source**: https://a.com\n**Saved**: 2026-03-05 10:00\n## Summary\nSummary 1",
                    "created_time": 1000,
                },
            ]
        )
        joplin.get_tag_id_by_name = AsyncMock(return_value="tag_unread")
        joplin.get_notes_with_tag = AsyncMock(return_value=[{"id": "n1"}])

        items, total = await get_queue(joplin, unread_only=True, page=1)

        assert total == 1
        assert len(items) == 1
        assert items[0]["title"] == "Article 1"
        assert items[0]["domain"] == "a.com"
        assert items[0]["id"] == "n1"


@pytest.mark.asyncio
class TestMarkAsRead:
    async def test_mark_as_read_updates_body_and_tags(self):
        joplin = MagicMock()
        joplin.get_note = AsyncMock(
            return_value={"body": "**Status**: 📖 Unread\nRest of note"}
        )
        joplin.update_note = AsyncMock()
        joplin.apply_tags = AsyncMock()
        joplin.get_tag_id_by_name = AsyncMock(return_value="tag_unread")
        joplin.unlink_tag_from_note = AsyncMock(return_value=True)

        ok = await mark_as_read(joplin, "note123")

        assert ok is True
        joplin.update_note.assert_called_once()
        updates = joplin.update_note.call_args[0][1]
        body = updates["body"]
        assert "**Status**: ✅ Read" in body
        assert "📖 Unread" not in body


@pytest.mark.asyncio
class TestDeleteFromQueue:
    async def test_delete_calls_joplin(self):
        joplin = MagicMock()
        joplin.delete_note = AsyncMock()

        ok = await delete_from_queue(joplin, "note123")

        assert ok is True
        joplin.delete_note.assert_called_once_with("note123")


@pytest.mark.asyncio
class TestGetStats:
    async def test_get_stats_counts_unread(self):
        joplin = MagicMock()
        joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder123")
        joplin.get_notes_in_folder = AsyncMock(
            return_value=[
                {"id": "n1"},
                {"id": "n2"},
                {"id": "n3"},
            ]
        )
        joplin.get_tag_id_by_name = AsyncMock(return_value="tag_unread")
        joplin.get_notes_with_tag = AsyncMock(return_value=[{"id": "n1"}, {"id": "n2"}])

        stats = await get_stats(joplin)

        assert stats["total"] == 3
        assert stats["unread"] == 2
        assert stats["read"] == 1
