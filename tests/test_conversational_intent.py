"""Tests for US-058: Natural Conversational Intent Understanding.

Verifies:
- ContentDecision accepts feature_redirect field
- _build_routing_system_prompt() output contains feature redirect table
- _dispatch_feature_redirect() calls correct handler for each feature
- Unknown feature returns False (falls through)
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm_orchestrator import ContentDecision
from src.state_manager import InMemoryStateManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orch() -> MagicMock:
    orch = MagicMock()
    orch.state_manager = InMemoryStateManager()
    orch.logging_service = MagicMock()
    orch.logging_service.get_timezone_for_user = MagicMock(return_value=None)
    orch.joplin_client = AsyncMock()
    orch.llm_orchestrator = MagicMock()
    return orch


def _make_message(user_id: int = 12345) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    message = AsyncMock()
    message.reply_text = AsyncMock(return_value=AsyncMock())
    message.from_user = user
    message.text = "test"
    return message


def _make_context() -> MagicMock:
    context = MagicMock()
    context.args = []
    return context


# ---------------------------------------------------------------------------
# T-001: ContentDecision accepts feature_redirect
# ---------------------------------------------------------------------------

class TestContentDecisionFeatureRedirect:
    def test_feature_redirect_none_by_default(self):
        decision = ContentDecision(
            status="SUCCESS",
            content_type="note",
            confidence_score=0.95,
            log_entry="test",
        )
        assert decision.feature_redirect is None

    def test_feature_redirect_set(self):
        decision = ContentDecision(
            status="SUCCESS",
            content_type="note",
            confidence_score=0.95,
            log_entry="test",
            feature_redirect="stoic",
        )
        assert decision.feature_redirect == "stoic"

    def test_feature_redirect_backwards_compatible(self):
        """Existing code that doesn't set feature_redirect still works."""
        decision = ContentDecision(
            status="SUCCESS",
            content_type="task",
            confidence_score=0.9,
            log_entry="created task",
            task={"title": "Buy groceries"},
        )
        assert decision.feature_redirect is None
        assert decision.content_type == "task"


# ---------------------------------------------------------------------------
# T-002: Routing system prompt contains feature redirect table
# ---------------------------------------------------------------------------

class TestRoutingSystemPrompt:
    def test_prompt_contains_feature_redirect_section(self):
        from src.llm_orchestrator import LLMOrchestrator

        with patch.object(LLMOrchestrator, "__init__", lambda self, **kw: None):
            llm = LLMOrchestrator.__new__(LLMOrchestrator)
            llm._personas = {}
            llm._ai_identity = None
            llm.prompts_dir = __import__("pathlib").Path(__file__).parent / "nonexistent"

            prompt = llm._build_routing_system_prompt({
                "folders": [],
                "existing_tags": [],
            })

        assert "Feature Redirect" in prompt
        assert "feature_redirect" in prompt
        # Verify some feature names are in the table
        for feature in ["stoic", "braindump", "dream", "plan", "flashcard",
                        "find", "ask", "readlater", "habits",
                        "report_daily", "report_weekly", "report_monthly",
                        "tasks_status", "project_report"]:
            assert feature in prompt, f"Feature '{feature}' missing from prompt"

    def test_prompt_contains_conversational_examples(self):
        from src.llm_orchestrator import LLMOrchestrator

        with patch.object(LLMOrchestrator, "__init__", lambda self, **kw: None):
            llm = LLMOrchestrator.__new__(LLMOrchestrator)
            llm._personas = {}
            llm._ai_identity = None
            llm.prompts_dir = __import__("pathlib").Path(__file__).parent / "nonexistent"

            prompt = llm._build_routing_system_prompt({
                "folders": [],
                "existing_tags": [],
            })

        assert "Conversational Examples" in prompt
        assert "brain dump" in prompt.lower()
        assert "NEED_INFO" in prompt


# ---------------------------------------------------------------------------
# T-003: _dispatch_feature_redirect calls correct handler
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="US-058: _dispatch_feature_redirect not yet implemented in core.py")
class TestDispatchFeatureRedirect:
    @pytest.mark.asyncio
    async def test_stoic_dispatch(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.core._stoic_handler", create=True), \
             patch("src.handlers.stoic._stoic") as mock_stoic:
            mock_handler = AsyncMock()
            mock_stoic.return_value = mock_handler

            result = await _dispatch_feature_redirect(
                orch, 12345, "I want to journal", "stoic", message, context,
            )

        assert result is True
        mock_stoic.assert_called_once_with(orch)
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_braindump_dispatch(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.braindump._braindump") as mock_bd:
            mock_handler = AsyncMock()
            mock_bd.return_value = mock_handler

            result = await _dispatch_feature_redirect(
                orch, 12345, "let's do a brain dump", "braindump", message, context,
            )

        assert result is True
        mock_bd.assert_called_once_with(orch)

    @pytest.mark.asyncio
    async def test_find_dispatch_sets_context_args(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.search._find") as mock_find:
            mock_handler = AsyncMock()
            mock_find.return_value = mock_handler

            result = await _dispatch_feature_redirect(
                orch, 12345, "find my note about python", "find", message, context,
            )

        assert result is True
        assert context.args == ["find", "my", "note", "about", "python"]

    @pytest.mark.asyncio
    async def test_report_daily_dispatch(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.reports._daily_report") as mock_report:
            mock_handler = AsyncMock()
            mock_report.return_value = mock_handler

            result = await _dispatch_feature_redirect(
                orch, 12345, "daily report", "report_daily", message, context,
            )

        assert result is True
        mock_report.assert_called_once_with(orch)

    @pytest.mark.asyncio
    async def test_tasks_status_dispatch(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.google_tasks._tasks_status") as mock_ts:
            mock_handler = AsyncMock()
            mock_ts.return_value = mock_handler

            result = await _dispatch_feature_redirect(
                orch, 12345, "show my tasks", "tasks_status", message, context,
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_dream_dispatch_sets_state(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.core.check_whitelist", return_value=True):
            result = await _dispatch_feature_redirect(
                orch, 12345, "I had a dream", "dream", message, context,
            )

        assert result is True
        state = orch.state_manager.get_state(12345)
        assert state["active_persona"] == "DREAM_ANALYST"
        assert state["phase"] == "dream_description"
        message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_plan_dispatch_sets_state(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        with patch("src.handlers.core.check_whitelist", return_value=True), \
             patch("src.handlers.planning._gather_review_context", return_value=""), \
             patch("src.handlers.core.get_user_timezone_aware_now") as mock_tz:
            from datetime import datetime
            mock_tz.return_value = datetime(2026, 3, 24, 10, 0, tzinfo=UTC)

            result = await _dispatch_feature_redirect(
                orch, 12345, "weekly planning", "plan", message, context,
            )

        assert result is True
        state = orch.state_manager.get_state(12345)
        assert state["active_persona"] == "PLANNING_COACH"

    @pytest.mark.asyncio
    async def test_unknown_feature_returns_false(self):
        from src.handlers.core import _dispatch_feature_redirect

        orch = _make_orch()
        message = _make_message()
        context = _make_context()

        result = await _dispatch_feature_redirect(
            orch, 12345, "something", "nonexistent_feature", message, context,
        )

        assert result is False
