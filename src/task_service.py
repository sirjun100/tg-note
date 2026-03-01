"""
Task Service for Google Tasks Integration

Analyzes AI decisions and creates Google Tasks for action items.
Integrates with the logging service to track task-note relationships.
"""

import re
from typing import List, Dict, Any, Optional
from src.google_tasks_client import GoogleTasksClient
from src.logging_service import LoggingService, Decision


class TaskService:
    """Service for creating Google Tasks from AI decisions"""

    def __init__(self, tasks_client: GoogleTasksClient, logging_service: LoggingService):
        self.tasks_client = tasks_client
        self.logging_service = logging_service

    def analyze_decision_for_tasks(self, decision: Decision) -> List[Dict[str, Any]]:
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

    def _extract_action_items(self, text: str) -> List[Dict[str, Any]]:
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

    def _extract_action(self, text: str) -> Optional[str]:
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

    def _extract_date(self, text: str) -> Optional[str]:
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
                date_str = match.group(1) if match.groups() else match.group(0)
                # In a real implementation, you'd parse this into RFC3339 format
                # For now, return as-is or None
                return None  # Placeholder

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

    def create_tasks_from_decision(self, decision: Decision, user_id: str) -> List[Dict[str, Any]]:
        """Create Google Tasks from a decision with enhanced error handling and linking

        Args:
            decision: The AI decision
            user_id: User identifier for token lookup

        Returns:
            List of created task dictionaries
        """
        created_tasks = []

        try:
            # Load user's Google token
            token = self.logging_service.load_google_token(user_id)
            if not token:
                # Do not log as "failed" sync: no sync was attempted (user must link account first)
                print(f"⚠️ No Google token for user {user_id}; skipping task creation. User can /authorize_google_tasks to link.")
                return []

            # Load user's Google Tasks configuration
            config = self.logging_service.get_google_tasks_config(int(user_id))
            if not config or not config.get('enabled'):
                print(f"⚠️ Google Tasks is disabled for user {user_id}")
                return []

            # Check if auto task creation is enabled
            if not config.get('auto_create_tasks'):
                print(f"⚠️ Auto task creation is disabled for user {user_id}")
                return []

            # Check privacy mode
            if config.get('privacy_mode') and decision.status == "SUCCESS":
                # Privacy mode: don't create tasks for certain tags
                note_tags = decision.tags or []
                sensitive_tags = ['personal', 'private', 'confidential', 'sensitive']
                if any(tag.lower() in sensitive_tags for tag in note_tags):
                    print(f"🔒 Privacy mode: Skipping task creation for sensitive note")
                    return []

            # Check if only tagged notes should create tasks
            if config.get('include_only_tagged'):
                task_creation_tags = config.get('task_creation_tags', [])
                if task_creation_tags:
                    note_tags = decision.tags or []
                    if not any(tag in task_creation_tags for tag in note_tags):
                        print(f"⚠️ Note doesn't have required tags for task creation")
                        return []

            # Set token on client
            self.tasks_client.set_token(token)

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
                    print(f"❌ {error_msg}")
                    self.logging_service.log_task_sync(
                        user_id, None, "", "none", None, None,
                        "joplin_to_google", "failed", error_msg
                    )
                    return []

            # Analyze decision for tasks
            potential_tasks = self.analyze_decision_for_tasks(decision)

            for task_data in potential_tasks:
                try:
                    # Create the task
                    task = self.tasks_client.create_task(
                        title=task_data["title"],
                        notes=task_data["notes"],
                        task_list_id=task_list_id,
                        due_date=task_data.get("due_date")
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

                        print(f"✅ Created Google Task: {task_data['title']} (ID: {google_task_id})")
                    else:
                        error_msg = f"API returned empty response for task: {task_data['title']}"
                        print(f"❌ {error_msg}")
                        self.logging_service.log_task_sync(
                            int(user_id), None, "", "create", None, None,
                            "joplin_to_google", "failed", error_msg
                        )

                except Exception as e:
                    error_msg = f"Error creating task '{task_data['title']}': {str(e)}"
                    print(f"❌ {error_msg}")
                    self.logging_service.log_task_sync(
                        int(user_id), None, "", "create", None, None,
                        "joplin_to_google", "failed", error_msg
                    )

        except Exception as e:
            error_msg = f"Unexpected error in task creation: {str(e)}"
            print(f"❌ {error_msg}")
            self.logging_service.log_task_sync(
                int(user_id), None, "", "create", None, None,
                "joplin_to_google", "failed", error_msg
            )

        return created_tasks

    def get_user_tasks(self, user_id: str, task_list_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's Google Tasks"""
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return []

        self.tasks_client.set_token(token)

        try:
            if not task_list_id:
                task_list_id = self.tasks_client.get_default_task_list()
            return self.tasks_client.get_tasks(task_list_id)
        except Exception as e:
            error_msg = f"Error getting tasks for user {user_id}: {e}"
            print(f"❌ {error_msg}")
            self.logging_service.log_task_sync(
                int(user_id), None, "", "read", None, None,
                "google_to_joplin", "failed", error_msg
            )
            return []

    def get_available_task_lists(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all available task lists for a user"""
        token = self.logging_service.load_google_token(user_id)
        if not token:
            return []

        self.tasks_client.set_token(token)

        try:
            return self.tasks_client.get_task_lists()
        except Exception as e:
            error_msg = f"Error getting task lists for user {user_id}: {e}"
            print(f"❌ {error_msg}")
            return []

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

    def set_task_creation_tags(self, user_id: int, tags: List[str]) -> bool:
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

    def get_task_sync_status(self, user_id: int) -> Dict[str, Any]:
        """Get task synchronization status for a user"""
        try:
            sync_history = self.logging_service.get_sync_history(user_id, limit=10)
            task_links = self.logging_service.get_all_task_links(user_id)
            failed_syncs = self.logging_service.get_failed_syncs(user_id)

            total_synced = len(task_links)
            failed_count = len(failed_syncs)
            success_count = max(total_synced - failed_count, 0)

            return {
                "total_synced": total_synced,
                "success_count": success_count,
                "failed_count": failed_count,
                "recent_syncs": sync_history[:5],
                "failed_syncs": failed_syncs[:5]
            }
        except Exception as e:
            print(f"❌ Error getting sync status: {e}")
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
        user_id="123",
        status="SUCCESS",
        note_title="Meeting Notes",
        note_body="TODO: Follow up with client about proposal\nCall Sarah next week\nSchedule demo for Thursday"
    )

    tasks = task_service.analyze_decision_for_tasks(decision)
    print(f"Found {len(tasks)} potential tasks:")
    for task in tasks:
        print(f"- {task['title']} ({task['priority']})")