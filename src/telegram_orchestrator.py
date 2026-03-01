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
from typing import Optional

from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from src.enrichment_service import EnrichmentService
from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator
from src.logging_service import LoggingService
from src.report_generator import ReportGenerator
from src.reorg_orchestrator import ReorgOrchestrator
from src.scheduler_service import get_scheduler_service
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

        from config import LOGS_DB_PATH, STATE_DB_PATH

        self.state_manager = StateManager(db_path=STATE_DB_PATH)
        self.logging_service = LoggingService(db_path=LOGS_DB_PATH)

        self.task_service: Optional[object] = None
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
        logger.info("All services initialized")


# ---------------------------------------------------------------------------
# Webhook URL resolution
# ---------------------------------------------------------------------------

def _resolve_webhook_url() -> Optional[str]:
    """Return the public webhook URL if we should run in webhook mode."""
    url = os.environ.get("WEBHOOK_URL")
    if url:
        return url.rstrip("/")
    app_name = os.environ.get("FLY_APP_NAME")
    if app_name:
        return f"https://{app_name}.fly.dev"
    return None


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
        register_braindump_handlers,
        register_core_handlers,
        register_google_tasks_handlers,
        register_reorg_handlers,
        register_report_handlers,
    )

    register_google_tasks_handlers(application, orchestrator)
    register_report_handlers(application, orchestrator)
    register_braindump_handlers(application, orchestrator)
    register_reorg_handlers(application, orchestrator)
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
        except Exception as exc:
            logger.error("Scheduler start failed: %s", exc)

        logger.info("Bot running in WEBHOOK mode on port %d", port)
        await stop_event.wait()
        logger.info("Shutdown signal received, stopping gracefully...")

        try:
            await orchestrator.scheduler.stop()
        except Exception as exc:
            logger.error("Scheduler stop failed: %s", exc)
        await server.stop()
        await application.stop()


def _run_polling(application: Application, orchestrator: TelegramOrchestrator) -> None:
    """Polling mode — used for local development."""

    async def _startup(context: object) -> None:
        try:
            await orchestrator.joplin_client.ensure_project_status_tags()
        except Exception as exc:
            logger.warning("Failed to ensure project status tags: %s", exc)
        try:
            await orchestrator.scheduler.start()
        except Exception as exc:
            logger.error("Scheduler start failed: %s", exc)

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
