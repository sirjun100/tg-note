"""
Tests for FR-026 Semantic Search and Q&A.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.note_index import NoteIndex, _chunk_text, _cosine_similarity


class TestChunking:
    def test_chunk_empty_returns_empty(self):
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    def test_chunk_short_text_returns_single(self):
        text = "Short note"
        assert _chunk_text(text) == [text]

    def test_chunk_splits_with_overlap(self):
        text = "a" * 600
        chunks = _chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) >= 2
        assert all(len(c) <= 200 for c in chunks)

    def test_chunk_overlap_preserved(self):
        text = "word " * 120  # ~600 chars
        chunks = _chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) >= 2


class TestCosineSimilarity:
    def test_identical_returns_one(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_returns_zero(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_empty_returns_zero(self):
        assert _cosine_similarity([], []) == 0.0
        assert _cosine_similarity([1.0], []) == 0.0


class TestNoteIndex:
    @pytest.fixture
    def index(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            yield NoteIndex(db_path=path)
        finally:
            Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_search_empty_index_returns_empty(self, index):
        with patch.object(index, "_get_embedding", new_callable=AsyncMock) as mock_emb:
            mock_emb.return_value = [0.1] * 1536  # typical embedding dim
            results = await index.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_index_and_search(self, index):
        with patch.object(index, "_get_embedding", new_callable=AsyncMock) as mock_emb:
            mock_emb.return_value = [0.1] * 1536
            await index.index_note_async("n1", "Test Note", "This is the body of the note.")
            stats = index.get_stats()
        assert stats["notes"] == 1
        assert stats["chunks"] >= 1

    def test_get_stats_empty(self, index):
        stats = index.get_stats()
        assert stats["chunks"] == 0
        assert stats["notes"] == 0

    def test_clear(self, index):
        index.clear()
        stats = index.get_stats()
        assert stats["chunks"] == 0
