"""
Handler modules — each registers its own command/message handlers.
"""

from src.handlers.ask import register_ask_handlers
from src.handlers.braindump import register_braindump_handlers
from src.handlers.core import register_core_handlers
from src.handlers.dream import register_dream_handlers
from src.handlers.flashcard import register_flashcard_handlers
from src.handlers.google_tasks import register_google_tasks_handlers
from src.handlers.habits import register_habit_handlers
from src.handlers.health import register_health_handlers
from src.handlers.photo import register_photo_handlers
from src.handlers.planning import register_planning_handlers
from src.handlers.profile import register_profile_handlers
from src.handlers.reading import register_reading_handlers
from src.handlers.reorg import register_reorg_handlers
from src.handlers.reports import register_report_handlers
from src.handlers.search import register_search_handlers
from src.handlers.stoic import register_stoic_handlers
from src.handlers.voice import register_voice_handlers

__all__ = [
    "register_ask_handlers",
    "register_core_handlers",
    "register_dream_handlers",
    "register_flashcard_handlers",
    "register_google_tasks_handlers",
    "register_habit_handlers",
    "register_health_handlers",
    "register_planning_handlers",
    "register_profile_handlers",
    "register_photo_handlers",
    "register_reading_handlers",
    "register_report_handlers",
    "register_braindump_handlers",
    "register_reorg_handlers",
    "register_search_handlers",
    "register_stoic_handlers",
    "register_voice_handlers",
]
