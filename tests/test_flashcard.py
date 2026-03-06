"""Tests for flashcard service (FR-033)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.flashcard_service import (
    add_card,
    get_card_by_id,
    get_due_cards,
    get_stats,
    record_review,
)


@pytest.fixture
def flashcard_db():
    """Use a temp DB for flashcard tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        with patch("src.flashcard_service._get_db_path", return_value=path):
            from src.flashcard_service import _init_db

            _init_db()
            yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_add_card(flashcard_db):
    card = add_card(1, "note1", "What is 2+2?", "4")
    assert card["user_id"] == 1
    assert card["note_id"] == "note1"
    assert card["question"] == "What is 2+2?"
    assert card["answer"] == "4"
    assert "id" in card


def test_get_stats_empty(flashcard_db):
    stats = get_stats(1)
    assert stats["total"] == 0
    assert stats["due"] == 0


def test_get_stats_with_cards(flashcard_db):
    add_card(1, "n1", "Q1", "A1")
    add_card(1, "n1", "Q2", "A2")
    stats = get_stats(1)
    assert stats["total"] == 2
    assert stats["due"] == 2


def test_get_due_cards(flashcard_db):
    add_card(1, "n1", "Q1", "A1")
    add_card(1, "n1", "Q2", "A2")
    due = get_due_cards(1, limit=5)
    assert len(due) == 2
    assert due[0]["question"] == "Q1"
    assert due[0]["interval_days"] == 0


def test_record_review_schedules_next(flashcard_db):
    card = add_card(1, "n1", "Q1", "A1")
    record_review(1, card["id"], "good")
    stats = get_stats(1)
    assert stats["total"] == 1
    assert stats["due"] == 0  # Card scheduled for tomorrow


def test_get_card_by_id(flashcard_db):
    card = add_card(1, "n1", "Q", "A")
    found = get_card_by_id(card["id"], 1)
    assert found is not None
    assert found["question"] == "Q"
    assert get_card_by_id("nonexistent", 1) is None
