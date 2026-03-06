"""
Flashcard service: CRUD, SM-2 scheduling, session logic.

Sprint 14 - FR-033.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.settings import get_settings

logger = logging.getLogger(__name__)

# SM-2 default parameters
INITIAL_EASINESS = 2.5
MIN_EASINESS = 1.3


def _get_db_path() -> str:
    return get_settings().database.state_db_path


def _init_db() -> None:
    """Create flashcard tables if they don't exist."""
    db_path = _get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            note_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_reviews (
            id TEXT PRIMARY KEY,
            card_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            rating TEXT NOT NULL,
            interval_days REAL NOT NULL,
            easiness_factor REAL NOT NULL,
            next_review DATE NOT NULL,
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES flashcards(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcard_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cards_shown INTEGER DEFAULT 0,
            cards_correct INTEGER DEFAULT 0,
            ended_at TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_card_reviews_user_next ON card_reviews(user_id, next_review)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_user ON flashcards(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_note ON flashcards(note_id)")
    conn.commit()
    conn.close()


_lock = threading.Lock()


def _with_conn(fn):
    """Run fn(conn) with a connection from the state DB."""
    with _lock:
        _init_db()
        conn = sqlite3.connect(_get_db_path())
        try:
            conn.row_factory = sqlite3.Row
            return fn(conn)
        finally:
            conn.close()


def _schedule_card(rating: str, interval: float, ef: float) -> tuple[float, float]:
    """SM-2 scheduling. Returns (new_interval_days, new_ef)."""
    # For new cards (interval 0), use initial intervals
    if interval <= 0:
        if rating == "again":
            return (1.0, max(MIN_EASINESS, ef - 0.2))
        if rating == "hard":
            return (1.2, max(MIN_EASINESS, ef - 0.15))
        if rating == "good":
            return (1.0, ef)  # 1 day for first "good"
        if rating == "easy":
            return (2.5, min(2.5, ef + 0.15))
        return (1.0, ef)

    if rating == "again":
        return (1.0, max(MIN_EASINESS, ef - 0.2))
    if rating == "hard":
        return (interval * 1.2, max(MIN_EASINESS, ef - 0.15))
    if rating == "good":
        return (interval * ef, ef)
    if rating == "easy":
        return (interval * ef * 1.3, min(2.5, ef + 0.15))
    return (interval * ef, ef)


def add_card(
    user_id: int,
    note_id: str,
    question: str,
    answer: str,
) -> dict[str, Any]:
    """Add a flashcard. Returns card dict."""
    card_id = str(uuid.uuid4())[:8]

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO flashcards (id, user_id, note_id, question, answer) VALUES (?, ?, ?, ?, ?)",
            (card_id, user_id, note_id, question.strip(), answer.strip()),
        )
        conn.commit()
        cursor.execute(
            "SELECT id, user_id, note_id, question, answer, created_at FROM flashcards WHERE id = ?",
            (card_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    return _with_conn(do)


def add_cards_from_note(
    user_id: int,
    note_id: str,
    note_title: str,
    pairs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Add multiple flashcards from a note. Returns list of cards."""
    cards = []
    for p in pairs:
        q = p.get("question", "").strip()
        a = p.get("answer", "").strip()
        if q and a:
            cards.append(add_card(user_id, note_id, q, a))
    return cards


def get_cards_for_user(user_id: int, note_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Get all cards for user, optionally filtered by note_ids."""
    def do(conn):
        cursor = conn.cursor()
        if note_ids:
            placeholders = ",".join("?" * len(note_ids))
            cursor.execute(
                f"SELECT id, user_id, note_id, question, answer, created_at FROM flashcards "
                f"WHERE user_id = ? AND note_id IN ({placeholders})",
                [user_id] + note_ids,
            )
        else:
            cursor.execute(
                "SELECT id, user_id, note_id, question, answer, created_at FROM flashcards WHERE user_id = ?",
                (user_id,),
            )
        return [dict(r) for r in cursor.fetchall()]

    return _with_conn(do)


def get_most_recent_review(card_id: str, user_id: int) -> dict[str, Any] | None:
    """Get the most recent review for a card."""
    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, card_id, user_id, rating, interval_days, easiness_factor, next_review, reviewed_at "
            "FROM card_reviews WHERE card_id = ? AND user_id = ? ORDER BY reviewed_at DESC LIMIT 1",
            (card_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    return _with_conn(do)


def get_due_cards(
    user_id: int,
    note_ids: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get cards due for review: new cards + cards with next_review <= today."""
    today = date.today().isoformat()

    def do(conn):
        cursor = conn.cursor()
        # Get cards that have no review
        cursor.execute(
            "SELECT id, user_id, note_id, question, answer, created_at FROM flashcards WHERE user_id = ?",
            (user_id,),
        )
        all_cards = [dict(r) for r in cursor.fetchall()]
        if note_ids:
            all_cards = [c for c in all_cards if c["note_id"] in note_ids]

        due = []
        for c in all_cards:
            cursor.execute(
                "SELECT interval_days, easiness_factor, next_review FROM card_reviews "
                "WHERE card_id = ? AND user_id = ? ORDER BY reviewed_at DESC LIMIT 1",
                (c["id"], user_id),
            )
            row = cursor.fetchone()
            if row is None:
                due.append({**c, "interval_days": 0, "easiness_factor": INITIAL_EASINESS})
            else:
                r = dict(row)
                if r["next_review"] and r["next_review"] <= today:
                    due.append({**c, **r})
            if len(due) >= limit:
                break
        return due[:limit]

    return _with_conn(do)


def record_review(
    user_id: int,
    card_id: str,
    rating: str,
) -> dict[str, Any]:
    """Record a review and return updated card state."""
    review_id = str(uuid.uuid4())[:8]
    prev = get_most_recent_review(card_id, user_id)
    interval = 0.0
    ef = INITIAL_EASINESS
    if prev:
        interval = prev["interval_days"]
        ef = prev["easiness_factor"]

    new_interval, new_ef = _schedule_card(rating, interval, ef)
    next_review = (date.today() + timedelta(days=new_interval)).isoformat()

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO card_reviews (id, card_id, user_id, rating, interval_days, easiness_factor, next_review) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (review_id, card_id, user_id, rating, new_interval, new_ef, next_review),
        )
        conn.commit()
        return {"interval_days": new_interval, "easiness_factor": new_ef, "next_review": next_review}

    return _with_conn(do)


def create_session(user_id: int) -> str:
    """Create a flashcard session. Returns session id."""
    session_id = str(uuid.uuid4())[:8]

    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO flashcard_sessions (id, user_id) VALUES (?, ?)",
            (session_id, user_id),
        )
        conn.commit()
        return session_id

    return _with_conn(do)


def update_session(session_id: str, cards_shown: int, cards_correct: int) -> None:
    """Update session stats and set ended_at."""
    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE flashcard_sessions SET cards_shown = ?, cards_correct = ?, ended_at = ? WHERE id = ?",
            (cards_shown, cards_correct, datetime.utcnow().isoformat(), session_id),
        )
        conn.commit()

    _with_conn(do)


def get_stats(user_id: int) -> dict[str, Any]:
    """Get flashcard stats: due count, total cards."""
    def do(conn):
        cursor = conn.cursor()
        today = date.today().isoformat()

        cursor.execute("SELECT COUNT(*) FROM flashcards WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]

        # New cards (never reviewed)
        cursor.execute(
            """
            SELECT COUNT(*) FROM flashcards f
            WHERE f.user_id = ?
              AND NOT EXISTS (SELECT 1 FROM card_reviews r WHERE r.card_id = f.id AND r.user_id = ?)
            """,
            (user_id, user_id),
        )
        new_count = cursor.fetchone()[0]

        # Reviewed cards due today
        cursor.execute(
            """
            SELECT COUNT(DISTINCT f.id) FROM flashcards f
            JOIN card_reviews r ON r.card_id = f.id AND r.user_id = f.user_id
            WHERE f.user_id = ? AND r.next_review <= ?
            """,
            (user_id, today),
        )
        reviewed_due = cursor.fetchone()[0]
        due_count = new_count + reviewed_due

        return {"total": total, "due": due_count}

    return _with_conn(do)


def get_card_by_id(card_id: str, user_id: int) -> dict[str, Any] | None:
    """Get a single card by id."""
    def do(conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, note_id, question, answer, created_at FROM flashcards WHERE id = ? AND user_id = ?",
            (card_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    return _with_conn(do)
