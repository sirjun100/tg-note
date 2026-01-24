"""
Report Generator for Daily Priority Reports

Generates unified daily priority reports aggregating:
- Joplin notes (with priority tags: #urgent, #critical, #important, #high)
- Google Tasks (incomplete/needsAction status)
- Pending clarifications from conversation state
- Completion tracking since last report
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for report items"""
    CRITICAL = 5
    HIGH = 3
    MEDIUM = 1
    LOW = 0


class ItemSource(Enum):
    """Source of report items"""
    JOPLIN = "joplin"
    GOOGLE_TASKS = "google_tasks"
    PENDING_CLARIFICATION = "clarification"


@dataclass
class ReportItem:
    """Individual item in a report"""
    id: str
    source: ItemSource
    title: str
    description: Optional[str] = None
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    due_date: Optional[datetime] = None
    is_overdue: bool = False
    days_overdue: int = 0
    impact_score: float = 2.0  # 1-3 scale
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority_score: float = 0.0  # Calculated score

    def calculate_priority_score(self) -> float:
        """
        Calculate priority score for ranking items

        Formula: (Priority_Level × 10) + (Urgency × 8) + (Impact × 5) - (Days_Overdue × 2)

        Where:
        - Priority_Level: 0-5 based on priority tags
        - Urgency: 0-3 based on due date (0=future, 1=this week, 2=tomorrow, 3=today)
        - Impact: 1-3 (high importance)
        - Days_Overdue: negative penalty per day past due
        """
        # Priority level component
        priority_component = self.priority_level.value * 10

        # Urgency component (based on due date)
        urgency = 0
        if self.due_date:
            days_until_due = (self.due_date.date() - datetime.now().date()).days
            if days_until_due < 0:
                urgency = 3  # Overdue - highest urgency
            elif days_until_due == 0:
                urgency = 3  # Due today
            elif days_until_due == 1:
                urgency = 2  # Due tomorrow
            elif days_until_due <= 7:
                urgency = 1  # This week
            else:
                urgency = 0  # Future
        urgency_component = urgency * 8

        # Impact component
        impact_component = self.impact_score * 5

        # Overdue penalty
        overdue_penalty = self.days_overdue * 2

        # Calculate final score
        score = priority_component + urgency_component + impact_component - overdue_penalty

        self.priority_score = max(0, score)  # Ensure non-negative
        return self.priority_score


@dataclass
class ReportData:
    """Complete daily report data"""
    user_id: int
    report_date: datetime
    critical_items: List[ReportItem] = field(default_factory=list)
    high_items: List[ReportItem] = field(default_factory=list)
    medium_items: List[ReportItem] = field(default_factory=list)
    low_items: List[ReportItem] = field(default_factory=list)
    pending_clarification: List[str] = field(default_factory=list)
    completed_items: List[str] = field(default_factory=list)
    joplin_count: int = 0
    google_tasks_count: int = 0
    clarification_count: int = 0
    completed_count: int = 0

    @property
    def total_items(self) -> int:
        """Total items in report"""
        return (
            len(self.critical_items)
            + len(self.high_items)
            + len(self.medium_items)
            + len(self.low_items)
        )

    @property
    def all_items(self) -> List[ReportItem]:
        """All items sorted by priority score"""
        items = (
            self.critical_items + self.high_items + self.medium_items + self.low_items
        )
        return sorted(items, key=lambda x: x.priority_score, reverse=True)


