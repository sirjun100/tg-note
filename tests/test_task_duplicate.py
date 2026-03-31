#!/usr/bin/env python3
"""
Unit tests for US-055: Google Tasks duplicate check before add.

Covers: detect_duplicate_task(), _normalize_title_for_duplicate_check(),
duplicate-found flow, no-duplicate flow, cancel flow.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _make_task(title: str, task_id: str = "t1") -> dict:
    return {"id": task_id, "title": title, "status": "needsAction"}


class TestNormalizeTitleForDuplicateCheck:
    """Title normalization for duplicate detection."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        return TaskService(MagicMock(), MagicMock())

    def test_empty_returns_empty(self, service):
        assert service._normalize_title_for_duplicate_check("") == ""
        assert service._normalize_title_for_duplicate_check("   ") == ""

    def test_lowercase(self, service):
        assert service._normalize_title_for_duplicate_check("Call John") == "calljohn"

    def test_strips_punctuation(self, service):
        assert service._normalize_title_for_duplicate_check("Call John!") == "calljohn"
        assert service._normalize_title_for_duplicate_check("Buy milk, bread & eggs.") == "buymilkbreadeggs"

    def test_whitespace_removed(self, service):
        assert service._normalize_title_for_duplicate_check("  Call  John  ") == "calljohn"


