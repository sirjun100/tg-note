#!/usr/bin/env python3
"""
Integration test for Sprint 5 - Complete tag display workflow

This test verifies the complete flow:
1. Apply tags to a note and differentiate between new and existing
2. Format tags for display in Telegram message
3. Log tag creation to database for audit trail
"""

import unittest
import tempfile
import os
import sys
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from joplin_client import JoplinClient
from logging_service import LoggingService
from unittest.mock import MagicMock, Mock


class TestSprintFiveIntegration(unittest.TestCase):
    """Integration tests for Sprint 5 tag display feature"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.logging_service = LoggingService(db_path=self.db_path)
        self.joplin_client = JoplinClient()
        self.joplin_client.fetch_tags = MagicMock()
        self.joplin_client._get_or_create_tag = MagicMock()
        self.joplin_client._link_tag_to_note = MagicMock()

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_complete_workflow_user_sends_message(self):
        """Test complete workflow when user sends a message with tags"""
        print("\n=== Complete Workflow Test ===")
        print("Scenario: User sends message → LLM generates note with tags → Display tags in response")

        # Step 1: LLM generates note with tags
        user_id = 12345
        note_id = "note_abc123"
        tags_from_llm = ['urgent', 'project', 'meeting']

        print(f"\n1. LLM generated note with tags: {tags_from_llm}")

        # Step 2: Apply tags to note
        existing_tags = [
            {'id': '1', 'title': 'urgent'},
            {'id': '2', 'title': 'ai'}
        ]
        self.joplin_client.fetch_tags.return_value = existing_tags
        self.joplin_client._get_or_create_tag.side_effect = lambda t: f'tag_{t}'
        self.joplin_client._link_tag_to_note.return_value = True

        tag_info = self.joplin_client.apply_tags_and_track_new(note_id, tags_from_llm)

        print(f"\n2. Applied tags to note:")
        print(f"   New tags: {tag_info['new_tags']}")
        print(f"   Existing tags: {tag_info['existing_tags']}")
        print(f"   Success: {tag_info['success']}")

        # Verify tag differentiation
        self.assertTrue(tag_info['success'])
        self.assertIn('urgent', tag_info['existing_tags'])
        self.assertIn('project', tag_info['new_tags'])
        self.assertIn('meeting', tag_info['new_tags'])

        # Step 3: Format tags for display
        formatted_tags = self._format_tags_for_display(tag_info)
        print(f"\n3. Formatted for display: {formatted_tags}")

        # Verify formatting
        self.assertIn("urgent", formatted_tags)
        self.assertIn("project (new)", formatted_tags)
        self.assertIn("meeting (new)", formatted_tags)

        # Step 4: Create success message with tags
        success_message = f"✅ Note created: 'Meeting Notes' in folder 'Work'\nTags: {formatted_tags}"
        print(f"\n4. Success message:\n{success_message}")

        # Step 5: Log tag creation to database
        for tag_name in tag_info['new_tags']:
            self.logging_service.log_tag_creation(
                user_id=user_id,
                note_id=note_id,
                tag_name=tag_name,
                is_new=True
            )

        for tag_name in tag_info['existing_tags']:
            self.logging_service.log_tag_creation(
                user_id=user_id,
                note_id=note_id,
                tag_name=tag_name,
                is_new=False
            )

        print(f"\n5. Logged tag creation to database")

        # Step 6: Verify database contains audit trail
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ?',
                (user_id, note_id)
            )
            total_tags = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ? AND is_new_tag = 1',
                (user_id, note_id)
            )
            new_tag_count = cursor.fetchone()[0]

            cursor.execute(
                'SELECT tag_name FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ? ORDER BY created_at',
                (user_id, note_id)
            )
            logged_tags = [row[0] for row in cursor.fetchall()]

        print(f"\n6. Database audit trail:")
        print(f"   Total tags logged: {total_tags}")
        print(f"   New tags logged: {new_tag_count}")
        print(f"   Tags: {logged_tags}")

        # Final verification
        self.assertEqual(total_tags, 3)
        self.assertEqual(new_tag_count, 2)
        self.assertEqual(set(logged_tags), set(tags_from_llm))

        print("\n✅ Complete workflow test PASSED")

    def test_workflow_with_no_new_tags(self):
        """Test workflow when all tags already exist"""
        print("\n=== Workflow with No New Tags ===")

        user_id = 12345
        note_id = "note_def456"
        tags_from_llm = ['urgent', 'important']

        # All tags already exist
        existing_tags = [
            {'id': '1', 'title': 'urgent'},
            {'id': '2', 'title': 'important'}
        ]
        self.joplin_client.fetch_tags.return_value = existing_tags
        self.joplin_client._get_or_create_tag.side_effect = lambda t: f'tag_{t}'
        self.joplin_client._link_tag_to_note.return_value = True

        tag_info = self.joplin_client.apply_tags_and_track_new(note_id, tags_from_llm)

        print(f"Applied tags: {tag_info['all_tags']}")
        print(f"New tags: {tag_info['new_tags']}")
        print(f"Existing tags: {tag_info['existing_tags']}")

        formatted = self._format_tags_for_display(tag_info)
        print(f"Formatted: {formatted}")

        # Verify no "(new)" suffix since all are existing
        self.assertNotIn("(new)", formatted)
        self.assertEqual(formatted, "urgent, important")

        print("✅ No new tags workflow test PASSED")

    def test_workflow_with_empty_tags(self):
        """Test workflow when note has no tags"""
        print("\n=== Workflow with No Tags ===")

        user_id = 12345
        note_id = "note_ghi789"
        tags_from_llm = []

        self.joplin_client.fetch_tags.return_value = []

        tag_info = self.joplin_client.apply_tags_and_track_new(note_id, tags_from_llm)

        print(f"Applied tags: {tag_info['all_tags']}")

        formatted = self._format_tags_for_display(tag_info)
        print(f"Formatted: '{formatted}'")

        # Verify empty result
        self.assertEqual(formatted, "")

        success_message = f"✅ Note created: 'Meeting Notes' in folder 'Work'"
        print(f"Success message (no tag line):\n{success_message}")

        print("✅ Empty tags workflow test PASSED")

    def test_workflow_with_special_character_tags(self):
        """Test workflow with special characters in tag names"""
        print("\n=== Workflow with Special Character Tags ===")

        user_id = 12345
        note_id = "note_jkl012"
        tags_from_llm = ['urgent/high', 'project-alpha', 'v2.0']

        self.joplin_client.fetch_tags.return_value = []
        self.joplin_client._get_or_create_tag.side_effect = lambda t: f'tag_{t}'
        self.joplin_client._link_tag_to_note.return_value = True

        tag_info = self.joplin_client.apply_tags_and_track_new(note_id, tags_from_llm)

        print(f"Applied tags: {tag_info['all_tags']}")

        formatted = self._format_tags_for_display(tag_info)
        print(f"Formatted: {formatted}")

        # Verify special characters are preserved
        self.assertIn("urgent/high", formatted)
        self.assertIn("project-alpha", formatted)
        self.assertIn("v2.0", formatted)

        # Log to database to ensure special characters are handled
        for tag_name in tag_info['new_tags']:
            self.logging_service.log_tag_creation(
                user_id=user_id,
                note_id=note_id,
                tag_name=tag_name,
                is_new=True
            )

        # Verify database stored special characters correctly
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT tag_name FROM tag_creation_history WHERE tag_name = ?',
                ('urgent/high',)
            )
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'urgent/high')

        print("✅ Special character tags workflow test PASSED")

    @staticmethod
    def _format_tags_for_display(tag_info):
        """Helper to format tags for display"""
        if not tag_info.get('all_tags'):
            return ""

        new_tag_set = set(tag_info.get('new_tags', []))
        formatted_tags = []

        for tag in tag_info.get('all_tags', []):
            if tag in new_tag_set:
                formatted_tags.append(f"{tag} (new)")
            else:
                formatted_tags.append(tag)

        return ", ".join(formatted_tags)


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("SPRINT 5 INTEGRATION TESTS - Tag Display Feature")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestSprintFiveIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("✅ Tag differentiation works correctly")
        print("✅ Tag formatting for display works")
        print("✅ Database logging captures all tag events")
        print("✅ Special characters are handled properly")
        print("✅ Empty tag lists are handled correctly")
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