class ReportGenerator:
    """Generates daily priority reports from Joplin and Google Tasks"""

    # Tags that indicate priority levels
    PRIORITY_TAGS = {
        "urgent": PriorityLevel.CRITICAL,
        "critical": PriorityLevel.CRITICAL,
        "important": PriorityLevel.HIGH,
        "high": PriorityLevel.HIGH,
        "medium": PriorityLevel.MEDIUM,
        "low": PriorityLevel.LOW,
    }

    # Minimum priority level to include in report (can be configured)
    MIN_PRIORITY_THRESHOLD = PriorityLevel.LOW

    # Maximum items to include per category
    MAX_ITEMS_PER_CATEGORY = 20

    def __init__(self, joplin_client=None, task_service=None):
        """
        Initialize report generator

        Args:
            joplin_client: JoplinClient instance for fetching notes
            task_service: TaskService instance for fetching Google Tasks
        """
        self.logger = logger
        self.joplin_client = joplin_client
        self.task_service = task_service

    def extract_priority_from_tags(self, tags: List[str]) -> PriorityLevel:
        """Extract priority level from tag list"""
        if not tags:
            return PriorityLevel.MEDIUM

        # Find highest priority tag
        highest_priority = PriorityLevel.LOW
        for tag in tags:
            tag_lower = tag.lower().strip("#")
            if tag_lower in self.PRIORITY_TAGS:
                tag_priority = self.PRIORITY_TAGS[tag_lower]
                if tag_priority.value > highest_priority.value:
                    highest_priority = tag_priority

        return highest_priority

    def calculate_impact(self, item_dict: Dict[str, Any], source: ItemSource) -> float:
        """
        Calculate impact score for an item (1-3 scale)

        Impact factors:
        - Blocking other work (Joplin): 3
        - High urgency (due very soon): 2.5
        - Medium impact: 2
        - Low impact: 1
        """
        impact = 2.0  # Default medium impact

        # Check for blocking indicators
        if source == ItemSource.JOPLIN:
            body = item_dict.get("body", "").lower()
            if any(word in body for word in ["blocking", "blocker", "blocked by"]):
                impact = 3.0
            elif item_dict.get("is_overdue"):
                impact = 2.5

        elif source == ItemSource.GOOGLE_TASKS:
            # Google Tasks don't have descriptions usually
            if item_dict.get("status") == "needsAction":
                impact = 2.0

        return min(3.0, max(1.0, impact))  # Clamp 1-3

    def calculate_overdue_days(self, due_date: Optional[datetime]) -> int:
        """Calculate number of days an item is overdue"""
        if not due_date:
            return 0

        days_overdue = (datetime.now().date() - due_date.date()).days
        return max(0, days_overdue)

    def create_joplin_item(self, note: Dict[str, Any]) -> Optional[ReportItem]:
        """Convert a Joplin note to a ReportItem"""
        try:
            # Extract priority from tags
            tags = note.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            priority_level = self.extract_priority_from_tags(tags)

            # Extract due date if present (look for date patterns in body or metadata)
            due_date = self._extract_due_date_from_note(note)
            days_overdue = self.calculate_overdue_days(due_date)
            is_overdue = days_overdue > 0

            impact = self.calculate_impact(note, ItemSource.JOPLIN)

            item = ReportItem(
                id=note.get("id", ""),
                source=ItemSource.JOPLIN,
                title=note.get("title", "Untitled Note"),
                description=note.get("body", "")[:100],  # First 100 chars
                priority_level=priority_level,
                due_date=due_date,
                is_overdue=is_overdue,
                days_overdue=days_overdue,
                impact_score=impact,
                tags=tags,
                metadata={
                    "folder": note.get("folder_id", ""),
                    "created": note.get("created", ""),
                    "updated": note.get("updated", ""),
                },
            )

            item.calculate_priority_score()
            return item

        except Exception as e:
            self.logger.error(f"Failed to create Joplin item: {e}")
            return None

    def create_google_task_item(
        self, task: Dict[str, Any]
    ) -> Optional[ReportItem]:
        """Convert a Google Task to a ReportItem"""
        try:
            # Extract due date
            due_date = None
            if "due" in task:
                try:
                    due_date = datetime.fromisoformat(
                        task["due"].replace("Z", "+00:00")
                    )
                except:
                    pass

            days_overdue = self.calculate_overdue_days(due_date)
            is_overdue = days_overdue > 0

            # Google Tasks don't have priority, infer from due date
            priority_level = PriorityLevel.HIGH if is_overdue else PriorityLevel.MEDIUM

            impact = self.calculate_impact(task, ItemSource.GOOGLE_TASKS)

            item = ReportItem(
                id=task.get("id", ""),
                source=ItemSource.GOOGLE_TASKS,
                title=task.get("title", "Untitled Task"),
                description=task.get("notes", "")[:100],
                priority_level=priority_level,
                due_date=due_date,
                is_overdue=is_overdue,
                days_overdue=days_overdue,
                impact_score=impact,
                metadata={
                    "task_list_id": task.get("tasklist_id", ""),
                    "status": task.get("status", "needsAction"),
                    "completed": task.get("completed", ""),
                },
            )

            item.calculate_priority_score()
            return item

        except Exception as e:
            self.logger.error(f"Failed to create Google Task item: {e}")
            return None

    def create_clarification_item(
        self, note_id: str, note_title: str
    ) -> ReportItem:
        """Create a pending clarification item"""
        return ReportItem(
            id=note_id,
            source=ItemSource.PENDING_CLARIFICATION,
            title=note_title,
            priority_level=PriorityLevel.HIGH,
            description="Awaiting your response",
            impact_score=2.5,
        )

    def categorize_items(self, items: List[ReportItem]) -> ReportData:
        """Categorize items by priority level"""
        report = ReportData(user_id=0, report_date=datetime.now())

        for item in items:
            if item.priority_level == PriorityLevel.CRITICAL:
                report.critical_items.append(item)
            elif item.priority_level == PriorityLevel.HIGH:
                report.high_items.append(item)
            elif item.priority_level == PriorityLevel.MEDIUM:
                report.medium_items.append(item)
            else:
                report.low_items.append(item)

        return report

    def _extract_due_date_from_note(self, note: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract due date from note body or metadata

        Looks for patterns like:
        - Due: 2025-01-25
        - Due today
        - Due tomorrow
        - Deadline: [date]
        """
        # TODO: Implement date extraction logic
        # For now, return None (no due date extraction from Joplin notes)
        return None

    def generate_report(
        self,
        user_id: int,
        joplin_notes: List[Dict[str, Any]],
        google_tasks: List[Dict[str, Any]],
        pending_clarifications: List[Tuple[str, str]] = None,
        completed_items: List[str] = None,
    ) -> ReportData:
        """
        Generate a complete daily report

        Args:
            user_id: Telegram user ID
            joplin_notes: List of Joplin notes
            google_tasks: List of Google Tasks
            pending_clarifications: List of (note_id, note_title) tuples
            completed_items: List of completed item titles

        Returns:
            ReportData with categorized and scored items
        """
        self.logger.debug(
            f"Generating report for user {user_id}: "
            f"{len(joplin_notes)} notes, {len(google_tasks)} tasks"
        )

        items = []

        # Process Joplin notes
        for note in joplin_notes:
            item = self.create_joplin_item(note)
            if item:
                items.append(item)

        # Process Google Tasks
        for task in google_tasks:
            # Only include incomplete tasks
            if task.get("status") != "completed":
                item = self.create_google_task_item(task)
                if item:
                    items.append(item)

        # Categorize by priority
        report = self.categorize_items(items)
        report.user_id = user_id
        report.report_date = datetime.now()

        # Add pending clarifications
        if pending_clarifications:
            for note_id, note_title in pending_clarifications:
                report.pending_clarification.append(note_title)
            report.clarification_count = len(pending_clarifications)

        # Add completed items
        if completed_items:
            report.completed_items = completed_items
            report.completed_count = len(completed_items)

        # Count by source
        for item in report.all_items:
            if item.source == ItemSource.JOPLIN:
                report.joplin_count += 1
            elif item.source == ItemSource.GOOGLE_TASKS:
                report.google_tasks_count += 1

        self.logger.info(
            f"Report generated: {report.total_items} items "
            f"({report.joplin_count} Joplin, {report.google_tasks_count} Tasks)"
        )

        return report

    def get_top_recommendation(self, report: ReportData) -> Optional[str]:
        """Get the most urgent item to tackle first"""
        if not report.all_items:
            return None

        # Most urgent is first item (already sorted by priority score)
        top_item = report.all_items[0]
        return top_item.title

    def filter_by_priority(
        self, items: List[ReportItem], min_priority: PriorityLevel
    ) -> List[ReportItem]:
        """Filter items by minimum priority level"""
        return [item for item in items if item.priority_level.value >= min_priority.value]

    def limit_items(self, items: List[ReportItem], limit: int = None) -> List[ReportItem]:
        """Limit number of items returned"""
        if limit is None:
            limit = self.MAX_ITEMS_PER_CATEGORY
        return items[:limit]

    async def fetch_joplin_notes_for_report(
        self, user_id: int, min_priority: PriorityLevel = PriorityLevel.LOW
    ) -> List[Dict[str, Any]]:
        """
        Fetch high-priority Joplin notes

        Args:
            user_id: Telegram user ID
            min_priority: Minimum priority level to include

        Returns:
            List of note dictionaries
        """
        if not self.joplin_client:
            self.logger.warning("Joplin client not configured")
            return []

        try:
            # Get all folders
            folders = self.joplin_client.get_folders()
            if not folders:
                self.logger.info("No Joplin folders found")
                return []

            # Collect notes from all folders
            all_notes = []
            for folder in folders:
                try:
                    notes = self.joplin_client.get_notes_in_folder(folder["id"])
                    if notes:
                        for note in notes:
                            # Extract tags for priority filtering
                            tags = note.get("tags", [])
                            if isinstance(tags, str):
                                tags = [t.strip().lower() for t in tags.split(",")]
                            else:
                                tags = [t.lower() for t in tags]

                            # Check if note has priority tags
                            has_priority_tag = any(
                                tag in self.PRIORITY_TAGS for tag in tags
                            )
                            if has_priority_tag:
                                all_notes.append(note)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch notes from folder {folder['id']}: {e}")
                    continue

            self.logger.debug(f"Fetched {len(all_notes)} Joplin notes with priority tags")
            return all_notes

        except Exception as e:
            self.logger.error(f"Failed to fetch Joplin notes: {e}")
            return []

    async def fetch_google_tasks_for_report(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Fetch incomplete Google Tasks

        Args:
            user_id: Telegram user ID

        Returns:
            List of task dictionaries
        """
        if not self.task_service:
            self.logger.debug("Google Tasks client not configured")
            return []

        try:
            # Get task lists
            task_lists = await self.task_service.get_task_lists(user_id)
            if not task_lists:
                self.logger.debug("No Google task lists found")
                return []

            # Fetch tasks from all lists
            all_tasks = []
            for task_list in task_lists:
                try:
                    tasks = await self.task_service.get_tasks(
                        user_id, task_list["id"], show_completed=False
                    )
                    if tasks:
                        # Add task list ID for reference
                        for task in tasks:
                            task["tasklist_id"] = task_list["id"]
                        all_tasks.extend(tasks)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch tasks from list {task_list['id']}: {e}"
                    )
                    continue

            self.logger.debug(f"Fetched {len(all_tasks)} incomplete Google Tasks")
            return all_tasks

        except Exception as e:
            self.logger.error(f"Failed to fetch Google Tasks: {e}")
            return []

    async def aggregate_report_items(
        self,
        user_id: int,
        joplin_notes: List[Dict[str, Any]],
        google_tasks: List[Dict[str, Any]],
        min_priority: PriorityLevel = PriorityLevel.LOW,
    ) -> List[ReportItem]:
        """
        Aggregate items from both sources and rank by priority

        Args:
            user_id: Telegram user ID
            joplin_notes: List of Joplin notes
            google_tasks: List of Google Tasks
            min_priority: Minimum priority level to include

        Returns:
            Sorted list of ReportItems by priority score
        """
        items = []

        # Create ReportItems from Joplin notes
        for note in joplin_notes:
            try:
                item = self.create_joplin_item(note)
                if item and item.priority_level.value >= min_priority.value:
                    items.append(item)
            except Exception as e:
                self.logger.warning(f"Failed to process Joplin note {note.get('id')}: {e}")
                continue

        # Create ReportItems from Google Tasks
        for task in google_tasks:
            try:
                item = self.create_google_task_item(task)
                if item and item.priority_level.value >= min_priority.value:
                    items.append(item)
            except Exception as e:
                self.logger.warning(f"Failed to process Google Task {task.get('id')}: {e}")
                continue

        # Sort by priority score (highest first)
        items.sort(key=lambda x: x.priority_score, reverse=True)

        self.logger.debug(f"Aggregated {len(items)} report items from both sources")

        return items

    async def generate_report_async(
        self,
        user_id: int,
        pending_clarifications: List[Tuple[str, str]] = None,
        completed_items: List[str] = None,
        min_priority: PriorityLevel = PriorityLevel.LOW,
    ) -> ReportData:
        """
        Generate a complete daily report asynchronously

        Fetches data from both Joplin and Google Tasks, aggregates, and generates report.

        Args:
            user_id: Telegram user ID
            pending_clarifications: List of (note_id, note_title) tuples
            completed_items: List of completed item titles
            min_priority: Minimum priority level to include

        Returns:
            ReportData with categorized and scored items
        """
        self.logger.info(f"Generating async report for user {user_id}")

        try:
            # Fetch from both sources concurrently
            joplin_notes = await self.fetch_joplin_notes_for_report(user_id, min_priority)
            google_tasks = await self.fetch_google_tasks_for_report(user_id)

            # Aggregate items
            items = await self.aggregate_report_items(
                user_id, joplin_notes, google_tasks, min_priority
            )

            # Categorize by priority
            report = self.categorize_items(items)
            report.user_id = user_id
            report.report_date = datetime.now()

            # Add pending clarifications
            if pending_clarifications:
                for note_id, note_title in pending_clarifications:
                    report.pending_clarification.append(note_title)
                report.clarification_count = len(pending_clarifications)

            # Add completed items
            if completed_items:
                report.completed_items = completed_items
                report.completed_count = len(completed_items)

            # Count by source
            report.joplin_count = sum(
                1 for item in report.all_items if item.source == ItemSource.JOPLIN
            )
            report.google_tasks_count = sum(
                1 for item in report.all_items if item.source == ItemSource.GOOGLE_TASKS
            )

            self.logger.info(
                f"Report generated: {report.total_items} items "
                f"({report.joplin_count} Joplin, {report.google_tasks_count} Tasks)"
            )

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate async report: {e}")
            # Return empty report on error
            report = ReportData(user_id=user_id, report_date=datetime.now())
            return report


