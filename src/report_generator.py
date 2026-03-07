"""
Report Generator for Daily Priority Reports

Generates unified daily priority reports aggregating:
- Joplin notes (with priority tags: #urgent, #critical, #important, #high)
- Google Tasks (incomplete/needsAction status)
- Notes created today, tasks completed today
- Pending clarifications from conversation state
- Completion tracking since last report

FR-037: Uses monospace tables with parse_mode="HTML" for Telegram.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.report_formatter import escape_for_html
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.logging_service import LoggingService

logger = logging.getLogger(__name__)


def get_llm_orchestrator():
    """Lazy import to avoid circular dependencies"""
    from src.llm_orchestrator import LLMOrchestrator
    return LLMOrchestrator()


class PriorityLevel(Enum):
    """Priority levels for report items. FR-039: URGENT for *** at start of task title."""
    URGENT = 6
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
    description: str | None = None
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    due_date: datetime | None = None
    is_overdue: bool = False
    days_overdue: int = 0
    impact_score: float = 2.0  # 1-3 scale
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
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
    critical_items: list[ReportItem] = field(default_factory=list)
    high_items: list[ReportItem] = field(default_factory=list)
    medium_items: list[ReportItem] = field(default_factory=list)
    low_items: list[ReportItem] = field(default_factory=list)
    joplin_notes: list[ReportItem] = field(default_factory=list)  # Separate section for all Joplin notes
    pending_clarification: list[str] = field(default_factory=list)
    completed_items: list[str] = field(default_factory=list)
    notes_created_today: list[tuple[str, str]] = field(default_factory=list)  # (title, folder)
    tasks_completed_today: list[str] = field(default_factory=list)
    inbox_notes_count: int = 0  # Unprocessed notes in Inbox folder ("in")
    joplin_count: int = 0
    google_tasks_count: int = 0
    clarification_count: int = 0
    completed_count: int = 0
    stalled_projects: list[str] = field(default_factory=list)  # FR-034: projects with no next actions

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
    def all_items(self) -> list[ReportItem]:
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

    # Hybrid selection strategy: tagged + recently modified
    # Include notes if they have priority tags OR modified in last N days
    RECENT_DAYS_THRESHOLD = 7  # Show notes modified in last 7 days

    def __init__(
        self,
        joplin_client=None,
        task_service=None,
        logging_service: LoggingService | None = None,
    ):
        """
        Initialize report generator

        Args:
            joplin_client: JoplinClient instance for fetching notes
            task_service: TaskService instance for fetching Google Tasks
            logging_service: LoggingService for user timezone (report config)
        """
        self.logger = logger
        self.joplin_client = joplin_client
        self.task_service = task_service
        self.logging_service = logging_service

    def extract_priority_from_tags(self, tags: list[str]) -> PriorityLevel:
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

    def analyze_importance_with_ai(
        self, title: str, body: str, current_priority: PriorityLevel
    ) -> PriorityLevel:
        """
        Use AI to analyze note/task importance based on content

        Args:
            title: Item title
            body: Item description/body
            current_priority: Current priority based on tags/metadata

        Returns:
            Updated priority level based on AI analysis
        """
        try:
            # Skip AI analysis if content is very short or already high priority
            if len(title) < 5 or current_priority in [
                PriorityLevel.CRITICAL,
                PriorityLevel.HIGH,
            ]:
                return current_priority

            llm = get_llm_orchestrator()
            content = f"Title: {title}\n\nContent: {body[:500]}"

            prompt = f"""Analyze this task/note and determine its importance/priority.

Content:
{content}

Determine the priority level based on:
1. Action urgency (keywords: must, urgent, asap, critical, blocking, etc.)
2. Impact scope (affects others, blocking work, customer-facing, etc.)
3. Time sensitivity (deadlines, recurring, time-dependent, etc.)
4. Complexity (requires deep thinking, risky if wrong, etc.)

Respond with ONLY one of these words:
- CRITICAL (must do immediately, blocking other work)
- HIGH (important, should do soon)
- MEDIUM (important but not urgent)
- LOW (nice to have, can defer)

