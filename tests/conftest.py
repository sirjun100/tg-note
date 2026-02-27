"""Shared fixtures for all tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ALLOWED_TELEGRAM_USER_IDS", "12345")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")


@pytest.fixture()
def tmp_db(tmp_path: Path):
    """Yield a temporary SQLite path for state / log databases."""
    return str(tmp_path / "test.db")
