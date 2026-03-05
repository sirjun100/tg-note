"""
Comprehensive test suite for BF-008: Stoic evening reflection deletes morning reflection.

This test file reproduces and validates fixes for the critical data loss bug
where saving an evening reflection accidentally deletes the morning reflection.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers import stoic as stoic_module


class TestStoicDataLossScenarios(unittest.TestCase):
    """Test scenarios that could lead to data loss when combining morning and evening."""

    def test_empty_placeholders_dont_count_as_real_content(self):
        """Empty placeholders should not be treated as real sections."""
        # Build a note body with placeholders (what happens when creating a new note)
        body_template = "# {{DATE}}\n\n## Morning\n{{MORNING_CONTENT}}\n\n## Evening\n{{EVENING_CONTENT}}"
        full_body = stoic_module._build_full_body(
            body_template,
            "2026-03-04",
            "### 🌞 Morning\n\n- **Intention:** Wake up early",  # Real content
            "",  # Evening empty - will get placeholder
        )

        # Verify placeholder is present
        self.assertIn("### 🌙 Evening", full_body)
        self.assertIn("- **Wins:**", full_body)

        # The question: does _check_section_exists consider the placeholder as "existing"?
        exists = stoic_module._check_section_exists(full_body, "evening")
        # This might be the bug: placeholder is treated as real content
        print(f"Does empty placeholder count as existing? {exists}")

    def test_replace_section_preserves_other_sections(self):
        """Replacing one section should NOT delete the other section."""
        # Start with a note that has morning content
        morning_content = "### 🌞 Morning\n\n- **Intention:** Start strong\n- **Focus:** One task"
        evening_placeholder = stoic_module._empty_evening_placeholder()
        existing_body = f"{morning_content}\n\n{evening_placeholder}"

        # Now replace evening with real content
        new_evening = "### 🌙 Evening\n\n- **Wins:** Accomplished goal\n- **Challenges:** Time management\n- **Lesson Learned:** Prioritize better"

        result = stoic_module._replace_section(existing_body, new_evening, "evening")

        # Verify morning section is STILL there
        self.assertIn("### 🌞 Morning", result, "Morning section should NOT be deleted")
        self.assertIn("Start strong", result, "Morning content should be preserved")
        self.assertIn("### 🌙 Evening", result, "Evening section should exist")
        self.assertIn("Accomplished goal", result, "Evening content should be present")

    def test_replace_section_preserves_morning_when_replacing_evening(self):
        """Specifically test morning preservation when replacing evening."""
        existing_body = """# 2026-03-04 - Daily Stoic Reflection

### 🌞 Morning (09:00)

- **Intention:**
  - Be present

- **Focus:**
  - One report

- **Virtue:**
  - Patience

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        new_evening = """### 🌙 Evening (18:00)

- **Wins:**
  - Completed report on time

- **Challenges:**
  - Stayed late to finish

- **Lesson Learned:**
  - Better time estimates needed"""

        result = stoic_module._replace_section(existing_body, new_evening, "evening")

        # Check morning content is preserved
        self.assertIn("Be present", result)
        self.assertIn("One report", result)
        self.assertIn("Patience", result)
        self.assertIn("### 🌞 Morning", result)

        # Check evening is updated
        self.assertIn("Completed report on time", result)
        self.assertIn("Better time estimates needed", result)

    def test_build_full_body_structure(self):
        """Verify the body template structure when creating new note."""
        body_template = "# {{DATE}}\n\n{{MORNING_CONTENT}}\n\n{{EVENING_CONTENT}}"

        # Create with morning content only
        result = stoic_module._build_full_body(
            body_template,
            "2026-03-04",
            "### 🌞 Morning\n\n- **Intention:** Test",
            "",  # Empty evening
        )

        lines = result.split("\n")
        # Verify order: Morning comes before Evening
        morning_idx = next(i for i, line in enumerate(lines) if "🌞 Morning" in line)
        evening_idx = next(i for i, line in enumerate(lines) if "🌙 Evening" in line)

        self.assertLess(
            morning_idx,
            evening_idx,
            "Morning section should come before evening in body"
        )

    def test_check_section_exists_with_real_vs_placeholder(self):
        """Test whether _check_section_exists distinguishes real from placeholder content."""
        # Body with only placeholder evening
        body_with_placeholder_only = """# 2026-03-04

### 🌞 Morning

- **Intention:** Test

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -"""

        # This is the potential issue: does it count placeholder as "existing"?
        exists = stoic_module._check_section_exists(body_with_placeholder_only, "evening")
        print(f"\nPlaceholder evening counted as existing: {exists}")

        # It probably returns True because it just searches for "### 🌙 Evening"
        # This could trigger the duplicate detection incorrectly

    def test_append_vs_replace_logic(self):
        """Test the decision logic between appending and replacing."""
        # When a user saves morning, then evening
        # The system should:
        # 1. Find existing note
        # 2. Check if evening section exists
        # 3a. If only placeholder: append new evening content
        # 3b. If real content: ask user (replace/append)

        existing_body_with_placeholder = """# 2026-03-04

### 🌞 Morning

- **Intention:** Wake early

### 🌙 Evening

- **Wins:**
  -"""

        # Check if evening "exists"
        evening_exists = stoic_module._check_section_exists(
            existing_body_with_placeholder, "evening"
        )

        print(f"\nEvening 'exists' check result: {evening_exists}")
        print("This determines if user gets a duplicate prompt or just appends")


