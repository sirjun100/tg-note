"""
Habit tracking service: CRUD, streak calculation, stats.

Sprint 11 Story 4 - FR-032.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.settings import get_settings

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    return get_settings().database.state_db_path


def _init_db() -> None:
    """Create habits tables if they don't exist."""
    db_path = _get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            UNIQUE(user_id, name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_entries (
            id TEXT PRIMARY KEY,
            habit_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits(id),
            UNIQUE(habit_id, date)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_habit_entries_user_date ON habit_entries(user_id, date)"
    )
    conn.commit()
    conn.close()


_lock = threading.Lock()


def _with_conn(fn):
    """Run fn(conn) with a connection from the habits DB."""
    with _lock:
        _init_db()
        conn = sqlite3.connect(_get_db_path())
        try:
            conn.row_factory = sqlite3.Row
            return fn(conn)
        finally:
            conn.close()


def add_habit(user_id: int, name: str) -> dict[str, Any] | None:
    """Add a habit. Returns habit dict or None if duplicate."""
    name = name.strip()
    if not name:
        return None

    def do(conn):
        cursor = conn.cursor()
        habit_id = str(uuid.uuid4())[:8]
        try:
            cursor.execute(
                "INSERT INTO habits (id, user_id, name) VALUES (?, ?, ?)",
                (habit_id, user_id, name),
            )
            conn.commit()
            cursor.execute(
                "SELECT id, user_id, name, created_at, active FROM habits WHERE id = ?",
                (habit_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.IntegrityError:
            conn.rollback()
            return None

    return _with_conn(do)


def remove_habit(user_id: int, name: str) -> bool:
    """Remove a habit by name. Returns True if found and removed."""
    name = name.strip().lower()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM habits WHERE user_id = ? AND LOWER(name) = ?",
            (user_id, name),
        )
        conn.commit()
        return cursor.rowcount > 0

    return _with_conn(do)


def get_habits(user_id: int) -> list[dict[str, Any]]:
    """Get all active habits for user."""
    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, name, created_at, active FROM habits WHERE user_id = ? AND active = 1 ORDER BY name",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]

    return _with_conn(do)


def get_habit_by_id(user_id: int, habit_id: str) -> dict[str, Any] | None:
    """Get habit by id."""
    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, name, created_at, active FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    return _with_conn(do)


def get_habit_by_name(user_id: int, name: str) -> dict[str, Any] | None:
    """Get habit by name (case-insensitive)."""
    name = name.strip().lower()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, name, created_at, active FROM habits WHERE user_id = ? AND LOWER(name) = ?",
            (user_id, name),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    return _with_conn(do)


def log_entry(user_id: int, habit_id: str, entry_date: date, completed: bool) -> bool:
    """Log a habit entry. Returns True on success."""
    date_str = entry_date.isoformat()

    def do(conn):
        cursor = conn.cursor()
        entry_id = str(uuid.uuid4())[:8]
        try:
            cursor.execute(
                "INSERT INTO habit_entries (id, habit_id, user_id, date, completed) VALUES (?, ?, ?, ?, ?)",
                (entry_id, habit_id, user_id, date_str, 1 if completed else 0),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            cursor.execute(
                "UPDATE habit_entries SET completed = ?, logged_at = CURRENT_TIMESTAMP WHERE habit_id = ? AND date = ?",
                (1 if completed else 0, habit_id, date_str),
            )
            conn.commit()
            return cursor.rowcount > 0

    return _with_conn(do)


def delete_today_entry(user_id: int, habit_id: str, entry_date: date) -> bool:
    """Delete today's entry for a habit."""
    date_str = entry_date.isoformat()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM habit_entries WHERE habit_id = ? AND user_id = ? AND date = ?",
            (habit_id, user_id, date_str),
        )
        conn.commit()
        return cursor.rowcount > 0

    return _with_conn(do)


def get_entries_for_habit(user_id: int, habit_id: str, limit_days: int = 365) -> list[dict[str, Any]]:
    """Get entries for a habit, most recent first."""
    cutoff = (date.today() - timedelta(days=limit_days)).isoformat()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, habit_id, user_id, date, completed, logged_at FROM habit_entries WHERE habit_id = ? AND user_id = ? AND date >= ? ORDER BY date DESC",
            (habit_id, user_id, cutoff),
        )
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            d["completed"] = bool(d.get("completed", 0))
            rows.append(d)
        return rows

    return _with_conn(do)


def get_today_entries(user_id: int, today: date) -> dict[str, dict[str, Any]]:
    """Get today's entries keyed by habit_id."""
    date_str = today.isoformat()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, habit_id, user_id, date, completed, logged_at FROM habit_entries WHERE user_id = ? AND date = ?",
            (user_id, date_str),
        )
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            d = dict(r)
            d["completed"] = bool(d.get("completed", 0))
            result[d["habit_id"]] = d
        return result

    return _with_conn(do)


def calculate_streak(entries: list[dict[str, Any]], today: date) -> int:
    """
    Calculate current streak. Entries should be sorted by date descending.
    Streak = consecutive days (including today) with completed=True.
    """
    if not entries:
        return 0
    by_date = {e["date"]: e for e in entries}
    streak = 0
    d = today
    while True:
        d_str = d.isoformat()
        if d_str not in by_date:
            break
        if not by_date[d_str].get("completed", False):
            break
        streak += 1
        d -= timedelta(days=1)
    return streak


def calculate_longest_streak(entries: list[dict[str, Any]]) -> int:
    """Calculate longest streak from entries (sorted by date desc)."""
    if not entries:
        return 0
    completed_dates = sorted(
        {e["date"] for e in entries if e.get("completed", False)},
        reverse=True,
    )
    if not completed_dates:
        return 0
    longest = 1
    current = 1
    for i in range(1, len(completed_dates)):
        prev = date.fromisoformat(completed_dates[i - 1])
        curr = date.fromisoformat(completed_dates[i])
        if (prev - curr).days == 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    return max(longest, current)


def get_stats(user_id: int, today: date) -> list[dict[str, Any]]:
    """Get stats for all habits: streak, longest, last 7/30 days, completion rate."""
    habits = get_habits(user_id)
    result = []
    for h in habits:
        entries = get_entries_for_habit(user_id, h["id"])
        current_streak = calculate_streak(entries, today)
        longest_streak = calculate_longest_streak(entries)

        entries_7 = [e for e in entries if (today - date.fromisoformat(e["date"])).days < 7]
        completed_7 = sum(1 for e in entries_7 if e.get("completed"))
        total_7 = 7

        entries_30 = [e for e in entries if (today - date.fromisoformat(e["date"])).days < 30]
        completed_30 = sum(1 for e in entries_30 if e.get("completed"))
        total_30 = 30

        result.append({
            "habit_id": h["id"],
            "name": h["name"],
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_7_days": completed_7,
            "total_7": total_7,
            "last_30_days": completed_30,
            "total_30": total_30,
            "completion_rate_7": (completed_7 / total_7 * 100) if total_7 else 0,
            "completion_rate_30": (completed_30 / total_30 * 100) if total_30 else 0,
        })
    return result
