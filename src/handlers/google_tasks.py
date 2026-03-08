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


def register_google_tasks_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    # New names (tasks_* prefix); old names kept as aliases for backward compatibility
    application.add_handler(CommandHandler("tasks_connect", _authorize(orch)))
    application.add_handler(CommandHandler("authorize_google_tasks", _authorize(orch)))
    application.add_handler(CommandHandler("tasks_verify", _verify(orch)))
    application.add_handler(CommandHandler("verify_google", _verify(orch)))
    application.add_handler(CommandHandler("tasks_config", _config(orch)))
    application.add_handler(CommandHandler("google_tasks_config", _config(orch)))
    application.add_handler(CommandHandler("tasks_status", _tasks_status(orch)))
    application.add_handler(CommandHandler("google_tasks_status", _tasks_status(orch)))
    application.add_handler(CommandHandler("tasks_set_list", _set_task_list(orch)))
    application.add_handler(CommandHandler("set_task_list", _set_task_list(orch)))
    application.add_handler(CommandHandler("tasks_list", _list_inbox_tasks(orch)))
    application.add_handler(CommandHandler("list_inbox_tasks", _list_inbox_tasks(orch)))
    application.add_handler(CommandHandler("tasks_toggle_auto", _toggle_auto_tasks(orch)))
    application.add_handler(CommandHandler("toggle_auto_tasks", _toggle_auto_tasks(orch)))
    application.add_handler(CommandHandler("tasks_toggle_privacy", _toggle_privacy(orch)))
    application.add_handler(CommandHandler("toggle_privacy", _toggle_privacy(orch)))
    application.add_handler(CommandHandler("tasks_toggle_project_sync", _toggle_project_sync(orch)))
    application.add_handler(CommandHandler("toggle_project_sync", _toggle_project_sync(orch)))
    application.add_handler(CommandHandler("tasks_sync_projects", _sync_projects(orch)))
    application.add_handler(CommandHandler("sync_projects", _sync_projects(orch)))
    application.add_handler(CommandHandler("tasks_reset_project_sync", _reset_project_sync(orch)))
    application.add_handler(CommandHandler("reset_project_sync", _reset_project_sync(orch)))
    application.add_handler(CommandHandler("tasks_set_projects_folder", _set_projects_folder(orch)))
    application.add_handler(CommandHandler("set_projects_folder", _set_projects_folder(orch)))
    application.add_handler(CommandHandler("tasks_cleanup", _cleanup_completed_tasks(orch)))
    application.add_handler(CommandHandler("cleanup_completed_tasks", _cleanup_completed_tasks(orch)))


def _authorize(orch: TelegramOrchestrator):
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
                "3. Send it back to me with: /tasks_verify [code]\n\n"
                "Example: `/tasks_verify 4/0AY0e-g7X...`"
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


def _verify(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: `/tasks_verify [authorization_code]`\n\n"
                "Example: `/tasks_verify 4/0AY0e-g7X...`"
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
                "project_sync_enabled": False,
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
                "/tasks_config - Manage settings\n"
                "/tasks_status - View sync status\n\n"
                "Use /status to verify the connection."
            )
            logger.info("Google Tasks authorized for user %d", user.id)
        except ValueError as exc:
            await update.message.reply_text(f"❌ Invalid authorization code or configuration error: {exc}")
            logger.error("Google Tasks verification failed: %s", exc)
        except Exception as exc:
            await update.message.reply_text(
                f"❌ Authorization failed: {exc}\n\nPlease try again with: `/tasks_connect`"
            )
            logger.error("Error in Google Tasks verification: %s", exc)

    return handler


