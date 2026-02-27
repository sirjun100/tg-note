"""
Google Tasks handlers: authorization, configuration, listing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.security_utils import check_whitelist

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def register_google_tasks_handlers(application: Any, orch: "TelegramOrchestrator") -> None:
    application.add_handler(CommandHandler("authorize_google_tasks", _authorize(orch)))
    application.add_handler(CommandHandler("verify_google", _verify(orch)))
    application.add_handler(CommandHandler("google_tasks_config", _config(orch)))
    application.add_handler(CommandHandler("set_task_list", _set_task_list(orch)))
    application.add_handler(CommandHandler("toggle_auto_tasks", _toggle_auto_tasks(orch)))
    application.add_handler(CommandHandler("toggle_privacy", _toggle_privacy(orch)))
    application.add_handler(CommandHandler("google_tasks_status", _tasks_status(orch)))
    application.add_handler(CommandHandler("list_inbox_tasks", _list_inbox_tasks(orch)))


def _authorize(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()
            auth_url, state = tasks_client.get_authorization_url()

            orch.state_manager.update_state(user.id, {"google_auth_state": state})

            msg = (
                "🔐 Google Tasks Authorization\n\n"
                "Click the link below to authorize the bot to access your Google Tasks:\n\n"
                f"{auth_url}\n\n"
                "After clicking the link and authorizing:\n"
                "1. You'll see an authorization code\n"
                "2. Copy the code\n"
                "3. Send it back to me with: /verify_google [code]\n\n"
                "Example: `/verify_google 4/0AY0e-g7X...`"
            )
            await update.message.reply_text(msg)
            logger.info("Google Tasks authorization initiated for user %d", user.id)
        except ValueError as exc:
            await update.message.reply_text(
                f"❌ Google Tasks is not properly configured: {exc}\n"
                "Please check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        except Exception as exc:
            logger.error("Error in Google Tasks authorization: %s", exc)
            await update.message.reply_text(f"❌ Authorization failed: {exc}")

    return handler


def _verify(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: `/verify_google [authorization_code]`\n\n"
                "Example: `/verify_google 4/0AY0e-g7X...`"
            )
            return

        auth_code = context.args[0]
        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()
            token = tasks_client.exchange_code_for_token(auth_code)

            orch.logging_service.save_google_token(str(user.id), token)

            config = {
                "enabled": True,
                "auto_create_tasks": True,
                "include_only_tagged": False,
                "task_creation_tags": [],
                "privacy_mode": False,
            }
            orch.logging_service.save_google_tasks_config(user.id, config)

            state = orch.state_manager.get_state(user.id)
            if state and "google_auth_state" in state:
                del state["google_auth_state"]
                if state:
                    orch.state_manager.update_state(user.id, state)
                else:
                    orch.state_manager.clear_state(user.id)

            await update.message.reply_text(
                "✅ Google Tasks authorized successfully!\n\n"
                "Your bot can now:\n"
                "• Automatically create tasks from notes\n"
                "• Read your Google Tasks\n"
                "• Include tasks in daily/weekly reports\n\n"
                "Configure with:\n"
                "/google_tasks_config - Manage settings\n"
                "/google_tasks_status - View sync status\n\n"
                "Use /status to verify the connection."
            )
            logger.info("Google Tasks authorized for user %d", user.id)
        except ValueError as exc:
            await update.message.reply_text(f"❌ Invalid authorization code or configuration error: {exc}")
            logger.error("Google Tasks verification failed: %s", exc)
        except Exception as exc:
            await update.message.reply_text(
                f"❌ Authorization failed: {exc}\n\nPlease try again with: `/authorize_google_tasks`"
            )
            logger.error("Error in Google Tasks verification: %s", exc)

    return handler


def _config(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks integration is not available")
            return

        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text(
                    "❌ Google Tasks not authorized yet.\nUse /authorize_google_tasks first."
                )
                return

            task_lists = orch.task_service.get_available_task_lists(str(user.id))

            msg = "⚙️ Google Tasks Configuration\n\n"
            msg += f"Status: {'✅ Enabled' if cfg.get('enabled') else '❌ Disabled'}\n"
            msg += f"Auto task creation: {'✅ On' if cfg.get('auto_create_tasks') else '❌ Off'}\n"
            msg += f"Privacy mode: {'🔒 On' if cfg.get('privacy_mode') else '🔓 Off'}\n"
            msg += f"Current task list: {cfg.get('task_list_name', 'Not set')}\n\n"

            if task_lists:
                msg += "Available task lists:\n"
                for idx, tl in enumerate(task_lists, 1):
                    msg += f"{idx}. {tl.get('title')} (ID: {tl.get('id')[:10]}...)\n"
                msg += "\nReply with: /set_task_list [number]\n"
            else:
                msg += "No task lists found\n"

            msg += "\nOther commands:\n"
            msg += "/toggle_auto_tasks - Turn auto task creation on/off\n"
            msg += "/toggle_privacy - Turn privacy mode on/off\n"
            msg += "/google_tasks_status - View synchronization status\n"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error loading configuration: {exc}")
            logger.error("Error in google_tasks_config: %s", exc)

    return handler


def _set_task_list(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not context.args:
            await update.message.reply_text("Usage: /set_task_list [number]")
            return
        try:
            list_num = int(context.args[0]) - 1
            task_lists = orch.task_service.get_available_task_lists(str(user.id))
            if list_num < 0 or list_num >= len(task_lists):
                await update.message.reply_text("❌ Invalid task list number")
                return
            selected = task_lists[list_num]
            orch.task_service.set_preferred_task_list(user.id, selected.get("id"), selected.get("title"))
            await update.message.reply_text(f"✅ Task list changed to: {selected.get('title')}")
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")
            logger.error("Error in set_task_list: %s", exc)

    return handler


def _toggle_auto_tasks(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks not authorized")
                return
            enabled = not cfg.get("auto_create_tasks", True)
            orch.task_service.toggle_auto_task_creation(user.id, enabled)
            await update.message.reply_text(f"Auto task creation: {'✅ Enabled' if enabled else '❌ Disabled'}")
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")

    return handler


def _toggle_privacy(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks not authorized")
                return
            enabled = not cfg.get("privacy_mode", False)
            orch.task_service.toggle_privacy_mode(user.id, enabled)
            await update.message.reply_text(f"Privacy mode: {'🔒 Enabled' if enabled else '🔓 Disabled'}")
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")

    return handler


def _tasks_status(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            status = orch.task_service.get_task_sync_status(user.id)
            msg = "📊 Google Tasks Sync Status\n\n"
            msg += f"Total synced: {status.get('total_synced', 0)}\n"
            msg += f"✅ Successful: {status.get('success_count', 0)}\n"
            msg += f"❌ Failed: {status.get('failed_count', 0)}\n\n"
            if status.get("recent_syncs"):
                msg += "Recent syncs:\n"
                for sync in status["recent_syncs"][:3]:
                    action = sync.get("action", "unknown")
                    icon = "✅" if sync.get("sync_result") == "success" else "❌"
                    msg += f"{icon} {action} - {sync.get('created_at', 'N/A')}\n"
            if status.get("failed_syncs"):
                msg += f"\n⚠️ Failed syncs: {len(status['failed_syncs'])}\n"
                for sync in status["failed_syncs"][:2]:
                    msg += f"• {sync.get('error_message', 'Unknown error')}\n"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")
            logger.error("Error in google_tasks_status: %s", exc)

    return handler


def _list_inbox_tasks(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks integration not available")
            return

        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks not authorized\n\nUse /authorize_google_tasks to set up access"
                )
                return

            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg or not cfg.get("enabled"):
                await update.message.reply_text("❌ Google Tasks is disabled")
                return

            task_list_id = cfg.get("task_list_id")
            tasks_client = orch.task_service.tasks_client
            tasks_client.set_token(token)

            if not task_list_id:
                try:
                    task_lists = tasks_client.get_task_lists()
                    if tasks_client.token and tasks_client.token != token:
                        orch.logging_service.save_google_token(str(user.id), tasks_client.token)
                    if not task_lists:
                        await update.message.reply_text(
                            "❌ No Google Tasks lists found\n\n"
                            "Please create a task list in Google Tasks (https://calendar.google.com)"
                        )
                        return
                    task_list_id = task_lists[0]["id"]
                except Exception as exc:
                    await update.message.reply_text(f"❌ Error getting task lists: {exc}")
                    return

            tasks = tasks_client.get_tasks(task_list_id, show_completed=False)
            if tasks_client.token and tasks_client.token != token:
                orch.logging_service.save_google_token(str(user.id), tasks_client.token)

            if not tasks:
                await update.message.reply_text("📭 No pending tasks in Google Tasks")
                return

            task_list_name = cfg.get("task_list_name", "My Tasks")
            msg = f"📋 Google Tasks - {task_list_name} ({len(tasks)} pending)\n\n"
            for i, task in enumerate(tasks, 1):
                title = task.get("title", "Untitled")
                due = task.get("due", "")
                due_str = f" (due: {due[:10]})" if due else ""
                icon = "✅" if task.get("status") == "completed" else "⭕"
                msg += f"{i}. {icon} {title}{due_str}\n"

            await update.message.reply_text(msg)
            logger.info("Listed %d Google Tasks for user %d", len(tasks), user.id)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error listing tasks: {exc}")
            logger.error("Error in list_inbox_tasks: %s", exc)

    return handler
