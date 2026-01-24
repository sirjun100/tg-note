"""
Reorganization Orchestrator for Joplin Database
Handles PARA methodology implementation and database restructuring logic.
Includes comprehensive error handling, logging, and conflict detection.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.joplin_client import JoplinClient
from src.enrichment_service import EnrichmentService
from src.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


# Custom exceptions for better error handling
class ReorgException(Exception):
    """Base exception for reorganization operations"""
    pass


class TemplateFolderException(ReorgException):
    """Raised when folder initialization fails"""
    pass


class MigrationConflictException(ReorgException):
    """Raised when migration conflicts are detected"""
    pass


class MigrationExecutionException(ReorgException):
    """Raised when migration execution fails"""
    pass


@dataclass
class OperationLog:
    """Log entry for reorganization operations"""
    timestamp: str
    operation: str
    status: str  # 'success', 'warning', 'error'
    details: str
    affected_items: int = 0

class ReorgOrchestrator:
    """Orchestrates database reorganization based on PARA methodology"""

    PARA_TEMPLATES = {
        "status": {
            "Projects": ["🟢 Active", "🟡 Planned", "🔵 On Hold", "❌ Stalled"],
            "Areas": ["💼 Work & Career", "💪 Health & Fitness", "💰 Finance & Investing", "📚 Learning", "🏠 Home"],
            "Resources": ["📖 Books & Articles", "📋 Templates", "🔗 Reference"],
            "Archive": []
        },
        "roles": {
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
        try:
            template = self.PARA_TEMPLATES.get(template_name)
            if not template:
                logger.error(f"Template '{template_name}' not found. Available: {list(self.PARA_TEMPLATES.keys())}")
                raise TemplateFolderException(f"Unknown template: {template_name}")

            logger.info(f"🏗️ Initializing PARA structure using template: {template_name}")

            folders_created = 0
            for main_folder, sub_folders in template.items():
                try:
                    # Create main folder
                    main_folder_id = self.joplin_client.get_or_create_folder_by_path([main_folder])
                    if not main_folder_id:
                        raise TemplateFolderException(f"Failed to create main folder '{main_folder}'")

                    folders_created += 1
                    logger.debug(f"✓ Created main folder: {main_folder}")

                    # Create sub-folders
                    for sub in sub_folders:
                        try:
                            self.joplin_client.get_or_create_folder_by_path([main_folder, sub])
                            folders_created += 1
                            logger.debug(f"  ✓ Created sub-folder: {sub}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Failed to create sub-folder {sub}: {e}")

                except Exception as e:
                    logger.error(f"Failed to create main folder '{main_folder}': {e}")
                    raise

            logger.info(f"✅ PARA structure initialization complete: {folders_created} folders created")
            return True

        except TemplateFolderException as e:
            logger.error(f"Template initialization error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during structure initialization: {e}", exc_info=True)
            raise ReorgException(f"Failed to initialize PARA structure: {e}")

    async def generate_migration_plan(self) -> Dict[str, Any]:
        """
        Scan all notes and suggest migration to PARA structure using LLM classification.
        """
        try:
            notes = self.joplin_client.get_all_notes()
            folders = self.joplin_client.get_folders()

            logger.debug(f"Migration plan: Found {len(notes)} notes and {len(folders)} folders")

            # Build folder list for LLM context
            folder_text = ""
            for f in folders:
                folder_text += f"- {f['id']}: {f['title']}\n"

            plan = {
                "summary": {
                    "total_notes": len(notes),
                    "notes_to_move": 0,
                    "folders_to_create": 0,
                    "analysis_sample_size": 0
                },
                "moves": []
            }

            if not notes:
                logger.warning("No notes found in Joplin for migration planning")
                return plan

            # Randomly sample or process first N for preview (to avoid huge token usage)
            limit = 20
            processed_count = 0

            for note in notes:
                if processed_count >= limit:
                    break

                note_title = note.get('title', 'Untitled')
                note_body = note.get('body', '')
                current_folder_id = note.get('parent_id')

                try:
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
                    plan["summary"]["analysis_sample_size"] = processed_count

                except Exception as e:
                    logger.warning(f"Failed to classify note '{note_title}': {e}")
                    processed_count += 1
                    continue

            logger.info(f"Migration plan generated: {len(plan['moves'])} moves suggested for {processed_count} notes analyzed")
            return plan

        except Exception as e:
            logger.error(f"Failed to generate migration plan: {e}", exc_info=True)
            return {
                "summary": {
                    "total_notes": 0,
                    "notes_to_move": 0,
                    "error": str(e)
                },
                "moves": []
            }

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

    def detect_conflicts(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect potential conflicts in a migration plan.

        Returns:
            Dict with conflict types and details
        """
        conflicts = {
            "duplicate_targets": [],
            "duplicate_titles_in_folder": [],
            "target_folder_issues": [],
            "tag_conflicts": [],
            "total_conflicts": 0
        }

        # Get all notes for reference
        all_notes = self.joplin_client.get_all_notes()
        all_folders = self.joplin_client.get_folders()

        # Create lookup maps
        notes_by_id = {n['id']: n for n in all_notes}
        folders_by_id = {f['id']: f for f in all_folders}

        # Track planned moves by target folder
        moves_by_target = {}

        for move in plan:
            note_id = move.get("note_id")
            target_id = move.get("target_folder_id")

            if not note_id or not target_id:
                continue

            # Check if target folder exists
            if target_id not in folders_by_id:
                conflicts["target_folder_issues"].append({
                    "note_id": note_id,
                    "target_id": target_id,
                    "issue": "Target folder does not exist"
                })
                conflicts["total_conflicts"] += 1
                continue

            # Track notes moving to same folder
            if target_id not in moves_by_target:
                moves_by_target[target_id] = []
            moves_by_target[target_id].append({
                "note_id": note_id,
                "title": notes_by_id.get(note_id, {}).get('title', 'Unknown')
            })

        # Detect duplicate titles in target folders
        for target_id, notes_list in moves_by_target.items():
            titles = [n['title'] for n in notes_list]
            unique_titles = set(titles)

            if len(titles) != len(unique_titles):
                # Find duplicates
                seen = set()
                for title in titles:
                    if title in seen:
                        conflicts["duplicate_titles_in_folder"].append({
                            "target_folder_id": target_id,
                            "title": title,
                            "count": titles.count(title)
                        })
                    seen.add(title)
                conflicts["total_conflicts"] += len(conflicts["duplicate_titles_in_folder"])

        # Check for tag conflicts
        audit = self.audit_tags()
        if audit.get("duplicate_names"):
            conflicts["tag_conflicts"] = audit["duplicate_names"]
            conflicts["total_conflicts"] += len(audit["duplicate_names"])

        logger.info(f"Conflict detection complete: {conflicts['total_conflicts']} conflicts found")
        return conflicts

    def resolve_conflict(self, conflict_type: str, resolution: str) -> bool:
        """
        Attempt to resolve a detected conflict.

        Args:
            conflict_type: Type of conflict (e.g., "duplicate_title")
            resolution: How to resolve (e.g., "rename", "skip", "merge")

        Returns:
            True if resolution successful
        """
        try:
            logger.info(f"Attempting to resolve {conflict_type} with strategy: {resolution}")
            # Implementation would depend on conflict type and resolution strategy
            # For now, return True as placeholder
            return True
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return False

    def execute_migration_plan(self, plan: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Execute a series of note moves with comprehensive error handling.

        Args:
            plan: List of moves: {"note_id": "...", "target_folder_id": "..."}

        Returns:
            Results with success/failed counts
        """
        try:
            if not plan:
                logger.warning("Migration plan is empty, nothing to execute")
                return {"success": 0, "failed": 0, "skipped": 0}

            results = {"success": 0, "failed": 0, "skipped": 0}
            logger.info(f"🔄 Starting migration execution for {len(plan)} moves")

            for i, move in enumerate(plan, 1):
                try:
                    note_id = move.get("note_id")
                    target_id = move.get("target_folder_id")
                    note_title = move.get("note_title", "Unknown")

                    if not note_id or not target_id:
                        logger.warning(f"Skipping move {i}: Invalid note_id or target_id")
                        results["skipped"] += 1
                        continue

                    logger.debug(f"Moving note {i}/{len(plan)}: '{note_title}' → folder {target_id[:8]}...")

                    if self.joplin_client.move_note(note_id, target_id):
                        results["success"] += 1
                        logger.debug(f"  ✓ Successfully moved: {note_title}")
                    else:
                        results["failed"] += 1
                        logger.warning(f"  ✗ Failed to move: {note_title}")

                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"  ✗ Error moving note {note_id}: {e}", exc_info=True)

            logger.info(f"✅ Migration complete: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
            return results

        except Exception as e:
            logger.error(f"Migration execution failed: {e}", exc_info=True)
            raise MigrationExecutionException(f"Failed to execute migration plan: {e}")
