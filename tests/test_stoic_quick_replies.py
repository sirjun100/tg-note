"""
Unit tests for US-053: Stoic quick-reply keyboards.

Tests:
- T-024: Energy question returns 1–5 numeric keyboard
- T-025: Mood/feeling question returns emoji mood keyboard
- T-026: Yes/no question returns Yes/No/Skip keyboard
- T-027: Generic question returns Skip keyboard
- T-028: _remove_keyboard returns ReplyKeyboardRemove
"""
from __future__ import annotations

import unittest

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

from src.handlers.stoic import _quick_replies_for_question, _remove_keyboard


class TestQuickRepliesForQuestion(unittest.TestCase):
    """T-024 – T-027: Context-appropriate keyboard per question type."""

    # -----------------------------------------------------------------------
    # T-024: Energy question → 1–5 numeric keyboard
    # -----------------------------------------------------------------------

    def test_energy_rate_returns_numeric_keyboard(self):
        markup = _quick_replies_for_question("Rate your energy level 1–5")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("1", flat)
        self.assertIn("5", flat)

    def test_energy_scale_returns_numeric_keyboard(self):
        markup = _quick_replies_for_question("Energy: on a scale of 1 to 5?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("3", flat)

    def test_energy_level_returns_numeric_keyboard(self):
        markup = _quick_replies_for_question("What is your energy level today?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertEqual(sorted(flat), ["1", "2", "3", "4", "5"])

    # -----------------------------------------------------------------------
    # T-025: Mood / feeling → emoji mood keyboard
    # -----------------------------------------------------------------------

    def test_mood_question_returns_mood_keyboard(self):
        markup = _quick_replies_for_question("How is your mood today?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        mood_options = {"Good 😊", "Okay 😐", "Low 😔", "Energized ⚡", "Stressed 😤", "Grateful 🙏"}
        found = mood_options.intersection(flat)
        self.assertGreater(len(found), 0, "Should have at least one mood option")

    def test_feeling_question_returns_mood_keyboard(self):
        markup = _quick_replies_for_question("How are you feeling right now?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Good 😊", flat)

    def test_emotion_question_returns_mood_keyboard(self):
        markup = _quick_replies_for_question("What emotion is predominant?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Grateful 🙏", flat)

    # -----------------------------------------------------------------------
    # T-026: Yes/no question → Yes / No / Skip keyboard
    # -----------------------------------------------------------------------

    def test_did_you_question_returns_yes_no_keyboard(self):
        markup = _quick_replies_for_question("Did you exercise today?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Yes", flat)
        self.assertIn("No", flat)
        self.assertIn("Skip", flat)

    def test_were_you_question_returns_yes_no_keyboard(self):
        markup = _quick_replies_for_question("Were you productive?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Yes", flat)

    def test_have_you_question_returns_yes_no_keyboard(self):
        markup = _quick_replies_for_question("Have you completed your morning routine?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("No", flat)

    def test_skip_keyword_returns_yes_no_keyboard(self):
        markup = _quick_replies_for_question("Did you skip meditation this morning?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Yes", flat)

    # -----------------------------------------------------------------------
    # T-027: Generic / open question → Skip keyboard only
    # -----------------------------------------------------------------------

    def test_open_question_returns_skip_only(self):
        markup = _quick_replies_for_question("What is your main intention for today?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertIn("Skip", flat)
        # Should NOT have Yes/No (no yes/no context)
        self.assertNotIn("Yes", flat)
        self.assertNotIn("No", flat)

    def test_philosophical_question_returns_skip_only(self):
        markup = _quick_replies_for_question("What is the highest priority for deep work today?")
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        flat = [btn.text for row in markup.keyboard for btn in row]
        self.assertEqual(flat, ["Skip"])

    # -----------------------------------------------------------------------
    # T-027: one_time_keyboard and resize_keyboard are set
    # -----------------------------------------------------------------------

    def test_keyboard_is_one_time(self):
        markup = _quick_replies_for_question("Rate your energy level 1–5")
        self.assertTrue(markup.one_time_keyboard)

    def test_keyboard_is_resized(self):
        markup = _quick_replies_for_question("How are you feeling?")
        self.assertTrue(markup.resize_keyboard)


class TestRemoveKeyboard(unittest.TestCase):
    """T-028: _remove_keyboard returns ReplyKeyboardRemove."""

    def test_remove_keyboard_returns_correct_type(self):
        result = _remove_keyboard()
        self.assertIsInstance(result, ReplyKeyboardRemove)


if __name__ == "__main__":
    unittest.main()