def _config(orch: TelegramOrchestrator):
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
                    "❌ Google Tasks not authorized yet.\nUse /tasks_connect first."
                )
                return

            task_lists = orch.task_service.get_available_task_lists(str(user.id))

            msg = "⚙️ Google Tasks Configuration\n\n"
            msg += f"Status: {'✅ Enabled' if cfg.get('enabled') else '❌ Disabled'}\n"
            msg += f"Auto task creation: {'✅ On' if cfg.get('auto_create_tasks') else '❌ Off'}\n"
            msg += f"Privacy mode: {'🔒 On' if cfg.get('privacy_mode') else '🔓 Off'}\n"
            msg += f"Project sync (FR-034): {'✅ On' if cfg.get('project_sync_enabled') else '❌ Off'}\n"
            msg += f"Current task list: {cfg.get('task_list_name', 'Not set')}\n\n"

            if task_lists:
                msg += "Available task lists:\n"
                for idx, tl in enumerate(task_lists, 1):
                    msg += f"{idx}. {tl.get('title')} (ID: {tl.get('id')[:10]}...)\n"
                msg += "\nReply with: /tasks_set_list [number]\n"
            else:
                msg += "No task lists found\n"

            msg += "\nOther commands:\n"
            msg += "/tasks_toggle_auto - Turn auto task creation on/off\n"
            msg += "/tasks_toggle_privacy - Turn privacy mode on/off\n"
            msg += "/tasks_toggle_project_sync - Joplin projects as parent tasks (FR-034)\n"
            msg += "/tasks_sync_projects - Create parent tasks for all project folders\n"
            msg += "/tasks_reset_project_sync - Clear mappings (use before re-syncing to a different list)\n"
            msg += "/tasks_set_projects_folder - Choose which folder = Projects root\n"
            msg += "/tasks_status - View synchronization status\n"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error loading configuration: {exc}")
            logger.error("Error in google_tasks_config: %s", exc)

    return handler


