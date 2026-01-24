"""
Enrichment Service for Joplin Notes
Handles metadata injection, summarization, and key insight extraction.
"""

import logging
from typing import Dict, List, Optional, Any
from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class EnrichmentService:
    """Enriches notes with AI-generated metadata and formatting"""

    def __init__(self, joplin_client: JoplinClient, llm_orchestrator: LLMOrchestrator):
        self.joplin_client = joplin_client
        self.llm_orchestrator = llm_orchestrator

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
        new_body = meta_header + body
        if body.startswith("---") and "Status:" in body:
            logger.info(f"Note {note_id} already enriched, skipping header injection")
            # Maybe update existing metadata in future?
            return True

        # Update note and apply tags
        success = self.joplin_client.update_note(note_id, {"body": new_body})
        
        suggested_tags = metadata.get('suggested_tags', [])
        if suggested_tags:
            self.joplin_client.apply_tags(note_id, suggested_tags)
            
        return success
