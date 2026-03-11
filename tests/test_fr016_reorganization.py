"""
Integration tests for FR-016: Joplin Database Reorganization

Tests cover:
- PARA structure initialization
- Migration plan generation
- Conflict detection
- Migration execution
- Batch enrichment operations
- Tag auditing
- Error handling and recovery
"""

import unittest
from unittest.mock import AsyncMock, Mock

from src.enrichment_service import EnrichmentService, EnrichmentStats
from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator
from src.reorg_orchestrator import ReorgOrchestrator, TemplateFolderException


class TestReorgOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Test suite for ReorgOrchestrator"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_joplin = Mock(spec=JoplinClient)
        self.mock_llm = Mock(spec=LLMOrchestrator)
        self.orchestrator = ReorgOrchestrator(self.mock_joplin, self.mock_llm)

    def test_get_available_templates(self):
        """Test getting list of available PARA templates"""
        templates = self.orchestrator.get_available_templates()

        self.assertIsInstance(templates, list)
        self.assertGreater(len(templates), 0)
        self.assertIn("status", templates)
        self.assertIn("roles", templates)

    async def test_initialize_structure_valid_template(self):
        """Test successful PARA structure initialization"""
        self.mock_joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder_id_123")

        result = await self.orchestrator.initialize_structure("status")

        self.assertTrue(result)
        self.assertGreater(self.mock_joplin.get_or_create_folder_by_path.call_count, 0)

    async def test_initialize_structure_invalid_template(self):
        """Test initialization with invalid template name"""
        with self.assertRaises(TemplateFolderException):
            await self.orchestrator.initialize_structure("Invalid Template")

    async def test_initialize_structure_folder_creation_failure(self):
        """Test initialization when folder creation fails"""
        self.mock_joplin.get_or_create_folder_by_path = AsyncMock(return_value=None)

        with self.assertRaises(TemplateFolderException):
            await self.orchestrator.initialize_structure("status")

    async def test_audit_tags_no_duplicates(self):
        """Test tag audit when no duplicates exist"""
        self.mock_joplin.fetch_tags = AsyncMock(return_value=[
            {'id': '1', 'title': 'urgent'},
            {'id': '2', 'title': 'important'},
            {'id': '3', 'title': 'review'}
        ])

        audit = await self.orchestrator.audit_tags()

        self.assertEqual(audit['total_tags'], 3)
        self.assertEqual(len(audit['duplicate_names']), 0)

    async def test_audit_tags_with_duplicates(self):
        """Test tag audit detects case-insensitive duplicates"""
        self.mock_joplin.fetch_tags = AsyncMock(return_value=[
            {'id': '1', 'title': 'Urgent'},
            {'id': '2', 'title': 'urgent'},
            {'id': '3', 'title': 'Important'}
        ])

        audit = await self.orchestrator.audit_tags()

        self.assertEqual(audit['total_tags'], 3)
        self.assertGreater(len(audit['duplicate_names']), 0)

    async def test_detect_conflicts_no_issues(self):
        """Test conflict detection when no conflicts exist"""
        self.mock_joplin.get_all_notes = AsyncMock(return_value=[
            {'id': '1', 'title': 'Note 1', 'parent_id': 'folder_a'},
            {'id': '2', 'title': 'Note 2', 'parent_id': 'folder_b'}
        ])
        self.mock_joplin.get_folders = AsyncMock(return_value=[
            {'id': 'folder_a', 'title': 'Folder A'},
            {'id': 'folder_b', 'title': 'Folder B'},
            {'id': 'folder_target', 'title': 'Target Folder'}
        ])
        self.mock_joplin.fetch_tags = AsyncMock(return_value=[])

        plan = [
            {'note_id': '1', 'target_folder_id': 'folder_target', 'note_title': 'Note 1'},
            {'note_id': '2', 'target_folder_id': 'folder_target', 'note_title': 'Note 2'}
        ]

        conflicts = await self.orchestrator.detect_conflicts(plan)

        self.assertEqual(conflicts['total_conflicts'], 0)

    async def test_detect_conflicts_duplicate_titles(self):
        """Test conflict detection for duplicate titles in target folder"""
        self.mock_joplin.get_all_notes = AsyncMock(return_value=[
            {'id': '1', 'title': 'Same Name', 'parent_id': 'folder_a'},
            {'id': '2', 'title': 'Same Name', 'parent_id': 'folder_b'}
        ])
        self.mock_joplin.get_folders = AsyncMock(return_value=[
            {'id': 'folder_a', 'title': 'Folder A'},
            {'id': 'folder_b', 'title': 'Folder B'},
            {'id': 'folder_target', 'title': 'Target Folder'}
        ])
        self.mock_joplin.fetch_tags = AsyncMock(return_value=[])

        plan = [
            {'note_id': '1', 'target_folder_id': 'folder_target', 'note_title': 'Same Name'},
            {'note_id': '2', 'target_folder_id': 'folder_target', 'note_title': 'Same Name'}
        ]

        conflicts = await self.orchestrator.detect_conflicts(plan)

        self.assertGreater(conflicts['total_conflicts'], 0)
        self.assertGreater(len(conflicts['duplicate_titles_in_folder']), 0)

    async def test_execute_migration_plan_success(self):
        """Test successful execution of migration plan"""
        self.mock_joplin.move_note = AsyncMock(return_value=None)
        self.mock_joplin.get_folders = AsyncMock(return_value=[])
        self.mock_joplin.apply_tags = AsyncMock(return_value=True)

        plan = [
            {'note_id': '1', 'target_folder_id': 'target_1', 'note_title': 'Note 1'},
            {'note_id': '2', 'target_folder_id': 'target_2', 'note_title': 'Note 2'}
        ]

        results = await self.orchestrator.execute_migration_plan(plan)

        self.assertEqual(results['success'], 2)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(self.mock_joplin.move_note.call_count, 2)

    async def test_execute_migration_plan_with_failures(self):
        """Test migration execution with some failures"""
        self.mock_joplin.move_note = AsyncMock(side_effect=[None, Exception("API error"), None])
        self.mock_joplin.get_folders = AsyncMock(return_value=[])
        self.mock_joplin.apply_tags = AsyncMock(return_value=True)

        plan = [
            {'note_id': '1', 'target_folder_id': 'target_1', 'note_title': 'Note 1'},
            {'note_id': '2', 'target_folder_id': 'target_2', 'note_title': 'Note 2'},
            {'note_id': '3', 'target_folder_id': 'target_3', 'note_title': 'Note 3'}
        ]

        results = await self.orchestrator.execute_migration_plan(plan)

        self.assertEqual(results['success'], 2)
        self.assertEqual(results['failed'], 1)

    async def test_execute_migration_plan_empty(self):
        """Test migration execution with empty plan"""
        results = await self.orchestrator.execute_migration_plan([])

        self.assertEqual(results['success'], 0)
        self.assertEqual(results['failed'], 0)


