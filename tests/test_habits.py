"""Tests for Habit Tracking (FR-032)."""

from __future__ import annotations

import tempfile
import os
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.habit_service import (
    add_habit,
    calculate_longest_streak,
    calculate_streak,
    get_entries_for_habit,
    get_habits,
    get_stats,
    get_today_entries,
    log_entry,
    remove_habit,
    delete_today_entry,
)


@pytest.fixture
def temp_db():
    """Use a temporary database for habit tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        with patch("src.habit_service._get_db_path", return_value=path):
            yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


class TestHabitCRUD:
    def test_add_habit(self, temp_db):
        habit = add_habit(123, "Exercise")
        assert habit is not None
        assert habit["name"] == "Exercise"
        assert habit["user_id"] == 123
        assert "id" in habit

    def test_add_duplicate_returns_none(self, temp_db):
        add_habit(123, "Exercise")
        habit2 = add_habit(123, "Exercise")
        assert habit2 is None

    def test_remove_habit(self, temp_db):
        add_habit(123, "Exercise")
        ok = remove_habit(123, "exercise")
        assert ok is True
        habits = get_habits(123)
        assert len(habits) == 0

    def test_get_habits(self, temp_db):
        add_habit(123, "Exercise")
        add_habit(123, "Read")
        habits = get_habits(123)
        assert len(habits) == 2
        names = [h["name"] for h in habits]
        assert "Exercise" in names
        assert "Read" in names


class TestHabitEntries:
    def test_log_entry(self, temp_db):
        habit = add_habit(123, "Exercise")
        ok = log_entry(123, habit["id"], date.today(), completed=True)
        assert ok is True
        entries = get_today_entries(123, date.today())
        assert habit["id"] in entries
        assert entries[habit["id"]]["completed"] is True

    def test_log_entry_overwrite(self, temp_db):
        habit = add_habit(123, "Exercise")
        log_entry(123, habit["id"], date.today(), completed=True)
        log_entry(123, habit["id"], date.today(), completed=False)
        entries = get_today_entries(123, date.today())
        assert entries[habit["id"]]["completed"] is False

    def test_delete_today_entry(self, temp_db):
        habit = add_habit(123, "Exercise")
        log_entry(123, habit["id"], date.today(), completed=True)
        ok = delete_today_entry(123, habit["id"], date.today())
        assert ok is True
        entries = get_today_entries(123, date.today())
        assert habit["id"] not in entries


class TestStreakCalculation:
    def test_calculate_streak_continuous(self, temp_db):
        habit = add_habit(123, "Exercise")
        today = date.today()
        for i in range(5):
            d = today - timedelta(days=i)
            log_entry(123, habit["id"], d, completed=True)
        entries = get_entries_for_habit(123, habit["id"])
        streak = calculate_streak(entries, today)
        assert streak == 5

    def test_calculate_streak_broken(self, temp_db):
        habit = add_habit(123, "Exercise")
        today = date.today()
        log_entry(123, habit["id"], today, completed=True)
        log_entry(123, habit["id"], today - timedelta(days=1), completed=True)
        log_entry(123, habit["id"], today - timedelta(days=3), completed=True)  # gap
        entries = get_entries_for_habit(123, habit["id"])
        streak = calculate_streak(entries, today)
        assert streak == 2

    def test_calculate_streak_skip_breaks(self, temp_db):
        habit = add_habit(123, "Exercise")
        today = date.today()
        log_entry(123, habit["id"], today, completed=True)
        log_entry(123, habit["id"], today - timedelta(days=1), completed=False)  # skipped
        entries = get_entries_for_habit(123, habit["id"])
        streak = calculate_streak(entries, today)
        assert streak == 1

    def test_calculate_longest_streak(self, temp_db):
        habit = add_habit(123, "Exercise")
        today = date.today()
        for i in range(5):
            log_entry(123, habit["id"], today - timedelta(days=i), completed=True)
        log_entry(123, habit["id"], today - timedelta(days=3), completed=False)  # break in middle
        entries = get_entries_for_habit(123, habit["id"])
        longest = calculate_longest_streak(entries)
        assert longest >= 2