class TestDetectDuplicateTaskNoMatch:
    """detect_duplicate_task returns None when no duplicate (note_index=None => string match)."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        svc.logging_service = logging_service
        svc.tasks_client = tasks_client
        return svc

    @pytest.mark.asyncio
    async def test_returns_none_when_no_token(self, service):
        service.logging_service.load_google_token.return_value = None
        assert await service.detect_duplicate_task("Call John", "123") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_task_list_id(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value=None)
        assert await service.detect_duplicate_task("Call John", "123") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_title(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.return_value = []
        assert await service.detect_duplicate_task("", "123") is None
        assert await service.detect_duplicate_task("   ", "123") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_tasks(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.return_value = []
        assert await service.detect_duplicate_task("Call John", "123") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.return_value = [
            _make_task("Buy groceries", "t1"),
            _make_task("Email Sarah", "t2"),
        ]
        assert await service.detect_duplicate_task("Call John", "123") is None


class TestDetectDuplicateTaskMatch:
    """detect_duplicate_task returns first matching task when duplicate exists (string match fallback)."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        svc.logging_service = logging_service
        svc.tasks_client = tasks_client
        return svc

    @pytest.mark.asyncio
    async def test_exact_match_returns_task(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        existing = _make_task("Call John", "t99")
        service.tasks_client.get_tasks.return_value = [
            _make_task("Buy groceries", "t1"),
            existing,
        ]
        result = await service.detect_duplicate_task("Call John", "123")
        assert result is not None
        assert result["id"] == "t99"
        assert result["title"] == "Call John"

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        existing = _make_task("Call John", "t1")
        service.tasks_client.get_tasks.return_value = [existing]
        assert await service.detect_duplicate_task("CALL JOHN", "123") is existing
        assert await service.detect_duplicate_task("call john", "123") is existing

    @pytest.mark.asyncio
    async def test_match_after_stripping_punctuation(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        existing = _make_task("Call John!", "t1")
        service.tasks_client.get_tasks.return_value = [existing]
        result = await service.detect_duplicate_task("Call John", "123")
        assert result is not None
        assert result["title"] == "Call John!"

    @pytest.mark.asyncio
    async def test_first_match_returned(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        first = _make_task("Call John", "t1")
        second = _make_task("call john", "t2")
        service.tasks_client.get_tasks.return_value = [first, second]
        result = await service.detect_duplicate_task("Call John", "123")
        assert result is not None
        assert result["id"] == "t1"


class TestDetectDuplicateTaskFetchError:
    """detect_duplicate_task returns None on fetch error."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        svc.logging_service = logging_service
        svc.tasks_client = tasks_client
        return svc

    @pytest.mark.asyncio
    async def test_returns_none_when_get_tasks_raises(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.side_effect = Exception("API error")
        assert await service.detect_duplicate_task("Call John", "123") is None


class TestFuzzyMatchScore:
    """US-055: Fuzzy token/sequence matching for semantically similar tasks."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        return TaskService(MagicMock(), MagicMock())

    def test_identical_titles_score_one(self, service):
        assert service._fuzzy_match_score("Call John", "Call John") >= 0.99

    def test_similar_sponsor_tasks(self, service):
        score = service._fuzzy_match_score(
            "fill out sponsor form",
            "I will try to fill out the sponsorship for my daughter",
        )
        assert score >= 0.50, f"Expected >= 0.50, got {score:.3f}"

    def test_partial_stem_match(self, service):
        score = service._fuzzy_match_score(
            "fill out sponsor form",
            "Send the sponsorship for Leanne",
        )
        assert score >= 0.30, f"Expected >= 0.30, got {score:.3f}"

    def test_unrelated_tasks_low_score(self, service):
        score = service._fuzzy_match_score(
            "fill out sponsor form",
            "Setup aquarium equipment and cycle water",
        )
        assert score < 0.40, f"Expected < 0.40, got {score:.3f}"

    def test_unrelated_scan_notes(self, service):
        score = service._fuzzy_match_score(
            "fill out sponsor form",
            "scan notes de Lilianne",
        )
        assert score < 0.40, f"Expected < 0.40, got {score:.3f}"


class TestDetectDuplicateTaskFuzzy:
    """detect_duplicate_task catches semantically similar tasks via fuzzy matching."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        svc.logging_service = logging_service
        svc.tasks_client = tasks_client
        return svc

    @pytest.mark.asyncio
    async def test_fuzzy_catches_sponsorship_duplicate(self, service):
        """The exact scenario from the user's bug report."""
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        sponsorship_task = _make_task(
            "I will try to fill out the sponsorship for my daughter", "t3"
        )
        service.tasks_client.get_tasks.return_value = [
            _make_task("scan notes de Lilianne", "t1"),
            _make_task("write a bravo for lucas", "t2"),
            sponsorship_task,
            _make_task("Setup aquarium equipment and cycle water", "t4"),
        ]
        result = await service.detect_duplicate_task(
            "fill out sponsor form", "123"
        )
        assert result is not None
        assert result["id"] == "t3"

    @pytest.mark.asyncio
    async def test_fuzzy_no_false_positive_unrelated(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.return_value = [
            _make_task("Buy groceries", "t1"),
            _make_task("Email Sarah about meeting", "t2"),
            _make_task("Research thermostat Sinope", "t3"),
        ]
        result = await service.detect_duplicate_task(
            "fill out sponsor form", "123"
        )
        assert result is None


class TestDetectDuplicateTaskSemantic:
    """detect_duplicate_task with note_index uses semantic similarity (Gemini embeddings)."""

    @pytest.fixture
    def service(self):
        from src.task_service import TaskService
        logging_service = MagicMock()
        tasks_client = MagicMock()
        svc = TaskService(tasks_client, logging_service)
        svc.logging_service = logging_service
        svc.tasks_client = tasks_client
        return svc

    @pytest.mark.asyncio
    async def test_semantic_match_returns_task(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        existing = _make_task("Call the dentist tomorrow", "t1")
        service.tasks_client.get_tasks.return_value = [
            _make_task("Buy groceries", "t0"),
            existing,
        ]
        note_index = MagicMock()
        note_index.find_most_similar_title = AsyncMock(return_value=(1, 0.94))
        result = await service.detect_duplicate_task(
            "Call dentist", "123", note_index=note_index
        )
        assert result is not None
        assert result["id"] == "t1"
        assert result["title"] == "Call the dentist tomorrow"

    @pytest.mark.asyncio
    async def test_semantic_below_threshold_returns_none(self, service):
        service.logging_service.load_google_token.return_value = {"access_token": "x"}
        service.get_task_list_id_for_user = MagicMock(return_value="tl1")
        service.tasks_client.get_tasks.return_value = [
            _make_task("Buy groceries", "t1"),
        ]
        note_index = MagicMock()
        note_index.find_most_similar_title = AsyncMock(return_value=None)
        result = await service.detect_duplicate_task(
            "Call dentist", "123", note_index=note_index
        )
        assert result is None