class TestEnrichmentService(unittest.IsolatedAsyncioTestCase):
    """Test suite for EnrichmentService"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_joplin = Mock(spec=JoplinClient)
        self.mock_llm = Mock(spec=LLMOrchestrator)
        self.service = EnrichmentService(self.mock_joplin, self.mock_llm)

    async def test_enrich_note_success(self):
        """Test successful note enrichment"""
        self.mock_joplin.get_note.return_value = {
            'id': 'note_1',
            'title': 'Test Note',
            'body': 'This is test content'
        }
        self.mock_llm.enrich_note = AsyncMock(return_value={
            'metadata': {
                'status': 'Active',
                'priority': 'High',
                'summary': 'Test summary',
                'key_takeaways': ['Point 1', 'Point 2'],
                'suggested_tags': ['test', 'important']
            }
        })
        self.mock_joplin.update_note.return_value = True
        self.mock_joplin.apply_tags.return_value = True

        result = await self.service.enrich_note('note_1')

        self.assertTrue(result)
        self.mock_joplin.update_note.assert_called_once()
        self.mock_joplin.apply_tags.assert_called_once()

    async def test_enrich_note_already_enriched(self):
        """Test enriching a note that's already enriched"""
        body_with_metadata = "---\nStatus: Active\nPriority: High\n---\n\nOriginal content"
        self.mock_joplin.get_note.return_value = {
            'id': 'note_1',
            'title': 'Already Enriched',
            'body': body_with_metadata
        }

        result = await self.service.enrich_note('note_1')

        self.assertTrue(result)
        self.mock_joplin.update_note.assert_not_called()

    async def test_enrich_note_not_found(self):
        """Test enriching a note that doesn't exist"""
        self.mock_joplin.get_note.return_value = None

        result = await self.service.enrich_note('nonexistent_note')

        self.assertFalse(result)

    async def test_enrich_notes_batch(self):
        """Test batch enrichment of multiple notes"""
        notes = [
            {'id': 'note_1', 'title': 'Note 1', 'body': 'Content 1'},
            {'id': 'note_2', 'title': 'Note 2', 'body': 'Content 2'},
            {'id': 'note_3', 'title': 'Note 3', 'body': 'Content 3'}
        ]

        self.mock_joplin.get_note.side_effect = notes
        self.mock_llm.enrich_note = AsyncMock(return_value={
            'metadata': {
                'status': 'Active',
                'priority': 'Medium',
                'summary': 'Summary',
                'key_takeaways': [],
                'suggested_tags': []
            }
        })
        self.mock_joplin.update_note.return_value = True

        stats = await self.service.enrich_notes_batch(notes=notes, limit=3)

        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.enriched, 3)
        self.assertEqual(stats.failed, 0)

    async def test_enrich_notes_batch_with_filter(self):
        """Test batch enrichment with filtering"""
        notes = [
            {'id': 'note_1', 'title': 'Note 1', 'body': 'Content 1'},
            {'id': 'note_2', 'title': 'Note 2', 'body': '---\nStatus: Active\n---\nContent 2'},  # Already enriched
            {'id': 'note_3', 'title': 'Note 3', 'body': 'Content 3'}
        ]

        self.mock_joplin.get_note.side_effect = notes
        self.mock_llm.enrich_note = AsyncMock(return_value={
            'metadata': {
                'status': 'Active',
                'priority': 'Medium',
                'summary': 'Summary',
                'key_takeaways': [],
                'suggested_tags': []
            }
        })
        self.mock_joplin.update_note.return_value = True

        def filter_func(n: dict) -> bool:
            return '---' not in n.get('body', '')

        stats = await self.service.enrich_notes_batch(
            notes=notes,
            filter_func=filter_func
        )

        # Should process 2 notes (filter out note_2)
        self.assertEqual(stats.total, 2)

    def test_enrichment_stats(self):
        """Test EnrichmentStats dataclass"""
        stats = EnrichmentStats(
            total=10,
            enriched=7,
            skipped=2,
            failed=1
        )

        self.assertEqual(stats.total, 10)
        self.assertEqual(stats.enriched, 7)
        self.assertEqual(stats.success_rate, 70.0)

        stats_dict = stats.to_dict()
        self.assertIn('success_rate', stats_dict)
        self.assertEqual(stats_dict['success_rate'], '70.0%')

    def test_is_already_enriched(self):
        """Test detection of already enriched notes"""
        enriched_body = "---\nStatus: Active\n---\nContent"
        not_enriched_body = "Just regular content"

        self.assertTrue(self.service._is_already_enriched(enriched_body))
        self.assertFalse(self.service._is_already_enriched(not_enriched_body))

    async def test_get_enrichment_summary(self):
        """Test enrichment summary generation"""
        notes = [
            {'body': 'Regular content'},
            {'body': '---\nStatus: Active\n---\nContent'},
            {'body': 'More regular content'},
            {'body': '---\nStatus: Done\n---\nContent'}
        ]
        self.mock_joplin.get_all_notes = AsyncMock(return_value=notes)

        summary = await self.service.get_enrichment_summary()

        self.assertEqual(summary['total_notes'], 4)
        self.assertEqual(summary['enriched_notes'], 2)
        self.assertEqual(summary['unenriched_notes'], 2)
        self.assertAlmostEqual(summary['enrichment_percentage'], 50.0)


class TestIntegrationWorkflow(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete FR-016 workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_joplin = Mock(spec=JoplinClient)
        self.mock_llm = Mock(spec=LLMOrchestrator)
        self.reorg = ReorgOrchestrator(self.mock_joplin, self.mock_llm)
        self.enrichment = EnrichmentService(self.mock_joplin, self.mock_llm)

    async def test_complete_reorganization_workflow(self):
        """Test complete workflow: init → preview → detect → execute"""
        self.mock_joplin.get_or_create_folder_by_path = AsyncMock(return_value="folder_id")
        self.mock_joplin.get_all_notes = AsyncMock(return_value=[])
        self.mock_joplin.get_folders = AsyncMock(return_value=[])
        self.mock_joplin.fetch_tags = AsyncMock(return_value=[])
        self.mock_joplin.move_note = AsyncMock(return_value=None)

        init_result = await self.reorg.initialize_structure("status")
        self.assertTrue(init_result)

        conflicts = await self.reorg.detect_conflicts([])
        self.assertEqual(conflicts['total_conflicts'], 0)

        results = await self.reorg.execute_migration_plan([])
        self.assertEqual(results['success'], 0)


if __name__ == '__main__':
    unittest.main()
