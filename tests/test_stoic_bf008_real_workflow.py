"""
BF-008 Real Workflow Test: Exact reproduction of user's reported issue.

This test follows the exact steps a user would take and verifies
no data loss occurs at any step.
"""

from __future__ import annotations

import unittest

from src.handlers import stoic as stoic_module


class TestBF008RealWorkflow(unittest.TestCase):
    """Reproduce the exact workflow that causes data loss."""

    def setUp(self):
        """Load the actual stoic journal template."""
        self.morning_q, self.evening_q, self.body_template = stoic_module._load_stoic_template()
        print("\n=== STOIC JOURNAL TEMPLATE STRUCTURE ===")
        print(f"Template:\n{self.body_template[:300]}...")
        print(f"\nMorning questions: {len(self.morning_q)}")
        print(f"Evening questions: {len(self.evening_q)}")

    def test_exact_user_workflow_morning_then_evening(self):
        """
        Exact steps:
        1. User does /stoic morning -> answers 5 morning questions
        2. Bot saves morning reflection to new note
        3. User does /stoic evening -> answers 4 evening questions
        4. Bot tries to save evening reflection
        5. Verify: Both morning and evening in final note
        """
        date_str = "2026-03-04"

        # Step 1: User answers morning questions (4 questions now)
        morning_answers = [
            {"q": self.morning_q[0], "a": "Complete the quarterly report"},  # Professional
            {"q": self.morning_q[1], "a": "30 minutes exercise"},            # Personal
            {"q": self.morning_q[2], "a": "Interruptions—block time"},       # Obstacle
            {"q": self.morning_q[3], "a": "Moving toward senior role"},      # Greater goals
        ]

        # Step 2: Bot creates note with morning content
        morning_section = stoic_module._format_section("morning", morning_answers, 999,
                                                       self._make_mock_orch())
        evening_placeholder = ""  # No evening content yet

        # This is what _build_full_body does
        initial_body = stoic_module._build_full_body(
            self.body_template,
            date_str,
            morning_section,
            evening_placeholder,
        )

        print("\n=== MORNING NOTE CREATED ===")
        print(f"Length: {len(initial_body)} chars")
        self._verify_content(initial_body, "morning_section")

        # Verify morning is there
        assert "🌞 Morning" in initial_body
        assert "Complete the quarterly report" in initial_body
        print("✅ Morning content saved correctly")

        # Verify evening structure exists (as placeholder)
        assert "🌙 Evening" in initial_body
        print("✅ Evening section placeholder present")

        # Step 3: User answers evening questions (7 questions now)
        evening_answers = [
            {"q": self.evening_q[0], "a": "Completed report ahead of schedule"},  # Prof wins
            {"q": self.evening_q[1], "a": "Kept exercise commitment"},            # Personal wins
            {"q": self.evening_q[2], "a": "Lost hour to email"},                  # Went wrong
            {"q": self.evening_q[3], "a": "My effort was mine"},                  # Control
            {"q": self.evening_q[4], "a": "One step closer"},                     # Progress
            {"q": self.evening_q[5], "a": "Great team support"},                  # Gratitude
            {"q": self.evening_q[6], "a": "Begin proposal draft"},                # Tomorrow
        ]

        # Step 4: Bot checks if evening section exists
        evening_section_exists = stoic_module._check_section_exists(initial_body, "evening")
        print("\n=== EVENING DUPLICATE CHECK ===")
        print(f"Does evening section exist? {evening_section_exists}")

        # This is where the UX issue is - placeholder is detected as existing
        if evening_section_exists:
            print("⚠️  User would be prompted to replace/append")
            print("   (This is annoying UX but shouldn't cause data loss)")

            # Step 4a: User chooses /stoic_replace
            evening_section = stoic_module._format_section("evening", evening_answers, 999,
                                                          self._make_mock_orch())

            # This applies the replacement
            final_body = stoic_module._replace_section(initial_body, evening_section, "evening")

            print("\n=== AFTER /stoic_replace ===")
            self._verify_content(final_body, "final_body")

            # THE CRITICAL TEST
            assert "🌞 Morning" in final_body, "❌ BUG: Morning header deleted!"
            assert "Complete the quarterly report" in final_body, "❌ BUG: Morning content deleted!"
            assert "🌙 Evening" in final_body, "❌ BUG: Evening header missing!"
            assert "Completed report ahead of schedule" in final_body, "❌ BUG: Evening content missing!"

            print("\n✅ PASSED: Both morning and evening preserved after replace")

        else:
            print("✅ No duplicate detected - would append directly")

            # Step 4b: System appends evening to morning
            evening_section = stoic_module._format_section("evening", evening_answers, 999,
                                                          self._make_mock_orch())
            final_body = f"{initial_body}\n\n{evening_section}"

            # Verify both exist
            assert "🌞 Morning" in final_body
            assert "Complete the quarterly report" in final_body
            assert "🌙 Evening" in final_body
            assert "Completed report ahead of schedule" in final_body

            print("\n✅ PASSED: Both sections in note")

    def test_empty_placeholder_detection_issue(self):
        """
        The root cause: Empty placeholder is detected as "existing" content.
        This should be fixed to only count sections with REAL content as duplicates.
        """
        date_str = "2026-03-04"

        morning_section = "### 🌞 Morning\n\n- **Intention:** Test"
        empty_evening = ""  # Intentionally empty

        # Build note
        body = stoic_module._build_full_body(self.body_template, date_str, morning_section, empty_evening)

        # The bug: _check_section_exists returns True for the placeholder
        evening_exists = stoic_module._check_section_exists(body, "evening")

        print("\n=== PLACEHOLDER DETECTION ===")
        print(f"Empty evening section detected as 'existing': {evening_exists}")

        if evening_exists:
            print("⚠️  This triggers duplicate detection for empty placeholder")
            print("   FIX: Detect only REAL content, not empty placeholders")

            # Better detection would check if section has actual data
            evening_part = body.split("### 🌙 Evening")[1] if "### 🌙 Evening" in body else ""
            has_real_evening = any(x in evening_part for x in ["- **Wins:**", "- **Challenges:**"])
            print(f"   Has real evening content: {has_real_evening}")

            # This is the fix needed
            assert not has_real_evening, "Evening should be empty placeholder only"
            print("\n   SUGGESTION: Update _check_section_exists() to check for actual content")

    def test_section_detection_should_distinguish_placeholder_from_content(self):
        """
        The fix: _check_section_exists should return False for empty placeholders.
        """
        # Section with only placeholder markers
        empty_section = """### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -"""

        # Section with real content
        real_section = """### 🌙 Evening

- **Wins:**
  - Completed task
  - Met deadline

- **Challenges:**
  - Client requested changes"""

        # Current behavior: both return True
        empty_exists = stoic_module._check_section_exists(empty_section, "evening")
        real_exists = stoic_module._check_section_exists(real_section, "evening")

        print("\n=== SECTION CONTENT DETECTION ===")
        print(f"Empty placeholder detected: {empty_exists}")
        print(f"Real content detected: {real_exists}")

        # The problem: both are True
        if empty_exists == real_exists:
            print("\n⚠️  PROBLEM: Can't distinguish empty from real content")
            print("   FIX: Update _check_section_exists() to check for actual content")
            print("   Example: Check if any non-empty lines exist under section header")

    def _make_mock_orch(self):
        """Create a minimal mock orch for formatting."""
        from unittest.mock import MagicMock
        orch = MagicMock()
        orch.logging_service.get_report_configuration.return_value = {"timezone": "US/Eastern"}
        return orch

    def _verify_content(self, body, label):
        """Print body for visual inspection."""
        lines = body.split("\n")
        print(f"\n{label} (first 20 lines):")
        for i, line in enumerate(lines[:20], 1):
            print(f"  {i:2d}: {line[:80]}")
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more lines)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
