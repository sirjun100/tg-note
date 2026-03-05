"""
Test suite for /stoic Stoic Journal flow.

Covers: template loading, question flow, message handling, save (create/update note).
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py adds project root to sys.path
from src.handlers import stoic as stoic_module


class TestLoadStoicTemplate(unittest.TestCase):
    """Test _load_stoic_template returns correct question counts and body."""

    def test_morning_questions_count(self):
        """Morning must have 7 questions: objectives, obstacle, goals, top 3 priorities (BF-009)."""
        morning_q, evening_q, body_tpl = stoic_module._load_stoic_template()
        self.assertGreaterEqual(
            len(morning_q), 7,
            "Template should define at least 7 morning questions"
        )
        self.assertIn("professional", (morning_q[0] or "").lower())
        self.assertIn("personal", (morning_q[1] or "").lower())
        self.assertIn("obstacle", (morning_q[2] or "").lower())
        self.assertIn("goal", (morning_q[3] or "").lower())
        self.assertIn("priority", (morning_q[4] or "").lower())
        self.assertIn("priority", (morning_q[5] or "").lower())
        self.assertIn("priority", (morning_q[6] or "").lower())

    def test_evening_questions_count(self):
        """Evening must have 8 questions: completed + wins + reflection + tomorrow (BF-009)."""
        morning_q, evening_q, body_tpl = stoic_module._load_stoic_template()
        self.assertGreaterEqual(len(evening_q), 8)

    def test_body_template_has_placeholders(self):
        """Body template must contain placeholders for morning/evening content."""
        _, _, body_tpl = stoic_module._load_stoic_template()
        self.assertIn("{{MORNING_CONTENT}}", body_tpl)
        self.assertIn("{{EVENING_CONTENT}}", body_tpl)
        self.assertIn("{{DATE}}", body_tpl)


class TestFormatSection(unittest.TestCase):
    """Test _format_section and _format_morning_content / _format_evening_content."""

    def test_format_morning_content_fills_all_sections(self):
        """With 7 answers, morning content includes objectives, obstacle, goals, Top 3 Priorities (BF-009)."""
        answers = [
            {"q": "professional?", "a": "Finish quarterly report"},
            {"q": "personal?", "a": "30 min exercise"},
            {"q": "obstacle?", "a": "Interruptions - will block time"},
            {"q": "goals?", "a": "Moving toward senior role"},
            {"q": "priority 1?", "a": "Complete report"},
            {"q": "priority 2?", "a": "Block time for deep work"},
            {"q": "priority 3?", "a": "One difficult conversation"},
        ]
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}
        out = stoic_module._format_morning_content(answers, 123, orch)
        self.assertIn("Professional Objective", out)
        self.assertIn("Personal Objective", out)
        self.assertIn("Obstacle", out)
        self.assertIn("Greater Goals", out)
        self.assertIn("Top 3 Priorities", out)
        self.assertIn("Complete report", out)
        self.assertIn("Block time for deep work", out)

    def test_format_evening_content_fills_all_sections(self):
        """Evening content includes Morning Priorities Completed + wins + reflection + Tomorrow (BF-009)."""
        answers = [
            {"q": "completed?", "a": "Finished report on time, kept exercise commitment"},
            {"q": "prof wins?", "a": "Delivered report"},
            {"q": "personal wins?", "a": "Kept exercise commitment"},
            {"q": "went wrong?", "a": "Lost hour to email"},
            {"q": "control?", "a": "My effort was mine"},
            {"q": "progress?", "a": "One step closer"},
            {"q": "grateful?", "a": "Support of my team"},
            {"q": "tomorrow?", "a": "Begin proposal draft"},
        ]
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}
        out = stoic_module._format_evening_content(answers, 123, orch)
        self.assertIn("Morning Priorities Completed", out)
        self.assertIn("Finished report on time", out)
        self.assertIn("What Went Well (Professional)", out)
        self.assertIn("What Went Well (Personal)", out)
        self.assertIn("What Went Wrong", out)
        self.assertIn("Within My Control", out)
        self.assertIn("Progress Toward Greater Goals", out)
        self.assertIn("Grateful For", out)
        self.assertIn("Tomorrow", out)
        self.assertIn("Begin proposal draft", out)

    def test_format_section_morning(self):
        """_format_section(mode='morning', answers) returns morning block."""
        answers = [{"q": "q1", "a": "a1"}]
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}
        out = stoic_module._format_section("morning", answers, 123, orch)
        self.assertIn("Morning", out)
        self.assertIn("a1", out)

    def test_format_section_evening(self):
        """_format_section(mode='evening', answers) returns evening block."""
        answers = [{"q": "q1", "a": "a1"}]
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}
        out = stoic_module._format_section("evening", answers, 123, orch)
        self.assertIn("Evening", out)


class TestHandleStoicMessage(unittest.IsolatedAsyncioTestCase):
    """Test that each reply gets the next question until all are asked."""

    async def test_first_answer_triggers_second_question(self):
        """After first answer, bot must send the second morning question (not 'Anything else?')."""
        morning_q, _, _ = stoic_module._load_stoic_template()
        self.assertGreaterEqual(len(morning_q), 2, "Need at least 2 morning questions for this test")

        orch = MagicMock()
        orch.state_manager.get_state.return_value = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "morning",
            "answers": [],
            "questions": morning_q,
            "body_template": "# {{DATE}}\n{{MORNING_CONTENT}}\n{{EVENING_CONTENT}}",
        }
        orch.state_manager.update_state = MagicMock()

        message = MagicMock()
        message.reply_text = AsyncMock()

        await stoic_module.handle_stoic_message(orch, 12345, "My intention is to focus.", message)

        orch.state_manager.update_state.assert_called_once()
        state = orch.state_manager.update_state.call_args[0][1]
        self.assertEqual(len(state["answers"]), 1)
        self.assertEqual(state["answers"][0]["a"], "My intention is to focus.")

        message.reply_text.assert_called_once()
        sent_text = message.reply_text.call_args[0][0]
        self.assertNotIn("Anything else?", sent_text, "Bot must ask the next question, not offer to finish")
        self.assertEqual(sent_text.strip(), morning_q[1].strip(), "Bot must send the second morning question")

    async def test_after_last_answer_offers_done(self):
        """After answering all morning questions, bot must say 'Anything else? ... /stoic_done'."""
        morning_q, _, _ = stoic_module._load_stoic_template()
        n = len(morning_q)
        self.assertGreaterEqual(n, 1)

        orch = MagicMock()
        orch.state_manager.get_state.return_value = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "morning",
            "answers": [{"q": morning_q[i], "a": f"answer_{i}"} for i in range(n)],
            "questions": morning_q,
            "body_template": "# {{DATE}}\n{{MORNING_CONTENT}}\n{{EVENING_CONTENT}}",
        }
        orch.state_manager.update_state = MagicMock()

        message = MagicMock()
        message.reply_text = AsyncMock()

        await stoic_module.handle_stoic_message(orch, 12345, "One more thought", message)

        sent_text = message.reply_text.call_args[0][0]
        self.assertIn("Anything else?", sent_text)
        self.assertIn("stoic_done", sent_text)


class TestFinishStoicSession(unittest.IsolatedAsyncioTestCase):
    """Test _finish_stoic_session: create note when none exists, update when today's note exists."""

    async def test_no_answers_returns_false(self):
        """When there are no answers, finish does not save and returns False."""
        orch = MagicMock()
        message = MagicMock()
        message.reply_text = AsyncMock()
        state = {"mode": "morning", "answers": [], "body_template": "# {{DATE}}\n{{MORNING_CONTENT}}\n{{EVENING_CONTENT}}"}

        result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        self.assertFalse(result)
        message.reply_text.assert_called()
        orch.joplin_client.get_or_create_folder_by_path.assert_not_called()

    async def test_creates_note_when_no_existing_today(self):
        """When today's note does not exist, finish creates a new note and returns True."""
        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)
        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(return_value=[])
        orch.joplin_client.create_note = AsyncMock(return_value="note_456")
        orch.joplin_client.apply_tags = AsyncMock(return_value=True)

        message = MagicMock()
        message.reply_text = AsyncMock()
        state = {
            "mode": "morning",
            "answers": [{"q": "Intention?", "a": "Have fun skiing"}],
            "body_template": "# {{DATE}} - Daily Stoic Reflection\n\n## Morning\n{{MORNING_CONTENT}}\n\n## Evening\n{{EVENING_CONTENT}}",
        }

        with patch.object(stoic_module, "get_current_date_str") as mock_date:
            mock_date.return_value = "2025-02-28"
            result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        self.assertTrue(result)
        orch.joplin_client.get_or_create_folder_by_path.assert_called_once()
        orch.joplin_client.create_note.assert_called_once()
        call_kw = orch.joplin_client.create_note.call_args[1]
        self.assertEqual(call_kw["title"], "2025-02-28 - Daily Stoic Reflection")
        self.assertIn("Morning", call_kw["body"])
        self.assertIn("Have fun skiing", call_kw["body"])
        orch.joplin_client.apply_tags.assert_called_once()

    async def test_updates_note_when_todays_note_exists(self):
        """When today's note exists, finish appends to it and returns True."""
        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)
        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(return_value=[
            {"id": "existing_note_id", "title": "2025-02-28 - Daily Stoic Reflection"},
        ])
        orch.joplin_client.get_note = AsyncMock(return_value={"id": "existing_note_id", "body": "Existing body"})
        orch.joplin_client.update_note = AsyncMock()
        orch.joplin_client.apply_tags = AsyncMock(return_value=True)

        message = MagicMock()
        message.reply_text = AsyncMock()
        state = {
            "mode": "evening",
            "answers": [{"q": "Wins?", "a": "Shipped feature"}],
            "body_template": "# {{DATE}}\n{{MORNING_CONTENT}}\n{{EVENING_CONTENT}}",
        }

        with patch.object(stoic_module, "get_current_date_str") as mock_date:
            mock_date.return_value = "2025-02-28"
            result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        self.assertTrue(result)
        orch.joplin_client.get_note.assert_called_once_with("existing_note_id")
        orch.joplin_client.update_note.assert_called_once()
        call_args = orch.joplin_client.update_note.call_args[0]
        self.assertEqual(call_args[0], "existing_note_id")
        self.assertIn("Existing body", call_args[1]["body"])
        self.assertIn("Evening", call_args[1]["body"])
        self.assertIn("Shipped feature", call_args[1]["body"])

    async def test_finish_uses_body_template_from_template_if_missing_in_state(self):
        """When state has no body_template, finish loads it from template and still saves."""
        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)
        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(return_value=[])
        orch.joplin_client.create_note = AsyncMock(return_value="note_456")
        orch.joplin_client.apply_tags = AsyncMock(return_value=True)

        message = MagicMock()
        message.reply_text = AsyncMock()
        state = {"mode": "morning", "answers": [{"q": "Q?", "a": "A"}], "body_template": ""}

        with patch.object(stoic_module, "get_current_date_str") as mock_date:
            mock_date.return_value = "2025-03-01"
            result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        self.assertTrue(result)
        orch.joplin_client.create_note.assert_called_once()
        body = orch.joplin_client.create_note.call_args[1]["body"]
        self.assertIn("2025-03-01", body)
        self.assertIn("A", body)


if __name__ == "__main__":
    unittest.main()
