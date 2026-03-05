"""
Validation tests for BF-008 fix: Smart duplicate detection.

This test suite validates that the improved _check_section_exists()
function correctly distinguishes between empty placeholders and real content,
allowing morning and evening reflections to coexist without false duplicate warnings.
"""

from __future__ import annotations

import unittest

from src.handlers import stoic as stoic_module


class TestBF008FixSmartDuplicateDetection(unittest.TestCase):
    """Test that empty placeholders don't trigger false duplicate warnings."""

    def test_empty_evening_not_detected_as_duplicate(self):
        """Empty evening placeholder should NOT be treated as existing content."""
        # Note created with morning only
        note_with_empty_evening = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning (09:00)

- **Intention:**
  Be focused

- **Focus:**
  Complete report

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        # The fix: empty placeholder should NOT trigger duplicate warning
        evening_exists = stoic_module._check_section_exists(note_with_empty_evening, "evening")

        self.assertFalse(
            evening_exists,
            "Empty evening placeholder should NOT be treated as existing content"
        )

    def test_real_evening_detected_as_duplicate(self):
        """Real evening content SHOULD be detected as existing."""
        note_with_real_evening = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning

- **Intention:**
  Be focused

### 🌙 Evening

- **Wins:**
  - Completed report

- **Challenges:**
  - Meeting ran long"""

        # This SHOULD be detected as existing
        evening_exists = stoic_module._check_section_exists(note_with_real_evening, "evening")

        self.assertTrue(
            evening_exists,
            "Real evening content SHOULD be detected as existing"
        )

    def test_morning_and_evening_coexist_without_false_duplicate(self):
        """User can save morning then evening without false duplicate warning."""
        # Step 1: Morning saves with empty evening placeholder
        morning_note = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning

- **Intention:** Start strong

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -"""

        # Step 2: User tries to save evening
        # OLD BEHAVIOR: Would trigger duplicate prompt (false positive)
        # NEW BEHAVIOR: Should allow saving without duplicate prompt
        should_prompt = stoic_module._check_section_exists(morning_note, "evening")

        self.assertFalse(
            should_prompt,
            "Should NOT prompt for duplicate when evening is just placeholder"
        )

        # User can now append the new evening content directly
        new_evening = """### 🌙 Evening

- **Wins:**
  - Completed work
  - Met deadline

- **Challenges:**
  - Time management

- **Lesson Learned:**
  - Plan better"""

        updated_note = f"{morning_note}\n\n{new_evening}"

        # Verify both exist
        self.assertIn("Start strong", updated_note)
        self.assertIn("Completed work", updated_note)

    def test_empty_morning_not_detected_as_duplicate(self):
        """Empty morning placeholder should NOT be treated as existing content."""
        note_with_empty_morning = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning

- **Intention:**
  -

- **Focus:**
  -

### 🌙 Evening

- **Wins:**
  - Good day"""

        morning_exists = stoic_module._check_section_exists(note_with_empty_morning, "morning")

        self.assertFalse(
            morning_exists,
            "Empty morning placeholder should NOT trigger duplicate warning"
        )

    def test_partial_morning_with_empty_evening(self):
        """Partially filled morning with empty evening should not trigger false duplicate."""
        partial_note = """# 2026-03-04

### 🌞 Morning

- **Intention:**
  - Be calm

- **Focus:**
  -

### 🌙 Evening

- **Wins:**
  -"""

        morning_exists = stoic_module._check_section_exists(partial_note, "morning")
        evening_exists = stoic_module._check_section_exists(partial_note, "evening")

        self.assertTrue(morning_exists, "Partial morning content should be detected")
        self.assertFalse(evening_exists, "Empty evening should not trigger duplicate")

    def test_edge_case_only_section_headers(self):
        """Note with only section headers and labels (no actual content)."""
        headers_only = """### 🌙 Evening

- **Wins:**

- **Challenges:**

- **Lesson Learned:**"""

        has_content = stoic_module._check_section_exists(headers_only, "evening")

        self.assertFalse(
            has_content,
            "Headers and labels without data should not count as existing content"
        )

    def test_edge_case_single_dash_bullets(self):
        """Note with only dash bullets (empty items)."""
        dashes_only = """### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        has_content = stoic_module._check_section_exists(dashes_only, "evening")

        self.assertFalse(
            has_content,
            "Dash bullets without actual text should not count as content"
        )

    def test_edge_case_actual_text_after_label(self):
        """Test that text after label colons counts as content."""
        with_inline_content = """### 🌙 Evening

- **Wins:** Completed task

- **Challenges:**
  -"""

        has_content = stoic_module._check_section_exists(with_inline_content, "evening")

        self.assertTrue(
            has_content,
            "Text after label should count as real content"
        )

    def test_whitespace_only_not_content(self):
        """Lines with only whitespace should not count as content."""
        whitespace_only = """### 🌙 Evening

- **Wins:**


- **Challenges:**

- **Lesson Learned:**
  -"""

        has_content = stoic_module._check_section_exists(whitespace_only, "evening")

        self.assertFalse(
            has_content,
            "Whitespace-only lines should not count as content"
        )


