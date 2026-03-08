"""
Task Service for Google Tasks Integration

Analyzes AI decisions and creates Google Tasks for action items.
Integrates with the logging service to track task-note relationships.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from src.exceptions import GoogleTasksConfigError
from src.google_tasks_client import GoogleTasksClient
from src.logging_service import Decision, LoggingService

logger = logging.getLogger(__name__)


class TaskService:
    """Service for creating Google Tasks from AI decisions"""

    def __init__(self, tasks_client: GoogleTasksClient, logging_service: LoggingService):
        self.tasks_client = tasks_client
        self.logging_service = logging_service

    def analyze_decision_for_tasks(self, decision: Decision) -> list[dict[str, Any]]:
        """Analyze a decision to identify potential tasks

        Args:
            decision: The AI decision from note processing

        Returns:
            List of task dictionaries with title, notes, priority
        """
        tasks = []

        # Extract action items from note content (title + body)
        content = f"{decision.note_title or ''}\n{decision.note_body or ''}"
        action_items = self._extract_action_items(content)

        for item in action_items:
            task = {
                "title": item["title"],
                "notes": f"From Joplin note: {decision.note_title}\n\n{item['context']}",
                "priority": item.get("priority", "normal"),
                "due_date": item.get("due_date")
            }
            tasks.append(task)

        return tasks

    def _extract_action_items(self, text: str) -> list[dict[str, Any]]:
        """Extract action items from text using pattern matching

        Looks for:
        - TODO items
        - Action verbs (follow up, call, email, etc.)
        - Deadlines and dates
        """
        items = []

        # Split into lines and analyze each
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for TODO patterns
            if re.search(r'\btodo\b|\btask\b|follow.?up|call|email|schedule|remind', line, re.IGNORECASE):
                # Extract the main action
                action = self._extract_action(line)
                if action:
                    # Check for dates
                    due_date = self._extract_date(line)

                    items.append({
                        "title": action[:100],  # Limit title length
                        "context": line,
                        "priority": self._determine_priority(line),
                        "due_date": due_date
                    })

        return items

    def _extract_action(self, text: str) -> str | None:
        """Extract the main action from a line of text"""
        # Remove common prefixes
        text = re.sub(r'^(todo|task|action|reminder)[:\-]?\s*', '', text, flags=re.IGNORECASE)

        # Look for action verbs
        action_patterns = [
            r'(follow up (?:on|with))',
            r'(call|contact|email|message)',
            r'(schedule|plan|organize)',
            r'(review|check|verify)',
            r'(complete|finish|submit)'
        ]

        for pattern in action_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the action and what follows
                action = match.group(0)
                remaining = text[match.end():].strip()
                if remaining:
                    action += " " + remaining

                # Clean up and limit length
                action = re.sub(r'[^\w\s\-]', '', action).strip()
                return action[:80] if action else None

        # If no specific action found, use the whole line if it looks like an action
        if len(text) < 100 and not text.endswith('.') and not text.endswith('?'):
            return text[:80]

        return None

    def _extract_date(self, text: str) -> str | None:
        """Extract due dates from text"""
        # Look for date patterns
        date_patterns = [
            r'by (\w+ \d{1,2})',
            r'due (\w+ \d{1,2})',
            r'on (\w+ \d{1,2})',
            r'(\w+ \d{1,2}, \d{4})',
            r'tomorrow|today|next week'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                _date_str = match.group(1) if match.groups() else match.group(0)
                # TODO: parse _date_str into RFC3339 format
                return None

        return None

    def _determine_priority(self, text: str) -> str:
        """Determine task priority based on text analysis"""
        high_priority_keywords = ['urgent', 'asap', 'critical', 'important', 'deadline']
        low_priority_keywords = ['when possible', 'eventually', 'someday']

        text_lower = text.lower()

        if any(keyword in text_lower for keyword in high_priority_keywords):
            return "high"
        elif any(keyword in text_lower for keyword in low_priority_keywords):
            return "low"
        else:
            return "normal"

    def _set_client_token(self, user_id: str, token: dict[str, Any]) -> None:
        """Set token on client with auto-refresh and persist callback."""
        def _save(new_token: dict[str, Any]) -> None:
            self.logging_service.save_google_token(user_id, new_token)

        self.tasks_client.set_token(token, token_updater=_save)

    def create_task_with_metadata(
        self,
        title: str,
        user_id: str,
        notes: str = "",
        due_date: str | None = None,
        parent_folder_id: str | None = None,
        parent_folder_title: str | None = None,
    ) -> list[dict[str, Any]]:
        """Create a Google Task with optional notes and due date (used by content routing)."""
        logger.info("Task creation with metadata for user %s: %s", user_id, title[:80])

        token = self.logging_service.load_google_token(user_id)
        if not token:
            logger.warning("No Google token for user %s; cannot create task", user_id)
            return []

        config = self.logging_service.get_google_tasks_config(int(user_id))
        if not config or not config.get("enabled"):
            msg = (
                f"Google Tasks disabled for user {user_id} "
                f"(config={'present' if config else 'missing'}, enabled={config.get('enabled') if config else 'N/A'})"
            )
            logger.warning(msg)
            raise GoogleTasksConfigError(
                msg,
                user_message="Google Tasks is disabled. Enable it in Settings or use /tasks_connect.",
            )

        self._set_client_token(user_id, token)

        task_list_id = config.get("task_list_id")
        if not task_list_id:
            try:
                task_list_id = self.tasks_client.get_default_task_list()
                logger.info("User %s: Using default task list %s", user_id, task_list_id)
            except Exception as e:
                logger.warning("User %s: Failed to get task list: %s", user_id, e)
                raise GoogleTasksConfigError(
                    str(e),
                    user_message=f"Could not get your Google Tasks list: {e}. Try /tasks_connect to re-connect.",
                ) from e

        parent_task_id: str | None = None
        if parent_folder_id and parent_folder_title and config.get("project_sync_enabled"):
            parent_task_id = self.get_or_create_project_parent_task(
                user_id, parent_folder_id, parent_folder_title, task_list_id
            )

        try:
            task = self.tasks_client.create_task(
                title=title,
                notes=notes,
                task_list_id=task_list_id,
                due_date=due_date,
                parent_task_id=parent_task_id,
            )
            if task:
                logger.info("Created Google Task for user %s: %s (ID: %s)", user_id, title[:50], task.get("id"))
                self.logging_service.log_task_sync(
                    user_id=int(user_id),
                    task_link_id=None,
                    google_task_id=task.get("id", ""),
                    action="created",
                    old_status=None,
                    new_status="needsAction",
                    sync_direction="joplin_to_google",
                    sync_result="success",
                )
                if self.tasks_client.token and self.tasks_client.token != token:
                    self.logging_service.save_google_token(user_id, self.tasks_client.token)
                return [task]
            return []
        except Exception as e:
            logger.warning("User %s: Error creating task: %s", user_id, e)
            self.logging_service.log_task_sync(
                user_id=int(user_id),
                task_link_id=None,
                google_task_id="",
                action="created",
                old_status=None,
                new_status=None,
                sync_direction="joplin_to_google",
                sync_result="failed",
                error_message=str(e),
            )
            if self.tasks_client.token and self.tasks_client.token != token:
                self.logging_service.save_google_token(user_id, self.tasks_client.token)
            raise

    def create_task_directly(self, title: str, user_id: str) -> list[dict[str, Any]]:
        """Create a single Google Task directly from user text (used by /task command).
        Bypasses action-item extraction — the user explicitly asked to create this task."""
        return self.create_task_with_metadata(title=title, user_id=user_id)

    def get_or_create_project_parent_task(
        self,
        user_id: str,
        folder_id: str,
        folder_title: str,
        task_list_id: str,
    ) -> str | None:
        """FR-034: Get or create Google parent task for a Joplin project folder. Returns google_task_id or None.
        Rename detection: if folder was renamed, updates the Google Task title."""
        mapping = self.logging_service.get_project_sync_mapping(int(user_id), folder_id)
        if mapping:
            google_task_id = mapping.get("google_task_id")
            stored_title = mapping.get("joplin_folder_title", "")
            if google_task_id and stored_title != folder_title:
                # Rename detection: folder was renamed in Joplin, update Google Task
                token = self.logging_service.load_google_token(user_id)
                if token:
                    self._set_client_token(user_id, token)
                    try:
                        updated = self.tasks_client.update_task(
                            google_task_id, task_list_id, {"title": folder_title}
                        )
                        if updated and self.tasks_client.token != token:
                            self.logging_service.save_google_token(user_id, self.tasks_client.token)
                        self.logging_service.save_project_sync_mapping(
                            user_id=int(user_id),
                            joplin_folder_id=folder_id,
                            joplin_folder_title=folder_title,
                            google_task_id=google_task_id,
                            google_task_list_id=task_list_id,
                        )
                        logger.info("FR-034: Updated project parent task title to '%s' (folder renamed)", folder_title)
                    except Exception as e:
                        logger.warning("FR-034: Failed to update project task title: %s", e)
            return google_task_id

        token = self.logging_service.load_google_token(user_id)
        if not token:
            return None

        self._set_client_token(user_id, token)
        try:
            parent_task = self.tasks_client.create_task(
                title=folder_title,
                notes=f"Joplin project: {folder_title}",
                task_list_id=task_list_id,
            )
            if parent_task:
                google_task_id = parent_task.get("id")
                self.logging_service.save_project_sync_mapping(
                    user_id=int(user_id),
                    joplin_folder_id=folder_id,
                    joplin_folder_title=folder_title,
                    google_task_id=google_task_id,
                    google_task_list_id=task_list_id,
                )
                logger.info("FR-034: Created project parent task '%s' for folder %s", folder_title, folder_id)
                return google_task_id
        except Exception as e:
            logger.warning("FR-034: Failed to create project parent task: %s", e)
        return None

    def cleanup_orphaned_project_mappings(
        self, user_id: str, existing_folder_ids: set[str]
    ) -> int:
        """FR-034: Remove mappings and delete Google tasks for folders no longer in Joplin.
        Returns number of mappings removed."""
        mappings = self.logging_service.get_all_project_sync_mappings(int(user_id))
        removed = 0
        for m in mappings:
            folder_id = m.get("joplin_folder_id")
            if folder_id and folder_id not in existing_folder_ids:
                google_task_id = m.get("google_task_id")
                task_list_id = m.get("google_task_list_id")
                if google_task_id and task_list_id:
                    token = self.logging_service.load_google_token(user_id)
                    if token:
                        self._set_client_token(user_id, token)
                        try:
                            self.tasks_client.delete_task(google_task_id, task_list_id)
                            logger.info(
                                "FR-034: Deleted orphaned project task %s (folder %s removed)",
                                google_task_id, folder_id,
                            )
                            if self.tasks_client.token != token:
                                self.logging_service.save_google_token(user_id, self.tasks_client.token)
                        except Exception as e:
                            logger.warning("FR-034: Failed to delete orphaned task: %s", e)
                self.logging_service.delete_project_sync_mapping(int(user_id), folder_id)
                removed += 1
        return removed

    def reset_project_sync(self, user_id: int) -> int:
        """Clear all project sync mappings for a user. Returns count cleared.
        Use before /tasks_sync_projects when you want to re-create parent tasks in a different list."""
        return self.logging_service.delete_all_project_sync_mappings(user_id)

    def sync_project_parent_tasks(
        self, user_id: str, project_folders: list[tuple[str, str]]
    ) -> tuple[int, int]:
        """FR-034: Create parent tasks for all project folders. Returns (created_count, existing_count)."""
        task_list_id = self.get_task_list_id_for_user(user_id)
        if not task_list_id:
            return 0, 0
        created, existing = 0, 0
        for folder_id, folder_title in project_folders:
            if self.logging_service.get_project_sync_mapping(int(user_id), folder_id):
                existing += 1
            elif self.get_or_create_project_parent_task(
                user_id, folder_id, folder_title, task_list_id
            ):
                created += 1
        return created, existing

    def create_tasks_from_decision(
        self,
        decision: Decision,
        user_id: str,
        parent_folder_id: str | None = None,
        parent_folder_title: str | None = None,
    ) -> list[dict[str, Any]]:
        """Create Google Tasks from a decision with enhanced error handling and linking.

        FR-034: When parent_folder_id and parent_folder_title are provided and project_sync_enabled,
        creates subtasks under the project's parent task in Google Tasks.

        Args:
            decision: The AI decision
            user_id: User identifier for token lookup
            parent_folder_id: Optional Joplin folder ID (project) for subtask creation
            parent_folder_title: Optional folder title for parent task creation

        Returns:
            List of created task dictionaries
        """
        created_tasks = []
        logger.info("Creating Google Tasks for user %s, title: %s", user_id, (decision.note_title or "")[:80])

        try:
            # Load user's Google token
            token = self.logging_service.load_google_token(user_id)
            if not token:
                logger.warning("No Google token for user %s; skipping task creation", user_id)
                return []

            # Load user's Google Tasks configuration
            config = self.logging_service.get_google_tasks_config(int(user_id))
            if not config or not config.get('enabled'):
                logger.warning("Google Tasks disabled for user %s", user_id)
                return []

            # Check if auto task creation is enabled
            if not config.get('auto_create_tasks'):
                logger.warning("Auto task creation disabled for user %s", user_id)
                return []

            # Check privacy mode
            if config.get('privacy_mode') and decision.status == "SUCCESS":
                # Privacy mode: don't create tasks for certain tags
                note_tags = decision.tags or []
                sensitive_tags = ['personal', 'private', 'confidential', 'sensitive']
                if any(tag.lower() in sensitive_tags for tag in note_tags):
                    print("🔒 Privacy mode: Skipping task creation for sensitive note")
                    return []

            # Check if only tagged notes should create tasks
            if config.get('include_only_tagged'):
                task_creation_tags = config.get('task_creation_tags', [])
                if task_creation_tags:
                    note_tags = decision.tags or []
                    if not any(tag in task_creation_tags for tag in note_tags):
                        print("⚠️ Note doesn't have required tags for task creation")
                        return []

            # Set token on client
            self._set_client_token(user_id, token)

            # FR-034: Resolve parent task for project sync
            parent_task_id: str | None = None
            if parent_folder_id and parent_folder_title and config.get("project_sync_enabled"):
                task_list_id_for_parent = config.get("task_list_id")
                if not task_list_id_for_parent:
                    try:
                        task_list_id_for_parent = self.tasks_client.get_default_task_list()
                    except Exception:
                        task_list_id_for_parent = None
                if task_list_id_for_parent:
                    parent_task_id = self.get_or_create_project_parent_task(
                        user_id, parent_folder_id, parent_folder_title, task_list_id_for_parent
                    )

            # Get or use configured task list
            task_list_id = config.get('task_list_id')
            if not task_list_id:
                # Use default task list
                try:
                    task_list_id = self.tasks_client.get_default_task_list()
                    # Update config with default task list
                    task_lists = self.tasks_client.get_task_lists()
                    if task_lists:
                        task_list_name = task_lists[0].get('title', 'My Tasks')
                        config['task_list_id'] = task_list_id
                        config['task_list_name'] = task_list_name
                        self.logging_service.save_google_tasks_config(int(user_id), config)
                except Exception as e:
                    error_msg = f"Failed to get task list: {e}"
                    logger.warning("User %s: %s", user_id, error_msg)
                    self.logging_service.log_task_sync(
                        int(user_id), None, "", "none", None, None,
                        "joplin_to_google", "failed", error_msg
                    )
                    return []

            # Analyze decision for tasks
            potential_tasks = self.analyze_decision_for_tasks(decision)
            if not potential_tasks:
                logger.info("No action items extracted for user %s (title: %s)", user_id, (decision.note_title or "")[:50])

            for task_data in potential_tasks:
                try:
                    # Create the task (subtask if parent_task_id set, FR-034)
                    task = self.tasks_client.create_task(
                        title=task_data["title"],
                        notes=task_data["notes"],
                        task_list_id=task_list_id,
                        due_date=task_data.get("due_date"),
                        parent_task_id=parent_task_id,
                    )

                    if task:
                        created_tasks.append(task)
                        google_task_id = task.get('id')

                        # Create task link if we have a Joplin note ID
                        if decision.joplin_note_id:
                            task_link_id = self.logging_service.create_task_link(
                                user_id=int(user_id),
                                joplin_note_id=decision.joplin_note_id,
                                google_task_id=google_task_id,
                                google_task_list_id=task_list_id,
                                joplin_note_title=decision.note_title or "Untitled",
                                google_task_title=task_data["title"]
                            )

                            # Log successful sync
                            self.logging_service.log_task_sync(
                                user_id=int(user_id),
                                task_link_id=task_link_id,
                                google_task_id=google_task_id,
                                action="created",
                                old_status=None,
                                new_status="needsAction",
                                sync_direction="joplin_to_google",
                                sync_result="success"
                            )

                        logger.info("Created Google Task for user %s: %s (ID: %s)", user_id, task_data['title'][:50], google_task_id)
                    else:
                        error_msg = f"API returned empty response for task: {task_data['title']}"
                        logger.warning("User %s: %s", user_id, error_msg)
                        self.logging_service.log_task_sync(
                            int(user_id), None, "", "create", None, None,
                            "joplin_to_google", "failed", error_msg
                        )

                except Exception as e:
                    error_msg = f"Error creating task '{task_data['title']}': {str(e)}"
                    logger.warning("User %s: %s", user_id, error_msg)
                    self.logging_service.log_task_sync(
                        int(user_id), None, "", "create", None, None,
                        "joplin_to_google", "failed", error_msg
                    )

        except Exception as e:
            error_msg = f"Unexpected error in task creation: {str(e)}"
            logger.warning("User %s: %s", user_id, error_msg)
            self.logging_service.log_task_sync(
                int(user_id), None, "", "create", None, None,
                "joplin_to_google", "failed", error_msg
            )

        # Persist refreshed token so DB has the new access_token (refresh_token is preserved in client)
        if self.tasks_client.token and self.tasks_client.token != token:
            self.logging_service.save_google_token(user_id, self.tasks_client.token)

        if created_tasks:
            logger.info("Created %d Google Task(s) for user %s", len(created_tasks), user_id)
        return created_tasks

    def get_user_tasks(
        self,
        user_id: str,
        task_list_id: str | None = None,
        show_completed: bool = False,
    ) -> list[dict[str, Any]]:
        """Get user's Google Tasks. Set show_completed=True to include completed tasks (BF-018)."""
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return []

        self._set_client_token(user_id, token)

        try:
            if not task_list_id:
                task_list_id = self.tasks_client.get_default_task_list()
            result = self.tasks_client.get_tasks(task_list_id, show_completed=show_completed)
            if self.tasks_client.token and self.tasks_client.token != token:
                self.logging_service.save_google_token(user_id, self.tasks_client.token)
            return result
        except Exception as e:
            error_msg = f"Error getting tasks for user {user_id}: {e}"
            print(f"❌ {error_msg}")
            self.logging_service.log_task_sync(
                int(user_id), None, "", "read", None, None,
                "google_to_joplin", "failed", error_msg
            )
            return []

    def get_stalled_project_titles(self, user_id: str) -> list[str]:
        """FR-034: Return project titles that have no incomplete subtasks (stalled projects)."""
        config = self.logging_service.get_google_tasks_config(int(user_id))
        if not config or not config.get("project_sync_enabled"):
            return []

        mappings = self.logging_service.get_all_project_sync_mappings(int(user_id))
        if not mappings:
            return []

        task_list_id = self.get_task_list_id_for_user(user_id)
        if not task_list_id:
            return []

        token = self.logging_service.load_google_token(user_id)
        if not token:
            return []

        self._set_client_token(user_id, token)
        try:
            all_tasks = self.tasks_client.get_all_tasks(task_list_id, show_completed=False)
            if self.tasks_client.token and self.tasks_client.token != token:
                self.logging_service.save_google_token(user_id, self.tasks_client.token)
        except Exception as e:
            logger.debug("Failed to fetch tasks for stalled projects: %s", e)
            return []

        # Parents that have at least one incomplete subtask
        parents_with_subtasks: set[str] = set()
        for task in all_tasks:
            parent = task.get("parent")
            if parent:
                parents_with_subtasks.add(parent)

        stalled = [
            m.get("joplin_folder_title", "Unknown")
            for m in mappings
            if m.get("google_task_id") and m["google_task_id"] not in parents_with_subtasks
        ]
        return stalled

    def get_task_list_id_for_user(self, user_id: str) -> str | None:
        """Get the task list ID used for the user (from config or default)."""
        config = self.logging_service.get_google_tasks_config(int(user_id))
        if config and config.get("task_list_id"):
            return config["task_list_id"]
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return None
        self._set_client_token(user_id, token)
        try:
            return self.tasks_client.get_default_task_list()
        except Exception:
            return None

    def get_available_task_lists(self, user_id: str) -> list[dict[str, Any]]:
        """Get all available task lists for a user"""
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return []

        self._set_client_token(user_id, token)

        try:
            result = self.tasks_client.get_task_lists()
            if self.tasks_client.token and self.tasks_client.token != token:
                self.logging_service.save_google_token(user_id, self.tasks_client.token)
            return result
        except Exception as e:
            error_msg = f"Error getting task lists for user {user_id}: {e}"
            print(f"❌ {error_msg}")
            return []

    def delete_completed_tasks_older_than(
        self, user_id: str, days: int = 30
    ) -> tuple[int, int]:
        """
        Delete completed tasks older than N days from all task lists.

        Returns:
            (deleted_count, error_count)
        """
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return 0, 0
        self._set_client_token(user_id, token)

        task_lists = self.get_available_task_lists(user_id)
        if not task_lists:
            return 0, 0

        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        errors = 0

        for tl in task_lists:
            task_list_id = tl.get("id")
            if not task_list_id:
                continue
            try:
                tasks = self.tasks_client.get_all_tasks(
                    task_list_id, show_completed=True
                )
            except Exception as e:
                logger.warning("Failed to fetch tasks from list %s: %s", task_list_id, e)
                continue

            for task in tasks:
                if task.get("status") != "completed":
                    continue
                completed_str = task.get("completed")
                if not completed_str:
                    continue
                try:
                    completed_dt = datetime.fromisoformat(
                        completed_str.replace("Z", "+00:00")
                    )
                    if completed_dt.timestamp() < cutoff.timestamp():
                        if self.tasks_client.delete_task(task.get("id"), task_list_id):
                            deleted += 1
                        else:
                            errors += 1
                except (ValueError, TypeError):
                    pass

        if self.tasks_client.token and self.tasks_client.token != token:
            self.logging_service.save_google_token(user_id, self.tasks_client.token)

        return deleted, errors

    def set_preferred_task_list(self, user_id: int, task_list_id: str,
                               task_list_name: str) -> bool:
        """Set the preferred task list for a user"""
        try:
            config = self.logging_service.get_google_tasks_config(user_id)
            if not config:
                config = {}

            config['task_list_id'] = task_list_id
            config['task_list_name'] = task_list_name
            self.logging_service.save_google_tasks_config(user_id, config)
            print(f"✅ Task list set to: {task_list_name} (ID: {task_list_id})")
            return True
        except Exception as e:
            error_msg = f"Error setting task list: {e}"
            print(f"❌ {error_msg}")
            return False

    def toggle_auto_task_creation(self, user_id: int, enabled: bool) -> bool:
        """Enable or disable automatic task creation"""
        try:
            config = self.logging_service.get_google_tasks_config(user_id)
            if not config:
                config = {}

            config['auto_create_tasks'] = enabled
            self.logging_service.save_google_tasks_config(user_id, config)
            status = "enabled" if enabled else "disabled"
            print(f"✅ Auto task creation {status}")
            return True
        except Exception as e:
            print(f"❌ Error toggling auto task creation: {e}")
            return False

    def toggle_privacy_mode(self, user_id: int, enabled: bool) -> bool:
        """Enable or disable privacy mode"""
        try:
            config = self.logging_service.get_google_tasks_config(user_id)
            if not config:
                config = {}

            config['privacy_mode'] = enabled
            self.logging_service.save_google_tasks_config(user_id, config)
            status = "enabled" if enabled else "disabled"
            print(f"✅ Privacy mode {status}")
            return True
        except Exception as e:
            print(f"❌ Error toggling privacy mode: {e}")
            return False

    def toggle_project_sync(self, user_id: int, enabled: bool) -> bool:
        """FR-034: Enable or disable Joplin project ↔ Google Tasks sync (subtasks under project parent)."""
        try:
            config = self.logging_service.get_google_tasks_config(user_id)
            if not config:
                config = {}

            config['project_sync_enabled'] = enabled
            self.logging_service.save_google_tasks_config(user_id, config)
            return True
        except Exception as e:
            logger.warning("Error toggling project sync: %s", e)
            return False

    def set_task_creation_tags(self, user_id: int, tags: list[str]) -> bool:
        """Set tags that trigger task creation (when include_only_tagged is True)"""
        try:
            config = self.logging_service.get_google_tasks_config(user_id)
            if not config:
                config = {}

            config['task_creation_tags'] = tags
            config['include_only_tagged'] = len(tags) > 0
            self.logging_service.save_google_tasks_config(user_id, config)
            print(f"✅ Task creation tags set to: {', '.join(tags)}")
            return True
        except Exception as e:
            print(f"❌ Error setting task creation tags: {e}")
            return False

    def validate_google_token(self, user_id: int) -> tuple[bool, str]:
        """Validate token by making a lightweight API call. Refreshes if expired.
        Returns (valid, error_message). error_message is empty when valid."""
        token = self.logging_service.load_google_token(str(user_id))
        if not token:
            return False, "Google Tasks not authorized"
        self._set_client_token(str(user_id), token)
        try:
            # Lightweight API call; with auto_refresh, token is refreshed if expired
            url = f"{self.tasks_client.BASE_URL}/users/@me/lists"
            resp = self.tasks_client.session.get(url)
            resp.raise_for_status()
            return True, ""
        except Exception as e:
            err_str = str(e).lower()
            if "token_expired" in err_str or "401" in err_str or "refresh" in err_str:
                return False, "Token expired or revoked. Re-authorization required."
            return False, str(e)

    def get_task_sync_status(self, user_id: int) -> dict[str, Any]:
        """Get task synchronization status for a user"""
        try:
            sync_history = self.logging_service.get_sync_history(user_id, limit=10)
            failed_syncs = self.logging_service.get_failed_syncs(user_id)
            successful_syncs = self.logging_service.get_successful_syncs(user_id)

            success_count = len(successful_syncs)
            failed_count = len(failed_syncs)
            total_synced = success_count + failed_count

            return {
                "total_synced": total_synced,
                "success_count": success_count,
                "failed_count": failed_count,
                "recent_syncs": sync_history[:5],
                "failed_syncs": failed_syncs[:5]
            }
        except Exception as e:
            logger.warning("Error getting sync status for user %s: %s", user_id, e)
            return {"error": str(e)}


# Integration helper
def should_create_tasks_for_decision(decision: Decision) -> bool:
    """Determine if a decision should trigger task creation"""
    # Only create tasks for successful note creations
    if decision.status != "SUCCESS":
        return False

    # Check if note content suggests action items
    content = (decision.note_body or "") + (decision.note_title or "")
    action_indicators = ['todo', 'task', 'follow', 'call', 'email', 'schedule', 'remind']

    return any(indicator in content.lower() for indicator in action_indicators)


# Example usage
if __name__ == "__main__":
    from src.logging_service import LoggingService

    logging_service = LoggingService()
    tasks_client = GoogleTasksClient()

    task_service = TaskService(tasks_client, logging_service)

    # Example decision
    decision = Decision(
        user_id=123,
        status="SUCCESS",
        note_title="Meeting Notes",
        note_body="TODO: Follow up with client about proposal\nCall Sarah next week\nSchedule demo for Thursday"
    )

    tasks = task_service.analyze_decision_for_tasks(decision)
    print(f"Found {len(tasks)} potential tasks:")
    for task in tasks:
        print(f"- {task['title']} ({task['priority']})")
