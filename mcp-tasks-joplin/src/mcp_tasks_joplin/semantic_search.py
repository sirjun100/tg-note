"""Semantic search over note index. Stub: returns message if not configured or index missing."""

from __future__ import annotations

from pathlib import Path


def search(
    query: str,
    limit: int = 8,
    min_score: float | None = None,
    index_db_path: str | None = None,
) -> tuple[list[dict], str | None]:
    """
    Vector search over note chunks. Returns (results, error_message).
    If index not configured or DB missing, returns ([], "Semantic search not configured").
    """
    if not (index_db_path or "").strip():
        return [], "Semantic search not configured (set MCP_NOTE_INDEX_DB_PATH or config semantic_search.index_db_path)"
    path = Path(index_db_path)
    if not path.exists():
        return [], f"Note index not found at {index_db_path}. Run the index builder script first."
    # TODO: implement SQLite + embeddings lookup when enabled
    return [], "Semantic search not yet implemented (index path set but search not built)"
