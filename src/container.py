"""
Service container / dependency injection.

Creates and wires all services once at startup.
Modules receive their dependencies instead of importing globals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.settings import AppSettings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceContainer:
    """Holds all application services — created once at startup."""

    settings: AppSettings = field(default_factory=get_settings)

    # Lazy-initialised services (set in .build())
    joplin: object = field(default=None, init=False)
    llm: object = field(default=None, init=False)
    state_manager: object = field(default=None, init=False)
    logging_service: object = field(default=None, init=False)
    task_service: Optional[object] = field(default=None, init=False)
    report_generator: object = field(default=None, init=False)
    scheduler: object = field(default=None, init=False)
    reorg: object = field(default=None, init=False)
    enrichment: object = field(default=None, init=False)

    def build(self) -> "ServiceContainer":
        """Instantiate all services with proper wiring."""
        from src.joplin_client import JoplinClient
        from src.llm_orchestrator import LLMOrchestrator
        from src.logging_service import LoggingService
        from src.state_manager import StateManager
        from src.report_generator import ReportGenerator
        from src.scheduler_service import get_scheduler_service
        from src.reorg_orchestrator import ReorgOrchestrator
        from src.enrichment_service import EnrichmentService

        self.joplin = JoplinClient(settings=self.settings.joplin)
        self.llm = LLMOrchestrator()
        self.state_manager = StateManager(db_path=self.settings.database.state_db_path)
        self.logging_service = LoggingService(db_path=self.settings.database.logs_db_path)

        # Optional Google Tasks
        self.task_service = self._build_task_service()

        self.report_generator = ReportGenerator(
            joplin_client=self.joplin,
            task_service=self.task_service,
        )

        self.scheduler = get_scheduler_service()

        self.reorg = ReorgOrchestrator(
            joplin_client=self.joplin,
            llm_orchestrator=self.llm,
        )

        self.enrichment = EnrichmentService(
            joplin_client=self.joplin,
            llm_orchestrator=self.llm,
        )

        logger.info("Service container built")
        return self

    def _build_task_service(self) -> Optional[object]:
        if not self.settings.google.is_configured:
            logger.info("Google Tasks not configured — skipping")
            return None
        try:
            from src.google_tasks_client import GoogleTasksClient
            from src.task_service import TaskService

            client = GoogleTasksClient()
            return TaskService(client, self.logging_service)
        except Exception as exc:
            logger.warning("Failed to init Google Tasks: %s", exc)
            return None


_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    global _container
    if _container is None:
        _container = ServiceContainer().build()
    return _container
