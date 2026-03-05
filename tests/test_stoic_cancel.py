"""
Test suite for /stoic_cancel command (BF-006).

Covers: Cancel active session, error handling, state clearing.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from src.handlers import stoic as stoic_module


class TestStoicCancel(unittest.TestCase):
    """Test _stoic_cancel handler."""

    def setUp(self):
        """Set up common mocks."""
        self.orch = MagicMock()
        self.orch.state_manager = MagicMock()
        self.user = User(id=123, is_bot=False, first_name="Test")
        self.chat = Chat(id=123, type="private")
        self.message = AsyncMock(spec=Message)
        self.message.reply_text = AsyncMock()

    @patch("src.handlers.stoic.check_whitelist")
    def test_cancel_active_session(self, mock_whitelist):
        """Cancel an active session clears state and confirms."""
        mock_whitelist.return_value = True
        self.orch.state_manager.get_state.return_value = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "morning",
            "answers": [{"q": "q1", "a": "a1"}, {"q": "q2", "a": "a2"}],
        }

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = self.message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        handler = stoic_module._stoic_cancel(self.orch)
        with patch("src.handlers.stoic.logger") as mock_logger:
            # Run async handler
            import asyncio
            asyncio.run(handler(update, context))

            # Verify state was cleared
            self.orch.state_manager.clear_state.assert_called_once_with(123)

            # Verify confirmation message sent
            self.message.reply_text.assert_called_once()
            call_args = self.message.reply_text.call_args
            self.assertIn("cancelled", call_args[0][0].lower())

            # Verify logging
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            self.assertIn("cancelled", log_call.lower())

    @patch("src.handlers.stoic.check_whitelist")
    def test_cancel_no_session(self, mock_whitelist):
        """Cancel with no active session returns error message."""
        mock_whitelist.return_value = True
        self.orch.state_manager.get_state.return_value = None

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = self.message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        handler = stoic_module._stoic_cancel(self.orch)
        import asyncio
        asyncio.run(handler(update, context))

        # Verify no state cleared
        self.orch.state_manager.clear_state.assert_not_called()

        # Verify error message sent
        self.message.reply_text.assert_called_once()
        call_args = self.message.reply_text.call_args
        self.assertIn("no active", call_args[0][0].lower())

    @patch("src.handlers.stoic.check_whitelist")
    def test_cancel_different_persona(self, mock_whitelist):
        """Cancel with different persona returns error message."""
        mock_whitelist.return_value = True
        self.orch.state_manager.get_state.return_value = {
            "active_persona": "GTD_EXPERT",
            "items": [],
        }

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = self.message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        handler = stoic_module._stoic_cancel(self.orch)
        import asyncio
        asyncio.run(handler(update, context))

        # Verify no state cleared
        self.orch.state_manager.clear_state.assert_not_called()

        # Verify error message sent
        self.message.reply_text.assert_called_once()
        call_args = self.message.reply_text.call_args
        self.assertIn("no active", call_args[0][0].lower())

    @patch("src.handlers.stoic.check_whitelist")
    def test_cancel_whitelist_check(self, mock_whitelist):
        """Cancel respects whitelist check."""
        mock_whitelist.return_value = False

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = self.message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        handler = stoic_module._stoic_cancel(self.orch)
        import asyncio
        asyncio.run(handler(update, context))

        # Verify no message sent (whitelist check fails)
        self.message.reply_text.assert_not_called()
        self.orch.state_manager.clear_state.assert_not_called()

    @patch("src.handlers.stoic.check_whitelist")
    def test_cancel_logs_answer_count(self, mock_whitelist):
        """Cancel logs the number of answers completed."""
        mock_whitelist.return_value = True
        self.orch.state_manager.get_state.return_value = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "evening",
            "answers": [{"q": "q", "a": "a"} for _ in range(3)],
        }

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.message = self.message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        handler = stoic_module._stoic_cancel(self.orch)
        with patch("src.handlers.stoic.logger") as mock_logger:
            import asyncio
            asyncio.run(handler(update, context))

            # Verify log includes answer count
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0]
            self.assertIn("3", str(log_call))  # 3 answers


class TestStoicHandlerMessages(unittest.TestCase):
    """Test updated help messages in stoic handlers."""

    def test_existing_session_message_suggests_cancel(self):
        """When user tries /stoic with active session, suggest /stoic_cancel."""
        orch = MagicMock()
        orch.state_manager = MagicMock()
        orch.state_manager.get_state.return_value = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "morning",
            "answers": [],
        }
        orch.logging_service = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}

        user = User(id=123, is_bot=False, first_name="Test")
        message = AsyncMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = user
        update.message = message
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = None

        with patch("src.handlers.stoic.check_whitelist", return_value=True):
            handler = stoic_module._stoic(orch)
            import asyncio
            asyncio.run(handler(update, context))

            # Verify message includes cancel option
            message.reply_text.assert_called_once()
            call_args = message.reply_text.call_args
            msg_text = call_args[0][0]
            self.assertIn("stoic_cancel", msg_text.lower())


if __name__ == "__main__":
    unittest.main()