def _set_task_list(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not context.args:
            await update.message.reply_text("Usage: /tasks_set_list [number]")
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


def _toggle_auto_tasks(orch: TelegramOrchestrator):
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


def _toggle_project_sync(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks not authorized")
                return
            enabled = not cfg.get("project_sync_enabled", False)
            if orch.task_service.toggle_project_sync(user.id, enabled):
                await update.message.reply_text(
                    f"Project sync (FR-034): {'✅ Enabled' if enabled else '❌ Disabled'}\n\n"
                    "When on, tasks from notes in Projects/ folders become subtasks under the project."
                )
            else:
                await update.message.reply_text("❌ Failed to update setting")
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")

    return handler


def _set_projects_folder(orch: TelegramOrchestrator):
    """FR-034 Option D: Set which Joplin folder is the Projects root (override default)."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not orch.joplin_client:
            await update.message.reply_text("❌ Joplin not available")
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text(
                    "❌ Google Tasks not configured\n\nUse /tasks_connect first"
                )
                return
            if not context.args:
                # Show current + list root folders to pick
                current = cfg.get("projects_folder_id")
                folders = await orch.joplin_client.get_folders()
                root_folders = [f for f in folders if not (f.get("parent_id") or "")]
                if not root_folders:
                    await update.message.reply_text("No root folders found in Joplin.")
                    return
                lines = [
                    "Choose which folder is your Projects root:",
                    "",
                    "Current: " + (current or "Default (Projects / 01 - projects / project)"),
                    "",
                    "Reply with the number to set, or 'default' to clear override:",
                ]
                for i, f in enumerate(root_folders[:15], 1):
                    fid = f.get("id", "")
                    title = f.get("title", "Unknown")
                    mark = " ← current" if fid == current else ""
                    lines.append(f"  {i}. {title}{mark}")
                lines.append("  0. Use default (clear override)")
                await update.message.reply_text("\n".join(lines))
                orch.state_manager.update_state(user.id, {
                    "awaiting_projects_folder": True,
                    "root_folders": [(f.get("id"), f.get("title", "Unknown")) for f in root_folders[:15]],
                })
                return
            # Direct arg: folder ID
            folder_id = context.args[0].strip()
            if folder_id.lower() == "default":
                cfg["projects_folder_id"] = None
                orch.logging_service.save_google_tasks_config(user.id, cfg)
                await update.message.reply_text("✅ Using default Projects folder (Projects / 01 - projects / project)")
                return
            folders = await orch.joplin_client.get_folders()
            if any(f.get("id") == folder_id for f in folders):
                cfg["projects_folder_id"] = folder_id
                orch.logging_service.save_google_tasks_config(user.id, cfg)
                await update.message.reply_text(f"✅ Projects root set to folder ID: {folder_id[:12]}...")
            else:
                await update.message.reply_text("❌ Unknown folder ID. Use /tasks_set_projects_folder without args to pick from list.")
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")
            logger.error("Error in set_projects_folder: %s", exc)

    return handler


def _sync_projects(orch: TelegramOrchestrator):
    """FR-034: Create parent tasks in Google Tasks for all Joplin project folders."""
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
                    "❌ Google Tasks not authorized\n\nUse /tasks_connect first"
                )
                return
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg or not cfg.get("project_sync_enabled"):
                await update.message.reply_text(
                    "❌ Project sync is disabled\n\nUse /tasks_toggle_project_sync to enable first"
                )
                return
            if not orch.reorg_orchestrator:
                await update.message.reply_text("❌ Could not access Joplin folders")
                return
            await update.message.chat.send_action("typing")
            proj_folder_id = cfg.get("projects_folder_id")
            projects = await orch.reorg_orchestrator.get_project_folders(
                projects_folder_id=proj_folder_id
            )
            if not projects:
                await update.message.reply_text(
                    "No project folders found.\n\n"
                    "Create folders under Projects (or 01 - projects) in Joplin."
                )
                return
            # FR-034 Option C: Cleanup orphaned mappings (folders deleted in Joplin)
            folders = await orch.joplin_client.get_folders()
            folder_ids = {f.get("id", "") for f in folders}
            removed = orch.task_service.cleanup_orphaned_project_mappings(
                str(user.id), folder_ids
            )
            created, existing = orch.task_service.sync_project_parent_tasks(
                str(user.id), projects
            )
            msg = (
                f"✅ Synced projects\n\n"
                f"Created: {created} parent task(s)\n"
                f"Already existed: {existing}"
            )
            if removed > 0:
                msg += f"\nRemoved: {removed} orphaned mapping(s)"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")
            logger.error("Error in sync_projects: %s", exc)

    return handler


def _reset_project_sync(orch: TelegramOrchestrator):
    """Clear all project sync mappings so the next /sync_projects creates fresh parent tasks."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks integration not available")
            return
        try:
            count = orch.task_service.reset_project_sync(user.id)
            msg = (
                f"✅ Cleared {count} project sync mapping(s).\n\n"
                "Next steps:\n"
                "1. Delete the old project parent tasks from the wrong list in Google Tasks (if any)\n"
                "2. Run /tasks_set_list [number] to choose the right list (e.g. Projects)\n"
                "3. Run /tasks_sync_projects to create fresh parent tasks in the correct list"
            )
            await update.message.reply_text(msg)
            logger.info("Reset project sync for user %d: cleared %d mappings", user.id, count)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error: {exc}")
            logger.error("Error in reset_project_sync: %s", exc)

    return handler


def _toggle_privacy(orch: TelegramOrchestrator):
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


def _tasks_status(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks not authorized\n\nUse /tasks_connect to set up access"
                )
                return

            # Validate token by making a lightweight API call (refreshes if expired)
            valid, err = orch.task_service.validate_google_token(user.id)
            if not valid:
                await update.message.reply_text(
                    f"❌ {err}\n\nUse /tasks_connect to re-connect."
                )
                return

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


def _list_inbox_tasks(orch: TelegramOrchestrator):
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
                    "❌ Google Tasks not authorized\n\nUse /tasks_connect to set up access"
                )
                return

            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg or not cfg.get("enabled"):
                await update.message.reply_text("❌ Google Tasks is disabled")
                return

            task_list_id = cfg.get("task_list_id")
            tasks_client = orch.task_service.tasks_client
            tasks_client.set_token(
                token,
                token_updater=lambda t: orch.logging_service.save_google_token(str(user.id), t),
            )

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


def _cleanup_completed_tasks(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks is not configured.")
            return

        token = orch.logging_service.load_google_token(str(user.id))
        if not token:
            await update.message.reply_text(
                "❌ Google Tasks not authorized\n\nUse /authorize_google_tasks to set up access"
            )
            return

        days = 30
        if context.args:
            try:
                days = int(context.args[0])
                if days < 1 or days > 365:
                    raise ValueError("Days must be 1–365")
            except ValueError:
                await update.message.reply_text(
                    "Usage: /tasks_cleanup [days]\n"
                    "Deletes completed tasks older than N days (default: 30).\n"
                    "Example: /tasks_cleanup 30"
                )
                return

        await update.message.chat.send_action("typing")
        deleted, errors = orch.task_service.delete_completed_tasks_older_than(
            str(user.id), days=days
        )
        if errors > 0:
            msg = f"🧹 Cleaned up {deleted} completed task(s) older than {days} days.\n⚠️ {errors} deletion(s) failed."
        else:
            msg = f"🧹 Cleaned up {deleted} completed task(s) older than {days} days."
        await update.message.reply_text(msg)
        logger.info("User %d cleaned up %d completed tasks (errors: %d)", user.id, deleted, errors)

    return handler
