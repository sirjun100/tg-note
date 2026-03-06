"""
Note index for semantic search (FR-026).

Chunks Joplin notes, embeds with OpenAI, stores in SQLite, supports cosine similarity search.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "text-embedding-004"  # Gemini
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
TOP_K_DEFAULT = 8


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class NoteIndex:
    """Manages vector embeddings for Joplin notes. FR-026."""

    def __init__(self, db_path: str | None = None) -> None:
        from src.settings import get_settings

        state_path = get_settings().database.state_db_path
        base = Path(state_path).parent if state_path else Path("data/bot")
        self.db_path = db_path or str(base / "note_index.db")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS note_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(note_id, chunk_index)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_note_embeddings_note_id ON note_embeddings(note_id)"
            )

    async def _get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """Get embedding vector from Gemini API (GEMINI_API_KEY)."""
        import httpx

        from src.settings import get_settings

        api_key = get_settings().google.gemini_api_key
        if not api_key or not api_key.strip():
            raise RuntimeError(
                "GEMINI_API_KEY not set. Semantic search requires Gemini embeddings. "
                "Add GEMINI_API_KEY to your .env file."
            )
        url = f"{GEMINI_BASE}/models/{EMBEDDING_MODEL}:embedContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": text[:8000]}]}],
            "taskType": task_type,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        emb = data.get("embedding") or {}
        values = emb.get("values")
        if not values:
            raise RuntimeError("Gemini embedding response missing 'embedding.values'")
        return values

    async def index_note_async(
        self, note_id: str, title: str, body: str
    ) -> int:
        """Index a single note. Returns number of chunks indexed."""
        chunks = _chunk_text(body or "")
        if not chunks:
            return 0
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM note_embeddings WHERE note_id = ?", (note_id,))
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self._get_embedding(chunk)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO note_embeddings
                        (note_id, title, chunk_index, chunk_text, embedding)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (note_id, title or "(Untitled)", i, chunk, json.dumps(embedding)),
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to embed chunk %d of note %s: %s", i, note_id, exc)
        return count

    async def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> list[dict[str, Any]]:
        """Find most similar note chunks. Returns list of {note_id, title, chunk_text, score}."""
        query_embedding = await self._get_embedding(query, task_type="RETRIEVAL_QUERY")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT note_id, title, chunk_index, chunk_text, embedding FROM note_embeddings"
            ).fetchall()
        if not rows:
            return []
        scored: list[tuple[dict, float]] = []
        for row in rows:
            emb = json.loads(row["embedding"])
            sim = _cosine_similarity(query_embedding, emb)
            scored.append(
                (
                    {
                        "note_id": row["note_id"],
                        "title": row["title"],
                        "chunk_text": row["chunk_text"],
                        "chunk_index": row["chunk_index"],
                    },
                    sim,
                )
            )
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        seen_notes: set[str] = set()
        for item, score in scored[: top_k * 2]:  # Allow more chunks, dedupe by note
            if item["note_id"] in seen_notes and len(results) >= top_k:
                continue
            seen_notes.add(item["note_id"])
            item["score"] = round(score, 4)
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    def get_stats(self) -> dict[str, Any]:
        """Return index statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM note_embeddings"
            ).fetchone()[0]
            notes = conn.execute(
                "SELECT COUNT(DISTINCT note_id) FROM note_embeddings"
            ).fetchone()[0]
            last = conn.execute(
                "SELECT MAX(created_at) FROM note_embeddings"
            ).fetchone()[0]
        return {
            "chunks": total,
            "notes": notes,
            "last_updated": last,
        }

    def clear(self) -> None:
        """Clear all embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM note_embeddings")