class TestBF008WorkflowWithFix(unittest.TestCase):
    """Test complete workflows with the BF-008 fix applied."""

    def test_morning_save_then_evening_save_without_duplicate_prompt(self):
        """
        BF-008 FIX: User can save morning, then evening, without false duplicate prompt.

        Before fix: Evening save would prompt "Do you want to replace/append?"
        After fix: Evening save appends directly without prompting
        """
        # Create a morning note with empty evening
        morning_note_content = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning (09:00)

- **Intention:**
  Be focused and productive

- **Focus:**
  Complete the project

- **Virtue:**
  Diligence and patience

- **Gratitude:**
  - My health
  - My team
  - My opportunities

- **Top 3 Tasks:**
  1. [ ] Write report
  2. [ ] Review code
  3. [ ] Meet client

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        # User tries to save evening
        should_show_duplicate_prompt = stoic_module._check_section_exists(
            morning_note_content, "evening"
        )

        # THE FIX: Should NOT prompt (placeholder doesn't count)
        self.assertFalse(
            should_show_duplicate_prompt,
            "BF-008 FIX: Evening placeholder should not trigger duplicate prompt"
        )

        # Evening content is appended (no duplicate prompt triggered)
        evening_content = """### 🌙 Evening (18:00)

- **Wins:**
  - Completed report ahead of schedule
  - Got positive feedback from client
  - Fixed two bugs

- **Challenges:**
  - Client asked for revisions
  - Meeting ran 30 minutes over

- **Lesson Learned:**
  - Communicate progress earlier in the day
  - Estimate time more accurately"""

        # Since empty evening placeholder exists, it gets replaced with new content
        # (In actual code, this would use the replace logic)
        # Simulate the behavior by replacing the empty evening
        final_note = stoic_module._replace_section(morning_note_content, evening_content, "evening")

        # Verify both sections coexist without data loss
        self.assertIn("Be focused and productive", final_note)
        self.assertIn("Complete the project", final_note)
        self.assertIn("Completed report ahead of schedule", final_note)
        self.assertIn("Communicate progress earlier", final_note)

        # Verify no duplicate evening sections
        evening_count = final_note.count("### 🌙 Evening")
        self.assertEqual(evening_count, 1, "Should have exactly one evening section")

    def test_successive_saves_same_section_correctly_prompts(self):
        """
        If user tries to save evening TWICE with real content,
        should correctly detect and prompt for replace/append.
        """
        first_evening_note = """# 2026-03-04

### 🌙 Evening

- **Wins:**
  - Good work

- **Challenges:**
  - Long day"""

        # First save is already there
        should_prompt = stoic_module._check_section_exists(first_evening_note, "evening")

        # Should CORRECTLY prompt (real content exists)
        self.assertTrue(
            should_prompt,
            "Should prompt when real evening content already exists"
        )

    def test_replace_empty_placeholder_preserves_other_sections(self):
        """HOTFIX validation: Replacing empty placeholder should NOT delete other sections."""
        # Note with morning content and empty evening placeholder
        note_with_placeholder = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning (09:00)

- **Intention:**
  Be focused and productive

- **Focus:**
  Complete the project

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        # New evening content to replace the placeholder
        new_evening = """### 🌙 Evening (18:00)

- **Wins:**
  - Completed report ahead of schedule

- **Challenges:**
  - Client asked for revisions

- **Lesson Learned:**
  - Communicate progress earlier in the day"""

        # Replace the empty evening section
        result = stoic_module._replace_section(note_with_placeholder, new_evening, "evening")

        # Critical: Morning section must still exist
        self.assertIn("### 🌞 Morning", result, "Morning section header deleted!")
        self.assertIn("Be focused and productive", result, "Morning content deleted!")
        self.assertIn("Complete the project", result, "Morning content deleted!")

        # Evening section should be updated
        self.assertIn("### 🌙 Evening (18:00)", result, "New evening section not present!")
        self.assertIn("Completed report ahead of schedule", result, "Evening content not added!")

        # Should have exactly one evening section header
        evening_count = result.count("### 🌙 Evening")
        self.assertEqual(evening_count, 1, "Should have exactly one evening section")


if __name__ == "__main__":
    unittest.main(verbosity=2)
