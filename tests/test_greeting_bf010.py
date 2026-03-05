"""
Tests for BF-010: Greeting parse entities fix.

Verifies that the greeting uses HTML (not Markdown) to avoid underscore parse errors,
and that the plain-text fallback strips HTML correctly.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module to test (conftest adds project root to path)
from src.handlers import core as core_module


class TestGreetingContent(unittest.TestCase):
    """Test greeting content and helpers."""

    def test_greeting_uses_html_not_markdown(self):
        """Greeting should use <b> tags, not **, to avoid Markdown underscore issues."""
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "UTC"}
        greeting = core_module._build_greeting_response(999, orch)
        # Should use HTML <b> for bold, not Markdown **
        self.assertIn("<b>📝 Capture</b>", greeting)
        self.assertIn("<b>🔍 Search</b>", greeting)
        self.assertIn("<b>📊 Review</b>", greeting)
        # Underscores in commands should be present (no Markdown italic)
        self.assertIn("/daily_report", greeting)
        self.assertIn("/weekly_report", greeting)
        self.assertIn("/monthly_report", greeting)
        # Angle brackets should be escaped for HTML
        self.assertIn("&lt;text&gt;", greeting)
        self.assertIn("&lt;query&gt;", greeting)

    def test_greeting_to_plain_strips_html(self):
        """_greeting_to_plain should strip <b> tags and unescape entities."""
        html = "<b>📝 Capture</b>\n• /task &lt;text&gt; → Create"
        plain = core_module._greeting_to_plain(html)
        self.assertNotIn("<b>", plain)
        self.assertNotIn("</b>", plain)
        self.assertIn("📝 Capture", plain)
        self.assertIn("<text>", plain)
        self.assertNotIn("&lt;", plain)
        self.assertNotIn("&gt;", plain)
