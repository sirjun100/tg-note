"""Tests for Sprint 17 brain dump features: modes, time context, session recovery, prefs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.handlers import braindump as bd
from src.state_manager import InMemoryStateManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orch(user_id: int = 12345) -> MagicMock:
    orch = MagicMock()
    orch.state_manager = InMemoryStateManager()
    orch.logging_service = MagicMock()
    orch.logging_service.get_timezone_for_user = MagicMock(return_value=None)
    return orch


def _make_update(user_id: int = 12345, text: str = "/braindump") -> tuple[MagicMock, MagicMock]:
    user = MagicMock()
    user.id = user_id
    message = AsyncMock()
    message.reply_text = AsyncMock(return_value=AsyncMock())
    message.text = text
    update = MagicMock()
    update.effective_user = user
    update.message = message
    return update, message


# ---------------------------------------------------------------------------
# T-001: Mode parsing
# ---------------------------------------------------------------------------

def test_parse_mode_no_args():
    assert bd._parse_mode(None) == "standard"
    assert bd._parse_mode([]) == "standard"


def test_parse_mode_quick():
    assert bd._parse_mode(["quick"]) == "quick"


def test_parse_mode_thorough():
    assert bd._parse_mode(["thorough"]) == "thorough"


def test_parse_mode_case_insensitive():
    assert bd._parse_mode(["QUICK"]) == "quick"


def test_parse_mode_unknown_defaults_to_standard():
    assert bd._parse_mode(["ultrafast"]) == "standard"


@pytest.mark.asyncio
async def test_braindump_quick_mode_sets_state():
    """Quick mode sets session_mode=quick and target_minutes=5 in state."""
    orch = _make_orch()
    update, message = _make_update()

    context = MagicMock()
    context.args = ["quick"]

    with patch("src.handlers.braindump.check_whitelist", return_value=True), \
         patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        handler = bd._braindump(orch)
        await handler(update, context)

    state = orch.state_manager.get_state(12345)
    assert state is not None
    assert state["session_mode"] == "quick"
    assert state["target_minutes"] == 5
    assert state["active_persona"] == "GTD_EXPERT"


@pytest.mark.asyncio
async def test_braindump_thorough_mode_sets_state():
    """Thorough mode sets session_mode=thorough and target_minutes=25."""
    orch = _make_orch()
    update, message = _make_update()
    context = MagicMock()
    context.args = ["thorough"]

    with patch("src.handlers.braindump.check_whitelist", return_value=True), \
         patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        handler = bd._braindump(orch)
        await handler(update, context)

    state = orch.state_manager.get_state(12345)
    assert state["session_mode"] == "thorough"
    assert state["target_minutes"] == 25


@pytest.mark.asyncio
async def test_braindump_default_mode_is_standard():
    """No args → standard mode, target 15 min."""
    orch = _make_orch()
    update, message = _make_update()
    context = MagicMock()
    context.args = []

    with patch("src.handlers.braindump.check_whitelist", return_value=True), \
         patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        handler = bd._braindump(orch)
        await handler(update, context)

    state = orch.state_manager.get_state(12345)
    assert state["session_mode"] == "standard"
    assert state["target_minutes"] == 15


@pytest.mark.asyncio
async def test_braindump_startup_message_includes_mode_and_target():
    """Startup message includes mode label and target minutes."""
    orch = _make_orch()
    update, message = _make_update()
    context = MagicMock()
    context.args = ["quick"]

    with patch("src.handlers.braindump.check_whitelist", return_value=True), \
         patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        handler = bd._braindump(orch)
        await handler(update, context)

    message.reply_text.assert_called_once()
    text = message.reply_text.call_args[0][0]
    assert "QUICK" in text.upper()
    assert "5" in text


# ---------------------------------------------------------------------------
# T-002: Time/day-phase context injected into LLM message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_braindump_message_injects_context_line():
    """handle_braindump_message prepends [Session: ...] context to LLM message."""
    orch = _make_orch()
    session_start = datetime.now(UTC) - timedelta(minutes=3)
    orch.state_manager.update_state(12345, {
        "active_persona": "GTD_EXPERT",
        "session_mode": "standard",
        "target_minutes": 15,
        "session_start": session_start.isoformat(),
        "captured_items": ["item1", "item2"],
        "conversation_history": [],
    })

    message = AsyncMock()
    message.reply_text = AsyncMock()

    captured: list[str] = []

    llm_response = MagicMock()
    llm_response.status = "NEED_INFO"
    llm_response.question = "What else?"

    async def _capture_process_message(user_message, **kwargs):
        captured.append(user_message)
        return llm_response

    orch.llm_orchestrator.process_message = _capture_process_message

    with patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        await bd.handle_braindump_message(orch, 12345, "nothing much", message)

    assert captured, "process_message was not called"
    sent_message = captured[0]
    assert "[Session:" in sent_message
    assert "standard" in sent_message
    assert "15min target" in sent_message


def test_day_phase():
    assert bd._day_phase(6) == "morning"
    assert bd._day_phase(11) == "morning"
    assert bd._day_phase(12) == "afternoon"
    assert bd._day_phase(16) == "afternoon"
    assert bd._day_phase(17) == "evening"
    assert bd._day_phase(23) == "evening"


# ---------------------------------------------------------------------------
# T-003: Session recovery — idle detection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_braindump_message_shows_resume_after_idle():
    """After 30+ min idle, user sees a 'session paused' resume message."""
    orch = _make_orch()
    session_start = datetime.now(UTC) - timedelta(minutes=35)
    orch.state_manager.update_state(12345, {
        "active_persona": "GTD_EXPERT",
        "session_mode": "standard",
        "target_minutes": 15,
        "session_start": session_start.isoformat(),
        "captured_items": [],
        "conversation_history": [],
    })
    # Manually set updated_at to 31 min ago via a second update then roll back timestamp
    # We simulate idle by patching get_state_updated_at
    old_time = (datetime.now(UTC) - timedelta(minutes=31)).strftime("%Y-%m-%d %H:%M:%S")
    orch.state_manager.get_state_updated_at = MagicMock(return_value=old_time)

    message = AsyncMock()
    message.reply_text = AsyncMock()

    llm_response = MagicMock()
    llm_response.status = "NEED_INFO"
    llm_response.question = "What else?"

    with patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)), \
         patch.object(orch.llm_orchestrator, "process_message", new_callable=AsyncMock, return_value=llm_response):
        await bd.handle_braindump_message(orch, 12345, "hello", message)

    # Should have sent a "paused/resuming" message before continuing
    reply_calls = [c[0][0] for c in message.reply_text.call_args_list]
    assert any("paused" in t.lower() or "resum" in t.lower() for t in reply_calls)


@pytest.mark.asyncio
async def test_handle_braindump_message_no_resume_within_timeout():
    """Within 30 min, no 'session paused' message is shown."""
    orch = _make_orch()
    session_start = datetime.now(UTC) - timedelta(minutes=5)
    orch.state_manager.update_state(12345, {
        "active_persona": "GTD_EXPERT",
        "session_mode": "standard",
        "target_minutes": 15,
        "session_start": session_start.isoformat(),
        "captured_items": [],
        "conversation_history": [],
    })
    recent_time = (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    orch.state_manager.get_state_updated_at = MagicMock(return_value=recent_time)

    message = AsyncMock()
    message.reply_text = AsyncMock()

    llm_response = MagicMock()
    llm_response.status = "NEED_INFO"
    llm_response.question = "What else?"

    with patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)), \
         patch.object(orch.llm_orchestrator, "process_message", new_callable=AsyncMock, return_value=llm_response):
        await bd.handle_braindump_message(orch, 12345, "hello", message)

    reply_calls = [c[0][0] for c in message.reply_text.call_args_list]
    assert not any("paused" in t.lower() for t in reply_calls)


# ---------------------------------------------------------------------------
# T-004: User preferences — mode persisted after session
# ---------------------------------------------------------------------------

def test_state_manager_user_prefs_roundtrip(tmp_path):
    """StateManager persists user preferences across instances."""
    from src.state_manager import StateManager
    db = str(tmp_path / "test.db")
    sm = StateManager(db_path=db)
    sm.set_user_pref(1, "default_braindump_mode", "thorough")
    assert sm.get_user_pref(1, "default_braindump_mode") == "thorough"

    # Persists across new instance
    sm2 = StateManager(db_path=db)
    assert sm2.get_user_pref(1, "default_braindump_mode") == "thorough"


def test_state_manager_user_prefs_missing_returns_none(tmp_path):
    from src.state_manager import StateManager
    sm = StateManager(db_path=str(tmp_path / "test.db"))
    assert sm.get_user_pref(99, "default_braindump_mode") is None


@pytest.mark.asyncio
async def test_braindump_uses_saved_mode_pref():
    """When no mode arg given, /braindump uses the saved default_braindump_mode preference."""
    orch = _make_orch()
    orch.state_manager.set_user_pref(12345, "default_braindump_mode", "thorough")

    update, message = _make_update()
    context = MagicMock()
    context.args = []  # no mode arg

    with patch("src.handlers.braindump.check_whitelist", return_value=True), \
         patch("src.handlers.braindump.get_user_timezone_aware_now", return_value=datetime.now(UTC)):
        handler = bd._braindump(orch)
        await handler(update, context)

    state = orch.state_manager.get_state(12345)
    assert state["session_mode"] == "thorough"
    assert state["target_minutes"] == 25


# ---------------------------------------------------------------------------
# DEF-026: create_note_in_joplin with url_context=None (braindump, photo OCR)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_note_in_joplin_with_url_context_none():
    """DEF-026: create_note_in_joplin must not crash when url_context is None."""
    from src.handlers.core import create_note_in_joplin

    orch = MagicMock()
    orch.joplin_client = MagicMock()
    orch.joplin_client.get_folders = AsyncMock(
        return_value=[{"id": "inbox123", "title": "Inbox", "parent_id": ""}]
    )
    orch.joplin_client.create_note = AsyncMock(return_value="note456")
    orch.joplin_client.apply_tags_and_track_new = AsyncMock(
        return_value={"new_tags": [], "existing_tags": [], "all_tags": ["brain-dump"]}
    )
    orch.joplin_client.fetch_tags = AsyncMock(return_value=[])

    note_data = {
        "title": "Brain Dump Summary",
        "body": "Test content",
        "parent_id": "Inbox",
        "tags": ["brain-dump"],
    }

    result = await create_note_in_joplin(orch, note_data, url_context=None)

    assert result is not None
    assert result.get("note_id") == "note456"


# ---------------------------------------------------------------------------
# DEF-027: GoogleAuthError shows re-auth message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_finish_session_shows_reauth_on_google_auth_error():
    """DEF-027: When create_tasks_from_decision raises GoogleAuthError, user sees re-auth message."""
    from src.exceptions import GoogleAuthError
    from src.handlers.braindump import _finish_session

    orch = MagicMock()
    orch.state_manager = InMemoryStateManager()
    orch.state_manager.update_state(12345, {"session_mode": "standard", "conversation_history": []})
    orch.logging_service = MagicMock()
    orch.logging_service.load_google_token = MagicMock(return_value={"access_token": "x"})
    orch.logging_service.get_google_tasks_config = MagicMock(return_value={"task_list_id": "list_1"})
    orch.logging_service.log_decision = MagicMock()
    orch.task_service = MagicMock()
    orch.task_service.create_tasks_from_decision = MagicMock(side_effect=GoogleAuthError("Token expired"))
    orch.reorg_orchestrator = MagicMock()
    orch.reorg_orchestrator.get_project_folder_for_sync = AsyncMock(return_value=None)

    message = AsyncMock()
    message.reply_text = AsyncMock()

    final_note = {"title": "Test", "body": "todo: x", "parent_id": "inbox", "tags": ["brain-dump"]}

    with patch("src.handlers.core.create_note_in_joplin", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"note_id": "note123"}
        await _finish_session(orch, 12345, message, note_data=final_note)

    reply_calls = [c[0][0] for c in message.reply_text.call_args_list]
    assert any("tasks_connect" in t and "re-authenticate" in t for t in reply_calls)