if __name__ == "__main__":
    # Example usage
    import json

    generator = ReportGenerator()

    # Example Joplin notes
    joplin_notes = [
        {
            "id": "note1",
            "title": "Follow up with client",
            "body": "This is blocking other work. Must complete today.",
            "tags": ["urgent", "work"],
        },
        {
            "id": "note2",
            "title": "Review Q1 budget",
            "body": "Quarterly budget review",
            "tags": ["important"],
        },
    ]

    # Example Google Tasks
    google_tasks = [
        {
            "id": "task1",
            "title": "Schedule team meeting",
            "due": datetime.now().isoformat(),
            "status": "needsAction",
        },
        {
            "id": "task2",
            "title": "Complete project report",
            "status": "completed",
        },
    ]

    report = generator.generate_report(
        user_id=12345,
        joplin_notes=joplin_notes,
        google_tasks=google_tasks,
        completed_items=["Design homepage mockup"],
    )

    print(f"\n📊 Report Summary:")
    print(f"Total items: {report.total_items}")
    print(f"Critical: {len(report.critical_items)}")
    print(f"High: {len(report.high_items)}")
    print(f"Medium: {len(report.medium_items)}")
    print(f"Completed: {report.completed_count}")
    print(f"\nTop Recommendation: {generator.get_top_recommendation(report)}")