Response:"""

            try:
                response = llm.get_response(prompt).strip().upper()

                # Map response to priority level
                priority_map = {
                    "CRITICAL": PriorityLevel.CRITICAL,
                    "HIGH": PriorityLevel.HIGH,
                    "MEDIUM": PriorityLevel.MEDIUM,
                    "LOW": PriorityLevel.LOW,
                }

                ai_priority = priority_map.get(response, current_priority)

                # Use AI priority if it's higher than current, otherwise keep current
                # This ensures AI analysis enhances but doesn't override explicit tagging
                if ai_priority.value > current_priority.value:
                    self.logger.debug(
                        f"AI upgraded priority {current_priority.name} -> {ai_priority.name}: {title[:50]}"
                    )
                    return ai_priority
                else:
                    return current_priority

            except Exception as e:
                self.logger.debug(f"AI importance analysis failed: {e}, keeping current priority")
                return current_priority

        except Exception as e:
            self.logger.debug(f"Error in analyze_importance_with_ai: {e}")
            return current_priority

    def calculate_impact(self, item_dict: dict[str, Any], source: ItemSource) -> float:
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

    def calculate_overdue_days(self, due_date: datetime | None) -> int:
        """Calculate number of days an item is overdue"""
        if not due_date:
            return 0

        days_overdue = (datetime.now().date() - due_date.date()).days
        return max(0, days_overdue)

    def create_joplin_item(self, note: dict[str, Any]) -> ReportItem | None:
        """Convert a Joplin note to a ReportItem"""
        try:
            # Extract priority from tags
            tags = note.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            priority_level = self.extract_priority_from_tags(tags)

            # Enhance priority with AI analysis of note content if no explicit tags
            if not tags or priority_level == PriorityLevel.MEDIUM:
                title = note.get("title", "")
                body = note.get("body", "")
                if title and body:  # Only analyze if we have content
                    priority_level = self.analyze_importance_with_ai(
                        title, body, priority_level
                    )

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
                    "folder": note.get("folder_name", note.get("folder_id", "")),
                    "created": note.get("created", ""),
                    "updated": note.get("updated", ""),
                },
            )

            item.calculate_priority_score()
            return item

        except Exception as e:
            self.logger.error(f"Failed to create Joplin item: {e}")
            return None

    def _detect_star_priority(self, title: str) -> PriorityLevel | None:
        """FR-039: Detect * / ** / *** or ⭐/★ at start of title. Star wins over due date."""
        if not title or not isinstance(title, str):
            return None
        t = title.strip()
        if t.startswith("***") or t.startswith("⭐⭐⭐") or t.startswith("★★★"):
            return PriorityLevel.URGENT
        if t.startswith("**") or t.startswith("⭐⭐") or t.startswith("★★"):
            return PriorityLevel.CRITICAL
        if t.startswith("*") or t.startswith("⭐") or t.startswith("★"):
            return PriorityLevel.HIGH
        return None

    def create_google_task_item(
        self, task: dict[str, Any]
    ) -> ReportItem | None:
        """Convert a Google Task to a ReportItem"""
        try:
            # Extract due date
            due_date = None
            if "due" in task:
                with contextlib.suppress(ValueError, TypeError, AttributeError):
                    due_date = datetime.fromisoformat(
                        task["due"].replace("Z", "+00:00")
                    )

            days_overdue = self.calculate_overdue_days(due_date)
            is_overdue = days_overdue > 0

            # FR-039: Star at start of title wins over due date
            title = task.get("title", "Untitled Task")
            star_priority = self._detect_star_priority(title)
            if star_priority is not None:
                priority_level = star_priority
            else:
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

    def categorize_items(self, items: list[ReportItem]) -> ReportData:
        """Categorize items by priority level, separating Joplin notes"""
        report = ReportData(user_id=0, report_date=datetime.now())

        for item in items:
            # Separate Joplin notes into their own section
            if item.source == ItemSource.JOPLIN:
                report.joplin_notes.append(item)
            # Priority items (Google Tasks + any Joplin notes marked as high priority tasks)
            # FR-039: URGENT treated like CRITICAL (top of report)
            elif item.priority_level in (PriorityLevel.URGENT, PriorityLevel.CRITICAL):
                report.critical_items.append(item)
            elif item.priority_level == PriorityLevel.HIGH:
                report.high_items.append(item)
            elif item.priority_level == PriorityLevel.MEDIUM:
                report.medium_items.append(item)
            else:
                report.low_items.append(item)

        # Sort Joplin notes by priority score
        report.joplin_notes.sort(key=lambda x: x.priority_score, reverse=True)

        return report

    def _extract_due_date_from_note(self, note: dict[str, Any]) -> datetime | None:
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
        joplin_notes: list[dict[str, Any]],
        google_tasks: list[dict[str, Any]],
        pending_clarifications: list[tuple[str, str]] = None,
        completed_items: list[str] = None,
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
            for _note_id, note_title in pending_clarifications:
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

    def get_top_recommendation(self, report: ReportData) -> str | None:
        """Get the most urgent item to tackle first"""
        if not report.all_items:
            return None

        # Most urgent is first item (already sorted by priority score)
        top_item = report.all_items[0]
        return top_item.title

    def filter_by_priority(
        self, items: list[ReportItem], min_priority: PriorityLevel
    ) -> list[ReportItem]:
        """Filter items by minimum priority level"""
        return [item for item in items if item.priority_level.value >= min_priority.value]

    def limit_items(self, items: list[ReportItem], limit: int = None) -> list[ReportItem]:
        """Limit number of items returned"""
        if limit is None:
            limit = self.MAX_ITEMS_PER_CATEGORY
        return items[:limit]

    def _has_priority_tag(self, note: dict[str, Any]) -> bool:
        """Check if note has any priority-indicating tags"""
        tags = note.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(",")]
        else:
            tags = [t.lower() for t in tags] if tags else []

        return any(tag in self.PRIORITY_TAGS for tag in tags)

    def _is_recently_modified(self, note: dict[str, Any], days_threshold: int = 7) -> bool:
        """Check if note was modified in the last N days"""
        try:
            updated_ms = note.get("updated", 0)
            if not updated_ms:
                return False

            updated_timestamp = updated_ms / 1000 if updated_ms > 10000000000 else updated_ms

            # Get the date
            updated_date = datetime.fromtimestamp(updated_timestamp).date()
            days_since_update = (datetime.now().date() - updated_date).days

            return days_since_update <= days_threshold
        except Exception as e:
            self.logger.debug(f"Error checking modification date: {e}")
            return False

    async def fetch_joplin_notes_for_report(
        self, user_id: int, min_priority: PriorityLevel = PriorityLevel.LOW
    ) -> list[dict[str, Any]]:
        """
        Fetch Joplin notes using hybrid strategy with smart fallback:
        - Include all notes with priority tags (#urgent, #critical, #important, #high, #medium)
        - Include all notes modified in the last 7 days
        - If filter results in too few notes, use AI to analyze untagged notes

        Args:
            user_id: Telegram user ID
            min_priority: Minimum priority level to include

        Returns:
            List of selected note dictionaries, sorted by relevance
        """
        if not self.joplin_client:
            self.logger.warning("Joplin client not configured")
            return []

        try:
            # Fetch all notes
            all_notes = []
            notes = self.joplin_client._make_request('GET', '/notes')
            if isinstance(notes, list):
                all_notes = notes
            elif isinstance(notes, dict) and 'items' in notes:
                all_notes = notes['items']

            if not all_notes:
                self.logger.debug("No Joplin notes found")
                return []

            # Get folder mapping
            folders = self.joplin_client.get_folders()
            folder_map = {f["id"]: f.get("title", "Unknown") for f in folders}

            # Try hybrid filtering first: tags + recent modifications
            selected_notes = []
            for note in all_notes:
                has_tag = self._has_priority_tag(note)
                is_recent = self._is_recently_modified(note, self.RECENT_DAYS_THRESHOLD)

                if has_tag or is_recent:
                    # Enrich with folder information
                    folder_id = note.get("parent_id", "")
                    note["folder_id"] = folder_id
                    note["folder_name"] = folder_map.get(folder_id, "Unknown")
                    selected_notes.append(note)

            # Fallback: if hybrid filter returns too few notes, use AI to analyze all
            if len(selected_notes) == 0:
                self.logger.debug(
                    "Hybrid filter found 0 notes (no tags, no recent mods). "
                    "Using AI analysis to rank all notes by importance."
                )
                # Use all notes and let AI analysis rank them
                for note in all_notes:
                    folder_id = note.get("parent_id", "")
                    note["folder_id"] = folder_id
                    note["folder_name"] = folder_map.get(folder_id, "Unknown")
                selected_notes = all_notes
            elif len(selected_notes) < 5:
                self.logger.debug(
                    f"Hybrid filter found only {len(selected_notes)} notes. "
                    "Adding AI-analyzed untagged notes to reach minimum threshold."
                )
                # Add a few more notes analyzed by AI
                untagged_notes = [
                    n for n in all_notes
                    if not self._has_priority_tag(n) and n not in selected_notes
                ]
                for note in untagged_notes[:5]:
                    folder_id = note.get("parent_id", "")
                    note["folder_id"] = folder_id
                    note["folder_name"] = folder_map.get(folder_id, "Unknown")
                    selected_notes.append(note)

            self.logger.debug(
                f"Selected {len(selected_notes)} relevant Joplin notes from {len(all_notes)} total"
            )
            return selected_notes

        except Exception as e:
            self.logger.error(f"Failed to fetch Joplin notes: {e}")
            return []

    async def fetch_google_tasks_for_report(self, user_id: int) -> list[dict[str, Any]]:
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
            # Get task lists (get_available_task_lists is synchronous)
            task_lists = self.task_service.get_available_task_lists(str(user_id))
            if not task_lists:
                self.logger.debug("No Google task lists found")
                return []

            # Fetch tasks from all lists
            all_tasks = []
            for task_list in task_lists:
                try:
                    # get_user_tasks is synchronous
                    tasks = self.task_service.get_user_tasks(
                        str(user_id), task_list.get("id"), show_completed=False
                    )
                    if tasks:
                        # Only include incomplete tasks (never count completed as pending/unprocessed)
                        for task in tasks:
                            if task.get("status") != "completed":
                                task["tasklist_id"] = task_list.get("id")
                                all_tasks.append(task)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch tasks from list {task_list.get('id')}: {e}"
                    )
                    continue

            self.logger.debug(f"Fetched {len(all_tasks)} incomplete Google Tasks")
            return all_tasks

        except Exception as e:
            self.logger.error(f"Failed to fetch Google Tasks: {e}")
            return []

    async def fetch_notes_created_today(
        self, user_id: int
    ) -> list[tuple[str, str]]:
        """
        Fetch Joplin notes created today (user timezone).

        Returns:
            List of (title, folder) tuples.
        """
        if not self.joplin_client:
            return []

        try:
            now = get_user_timezone_aware_now(user_id, self.logging_service)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day.replace(
                hour=23, minute=59, second=59, microsecond=999_999
            )
            start_ts = int(start_of_day.timestamp() * 1000)
            end_ts = int(end_of_day.timestamp() * 1000)

            notes = await self.joplin_client.get_all_notes(
                fields="id,title,parent_id,created_time,user_created_time"
            )
            folders = await self.joplin_client.get_folders()
            folder_map = {f.get("id"): f.get("title", "Unknown") for f in folders}

            result: list[tuple[str, str]] = []
            for note in notes:
                created_ts = note.get("created_time") or note.get("user_created_time", 0)
                if start_ts <= created_ts <= end_ts:
                    folder = folder_map.get(note.get("parent_id", ""), "Unknown")
                    result.append((note.get("title", "Untitled"), folder))
            return result
        except Exception as e:
            self.logger.error(f"Failed to fetch notes created today: {e}")
            return []

    async def fetch_inbox_notes_count(self, user_id: int) -> int:
        """
        Count notes in Inbox folder(s) — unprocessed items ("in").

        Matches folders: inbox, brain dump, capture (case-insensitive).
        """
        if not self.joplin_client:
            return 0

        try:
            folders = await self.joplin_client.get_folders()
            inbox_ids: set[str] = set()
            for f in folders:
                title = (f.get("title") or "").strip().lower()
                if (
                    title in ("inbox", "brain dump", "capture", "00-inbox", "00 inbox")
                    or "inbox" in title
                    or ("brain" in title and "dump" in title)
                ):
                    inbox_ids.add(f.get("id", ""))

            if not inbox_ids:
                return 0

            notes = await self.joplin_client.get_all_notes(
                fields="id,parent_id"
            )
            return sum(
                1 for n in notes
                if n.get("parent_id") in inbox_ids
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch inbox notes count: {e}")
            return 0

    async def fetch_tasks_completed_today(self, user_id: int) -> list[str]:
        """
        Fetch Google Tasks completed today (user timezone).

        Returns:
            List of task titles.
        """
        if not self.task_service:
            return []

        try:
            now = get_user_timezone_aware_now(user_id, self.logging_service)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day.replace(
                hour=23, minute=59, second=59, microsecond=999_999
            )

            task_lists = self.task_service.get_available_task_lists(str(user_id))
            if not task_lists:
                return []

            start_ts = start_of_day.timestamp()
            end_ts = end_of_day.timestamp()
            result: list[str] = []
            for task_list in task_lists:
                tasks = self.task_service.get_user_tasks(
                    str(user_id), task_list.get("id"), show_completed=True
                ) or []
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
                        if start_ts <= completed_dt.timestamp() <= end_ts:
                            result.append(task.get("title", "Untitled Task"))
                    except (ValueError, TypeError):
                        pass
            return result
        except Exception as e:
            self.logger.error(f"Failed to fetch tasks completed today: {e}")
            return []

    async def aggregate_report_items(
        self,
        user_id: int,
        joplin_notes: list[dict[str, Any]],
        google_tasks: list[dict[str, Any]],
        min_priority: PriorityLevel = PriorityLevel.LOW,
    ) -> list[ReportItem]:
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
        pending_clarifications: list[tuple[str, str]] = None,
        completed_items: list[str] = None,
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
            # Fetch from all sources concurrently
            (
                joplin_notes,
                google_tasks,
                notes_created_today,
                tasks_completed_today,
                inbox_notes_count,
            ) = await asyncio.gather(
                self.fetch_joplin_notes_for_report(user_id, min_priority),
                self.fetch_google_tasks_for_report(user_id),
                self.fetch_notes_created_today(user_id),
                self.fetch_tasks_completed_today(user_id),
                self.fetch_inbox_notes_count(user_id),
            )

            # Aggregate items
            items = await self.aggregate_report_items(
                user_id, joplin_notes, google_tasks, min_priority
            )

            # Categorize by priority
            report = self.categorize_items(items)
            report.user_id = user_id
            report.report_date = datetime.now()
            report.notes_created_today = notes_created_today
            report.tasks_completed_today = tasks_completed_today
            report.inbox_notes_count = inbox_notes_count

            # Add pending clarifications
            if pending_clarifications:
                for _note_id, note_title in pending_clarifications:
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

            # FR-034: Stalled projects (no incomplete subtasks)
            if self.task_service:
                try:
                    report.stalled_projects = await asyncio.to_thread(
                        self.task_service.get_stalled_project_titles, str(user_id)
                    )
                except Exception as e:
                    self.logger.debug("Failed to fetch stalled projects: %s", e)

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

    def _format_item_line(self, item: ReportItem, show_source: bool = True) -> str:
        """
        Format a single report item as a line for Telegram

        Args:
            item: ReportItem to format
            show_source: Whether to show source (Joplin/Google Tasks)

        Returns:
            Formatted line
        """
        line = f"• {item.title}"

        # Add due date info if available
        if item.due_date:
            if item.is_overdue:
                days_str = (
                    f"OVERDUE since {item.due_date.strftime('%b %d')}"
                    if item.days_overdue > 0
                    else "OVERDUE"
                )
                line += f" - {days_str}"
            else:
                line += f" - Due {item.due_date.strftime('%b %d')}"

        # Add source indicator
        if show_source:
            source_emoji = "📝" if item.source == ItemSource.JOPLIN else "✅"
            line += f" ({source_emoji})"

        return line

    def _priority_label(self, level: PriorityLevel) -> str:
        """Return emoji + label for priority level. FR-039: URGENT."""
        labels = {
            PriorityLevel.URGENT: "🔥 Urgent",
            PriorityLevel.CRITICAL: "🔴 Critical",
            PriorityLevel.HIGH: "🟠 High",
            PriorityLevel.MEDIUM: "🟡 Medium",
            PriorityLevel.LOW: "🟢 Low",
        }
        return labels.get(level, "🟡 Medium")

    def _format_due_for_display(self, item: ReportItem) -> str:
        """Format due date for display. Returns empty string if no due date."""
        if not item.due_date:
            return ""
        due = item.due_date.date()
        today = datetime.now().date()
        delta = (due - today).days
        if delta < 0:
            return f"Overdue {abs(delta)}d"
        if delta == 0:
            return "Due today"
        if delta == 1:
            return "Due tomorrow"
        if delta <= 7:
            return f"Due in {delta}d"
        return f"Due {due.strftime('%b %d')}"

    def _source_label(self, item: ReportItem) -> str:
        """Return source label for table."""
        return "📝 Note" if item.source == ItemSource.JOPLIN else "✅ Task"

    def format_report_message(
        self, report: ReportData, include_details: bool = True
    ) -> str:
        """
        Format report data as plain text (Design A).
        Always specifies Task vs Note. Notes show folder (where).
        """
        has_content = (
            report.total_items
            or report.completed_items
            or report.pending_clarification
            or report.notes_created_today
            or report.tasks_completed_today
            or report.stalled_projects
        )
        if not has_content:
            return "📊 Daily Priority Report\n\nNo items to report today. Great job staying on top of things! 🎉"

        lines: list[str] = []

        # Header
        report_date = report.report_date.strftime("%b %d, %Y")
        lines.append(f"📊 Daily Priority Report — {report_date}")

        summary_parts = []
        if report.google_tasks_count > 0:
            summary_parts.append(f"{report.google_tasks_count} Tasks")
        if report.joplin_count > 0:
            summary_parts.append(f"{report.joplin_count} Notes")
        if report.notes_created_today:
            summary_parts.append(f"{len(report.notes_created_today)} created today")
        if report.tasks_completed_today:
            summary_parts.append(f"{len(report.tasks_completed_today)} completed")
        summary = " • ".join(summary_parts) if summary_parts else "No items"
        lines.append(f"{summary}\n")

        # In (unprocessed): pending tasks + inbox notes
        in_parts = []
        if report.google_tasks_count > 0:
            in_parts.append(f"{report.google_tasks_count} tasks")
        if report.inbox_notes_count > 0:
            in_parts.append(f"{report.inbox_notes_count} notes")
        if in_parts:
            lines.append(f"📥 In (unprocessed): {' • '.join(in_parts)}\n")

        # Notes created today (with folder)
        if report.notes_created_today:
            lines.append("📝 Notes created today")
            for title, folder in report.notes_created_today[:15]:
                lines.append(f"• [{folder}] {escape_for_html(title)}")
            if len(report.notes_created_today) > 15:
                lines.append(f"• ... +{len(report.notes_created_today) - 15} more")
            lines.append("")

        # Priority Tasks (Tasks = Google Tasks, pending)
        # No inferred priority label — Google Tasks have no real priority; show due date instead
        priority_items = (
            report.critical_items + report.high_items + report.medium_items + report.low_items
        )
        if priority_items:
            lines.append("🎯 Tasks (pending)")
            for item in priority_items[:15]:
                due_str = self._format_due_for_display(item)
                if due_str:
                    lines.append(f"• {escape_for_html(item.title)} — {due_str}")
                else:
                    lines.append(f"• {escape_for_html(item.title)}")
            if len(priority_items) > 15:
                lines.append(f"• ... +{len(priority_items) - 15} more tasks")
            lines.append("")

        # Notes (Joplin) — with folder (where)
        if report.joplin_notes:
            lines.append(f"📝 Notes ({report.joplin_count})")
            for note in report.joplin_notes[:15]:
                folder = note.metadata.get("folder", "Unknown")
                priority_emoji = (
                    "🔴" if note.priority_level == PriorityLevel.CRITICAL else
                    "🟠" if note.priority_level == PriorityLevel.HIGH else
                    "🟡" if note.priority_level == PriorityLevel.MEDIUM else "🟢"
                )
                lines.append(f"• {priority_emoji} [{folder}] {escape_for_html(note.title)}")
            if len(report.joplin_notes) > 15:
                lines.append(f"• ... +{len(report.joplin_notes) - 15} more notes")
            lines.append("")

        # FR-034: Stalled projects (no next actions)
        if report.stalled_projects:
            lines.append("⚠️ Projects with no next actions")
            for title in report.stalled_projects:
                lines.append(f"• {escape_for_html(title)}")
            lines.append("")

        # Pending clarifications
        if report.pending_clarification:
            lines.append("⏳ Pending Clarification")
            for item_title in report.pending_clarification:
                lines.append(f"• {escape_for_html(item_title)}")
            lines.append("")

        # Completed (tasks from API + any from conversation state)
        all_completed = list(
            dict.fromkeys(report.tasks_completed_today + report.completed_items)
        )
        if all_completed:
            lines.append(f"✨ Completed Today ({len(all_completed)} items)")
            for item_title in all_completed[:10]:
                lines.append(f"• {escape_for_html(item_title)}")
            if len(all_completed) > 10:
                lines.append(f"  ... and {len(all_completed) - 10} more")
            lines.append("")

        # Footer
        lines.append("—" * 25)
        lines.append("🔗 /daily_report — regenerate")
        lines.append("⚙️ /show_report_config — settings")

        return "\n".join(lines)

    def format_report_compact(self, report: ReportData) -> str:
        """
        Format report as a compact/brief message

        Args:
            report: ReportData to format

        Returns:
            Compact formatted message
        """
        if not report.total_items:
            return "📊 Daily Priority Report\n\nNo items today."

        lines = []
        report_date = report.report_date.strftime("%b %d")
        lines.append(f"📊 Daily Report - {report_date}")
        lines.append(f"Critical: {len(report.critical_items)} | High: {len(report.high_items)} | Medium: {len(report.medium_items)}")
        lines.append(f"Completed: {report.completed_count}")

        if report.all_items:
            top = report.all_items[0]
            lines.append(f"\n🎯 Top Priority: {top.title}")

        lines.append("\n/daily_report - Full report")

        return "\n".join(lines)

    def format_report_detailed(self, report: ReportData) -> str:
        """
        Format report with full details including descriptions

        Args:
            report: ReportData to format

        Returns:
            Detailed formatted message
        """
        lines = []
        report_date = report.report_date.strftime("%b %d, %Y")
        lines.append(f"📊 Daily Priority Report - {report_date}")
        lines.append(f"Total items: {report.total_items}")
        lines.append("")

        # Critical
        if report.critical_items:
            lines.append("🔴 CRITICAL ITEMS")
            for item in report.critical_items:
                lines.append(f"• {item.title}")
                if item.description:
                    lines.append(f"  {item.description}")
            lines.append("")

        # High
        if report.high_items:
            lines.append("🟠 HIGH PRIORITY")
            for item in report.high_items[:10]:
                lines.append(f"• {item.title}")
                if item.description:
                    lines.append(f"  {item.description}")
            lines.append("")

        return "\n".join(lines)

    def format_configuration_display(self, config: dict[str, Any]) -> str:
        """
        Format user's report configuration for display

        Args:
            config: Configuration dictionary

        Returns:
            Formatted configuration display
        """
        lines = []
        lines.append("⚙️ Your Report Configuration")
        lines.append("")

        # Status
        enabled = config.get("enabled", True)
        status = "✅ Enabled" if enabled else "❌ Disabled"
        lines.append(f"Status: {status}")

        # Delivery settings
        lines.append(f"Delivery Time: {config.get('delivery_time', '08:00')}")
        lines.append(f"Timezone: {config.get('timezone', 'UTC')}")

        # Content settings
        lines.append("")
        lines.append("Content Included:")
        lines.append(f"  • Critical: {'Yes' if config.get('include_critical') else 'No'}")
        lines.append(f"  • High Priority: {'Yes' if config.get('include_high') else 'No'}")
        lines.append(f"  • Medium Priority: {'Yes' if config.get('include_medium') else 'No'}")
        lines.append(f"  • Google Tasks: {'Yes' if config.get('include_google_tasks') else 'No'}")
        lines.append(f"  • Clarifications: {'Yes' if config.get('include_clarification_pending') else 'No'}")

        lines.append("")
        lines.append("Detail Level: " + config.get("detail_level", "detailed").capitalize())

        lines.append("")
        lines.append("Commands:")
        lines.append("  /configure_report_time <HH:MM>")
        lines.append("  /configure_report_timezone <timezone>")
        lines.append("  /toggle_daily_report on|off")
        lines.append("  /configure_report_content critical|high|medium|all")
        lines.append("  /report_help")

        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage

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

    print("\n📊 Report Summary:")
    print(f"Total items: {report.total_items}")
    print(f"Critical: {len(report.critical_items)}")
    print(f"High: {len(report.high_items)}")
    print(f"Medium: {len(report.medium_items)}")
    print(f"Completed: {report.completed_count}")
    print(f"\nTop Recommendation: {generator.get_top_recommendation(report)}")
