#!/usr/bin/env python3
"""
Unit tests for Sprint 5 - Display Tags in AI Response

Tests for:
- apply_tags_and_track_new() method in JoplinClient
- _format_tag_display() method in TelegramOrchestrator
- log_tag_creation() method in LoggingService
"""

import unittest
import tempfile
import os
import sys
import sqlite3
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from joplin_client import JoplinClient
from logging_service import LoggingService


class TestApplyTagsAndTrackNew(unittest.TestCase):
    """Test JoplinClient.apply_tags_and_track_new() method"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = JoplinClient()
        # Mock the _make_request method to avoid actual API calls
        self.client._make_request = MagicMock()

    def test_apply_tags_with_all_new_tags(self):
        """Test applying tags when all tags are new"""
        # Mock fetch_tags to return empty list (no existing tags)
        self.client.fetch_tags = MagicMock(return_value=[])
        self.client._get_or_create_tag = MagicMock(side_effect=['tag1_id', 'tag2_id', 'tag3_id'])
        self.client._link_tag_to_note = MagicMock(return_value=True)

        result = self.client.apply_tags_and_track_new('note_123', ['urgent', 'project', 'ai'])

        # All tags should be marked as new
        self.assertTrue(result['success'])
        self.assertEqual(result['new_tags'], ['urgent', 'project', 'ai'])
        self.assertEqual(result['existing_tags'], [])
        self.assertEqual(result['all_tags'], ['urgent', 'project', 'ai'])

    def test_apply_tags_with_all_existing_tags(self):
        """Test applying tags when all tags already exist"""
        # Mock fetch_tags to return existing tags
        existing_tags = [
            {'id': '1', 'title': 'urgent'},
            {'id': '2', 'title': 'project'},
            {'id': '3', 'title': 'ai'}
        ]
        self.client.fetch_tags = MagicMock(return_value=existing_tags)
        self.client._get_or_create_tag = MagicMock(side_effect=['tag1_id', 'tag2_id', 'tag3_id'])
        self.client._link_tag_to_note = MagicMock(return_value=True)

        result = self.client.apply_tags_and_track_new('note_123', ['urgent', 'project', 'ai'])

        # All tags should be marked as existing
        self.assertTrue(result['success'])
        self.assertEqual(result['new_tags'], [])
        self.assertEqual(result['existing_tags'], ['urgent', 'project', 'ai'])
        self.assertEqual(result['all_tags'], ['urgent', 'project', 'ai'])

    def test_apply_tags_with_mixed_tags(self):
        """Test applying tags when some are new and some already exist"""
        # Mock fetch_tags with some existing tags
        existing_tags = [
            {'id': '1', 'title': 'urgent'},
            {'id': '2', 'title': 'ai'}
        ]
        self.client.fetch_tags = MagicMock(return_value=existing_tags)
        self.client._get_or_create_tag = MagicMock(side_effect=['tag1_id', 'tag2_id', 'tag3_id'])
        self.client._link_tag_to_note = MagicMock(return_value=True)

        result = self.client.apply_tags_and_track_new('note_123', ['urgent', 'project', 'ai'])

        # Should differentiate between new and existing
        self.assertTrue(result['success'])
        self.assertEqual(result['new_tags'], ['project'])
        self.assertEqual(result['existing_tags'], ['urgent', 'ai'])
        self.assertEqual(result['all_tags'], ['urgent', 'project', 'ai'])

    def test_apply_tags_with_empty_list(self):
        """Test applying empty tag list"""
        self.client.fetch_tags = MagicMock(return_value=[])

        result = self.client.apply_tags_and_track_new('note_123', [])

        self.assertTrue(result['success'])
        self.assertEqual(result['new_tags'], [])
        self.assertEqual(result['existing_tags'], [])
        self.assertEqual(result['all_tags'], [])

    def test_apply_tags_failure_handling(self):
        """Test handling when tag application fails"""
        self.client.fetch_tags = MagicMock(return_value=[])
        self.client._get_or_create_tag = MagicMock(side_effect=['tag1_id', None, 'tag3_id'])
        self.client._link_tag_to_note = MagicMock(return_value=True)

        result = self.client.apply_tags_and_track_new('note_123', ['urgent', 'project', 'ai'])

        # Should mark as failed but still return partial results
        # When _get_or_create_tag returns None, the tag is not added to new_tags or existing_tags
        self.assertFalse(result['success'])
        # Only urgent and ai should be in new_tags (project failed)
        self.assertEqual(len(result['new_tags']), 2)

    def test_apply_tags_single_tag(self):
        """Test applying a single tag"""
        self.client.fetch_tags = MagicMock(return_value=[])
        self.client._get_or_create_tag = MagicMock(return_value='tag_id')
        self.client._link_tag_to_note = MagicMock(return_value=True)

        result = self.client.apply_tags_and_track_new('note_123', ['urgent'])

        self.assertTrue(result['success'])
        self.assertEqual(result['new_tags'], ['urgent'])
        self.assertEqual(result['all_tags'], ['urgent'])


class TestFormatTagDisplay(unittest.TestCase):
    """Test tag display formatting"""

    def test_format_all_new_tags(self):
        """Test formatting when all tags are new"""
        tag_info = {
            'new_tags': ['urgent', 'project', 'ai'],
            'existing_tags': [],
            'all_tags': ['urgent', 'project', 'ai']
        }
        # Create a simple function to test the formatting logic
        result = self._format_tags(tag_info)
        self.assertEqual(result, "urgent (new), project (new), ai (new)")

    def test_format_all_existing_tags(self):
        """Test formatting when all tags are existing"""
        tag_info = {
            'new_tags': [],
            'existing_tags': ['urgent', 'project', 'ai'],
            'all_tags': ['urgent', 'project', 'ai']
        }
        result = self._format_tags(tag_info)
        self.assertEqual(result, "urgent, project, ai")

    def test_format_mixed_tags(self):
        """Test formatting when tags are mixed"""
        tag_info = {
            'new_tags': ['project'],
            'existing_tags': ['urgent', 'ai'],
            'all_tags': ['urgent', 'project', 'ai']
        }
        result = self._format_tags(tag_info)
        # The order should follow all_tags
        self.assertIn('project (new)', result)
        self.assertIn('urgent,', result)
        self.assertIn('ai', result)

    def test_format_single_new_tag(self):
        """Test formatting a single new tag"""
        tag_info = {
            'new_tags': ['urgent'],
            'existing_tags': [],
            'all_tags': ['urgent']
        }
        result = self._format_tags(tag_info)
        self.assertEqual(result, "urgent (new)")

    def test_format_single_existing_tag(self):
        """Test formatting a single existing tag"""
        tag_info = {
            'new_tags': [],
            'existing_tags': ['urgent'],
            'all_tags': ['urgent']
        }
        result = self._format_tags(tag_info)
        self.assertEqual(result, "urgent")

    def test_format_empty_tags(self):
        """Test formatting empty tag list"""
        tag_info = {
            'new_tags': [],
            'existing_tags': [],
            'all_tags': []
        }
        result = self._format_tags(tag_info)
        self.assertEqual(result, "")

    def test_format_tags_with_special_characters(self):
        """Test formatting tags with special characters"""
        tag_info = {
            'new_tags': ['urgent-high', 'project/alpha'],
            'existing_tags': [],
            'all_tags': ['urgent-high', 'project/alpha']
        }
        result = self._format_tags(tag_info)
        self.assertIn('urgent-high (new)', result)
        self.assertIn('project/alpha (new)', result)

    @staticmethod
    def _format_tags(tag_info):
        """Helper method to test formatting logic"""
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


class TestLogTagCreation(unittest.TestCase):
    """Test LoggingService.log_tag_creation() method"""

    def setUp(self):
        """Set up test fixtures with temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Create logging service with temp database
        self.logging_service = LoggingService(db_path=self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_log_new_tag_creation(self):
        """Test logging a newly created tag"""
        self.logging_service.log_tag_creation(
            user_id=12345,
            note_id='note_123',
            tag_name='urgent',
            is_new=True
        )

        # Verify tag was logged
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM tag_creation_history WHERE user_id = ? AND tag_name = ?',
                (12345, 'urgent')
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[2], 'note_123')  # joplin_note_id
        self.assertEqual(row[3], 'urgent')     # tag_name
        self.assertEqual(row[4], 1)            # is_new_tag (True)

    def test_log_existing_tag_application(self):
        """Test logging application of existing tag"""
        self.logging_service.log_tag_creation(
            user_id=12345,
            note_id='note_123',
            tag_name='project',
            is_new=False
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM tag_creation_history WHERE user_id = ? AND tag_name = ?',
                (12345, 'project')
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[4], 0)  # is_new_tag (False)

    def test_log_multiple_tags(self):
        """Test logging multiple tags for same note"""
        tags = ['urgent', 'project', 'ai']

        for tag in tags:
            self.logging_service.log_tag_creation(
                user_id=12345,
                note_id='note_123',
                tag_name=tag,
                is_new=True
            )

        # Verify all tags were logged
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ?',
                (12345, 'note_123')
            )
            count = cursor.fetchone()[0]

        self.assertEqual(count, 3)

    def test_log_tags_different_users(self):
        """Test logging tags for different users"""
        self.logging_service.log_tag_creation(
            user_id=12345,
            note_id='note_123',
            tag_name='urgent',
            is_new=True
        )
        self.logging_service.log_tag_creation(
            user_id=67890,
            note_id='note_456',
            tag_name='urgent',
            is_new=True
        )

        # Verify both were logged
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tag_creation_history')
            count = cursor.fetchone()[0]

        self.assertEqual(count, 2)

    def test_log_tag_with_special_characters(self):
        """Test logging tags with special characters"""
        self.logging_service.log_tag_creation(
            user_id=12345,
            note_id='note_123',
            tag_name='project/alpha-v2',
            is_new=True
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT tag_name FROM tag_creation_history WHERE tag_name = ?',
                ('project/alpha-v2',)
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'project/alpha-v2')

    def test_log_tag_timestamp(self):
        """Test that timestamp is recorded"""
        self.logging_service.log_tag_creation(
            user_id=12345,
            note_id='note_123',
            tag_name='urgent',
            is_new=True
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT created_at FROM tag_creation_history WHERE tag_name = ?',
                ('urgent',)
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        timestamp = row[0]
        # Verify timestamp is a valid ISO format
        try:
            datetime.fromisoformat(timestamp)
        except:
            self.fail(f"Invalid timestamp format: {timestamp}")


class TestTagIntegration(unittest.TestCase):
    """Integration tests for complete tag workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.logging_service = LoggingService(db_path=self.db_path)

    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except:
                pass

    def test_complete_tag_workflow(self):
        """Test complete workflow: apply tags and log them"""
        # Simulate applying new and existing tags
        tag_info = {
            'success': True,
            'new_tags': ['urgent', 'project'],
            'existing_tags': ['ai'],
            'all_tags': ['urgent', 'project', 'ai']
        }

        user_id = 12345
        note_id = 'note_123'

        # Log all tags (simulating what telegram_orchestrator would do)
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

        # Verify database has correct entries
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ?',
                (user_id, note_id)
            )
            total_count = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ? AND is_new_tag = 1',
                (user_id, note_id)
            )
            new_count = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(*) FROM tag_creation_history WHERE user_id = ? AND joplin_note_id = ? AND is_new_tag = 0',
                (user_id, note_id)
            )
            existing_count = cursor.fetchone()[0]

        self.assertEqual(total_count, 3)
        self.assertEqual(new_count, 2)
        self.assertEqual(existing_count, 1)

    def test_tag_display_format_integration(self):
        """Test that formatted tags would display correctly"""
        tag_info = {
            'success': True,
            'new_tags': ['urgent', 'project'],
            'existing_tags': ['ai'],
            'all_tags': ['urgent', 'project', 'ai']
        }

        # Simulate the formatting that would happen in telegram_orchestrator
        formatted = self._format_tag_display(tag_info)
        expected = "urgent (new), project (new), ai"

        self.assertEqual(formatted, expected)

    @staticmethod
    def _format_tag_display(tag_info):
        """Simulate the formatting logic from telegram_orchestrator"""
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


def run_tests():
    """Run all unit tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestApplyTagsAndTrackNew))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatTagDisplay))
    suite.addTests(loader.loadTestsFromTestCase(TestLogTagCreation))
    suite.addTests(loader.loadTestsFromTestCase(TestTagIntegration))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