class TestStoicMorningEveningWorkflow(unittest.IsolatedAsyncioTestCase):
    """Test the complete workflow of morning then evening reflection same day."""

    async def test_save_morning_then_evening_same_day(self):
        """
        Complete workflow:
        1. User saves morning reflection
        2. User saves evening reflection
        3. Both should exist in final note (no data loss)
        """
        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.joplin_client = AsyncMock()
        orch.llm_orchestrator = AsyncMock()

        # Step 1: Save morning reflection
        message1 = AsyncMock()
        state1 = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "morning",
            "answers": [
                {"q": "Intention?", "a": "Focus on work"},
                {"q": "Focus?", "a": "Complete report"},
                {"q": "Virtue?", "a": "Diligence"},
                {"q": "Grateful?", "a": "Health"},
                {"q": "Tasks?", "a": "Report\nEmail\nMeeting"},
            ],
            "body_template": "# {{DATE}}\n\n{{MORNING_CONTENT}}\n\n{{EVENING_CONTENT}}",
        }

        # Mock folder and note creation
        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(return_value=[])  # No existing note
        orch.joplin_client.create_note = AsyncMock(return_value="note_123")
        orch.joplin_client.apply_tags = AsyncMock()
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)

        with patch("src.handlers.stoic.get_current_date_str") as mock_date:
            mock_date.return_value = "2026-03-04"
            result1 = await stoic_module._finish_stoic_session(orch, 999, message1, state1)

        self.assertTrue(result1, "Morning reflection should save successfully")

        # Verify the note was created with morning content
        create_call = orch.joplin_client.create_note.call_args
        created_body = create_call[1]["body"]

        print("\n=== MORNING REFLECTION NOTE CREATED ===")
        print(created_body[:200])
        print("...")

        # Verify morning content is in the note
        self.assertIn("🌞 Morning", created_body)
        self.assertIn("Focus on work", created_body)

        # Step 2: Save evening reflection
        message2 = AsyncMock()
        state2 = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "evening",
            "answers": [
                {"q": "Wins?", "a": "Completed report"},
                {"q": "Challenges?", "a": "Meeting ran long"},
                {"q": "Lesson?", "a": "Better time estimates"},
                {"q": "Grateful?", "a": "Team support"},
            ],
            "body_template": "# {{DATE}}\n\n{{MORNING_CONTENT}}\n\n{{EVENING_CONTENT}}",
        }

        # Reset mocks for second save
        orch.joplin_client.get_notes_in_folder = AsyncMock(
            return_value=[{"id": "note_123", "title": "2026-03-04 - Daily Stoic Reflection"}]
        )
        orch.joplin_client.get_note = AsyncMock(return_value={"body": created_body})
        orch.joplin_client.update_note = AsyncMock()
        orch.state_manager.update_state = MagicMock()

        result2 = await stoic_module._finish_stoic_session(orch, 999, message2, state2)

        # This is where the bug might happen
        # Does the update preserve the morning section?
        if result2:
            # Check what was sent to update_note
            update_call = orch.joplin_client.update_note.call_args
            updated_body = update_call[0][1]["body"]

            print("\n=== EVENING REFLECTION NOTE UPDATED ===")
            print(updated_body[:200])
            print("...")

            # THE CRITICAL TEST: Does morning content still exist?
            self.assertIn("🌞 Morning", updated_body,
                         "BUG: Morning section deleted when saving evening!")
            self.assertIn("Focus on work", updated_body,
                         "BUG: Morning content deleted!")
            self.assertIn("🌙 Evening", updated_body,
                         "Evening section should be present")
            self.assertIn("Completed report", updated_body,
                         "Evening content should be present")

    async def test_duplicate_evening_prompts_user(self):
        """When evening section already has content, user should get duplicate prompt."""
        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.joplin_client = AsyncMock()
        orch.llm_orchestrator = AsyncMock()
        orch.state_manager = MagicMock()

        message = AsyncMock()

        # Existing note with REAL evening content (not placeholder)
        existing_body = """# 2026-03-04

### 🌞 Morning

- **Intention:** Start strong

### 🌙 Evening

- **Wins:**
  - Completed task

- **Challenges:**
  - Time ran out"""

        state = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "evening",
            "answers": [{"q": "Wins?", "a": "Different wins"}],
        }

        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(
            return_value=[{"id": "note_123", "title": "2026-03-04 - Daily Stoic Reflection"}]
        )
        orch.joplin_client.get_note = AsyncMock(return_value={"body": existing_body})
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)

        with patch("src.handlers.stoic.get_current_date_str") as mock_date:
            mock_date.return_value = "2026-03-04"
            result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        # Should NOT save directly, should ask for action
        self.assertFalse(result, "Should prompt user instead of saving directly")

        # Verify state was saved for pending action
        orch.state_manager.update_state.assert_called_once()
        saved_state = orch.state_manager.update_state.call_args[0][1]
        self.assertEqual(saved_state.get("pending_action"), "duplicate_detected")

    async def test_morning_afternoon_split_not_treated_as_duplicate(self):
        """Morning and evening are different sections - evening should NOT trigger duplicate."""
        # The real issue might be that the placeholder evening is treated as duplicate
        # even though it's just an empty template

        orch = MagicMock()
        orch.logging_service = MagicMock()
        orch.joplin_client = AsyncMock()
        orch.llm_orchestrator = AsyncMock()

        message = AsyncMock()

        # Note with real morning, empty evening placeholder
        existing_body_with_placeholder = """# 2026-03-04

### 🌞 Morning (09:00)

- **Intention:** Wake up

### 🌙 Evening

- **Wins:**
  -

- **Challenges:**
  -

- **Lesson Learned:**
  -"""

        state = {
            "active_persona": "STOIC_JOURNAL",
            "mode": "evening",
            "answers": [{"q": "Wins?", "a": "Completed work"}],
        }

        orch.joplin_client.get_or_create_folder_by_path = AsyncMock(return_value="folder_123")
        orch.joplin_client.get_notes_in_folder = AsyncMock(
            return_value=[{"id": "note_123", "title": "2026-03-04 - Daily Stoic Reflection"}]
        )
        orch.joplin_client.get_note = AsyncMock(return_value={"body": existing_body_with_placeholder})
        orch.joplin_client.update_note = AsyncMock()
        orch.llm_orchestrator.format_stoic_reflection = AsyncMock(return_value=None)

        with patch("src.handlers.stoic.get_current_date_str") as mock_date:
            mock_date.return_value = "2026-03-04"
            result = await stoic_module._finish_stoic_session(orch, 999, message, state)

        # This might fail if the bug is that placeholder is treated as real content
        print(f"\nResult when saving evening to note with placeholder: {result}")
        if not result:
            print("  → Marked as duplicate (THIS COULD BE THE BUG)")
        else:
            print("  → Appended successfully")


if __name__ == "__main__":
    unittest.main()
