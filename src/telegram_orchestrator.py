"""
Telegram Orchestrator — thin coordinator that wires services and registers handlers.

Supports two modes:
  • Webhook (Fly.io / production): machine sleeps when idle, wakes on message
  • Polling (local development): always-on, no public URL needed

Mode is auto-detected: if WEBHOOK_URL or FLY_APP_NAME is set → webhook,
otherwise → polling.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from telegram.ext import Application

if TYPE_CHECKING:
    from src.task_service import TaskService

from config import TELEGRAM_BOT_TOKEN
from src.enrichment_service import EnrichmentService
from src.health.health_service import HealthService
from src.health.health_store import HealthStore
from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator
from src.logging_service import LoggingService
from src.note_index import NoteIndex
from src.reorg_orchestrator import ReorgOrchestrator
from src.report_generator import ReportGenerator
from src.scheduler_service import get_scheduler_service
from src.security_utils import ping_joplin_api
from src.settings import get_settings
from src.state_manager import StateManager

logger = logging.getLogger(__name__)

GOOGLE_TASKS_AVAILABLE = False
try:
    import src.google_tasks_client  # noqa: F401
    import src.task_service  # noqa: F401

    GOOGLE_TASKS_AVAILABLE = True
except ImportError:
    pass


class TelegramOrchestrator:
    """Holds all service instances; handlers reference them via ``orch.<service>``."""

    def __init__(self) -> None:
        self.joplin_client = JoplinClient()
        self.llm_orchestrator = LLMOrchestrator()

        settings = get_settings()

        self.state_manager = StateManager(db_path=settings.database.state_db_path)
        self.logging_service = LoggingService(db_path=settings.database.logs_db_path)
        self.health_store = HealthStore(db_path=settings.database.health_db_path)
        self.health_service = HealthService(store=self.health_store)

        self.task_service: TaskService | None = None
        if GOOGLE_TASKS_AVAILABLE:
            try:
                from src.google_tasks_client import GoogleTasksClient
                from src.task_service import TaskService

                tasks_client = GoogleTasksClient()
                self.task_service = TaskService(tasks_client, self.logging_service)
                logger.info("Google Tasks integration initialized")
            except ValueError:
                logger.warning("Google Tasks not configured (credentials missing)")
            except Exception as exc:
                logger.warning("Failed to init Google Tasks: %s", exc)

        self.report_generator = ReportGenerator(
            joplin_client=self.joplin_client,
            task_service=self.task_service,
            logging_service=self.logging_service,
        )
        self.scheduler = get_scheduler_service()
        self.reorg_orchestrator = ReorgOrchestrator(
            joplin_client=self.joplin_client,
            llm_orchestrator=self.llm_orchestrator,
        )
        self.enrichment_service = EnrichmentService(
            joplin_client=self.joplin_client,
            llm_orchestrator=self.llm_orchestrator,
        )
        self.note_index = NoteIndex()
        logger.info("All services initialized")


# ---------------------------------------------------------------------------
# Webhook URL resolution
# ---------------------------------------------------------------------------

def _resolve_webhook_url() -> str | None:
    """Return the public webhook URL if we should run in webhook mode."""
    url = os.environ.get("WEBHOOK_URL")
    if url:
        return url.rstrip("/")
    app_name = os.environ.get("FLY_APP_NAME")
    if app_name:
        return f"https://{app_name}.fly.dev"
    return None


# ---------------------------------------------------------------------------
# Startup notification
# ---------------------------------------------------------------------------

async def _send_startup_message(
    application: Application,
    orchestrator: TelegramOrchestrator,
    mode: str,
    port: int | None = None,
) -> None:
    """Send a detailed startup message to whitelisted users (when NOTIFY_STARTUP is not disabled)."""
    if os.environ.get("NOTIFY_STARTUP", "1").strip().lower() in ("0", "false", "no"):
        return
    allowed = get_settings().telegram.allowed_ids
    if not allowed:
        logger.debug("No allowed user IDs — skipping startup notification")
        return

    joplin_ok = await ping_joplin_api()
    scheduler_running = getattr(
        getattr(orchestrator.scheduler, "scheduler", None), "running", False
    )

    lines = [
        "🟢 Bot started",
        "",
        f"• Mode: {mode}",
    ]
    if port is not None:
        lines.append(f"• Port: {port}")
    lines.extend([
        f"• Scheduler: {'running' if scheduler_running else 'stopped'}",
        f"• Joplin: {'OK' if joplin_ok else '⚠️ unreachable'}",
    ])
    text = "\n".join(lines)

    for chat_id in allowed:
        try:
            await application.bot.send_message(chat_id=chat_id, text=text)
            logger.info("Startup message sent to %s", chat_id)
        except Exception as exc:
            logger.warning("Could not send startup message to %s: %s", chat_id, exc)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def _build_application(orchestrator: TelegramOrchestrator) -> Application:
    """Build a PTB Application with all handlers registered (no updater for webhook)."""
    webhook_url = _resolve_webhook_url()
    use_webhook = webhook_url is not None

    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    if use_webhook:
        builder = builder.updater(None)
    application: Application = builder.build()

    from src.handlers import (
        register_ask_handlers,
        register_braindump_handlers,
        register_core_handlers,
        register_dream_handlers,
        register_flashcard_handlers,
        register_google_tasks_handlers,
        register_habit_handlers,
        register_health_handlers,
        register_photo_handlers,
        register_planning_handlers,
        register_profile_handlers,
        register_reading_handlers,
        register_reorg_handlers,
        register_report_handlers,
        register_search_handlers,
        register_stoic_handlers,
        register_voice_handlers,
    )

    register_google_tasks_handlers(application, orchestrator)
    register_ask_handlers(application, orchestrator)
    register_report_handlers(application, orchestrator)
    register_braindump_handlers(application, orchestrator)
    register_stoic_handlers(application, orchestrator)
    register_dream_handlers(application, orchestrator)
    register_reorg_handlers(application, orchestrator)
    register_search_handlers(application, orchestrator)
    register_photo_handlers(application, orchestrator)
    register_reading_handlers(application, orchestrator)
    register_habit_handlers(application, orchestrator)
    register_health_handlers(application, orchestrator)
    register_flashcard_handlers(application, orchestrator)
    register_planning_handlers(application, orchestrator)
    register_profile_handlers(application, orchestrator)
    register_voice_handlers(application, orchestrator)
    register_core_handlers(application, orchestrator)

    return application


async def _run_webhook(application: Application, orchestrator: TelegramOrchestrator) -> None:
    """Webhook mode — register webhook, start HTTP server, handle SIGTERM."""
    import signal

    from src.webhook_server import WebhookServer

    webhook_url = _resolve_webhook_url()
    full_url = f"{webhook_url}/webhook"
    port = int(os.environ.get("PORT", "8080"))
    secret = os.environ.get("WEBHOOK_SECRET")

    server = WebhookServer(
        ptb_app=application,
        port=port,
        webhook_path="/webhook",
        secret_token=secret,
    )

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    async with application:
        await application.start()

        # Bind port first so Fly.io health checks pass (app is "listening")
        await server.start()
        logger.info("Webhook server listening on 0.0.0.0:%d", port)

        try:
            await orchestrator.joplin_client.ensure_project_status_tags()
        except Exception as exc:
            logger.warning("Failed to ensure project status tags: %s", exc)

        await application.bot.set_webhook(
            url=full_url,
            secret_token=secret,
            drop_pending_updates=True,
        )
        logger.info("Webhook registered: %s", full_url)

        try:
            await orchestrator.scheduler.start()
            # FR-034 Option A: Schedule daily orphaned project cleanup
            async def _project_cleanup():
                await _run_project_cleanup(orchestrator)
            orchestrator.scheduler.schedule_project_cleanup(_project_cleanup)
        except Exception as exc:
            logger.error("Scheduler start failed: %s", exc)

        logger.info("Bot running in WEBHOOK mode on port %d", port)
        await _send_startup_message(application, orchestrator, "WEBHOOK", port=port)
        await stop_event.wait()
        logger.info("Shutdown signal received, stopping gracefully...")

        try:
            await orchestrator.scheduler.stop()
        except Exception as exc:
            logger.error("Scheduler stop failed: %s", exc)
        await server.stop()
        await application.stop()


async def _run_project_cleanup(orchestrator: TelegramOrchestrator) -> None:
    """FR-034 Option A: Cleanup orphaned project mappings for all users with project sync enabled."""
    if not orchestrator.task_service or not orchestrator.joplin_client:
        return
    try:
        user_ids = orchestrator.logging_service.get_user_ids_with_project_sync_enabled()
        if not user_ids:
            return
        folders = await orchestrator.joplin_client.get_folders()
        folder_ids = {f.get("id", "") for f in folders}
        total = 0
        for uid in user_ids:
            removed = orchestrator.task_service.cleanup_orphaned_project_mappings(
                str(uid), folder_ids
            )
            total += removed
        if total > 0:
            logger.info("FR-034: Periodic cleanup removed %d orphaned project mapping(s)", total)
    except Exception as exc:
        logger.warning("FR-034: Project cleanup failed: %s", exc)


def _run_polling(application: Application, orchestrator: TelegramOrchestrator) -> None:
    """Polling mode — used for local development."""

    async def _startup(app: Application) -> None:
        try:
            await orchestrator.joplin_client.ensure_project_status_tags()
        except Exception as exc:
            logger.warning("Failed to ensure project status tags: %s", exc)
        try:
            await orchestrator.scheduler.start()
            async def _project_cleanup():
                await _run_project_cleanup(orchestrator)
            orchestrator.scheduler.schedule_project_cleanup(_project_cleanup)
        except Exception as exc:
            logger.error("Scheduler start failed: %s", exc)
        await _send_startup_message(app, orchestrator, "POLLING")

    async def _shutdown(context: object) -> None:
        try:
            await orchestrator.scheduler.stop()
        except Exception as exc:
            logger.error("Scheduler stop failed: %s", exc)

    application.post_init = _startup
    application.post_shutdown = _shutdown

    logger.info("Bot running in POLLING mode")
    application.run_polling(poll_interval=3, timeout=10, drop_pending_updates=True)


def main() -> None:
    """Entry-point: detect mode, build app, and run."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    orchestrator = TelegramOrchestrator()
    application = _build_application(orchestrator)

    webhook_url = _resolve_webhook_url()
    if webhook_url:
        asyncio.run(_run_webhook(application, orchestrator))
    else:
        _run_polling(application, orchestrator)


if __name__ == "__main__":
    main()
