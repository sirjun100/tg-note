"""
Telegram bot command and message handlers.

Each module groups related handlers by domain:
- core: /start, /status, /helpme, message routing
- google_tasks: Google Tasks OAuth and management
- reports: Daily reports, scheduling, configuration
- braindump: Brain dump capture sessions
- reorg: Joplin database reorganization (PARA)
"""

from src.handlers.core import register_core_handlers
from src.handlers.google_tasks import register_google_tasks_handlers
from src.handlers.reports import register_report_handlers
from src.handlers.braindump import register_braindump_handlers
from src.handlers.reorg import register_reorg_handlers


def register_all_handlers(application, orchestrator) -> None:
    """Register all handler groups on the application."""
    register_core_handlers(application, orchestrator)
    register_google_tasks_handlers(application, orchestrator)
    register_report_handlers(application, orchestrator)
    register_braindump_handlers(application, orchestrator)
    register_reorg_handlers(application, orchestrator)
