"""
Enrichment Service for Joplin Notes
Handles metadata injection, summarization, and key insight extraction.
Supports batch operations with progress tracking and filtering.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentStats:
    """Statistics for enrichment operations"""
    total: int = 0
    enriched: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.enriched / self.total) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'enriched': self.enriched,
            'skipped': self.skipped,
            'failed': self.failed,
            'success_rate': f"{self.success_rate:.1f}%"
        }

class EnrichmentService:
    """Enriches notes with AI-generated metadata and formatting"""

    def __init__(self, joplin_client: JoplinClient, llm_orchestrator: LLMOrchestrator):
        self.joplin_client = joplin_client
        self.llm_orchestrator = llm_orchestrator
        self._cancel_batch = False

    def _is_already_enriched(self, body: str) -> bool:
        """Check if a note body is already enriched"""
        return body.startswith("---") and "Status:" in body

    def cancel_batch_operation(self) -> None:
        """Request cancellation of current batch operation"""
        self._cancel_batch = True

    async def enrich_note(self, note_id: str) -> bool:
        """Fetch a note, get AI enrichment, and update the note"""
        note = self.joplin_client.get_note(note_id)
        if not note:
            logger.error(f"Note {note_id} not found for enrichment")
            return False

        title = note.get('title', 'Untitled')
        body = note.get('body', '')

        # Get enrichment from LLM
        enrichment_data = await self.llm_orchestrator.enrich_note(title, body)
        metadata = enrichment_data.get('metadata')
        
        if not metadata:
            logger.warning(f"No metadata generated for note {note_id}")
            return False

        # Construct new body with front matter metadata
        meta_header = "---\n"
        meta_header += f"Status: {metadata.get('status', 'N/A')}\n"
        meta_header += f"Priority: {metadata.get('priority', 'N/A')}\n"
        meta_header += f"Summary: {metadata.get('summary', 'N/A')}\n"
        
        takeaways = metadata.get('key_takeaways', [])
        if takeaways:
            meta_header += "Key Takeaways:\n"
            for t in takeaways:
                meta_header += f"  - {t}\n"
        
        meta_header += "---\n\n"

        # Check if note already has enrichment (avoid double enrichment)
        if self._is_already_enriched(body):
            logger.info(f"Note {note_id} already enriched, skipping")
            return True

        # Construct new body with front matter metadata
        new_body = meta_header + body

        # Update note and apply tags
        success = self.joplin_client.update_note(note_id, {"body": new_body})

        suggested_tags = metadata.get('suggested_tags', [])
        if suggested_tags:
            self.joplin_client.apply_tags(note_id, suggested_tags)

        logger.debug(f"Enriched note {note_id}: {metadata.get('priority', 'UNKNOWN')}")
        return success

    async def enrich_notes_batch(
        self,
        notes: Optional[List[Dict[str, Any]]] = None,
        limit: Optional[int] = None,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        progress_callback: Optional[Callable[[EnrichmentStats], None]] = None
    ) -> EnrichmentStats:
        """
        Enrich multiple notes with progress tracking.

        Args:
            notes: List of note dicts to enrich (if None, fetch all)
            limit: Maximum notes to enrich
            filter_func: Function to filter notes (e.g., lambda note: 'Status' not in note.get('body', ''))
            progress_callback: Function called with stats after each note

        Returns:
            EnrichmentStats with operation results
        """
        self._cancel_batch = False
        stats = EnrichmentStats()

        # Fetch notes if not provided
        if notes is None:
            notes = self.joplin_client.get_all_notes()
            logger.info(f"Fetched {len(notes)} notes for batch enrichment")

        # Apply filter if provided
        if filter_func:
            notes = [n for n in notes if filter_func(n)]
            logger.info(f"Filtered to {len(notes)} notes based on criteria")

        # Apply limit
        if limit:
            notes = notes[:limit]

        stats.total = len(notes)

        # Process each note
        for note in notes:
            if self._cancel_batch:
                logger.info("Batch enrichment cancelled by user")
                break

            try:
                note_id = note.get('id')
                body = note.get('body', '')

                # Skip already enriched notes
                if self._is_already_enriched(body):
                    stats.skipped += 1
                    logger.debug(f"Skipping already enriched note: {note.get('title', 'Untitled')}")
                else:
                    success = await self.enrich_note(note_id)
                    if success:
                        stats.enriched += 1
                    else:
                        stats.failed += 1

            except Exception as e:
                stats.failed += 1
                logger.error(f"Error enriching note {note.get('id', 'unknown')}: {e}")

            # Call progress callback if provided
            if progress_callback:
                try:
                    progress_callback(stats)
                except Exception as e:
                    logger.warning(f"Error in progress callback: {e}")

        logger.info(f"Batch enrichment complete: {stats.enriched} enriched, {stats.skipped} skipped, {stats.failed} failed")
        return stats

    def get_unenriched_notes_filter(self) -> Callable[[Dict[str, Any]], bool]:
        """Get a filter function to find notes without enrichment metadata"""
        return lambda note: not self._is_already_enriched(note.get('body', ''))

    def get_enrichment_summary(self, notes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Get summary of enrichment status across notes"""
        if notes is None:
            notes = self.joplin_client.get_all_notes()

        enriched_count = sum(1 for n in notes if self._is_already_enriched(n.get('body', '')))
        total_count = len(notes)

        return {
            'total_notes': total_count,
            'enriched_notes': enriched_count,
            'unenriched_notes': total_count - enriched_count,
            'enrichment_percentage': (enriched_count / total_count * 100) if total_count > 0 else 0
        }
