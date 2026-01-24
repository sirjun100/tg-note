"""
Reorganization Orchestrator for Joplin Database
Handles PARA methodology implementation and database restructuring logic.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from src.joplin_client import JoplinClient

from src.enrichment_service import EnrichmentService
from src.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class ReorgOrchestrator:
    """Orchestrates database reorganization based on PARA methodology"""

    PARA_TEMPLATES = {
        "PARA+ (Status-Based)": {
            "Projects": ["🟢 Active", "🟡 Planned", "🔵 On Hold", "❌ Stalled"],
            "Areas": ["💼 Work & Career", "💪 Health & Fitness", "💰 Finance & Investing", "📚 Learning", "🏠 Home"],
            "Resources": ["📖 Books & Articles", "📋 Templates", "🔗 Reference"],
            "Archive": []
        },
        "PARA Context (Role-Based)": {
            "Projects": ["Professional", "Personal", "Volunteer"],
            "Areas": ["Work", "Life", "Creative", "Health"],
            "Resources": ["Tools", "Templates", "Knowledge"],
            "Archive": []
        }
    }

    def __init__(self, joplin_client: JoplinClient, llm_orchestrator: LLMOrchestrator):
        self.joplin_client = joplin_client
        self.llm_orchestrator = llm_orchestrator

    def get_available_templates(self) -> List[str]:
        """Get list of available PARA templates"""
        return list(self.PARA_TEMPLATES.keys())

    def initialize_structure(self, template_name: str) -> bool:
        """Create the top-level folder structure based on template"""
        template = self.PARA_TEMPLATES.get(template_name)
        if not template:
            logger.error(f"Template '{template_name}' not found")
            return False

        logger.info(f"Initializing PARA structure using template: {template_name}")
        
        for main_folder, sub_folders in template.items():
            # Create main folder
            main_folder_id = self.joplin_client.get_or_create_folder_by_path([main_folder])
            if not main_folder_id:
                logger.error(f"Failed to create main folder '{main_folder}'")
                return False
                
            # Create sub-folders
            for sub in sub_folders:
                self.joplin_client.get_or_create_folder_by_path([main_folder, sub])
                
        return True

    async def generate_migration_plan(self) -> Dict[str, Any]:
        """
        Scan all notes and suggest migration to PARA structure using LLM classification.
        """
        notes = self.joplin_client.get_all_notes()
        folders = self.joplin_client.get_folders()
        
        # Build folder list for LLM context
        folder_text = ""
        for f in folders:
            folder_text += f"- {f['id']}: {f['title']}\n"

        plan = {
            "summary": {
                "total_notes": len(notes),
                "notes_to_move": 0,
                "folders_to_create": 0
            },
            "moves": []
        }
        
        # Randomly sample or process first N for preview (to avoid huge token usage)
        limit = 20
        processed_count = 0
        
        for note in notes:
            if processed_count >= limit:
                break
                
            note_title = note.get('title', 'Untitled')
            note_body = note.get('body', '')
            current_folder_id = note.get('parent_id')
            
            # Use LLM to classify
            classification = await self.llm_orchestrator.classify_note(note_title, note_body, folder_text)
            target_folder_id = classification.get('suggested_folder_id')
            
            if target_folder_id and target_folder_id != current_folder_id:
                plan["moves"].append({
                    "note_id": note['id'],
                    "note_title": note_title,
                    "source_folder_id": current_folder_id,
                    "target_folder_id": target_folder_id,
                    "reasoning": classification.get('reasoning', "AI matched folder content")
                })
                plan["summary"]["notes_to_move"] += 1
            
            processed_count += 1
        
        return plan

    def audit_tags(self) -> Dict[str, Any]:
        """Audit tags for duplicates, unused tags, or inconsistent casing"""
        tags = self.joplin_client.fetch_tags()
        
        audit = {
            "duplicate_names": [],
            "unused_tags": [],
            "total_tags": len(tags)
        }
        
        # Check for case-insensitive duplicates
        seen_names = {} # lowercase -> original
        for tag in tags:
            name = tag['title']
            name_lower = name.lower()
            
            if name_lower in seen_names:
                audit["duplicate_names"].append({
                    "original": seen_names[name_lower],
                    "duplicate": name,
                    "count": 0 # TODO: get counts
                })
            else:
                seen_names[name_lower] = name
                
        # TODO: Add usage counts for unused tag detection
        
        return audit

    def execute_migration_plan(self, plan: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Execute a series of note moves.
        Each move is: {"note_id": "...", "target_folder_id": "..."}
        """
        results = {"success": 0, "failed": 0}
        
        for move in plan:
            note_id = move.get("note_id")
            target_id = move.get("target_folder_id")
            
            if note_id and target_id:
                if self.joplin_client.move_note(note_id, target_id):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    
        return results
