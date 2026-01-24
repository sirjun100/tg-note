"""
Telegram Orchestrator - Main Bot Logic
Coordinates all components to handle Telegram messages and create Joplin notes.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

from src.joplin_client import JoplinClient
from src.llm_orchestrator import LLMOrchestrator
from src.state_manager import StateManager
from src.logging_service import LoggingService, TelegramMessage, Decision
from src.report_generator import ReportGenerator, PriorityLevel
from src.scheduler_service import get_scheduler_service
from src.security_utils import (
    check_whitelist, validate_message_text, ping_joplin_api,
    handle_api_error, format_error_message, format_success_message
)
from config import TELEGRAM_BOT_TOKEN

if TYPE_CHECKING:
    from src.google_tasks_client import GoogleTasksClient
    from src.task_service import TaskService

# Optional Google Tasks integration
GOOGLE_TASKS_AVAILABLE = False
try:
    import src.google_tasks_client
    import src.task_service
    GOOGLE_TASKS_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

class TelegramOrchestrator:
    """Main orchestrator for the Telegram bot"""

    def __init__(self):
        self.joplin_client = JoplinClient()
        self.llm_orchestrator = LLMOrchestrator()
        self.state_manager = StateManager()
        self.logging_service = LoggingService()

        # Initialize Google Tasks integration if available
        self.task_service = None
        if GOOGLE_TASKS_AVAILABLE:
            try:
                from src.google_tasks_client import GoogleTasksClient
                from src.task_service import TaskService
                tasks_client = GoogleTasksClient()
                self.task_service = TaskService(tasks_client, self.logging_service)
                logger.info("Google Tasks integration initialized")
            except ValueError:
                logger.warning("Google Tasks integration not configured (credentials missing)")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Tasks integration: {e}")

        # Initialize Report Generator for daily reports
        self.report_generator = ReportGenerator(
            joplin_client=self.joplin_client,
            task_service=self.task_service
        )
        logger.info("Report generator initialized")

        # Initialize Scheduler Service for scheduled reports
        self.scheduler = get_scheduler_service()
        logger.info("Scheduler service initialized")

        # Check Joplin connectivity on startup
        if not ping_joplin_api():
            logger.warning("Joplin API not accessible on startup")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # Check whitelist
        if not check_whitelist(user_id):
            await update.message.reply_text(
                "❌ Sorry, you're not authorized to use this bot."
            )
            return

        # Clear any existing state
        self.state_manager.clear_state(user_id)

        welcome_message = (
            "🤖 Welcome to the Intelligent Joplin Librarian!\n\n"
            "I can help you create notes in Joplin from your messages. "
            "Just send me what you'd like to note, and I'll figure out the details.\n\n"
            "If I need clarification, I'll ask questions. You can also reply to my questions.\n\n"
            "Quick Commands:\n"
            "/start - Show this message\n"
            "/helpme - Show detailed help with all commands\n"
            "/status - Check bot status\n"
            "/list_inbox_tasks - List pending Google Tasks\n\n"
            "For more commands, use: /helpme"
        )

        await update.message.reply_text(welcome_message)
        logger.info(f"Started conversation with user {user_id}")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        # Check Joplin connectivity
        joplin_ok = ping_joplin_api()

        status_msg = "🤖 Bot Status:\n\n"
        status_msg += f"Joplin API: {'✅ Connected' if joplin_ok else '❌ Not accessible'}\n"

        # Check if user has pending state
        has_pending = self.state_manager.has_pending_state(user.id)
        status_msg += f"Pending clarification: {'✅ Yes' if has_pending else '❌ No'}\n"

        # Check Google Tasks integration
        google_tasks_ok = False
        if self.task_service:
            try:
                # Try to load user's token
                token = self.logging_service.load_google_token(str(user.id))
                google_tasks_ok = token is not None
            except Exception:
                pass
        status_msg += f"Google Tasks: {'✅ Configured' if google_tasks_ok else '❌ Not configured'}\n"

        if not joplin_ok:
            status_msg += "\n⚠️ Make sure Joplin is running with Web Clipper enabled."

        await update.message.reply_text(status_msg)

    async def handle_helpme(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /helpme command - Show all available commands"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        help_message = (
            "🆘 Help - Available Commands\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "📝 **Two Systems**\n"
            "🔹 Regular messages → Creates NOTES in Joplin\n"
            "🔹 Action items → Creates TASKS in Google Tasks\n\n"

            "📋 **Commands**\n"
            "/start - Welcome message & quick command list\n"
            "/status - Check if Joplin & Google Tasks are connected\n"
            "/helpme - Show this detailed help message\n\n"

            "📅 **Google Tasks Management**\n"
            "/authorize_google_tasks - Connect your Google account\n"
            "/list_inbox_tasks - View your pending Google Tasks\n"
            "/google_tasks_status - See sync history & stats\n\n"

            "📊 **Daily Priority Reports**\n"
            "/daily_report - Get on-demand priority report\n"
            "/configure_report_time HH:MM - Set delivery time (e.g., 09:00)\n"
            "/configure_report_timezone TIMEZONE - Set your timezone\n"
            "/toggle_daily_report on|off - Enable/disable scheduled reports\n"
            "/show_report_config - View your report settings\n"
            "/configure_report_content LEVEL - Set report detail level\n"
            "/report_help - Show all report commands\n\n"

            "🧠 **GTD Brain Dump**\n"
            "/braindump - Start an interactive mind sweep session\n"
            "/braindump_stop - End the session early\n\n"

            "⚙️ **How It Works**\n"
            "📝 **For Regular Notes:**\n"
            "  1️⃣ Send: 'I had a great meeting with John'\n"
            "  2️⃣ Bot creates a note in Joplin\n"
            "  3️⃣ Adds tags & puts in right folder\n\n"

            "✅ **For Action Items (Google Tasks):**\n"
            "  1️⃣ Send: 'TODO: Call John tomorrow'\n"
            "  2️⃣ Bot creates ONLY a Google Task\n"
            "  3️⃣ No note created in Joplin\n"
            "  4️⃣ Decision logged to AI Decision Log\n\n"

            "🏷️ **Action Item Keywords**\n"
            "The bot creates Google Tasks when it sees:\n"
            "  • todo, task, action\n"
            "  • follow up, call, email\n"
            "  • schedule, remind\n\n"

            "💡 **Examples**\n"
            "✅ 'TODO: Buy milk from store' → Google Task only\n"
            "✅ 'Call Sarah tomorrow' → Google Task only\n"
            "✅ 'Had coffee with Sarah' → Joplin note only\n"
            "✅ 'IMPORTANT: Need to review budget by Friday' → Joplin note\n\n"

            "❓ **Questions?**\n"
            "Just send /status to check connectivity."
        )

        await update.message.reply_text(help_message)
        logger.info(f"Showed help message to user {user.id}")

    async def handle_authorize_google_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /authorize-google-tasks command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()
            auth_url, state = tasks_client.get_authorization_url()

            # Store state for verification (optional, for added security)
            self.state_manager.update_state(user.id, {'google_auth_state': state})

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
            logger.info(f"Google Tasks authorization initiated for user {user.id}")

        except ValueError as e:
            await update.message.reply_text(
                f"❌ Google Tasks is not properly configured: {e}\n"
                f"Please check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        except Exception as e:
            logger.error(f"Error in Google Tasks authorization: {e}")
            await update.message.reply_text(f"❌ Authorization failed: {e}")

    async def handle_verify_google(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /verify-google command to exchange code for token"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this bot.")
            return

        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Usage: `/verify_google [authorization_code]`\n\n"
                "Example: `/verify_google 4/0AY0e-g7X...`"
            )
            return

        auth_code = context.args[0]

        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()

            # Exchange code for token
            token = tasks_client.exchange_code_for_token(auth_code)

            # Save token to database
            self.logging_service.save_google_token(str(user.id), token)

            # Initialize Google Tasks configuration
            config = {
                'enabled': True,
                'auto_create_tasks': True,
                'include_only_tagged': False,
                'task_creation_tags': [],
                'privacy_mode': False
            }
            self.logging_service.save_google_tasks_config(user.id, config)

            # Clear the google_auth_state from state manager
            state = self.state_manager.get_state(user.id)
            if state and 'google_auth_state' in state:
                del state['google_auth_state']
                if state:
                    self.state_manager.update_state(user.id, state)
                else:
                    self.state_manager.clear_state(user.id)

            success_msg = (
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

            await update.message.reply_text(success_msg)
            logger.info(f"✅ Google Tasks authorized for user {user.id}")

        except ValueError as e:
            await update.message.reply_text(
                f"❌ Invalid authorization code or configuration error: {e}"
            )
            logger.error(f"Google Tasks verification failed: {e}")
        except Exception as e:
            await update.message.reply_text(
                f"❌ Authorization failed: {e}\n\n"
                "Please try again with: `/authorize_google_tasks`"
            )
            logger.error(f"Error in Google Tasks verification: {e}")

    async def handle_google_tasks_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /google-tasks-config command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not self.task_service:
            await update.message.reply_text("❌ Google Tasks integration is not available")
            return

        try:
            config = self.logging_service.get_google_tasks_config(user.id)
            if not config:
                await update.message.reply_text(
                    "❌ Google Tasks not authorized yet.\n"
                    "Use /authorize_google_tasks first."
                )
                return

            # Get available task lists
            task_lists = self.task_service.get_available_task_lists(str(user.id))

            msg = "⚙️ Google Tasks Configuration\n\n"
            msg += f"Status: {'✅ Enabled' if config.get('enabled') else '❌ Disabled'}\n"
            msg += f"Auto task creation: {'✅ On' if config.get('auto_create_tasks') else '❌ Off'}\n"
            msg += f"Privacy mode: {'🔒 On' if config.get('privacy_mode') else '🔓 Off'}\n"
            msg += f"Current task list: {config.get('task_list_name', 'Not set')}\n\n"

            if task_lists:
                msg += "Available task lists:\n"
                for idx, task_list in enumerate(task_lists, 1):
                    msg += f"{idx}. {task_list.get('title')} (ID: {task_list.get('id')[:10]}...)\n"
                msg += f"\nReply with: /set_task_list [number]\n"
            else:
                msg += "No task lists found\n"

            msg += "\nOther commands:\n"
            msg += "/toggle_auto_tasks - Turn auto task creation on/off\n"
            msg += "/toggle_privacy - Turn privacy mode on/off\n"
            msg += "/google_tasks_status - View synchronization status\n"

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Error loading configuration: {e}")
            logger.error(f"Error in google_tasks_config: {e}")

    async def handle_set_task_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /set-task-list command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not context.args:
            await update.message.reply_text("Usage: /set_task_list [number]")
            return

        try:
            list_num = int(context.args[0]) - 1
            task_lists = self.task_service.get_available_task_lists(str(user.id))

            if list_num < 0 or list_num >= len(task_lists):
                await update.message.reply_text("❌ Invalid task list number")
                return

            selected = task_lists[list_num]
            self.task_service.set_preferred_task_list(
                user.id,
                selected.get('id'),
                selected.get('title')
            )

            await update.message.reply_text(
                f"✅ Task list changed to: {selected.get('title')}"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            logger.error(f"Error in set_task_list: {e}")

    async def handle_toggle_auto_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toggle-auto-tasks command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            config = self.logging_service.get_google_tasks_config(user.id)
            if not config:
                await update.message.reply_text("❌ Google Tasks not authorized")
                return

            enabled = not config.get('auto_create_tasks', True)
            self.task_service.toggle_auto_task_creation(user.id, enabled)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            await update.message.reply_text(f"Auto task creation: {status}")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def handle_toggle_privacy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toggle-privacy command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            config = self.logging_service.get_google_tasks_config(user.id)
            if not config:
                await update.message.reply_text("❌ Google Tasks not authorized")
                return

            enabled = not config.get('privacy_mode', False)
            self.task_service.toggle_privacy_mode(user.id, enabled)
            status = "🔒 Enabled" if enabled else "🔓 Disabled"
            await update.message.reply_text(f"Privacy mode: {status}")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def handle_google_tasks_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /google-tasks-status command"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            status = self.task_service.get_task_sync_status(user.id)

            msg = "📊 Google Tasks Sync Status\n\n"
            msg += f"Total synced: {status.get('total_synced', 0)}\n"
            msg += f"✅ Successful: {status.get('success_count', 0)}\n"
            msg += f"❌ Failed: {status.get('failed_count', 0)}\n\n"

            if status.get('recent_syncs'):
                msg += "Recent syncs:\n"
                for sync in status['recent_syncs'][:3]:
                    action = sync.get('action', 'unknown')
                    result = "✅" if sync.get('sync_result') == 'success' else "❌"
                    msg += f"{result} {action} - {sync.get('created_at', 'N/A')}\n"

            if status.get('failed_syncs'):
                msg += f"\n⚠️ Failed syncs: {len(status['failed_syncs'])}\n"
                for sync in status['failed_syncs'][:2]:
                    msg += f"• {sync.get('error_message', 'Unknown error')}\n"

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            logger.error(f"Error in google_tasks_status: {e}")

    async def handle_list_inbox_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list_inbox_tasks command - List all tasks from Google Tasks"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not self.task_service:
            await update.message.reply_text("❌ Google Tasks integration not available")
            return

        try:
            # Load user's Google token
            token = self.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks not authorized\n\n"
                    "Use /authorize_google_tasks to set up access"
                )
                return

            # Get user's Google Tasks configuration
            config = self.logging_service.get_google_tasks_config(user.id)
            if not config or not config.get('enabled'):
                await update.message.reply_text("❌ Google Tasks is disabled")
                return

            # Get task list ID
            task_list_id = config.get('task_list_id')
            tasks_client = self.task_service.tasks_client
            tasks_client.set_token(token)

            if not task_list_id:
                # Try to get default task list
                try:
                    task_lists = tasks_client.get_task_lists()
                    # Save refreshed token if it was updated during the call
                    if tasks_client.token and tasks_client.token != token:
                        self.logging_service.save_google_token(str(user.id), tasks_client.token)

                    if not task_lists:
                        await update.message.reply_text(
                            "❌ No Google Tasks lists found\n\n"
                            "Please create a task list in Google Tasks (https://calendar.google.com)"
                        )
                        return
                    task_list_id = task_lists[0]['id']
                except Exception as e:
                    await update.message.reply_text(f"❌ Error getting task lists: {e}")
                    return

            # Get tasks from Google Tasks
            tasks = tasks_client.get_tasks(task_list_id, show_completed=False)

            # Save refreshed token if it was updated during the call
            if tasks_client.token and tasks_client.token != token:
                self.logging_service.save_google_token(str(user.id), tasks_client.token)

            if not tasks:
                task_list_name = config.get('task_list_name', 'My Tasks')
                await update.message.reply_text(f"📭 No pending tasks in Google Tasks")
                return

            # Build the message
            task_list_name = config.get('task_list_name', 'My Tasks')
            msg = f"📋 Google Tasks - {task_list_name} ({len(tasks)} pending)\n\n"

            for i, task in enumerate(tasks, 1):
                title = task.get('title', 'Untitled')
                due = task.get('due', '')
                status = task.get('status', 'needsAction')

                # Format due date if available
                due_str = ""
                if due:
                    due_str = f" (due: {due[:10]})"

                # Status icon
                icon = "⭕"
                if status == 'completed':
                    icon = "✅"

                msg += f"{i}. {icon} {title}{due_str}\n"

            await update.message.reply_text(msg)
            logger.info(f"Listed {len(tasks)} Google Tasks for user {user.id}")

        except Exception as e:
            await update.message.reply_text(f"❌ Error listing tasks: {e}")
            logger.error(f"Error in list_inbox_tasks: {e}")

    async def handle_daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /daily_report command - Generate on-demand daily priority report"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ You're not authorized to use this command.")
            return

        try:
            user_id = user.id

            # Show "typing" indicator
            await update.message.chat.send_action("typing")

            logger.info(f"Generating on-demand daily report for user {user_id}")

            # Get pending clarifications from state (if any)
            state = self.state_manager.get_state(user_id)
            pending_clarifications = state.get("pending_clarifications", []) if state else []

            # Generate report asynchronously
            report = await self.report_generator.generate_report_async(
                user_id=user_id,
                pending_clarifications=pending_clarifications,
                completed_items=[],  # TODO: Track completed items
                min_priority=PriorityLevel.LOW
            )

            # Format message
            if report.total_items == 0 and not pending_clarifications:
                message = self.report_generator.format_report_message(report)
            else:
                message = self.report_generator.format_report_message(report, include_details=True)

            # Send report
            await update.message.reply_text(message)

            # Log report generation
            self.logging_service.log_system_event(
                level="INFO",
                module="daily_report",
                message=f"Generated on-demand daily report for user {user_id}",
                extra_data={
                    "total_items": report.total_items,
                    "joplin_count": report.joplin_count,
                    "google_tasks_count": report.google_tasks_count,
                    "critical": len(report.critical_items),
                    "high": len(report.high_items),
                    "generated_by": "manual"
                }
            )

            logger.info(f"Daily report sent to user {user_id}: {report.total_items} items")

        except Exception as e:
            error_msg = "❌ Error generating daily report. Please try again later."
            await update.message.reply_text(error_msg)
            logger.error(f"Error in handle_daily_report: {e}", exc_info=True)

    async def send_scheduled_report(self, user_id: int) -> None:
        """
        Send a scheduled daily report to a user

        This is called by the scheduler at the configured time.

        Args:
            user_id: Telegram user ID
        """
        try:
            logger.info(f"Sending scheduled report to user {user_id}")

            # Get user's configuration
            config = self.logging_service.get_report_configuration(user_id)
            if not config or not config.get('enabled', True):
                logger.debug(f"Scheduled reports disabled for user {user_id}")
                return

            # Get pending clarifications from state
            state = self.state_manager.get_state(user_id)
            pending_clarifications = state.get("pending_clarifications", []) if state else []

            # Determine minimum priority level to include
            detail_level = config.get('detail_level', 'detailed')
            min_priority = PriorityLevel.LOW

            # Generate report
            report = await self.report_generator.generate_report_async(
                user_id=user_id,
                pending_clarifications=pending_clarifications,
                completed_items=[],
                min_priority=min_priority
            )

            # Filter by content settings
            if not config.get('include_critical') and not config.get('include_high'):
                logger.debug(f"User {user_id} has all content filters disabled")
                return

            # Format and send report
            message = self.report_generator.format_report_message(
                report, include_details=(detail_level == 'detailed')
            )

            # Send via Telegram
            from telegram import Bot
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            sent_message = await bot.send_message(chat_id=user_id, text=message)

            # Log report generation
            self.logging_service.log_daily_report(
                user_id=user_id,
                report_data={
                    'joplin_count': report.joplin_count,
                    'google_tasks_count': report.google_tasks_count,
                    'clarification_count': report.clarification_count,
                    'critical_items': len(report.critical_items),
                    'high_items': len(report.high_items),
                    'medium_items': len(report.medium_items),
                    'low_items': len(report.low_items),
                    'completed_count': report.completed_count,
                    'generated_by': 'scheduled'
                }
            )

            logger.info(
                f"Scheduled report sent to user {user_id}: "
                f"{report.total_items} items, message_id={sent_message.message_id}"
            )

        except Exception as e:
            logger.error(f"Failed to send scheduled report to user {user_id}: {e}", exc_info=True)

    async def handle_configure_report_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /configure_report_time command - Set report delivery time"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            user_id = user.id
            args = context.args

            if not args or len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /configure_report_time HH:MM\n"
                    "Example: /configure_report_time 08:00"
                )
                return

            time_str = args[0]

            # Validate time format
            try:
                hour, minute = map(int, time_str.split(":"))
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError()
            except:
                await update.message.reply_text(
                    f"❌ Invalid time format: {time_str}\n"
                    "Use 24-hour format: HH:MM (e.g., 08:00, 14:30)"
                )
                return

            # Get current config
            config = self.logging_service.get_report_configuration(user_id)
            if not config:
                config = {
                    'enabled': True,
                    'delivery_time': time_str,
                    'timezone': 'UTC',
                    'include_critical': True,
                    'include_high': True,
                    'include_medium': False,
                    'include_google_tasks': True,
                    'include_clarification_pending': True,
                    'detail_level': 'detailed'
                }
            else:
                config['delivery_time'] = time_str

            # Save config
            self.logging_service.save_report_configuration(user_id, config)

            # If enabled, reschedule the job with new time
            if config.get('enabled', True):
                timezone = config.get('timezone', 'UTC')
                scheduled = await self.scheduler.schedule_daily_report(
                    user_id=user_id,
                    delivery_time=time_str,
                    timezone_str=timezone,
                    report_callback=self.send_scheduled_report
                )
                if scheduled:
                    await update.message.reply_text(
                        f"✅ Report delivery time set to {time_str}\n"
                        f"Timezone: {timezone}\n"
                        f"✓ Scheduled"
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Report delivery time set to {time_str}\n"
                        f"Timezone: {timezone}\n"
                        f"⚠️ Failed to schedule job"
                    )
            else:
                await update.message.reply_text(
                    f"✅ Report delivery time set to {time_str}\n"
                    f"Timezone: {config.get('timezone', 'UTC')}\n"
                    f"(Reports currently disabled)"
                )

            logger.info(f"User {user_id} set report time to {time_str}")

        except Exception as e:
            await update.message.reply_text("❌ Error setting report time.")
            logger.error(f"Error in handle_configure_report_time: {e}")

    async def handle_configure_report_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /configure_report_timezone command - Set timezone"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            user_id = user.id
            args = context.args

            if not args or len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /configure_report_timezone TIMEZONE\n"
                    "Examples: US/Eastern, Europe/London, Asia/Tokyo, UTC"
                )
                return

            timezone_str = args[0]

            # Validate timezone using pytz
            try:
                import pytz
                pytz.timezone(timezone_str)
            except:
                await update.message.reply_text(
                    f"❌ Unknown timezone: {timezone_str}\n"
                    "Examples: US/Eastern, Europe/London, Asia/Tokyo, UTC"
                )
                return

            # Get current config
            config = self.logging_service.get_report_configuration(user_id)
            if not config:
                config = {
                    'enabled': True,
                    'delivery_time': '08:00',
                    'timezone': timezone_str,
                    'include_critical': True,
                    'include_high': True,
                    'include_medium': False,
                    'include_google_tasks': True,
                    'include_clarification_pending': True,
                    'detail_level': 'detailed'
                }
            else:
                config['timezone'] = timezone_str

            # Save config
            self.logging_service.save_report_configuration(user_id, config)

            # If enabled, reschedule the job with new timezone
            if config.get('enabled', True):
                delivery_time = config.get('delivery_time', '08:00')
                scheduled = await self.scheduler.schedule_daily_report(
                    user_id=user_id,
                    delivery_time=delivery_time,
                    timezone_str=timezone_str,
                    report_callback=self.send_scheduled_report
                )
                if scheduled:
                    await update.message.reply_text(
                        f"✅ Timezone set to {timezone_str}\n"
                        f"Report time: {delivery_time}\n"
                        f"✓ Scheduled"
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Timezone set to {timezone_str}\n"
                        f"Report time: {delivery_time}\n"
                        f"⚠️ Failed to schedule job"
                    )
            else:
                await update.message.reply_text(
                    f"✅ Timezone set to {timezone_str}\n"
                    f"Report time: {config.get('delivery_time', '08:00')}\n"
                    f"(Reports currently disabled)"
                )

            logger.info(f"User {user_id} set timezone to {timezone_str}")

        except Exception as e:
            await update.message.reply_text("❌ Error setting timezone.")
            logger.error(f"Error in handle_configure_report_timezone: {e}")

    async def handle_toggle_daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toggle_daily_report command - Enable/disable automatic reports"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            user_id = user.id
            args = context.args

            if not args or len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /toggle_daily_report on|off\n"
                    "Examples: /toggle_daily_report on"
                )
                return

            action = args[0].lower()

            if action not in ['on', 'off', 'yes', 'no', 'true', 'false', '1', '0']:
                await update.message.reply_text(
                    "❌ Invalid option. Use: on, off, yes, no, true, or false"
                )
                return

            enabled = action in ['on', 'yes', 'true', '1']

            # Get current config
            config = self.logging_service.get_report_configuration(user_id)
            if not config:
                config = {
                    'enabled': enabled,
                    'delivery_time': '08:00',
                    'timezone': 'UTC',
                    'include_critical': True,
                    'include_high': True,
                    'include_medium': False,
                    'include_google_tasks': True,
                    'include_clarification_pending': True,
                    'detail_level': 'detailed'
                }
            else:
                config['enabled'] = enabled

            # Save config
            self.logging_service.save_report_configuration(user_id, config)

            # Schedule or cancel job based on enabled state
            if enabled:
                delivery_time = config.get('delivery_time', '08:00')
                timezone = config.get('timezone', 'UTC')
                scheduled = await self.scheduler.schedule_daily_report(
                    user_id=user_id,
                    delivery_time=delivery_time,
                    timezone_str=timezone,
                    report_callback=self.send_scheduled_report
                )
                if scheduled:
                    await update.message.reply_text(
                        f"✅ Daily reports enabled\n"
                        f"Scheduled for: {delivery_time} {timezone}\n"
                        f"✓ Job scheduled"
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ Reports enabled but scheduling failed\n"
                        f"Configured for: {delivery_time} {timezone}"
                    )
            else:
                cancelled = await self.scheduler.cancel_daily_report(user_id)
                if cancelled:
                    await update.message.reply_text(
                        f"❌ Daily reports disabled\n"
                        f"✓ Job cancelled"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Daily reports disabled\n"
                        f"(No scheduled job found)"
                    )

            logger.info(f"User {user_id} {'enabled' if enabled else 'disabled'} daily reports")

        except Exception as e:
            await update.message.reply_text("❌ Error toggling daily reports.")
            logger.error(f"Error in handle_toggle_daily_report: {e}")

    async def handle_show_report_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /show_report_config command - Display current configuration"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            user_id = user.id

            # Get config
            config = self.logging_service.get_report_configuration(user_id)

            if not config:
                message = (
                    "⚙️ Your Report Configuration (Defaults)\n\n"
                    "Status: ✅ Enabled\n"
                    "Delivery Time: 08:00\n"
                    "Timezone: UTC\n\n"
                    "Content Included:\n"
                    "  • Critical: Yes\n"
                    "  • High Priority: Yes\n"
                    "  • Medium Priority: No\n"
                    "  • Google Tasks: Yes\n"
                    "  • Clarifications: Yes\n\n"
                    "Detail Level: detailed\n\n"
                    "No custom configuration set yet.\n"
                    "Use commands to customize."
                )
            else:
                message = self.report_generator.format_configuration_display(config)

            await update.message.reply_text(message)
            logger.info(f"User {user_id} viewed report configuration")

        except Exception as e:
            await update.message.reply_text("❌ Error retrieving configuration.")
            logger.error(f"Error in handle_show_report_config: {e}")

    async def handle_configure_report_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /configure_report_content command - Set priority filter"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            user_id = user.id
            args = context.args

            if not args or len(args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /configure_report_content LEVEL\n"
                    "Options: critical, high, medium, all\n"
                    "  • critical: Only critical items\n"
                    "  • high: Critical and high priority\n"
                    "  • medium: Critical, high, and medium\n"
                    "  • all: All priority levels"
                )
                return

            level = args[0].lower()

            if level not in ['critical', 'high', 'medium', 'all']:
                await update.message.reply_text(
                    "❌ Invalid level. Use: critical, high, medium, or all"
                )
                return

            # Get current config
            config = self.logging_service.get_report_configuration(user_id)
            if not config:
                config = {
                    'enabled': True,
                    'delivery_time': '08:00',
                    'timezone': 'UTC',
                    'include_critical': True,
                    'include_high': level in ['high', 'medium', 'all'],
                    'include_medium': level in ['medium', 'all'],
                    'include_low': level == 'all',
                    'include_google_tasks': True,
                    'include_clarification_pending': True,
                    'detail_level': 'detailed'
                }
            else:
                config['include_critical'] = True  # Always include critical
                config['include_high'] = level in ['high', 'medium', 'all']
                config['include_medium'] = level in ['medium', 'all']
                config['include_low'] = level == 'all'

            # Save config
            self.logging_service.save_report_configuration(user_id, config)

            await update.message.reply_text(
                f"✅ Report content set to: {level.upper()}\n"
                "Including:\n"
                f"  • Critical: Yes\n"
                f"  • High Priority: {'Yes' if level in ['high', 'medium', 'all'] else 'No'}\n"
                f"  • Medium Priority: {'Yes' if level in ['medium', 'all'] else 'No'}\n"
                f"  • Low Priority: {'Yes' if level == 'all' else 'No'}"
            )
            logger.info(f"User {user_id} set report content level to {level}")

        except Exception as e:
            await update.message.reply_text("❌ Error setting report content.")
            logger.error(f"Error in handle_configure_report_content: {e}")

    async def handle_report_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /report_help command - Show help for report commands"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            help_text = (
                "📊 Daily Priority Report Commands\n\n"
                "Generate Reports:\n"
                "  /daily_report - Generate report immediately\n\n"
                "Configure Delivery:\n"
                "  /configure_report_time <HH:MM> - Set delivery time (24-hour format)\n"
                "    Example: /configure_report_time 08:00\n\n"
                "  /configure_report_timezone <timezone> - Set your timezone\n"
                "    Example: /configure_report_timezone US/Eastern\n"
                "    Common: US/Eastern, US/Central, US/Pacific, Europe/London, Asia/Tokyo\n\n"
                "  /toggle_daily_report on|off - Enable/disable automatic reports\n"
                "    Example: /toggle_daily_report on\n\n"
                "Customize Content:\n"
                "  /configure_report_content <level> - Set minimum priority level\n"
                "    Options: critical, high, medium, all\n"
                "    Example: /configure_report_content high\n\n"
                "View Settings:\n"
                "  /show_report_config - View your current configuration\n\n"
                "Help:\n"
                "  /report_help - Show this help message\n\n"
                "What's Included:\n"
                "• High-priority Joplin notes (tagged: #urgent, #critical, #important)\n"
                "• Incomplete Google Tasks\n"
                "• Notes pending clarification\n"
                "• Items completed since last report\n"
                "• Smart priority ranking across all sources"
            )

            await update.message.reply_text(help_text)
            logger.info(f"User {user.id} viewed report help")

        except Exception as e:
            await update.message.reply_text("❌ Error retrieving help.")
            logger.error(f"Error in handle_report_help: {e}")

    async def handle_braindump(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /braindump command - Start interactive GTD brain dump session"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        user_id = user.id
        logger.info(f"User {user_id} starting /braindump session")

        # Check if session already active
        state = self.state_manager.get_state(user_id)
        if state and state.get('active_persona') == 'GTD_EXPERT':
            await update.message.reply_text("💡 You already have an active brain dump session! Just keep typing, or use /braindump_stop to finish.")
            return

        # Initialize Brain Dump state
        new_state = {
            'active_persona': 'GTD_EXPERT',
            'session_start': datetime.now().isoformat(),
            'captured_items': [],
            'conversation_history': []
        }
        
        # Load prompt for first question
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "gtd_expert.txt"
        first_question = "Ready to dump your brain? Let's do 15 minutes. First—what is the thing that has been poking at you the most lately? The one that keeps coming back."
        
        if prompt_path.exists():
            try:
                with open(prompt_path, "r") as f:
                    content = f.read()
                    # Extract last line as the first question if it's there
                    lines = content.strip().split("\n")
                    if lines:
                        first_question = lines[-1]
            except Exception as e:
                logger.warning(f"Failed to read prompt for first question: {e}")

        self.state_manager.update_state(user_id, new_state)
        await update.message.reply_text(f"🧠 *GTD MIND SWEEP SESSION STARTED*\n\n{first_question}", parse_mode='Markdown')

    async def handle_braindump_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /braindump_stop command - Finish current session early"""
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        user_id = user.id
        state = self.state_manager.get_state(user_id)

        if not state or state.get('active_persona') != 'GTD_EXPERT':
            await update.message.reply_text("❌ You don't have an active brain dump session. Use /braindump to start one.")
            return

        logger.info(f"User {user_id} stopping /braindump session via command")
        await self._finish_braindump_session(user_id, update.message)

    async def _handle_braindump_message(self, user_id: int, text: str, message: Message) -> None:
        """Handle a message during an active brain dump session"""
        state = self.state_manager.get_state(user_id)
        if not state:
            return

        history = state.get('conversation_history', [])
        
        # Prepare context (optional, but good for LLM)
        context = {
            "session_start": state.get('session_start'),
            "item_count": len(state.get('captured_items', []))
        }

        # Call LLM with GTD_EXPERT persona
        try:
            llm_response = self.llm_orchestrator.process_message(
                user_message=text,
                context=context,
                persona="gtd_expert",
                history=history
            )

            # Update history with user message
            history.append({"role": "user", "content": text})

            if llm_response.status == "SUCCESS":
                # Session is over, LLM provided the final summary
                logger.info(f"GTD session for user {user_id} completed by LLM")
                
                # Update state with the final note data before finishing
                state['final_note'] = llm_response.note
                state['conversation_history'] = history # Save full history
                self.state_manager.update_state(user_id, state)
                
                await self._finish_braindump_session(user_id, message, llm_response.note)
            
            else:
                # Session continues, LLM asked a new question
                next_question = llm_response.question or "Any other thoughts?"
                
                # Update history with assistant's response
                history.append({"role": "assistant", "content": next_question})
                
                # Update state
                state['conversation_history'] = history[-15:] # Keep last 15 for context
                self.state_manager.update_state(user_id, state)
                
                await message.reply_text(next_question)

        except Exception as e:
            logger.error(f"Error in GTD brain dump processing for user {user_id}: {e}")
            await message.reply_text("❌ Sorry, I had some trouble processing that. You can continue or use /braindump_stop to finish.")

    async def _finish_braindump_session(self, user_id: int, message: Message, note_data: Optional[Dict[str, Any]] = None) -> None:
        """Finalize the brain dump session and create the Joplin note"""
        state = self.state_manager.get_state(user_id)
        if not state:
            return

        await message.reply_text("🏁 *FINISHING BRAIN DUMP SESSION...*", parse_mode='Markdown')

        try:
            final_note = note_data or state.get('final_note')
            
            if not final_note:
                # If we don't have a final note yet (e.g. forced stop), 
                # we should try to generate one from the history
                history = state.get('conversation_history', [])
                if history:
                    await message.reply_text("📊 Generating summary of your session...")
                    llm_response = self.llm_orchestrator.process_message(
                        user_message="Please summarize everything we've talked about so far into an organized list.",
                        persona="gtd_expert",
                        history=history
                    )
                    if llm_response.status == "SUCCESS":
                        final_note = llm_response.note
                    else:
                        await message.reply_text("⚠️ Couldn't generate a structured summary. I'll save our conversation as-is.")
                        final_note = {
                            "title": f"Brain Dump Session - {datetime.now().strftime('%Y-%m-%d')}",
                            "body": "\n".join([f"{h['role']}: {h['content']}" for h in history]),
                            "parent_id": "Inbox", # Default or fallback
                            "tags": ["brain-dump", "mindsweep"]
                        }

            if final_note:
                # Ensure we have a valid folder ID
                if not final_note.get('parent_id') or final_note.get('parent_id') == 'Inbox':
                    # Try to find a 'Brain Dump' or 'Inbox' folder
                    folders = self.joplin_client.get_folders()
                    inbox_id = None
                    for f in folders:
                        if f['title'].lower() in ['inbox', 'brain dump', 'capture']:
                            inbox_id = f['id']
                            break
                    if inbox_id:
                        final_note['parent_id'] = inbox_id
                    elif folders:
                        final_note['parent_id'] = folders[0]['id']

                # Create the note
                note_result = await self._create_note_in_joplin(final_note)
                
                if note_result:
                    await message.reply_text(f"✅ *BRAIN DUMP SAVED TO JOPLIN*\n\nNote: {final_note['title']}", parse_mode='Markdown')
                    
                    # Log to database
                    decision = Decision(
                        user_id=user_id,
                        status="SUCCESS",
                        folder_chosen=final_note.get('parent_id'),
                        note_title=final_note.get('title'),
                        note_body=final_note.get('body'),
                        tags=final_note.get('tags', []),
                        joplin_note_id=note_result['note_id']
                    )
                    self.logging_service.log_decision(decision)

                    # Create Google Tasks if applicable
                    if GOOGLE_TASKS_AVAILABLE and self.task_service:
                        await message.reply_text("🚀 Extracting action items to Google Tasks...")
                        created_tasks = self.task_service.create_tasks_from_decision(decision, str(user_id))
                        if created_tasks:
                            await message.reply_text(f"✅ Created {len(created_tasks)} task(s) in Google Tasks.")
                else:
                    await message.reply_text("❌ Failed to save note to Joplin.")
            
            # Clear state
            self.state_manager.clear_state(user_id)
            await message.reply_text("✨ Brain dump session closed. Your head should feel lighter now!")

        except Exception as e:
            logger.error(f"Error finishing brain dump for user {user_id}: {e}", exc_info=True)
            await message.reply_text("❌ An error occurred while finishing your session. I've cleared the session state.")
            self.state_manager.clear_state(user_id)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages"""
        user = update.effective_user
        message = update.message

        if not user or not message or not message.text:
            return

        user_id = user.id
        text = message.text.strip()

        # Check whitelist
        if not check_whitelist(user_id):
            await message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        # Validate message
        validated_text = validate_message_text(text)
        if not validated_text:
            await message.reply_text("❌ Please send a valid message.")
            return

        try:
            logger.info(f"📨 Processing message from user {user_id}: '{validated_text[:50]}{'...' if len(validated_text) > 50 else ''}'")

            # Log the incoming message
            telegram_msg = TelegramMessage(user_id=user_id, message_text=validated_text)
            telegram_message_id = self.logging_service.log_telegram_message(telegram_msg)

            # Check if user has pending state (previous clarification)
            pending_state = self.state_manager.get_state(user_id)

            if pending_state:
                if pending_state.get('active_persona') == 'GTD_EXPERT':
                    logger.info(f"🧠 Handling GTD mind sweep message for user {user_id}")
                    await self._handle_braindump_message(user_id, validated_text, message)
                else:
                    logger.info(f"🔄 Handling clarification reply for user {user_id}")
                    # This is a reply to a clarification question
                    await self._handle_clarification_reply(user_id, validated_text, message)
            else:
                logger.info(f"🆕 Processing new request for user {user_id}")
                # This is a new request
                await self._handle_new_request(user_id, validated_text, message, telegram_message_id)

        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            error_msg = handle_api_error(e, "message handling")
            await message.reply_text(format_error_message(error_msg))

    async def _handle_new_request(self, user_id: int, text: str, message: Message, telegram_message_id: Optional[int]) -> None:
        """Handle a new note creation request"""
        # Check if this is an action item (task) vs a regular note
        from src.task_service import should_create_tasks_for_decision

        # Quick check: does message contain action indicators?
        action_indicators = ['todo', 'task', 'follow', 'call', 'email', 'schedule', 'remind']
        is_action_item = any(indicator in text.lower() for indicator in action_indicators)

        # CASE 1: Action item (TODO, call, remind, etc.) → Create Google Task directly
        if is_action_item:
            logger.info(f"Detected action item from user {user_id}: '{text[:50]}...'")

            if not self.task_service:
                logger.warning(f"Task service not available for user {user_id}")
                await message.reply_text("⚠️ Google Tasks integration is not available. Please authorize first with /authorize_google_tasks")
                return

            try:
                logger.info(f"Creating Google Task for action item: '{text}'")

                # Create task directly without LLM or clarification
                decision = Decision(
                    user_id=user_id,
                    telegram_message_id=telegram_message_id,
                    status="SUCCESS",
                    note_title=text,
                    note_body="",
                    tags=[]
                )

                created_tasks = self.task_service.create_tasks_from_decision(decision, str(user_id))
                tasks_created = len(created_tasks) if created_tasks else 0

                logger.info(f"Task creation result: {tasks_created} tasks created")

                if tasks_created > 0:
                    # Log to database
                    self.logging_service.log_decision(decision)
                    response_msg = format_success_message(f"✅ Created {tasks_created} Google Task(s): '{text}'")
                    await message.reply_text(response_msg)
                    logger.info(f"Successfully created {tasks_created} Google Task(s) for user {user_id}")
                else:
                    logger.warning(f"No tasks created for action item: {text}")
                    await message.reply_text(format_error_message("Failed to create Google Task. Please check /google_tasks_status"))
            except Exception as e:
                logger.error(f"Error creating Google Task for user {user_id}: {e}", exc_info=True)
                await message.reply_text(format_error_message(f"Failed to create task: {e}"))
            return

        # CASE 2: Regular note → Process with LLM (may ask for clarification)
        logger.info(f"Processing as Joplin note for user {user_id}: '{text[:50]}...'")

        # Check Joplin connectivity
        if not ping_joplin_api():
            await message.reply_text(
                "❌ I'm ready, but Joplin isn't accessible on your computer. "
                "Please make sure Joplin is running with Web Clipper enabled."
            )
            return

        # Get existing tags for context
        existing_tags = []
        try:
            tags = self.joplin_client.fetch_tags()
            existing_tags = [tag.get('title', '') for tag in tags if tag.get('title')]
        except Exception as e:
            logger.warning(f"Failed to fetch tags for context: {e}")

        # Get folders for context
        folders = self.joplin_client.get_folders()

        # Process with LLM
        context = {"existing_tags": existing_tags, "folders": folders}
        llm_response = self.llm_orchestrator.process_message(text, context)

        await self._process_llm_response(user_id, llm_response, message, telegram_message_id)

    async def _handle_clarification_reply(self, user_id: int, text: str, message) -> None:
        """Handle reply to clarification question"""
        # Get pending state
        state = self.state_manager.get_state(user_id)
        if not state:
            await message.reply_text("❌ No pending clarification found. Please start a new request.")
            return

        # Combine with original message
        original_message = state.get('original_message', '')
        combined_message = f"{original_message}\n\nClarification: {text}"

        # Check if combined message is an action item (task)
        action_indicators = ['todo', 'task', 'follow', 'call', 'email', 'schedule', 'remind']
        is_action_item = any(indicator in combined_message.lower() for indicator in action_indicators)

        # CASE 1: Action item → Create Google Task directly
        if is_action_item and self.task_service:
            logger.info(f"Detected action item in clarification reply for user {user_id}")
            try:
                decision = Decision(
                    user_id=user_id,
                    status="SUCCESS",
                    note_title=combined_message,
                    note_body="",
                    tags=[]
                )

                created_tasks = self.task_service.create_tasks_from_decision(decision, str(user_id))
                tasks_created = len(created_tasks) if created_tasks else 0

                if tasks_created > 0:
                    self.logging_service.log_decision(decision)
                    self.state_manager.clear_state(user_id)
                    response_msg = format_success_message(f"✅ Created {tasks_created} Google Task(s): '{combined_message}'")
                    await message.reply_text(response_msg)
                    logger.info(f"Successfully created {tasks_created} Google Task(s) for user {user_id}")
                else:
                    await message.reply_text(format_error_message("Failed to create Google Task. Please try again."))
            except Exception as e:
                logger.error(f"Error creating Google Task from clarification: {e}")
                await message.reply_text(format_error_message(f"Failed to create task: {e}"))
            return

        # CASE 2: Regular note → Process with LLM
        logger.info(f"Processing clarification as Joplin note for user {user_id}")

        # Get existing tags
        existing_tags = state.get('existing_tags', [])

        # Get folders for context
        folders = self.joplin_client.get_folders()

        # Process combined message
        context = {"existing_tags": existing_tags, "folders": folders}
        llm_response = self.llm_orchestrator.process_message(combined_message, context)

        await self._process_llm_response(user_id, llm_response, message, clear_state=True)

    async def _process_llm_response(self, user_id: int, llm_response, message, telegram_message_id: Optional[int] = None, clear_state: bool = False) -> None:
        """Process the LLM response and create Joplin note"""
        if llm_response.status == "SUCCESS" and llm_response.note:
            logger.info(f"Creating Joplin note for user {user_id}")
            note_result = await self._create_note_in_joplin(llm_response.note)

            if note_result:
                note_id = note_result['note_id']
                tag_info = note_result.get('tag_info', {})

                # Log the decision
                try:
                    self.joplin_client.append_log(llm_response.log_entry)
                except Exception as e:
                    logger.warning(f"Failed to append to log: {e}")

                # Log to database
                decision = Decision(
                    user_id=user_id,
                    telegram_message_id=telegram_message_id,
                    status=llm_response.status,
                    folder_chosen=llm_response.note.get('parent_id'),
                    note_title=llm_response.note.get('title'),
                    note_body=llm_response.note.get('body'),
                    tags=llm_response.note.get('tags', []),
                    joplin_note_id=note_id
                )
                self.logging_service.log_decision(decision)

                # Log tag creation to database
                self._log_tag_creation(user_id, note_id, tag_info)

                # Clear state and respond
                if clear_state:
                    self.state_manager.clear_state(user_id)

                # Get folder name for response
                folder_id = llm_response.note.get('parent_id')
                folder = self.joplin_client.get_folder(folder_id) if folder_id else None
                folder_name = folder.get('title', 'Unknown') if folder else 'Unknown'

                # Build success message with tags
                success_msg = f"✅ Note created: '{llm_response.note['title']}' in folder '{folder_name}'"

                # Add tag info if tags exist
                if tag_info.get('all_tags'):
                    tag_display = self._format_tag_display(tag_info)
                    success_msg += f"\nTags: {tag_display}"

                response_msg = format_success_message(success_msg)
                await message.reply_text(response_msg)

            else:
                await message.reply_text(
                    format_error_message("Failed to create note in Joplin. Please try again.")
                )

        elif llm_response.status == "NEED_INFO" and llm_response.question:
            # Store context and ask for clarification
            state = {
                'original_message': message.text,
                'existing_tags': llm_response.note.get('existing_tags', []) if llm_response.note else [],
                'llm_response': llm_response.dict()
            }

            self.state_manager.update_state(user_id, state)
            await message.reply_text(f"🤔 {llm_response.question}")

        else:
            # Unexpected response
            logger.error(f"Unexpected LLM response: {llm_response}")
            await message.reply_text(
                format_error_message("I had trouble understanding your request. Please try rephrasing.")
            )

    async def _create_note_in_joplin(self, note_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a note in Joplin with the provided data

        Returns:
            Dict with note_id and tag_info, or None if creation failed
        """
        try:
            logger.info(f"📝 Creating note in Joplin: '{note_data.get('title', 'Untitled')}'")

            # Validate note data
            from src.security_utils import validate_note_data
            errors = validate_note_data(note_data)
            if errors:
                logger.error(f"❌ Note validation failed: {errors}")
                return None

            # Create the note
            logger.debug(f"📁 Creating note in folder: {note_data['parent_id']}")

            note_id = self.joplin_client.create_note(
                folder_id=note_data['parent_id'],
                title=note_data['title'],
                body=note_data['body']
            )

            if not note_id:
                logger.error("❌ Failed to create note - no ID returned")
                return None

            logger.info(f"✅ Note created successfully with ID: {note_id}")

            # Apply tags if provided and track which are new
            tags = note_data.get('tags', [])
            tag_info = {
                'new_tags': [],
                'existing_tags': [],
                'all_tags': []
            }

            if tags:
                logger.debug(f"🏷️ Applying tags: {tags}")
                tag_info = self.joplin_client.apply_tags_and_track_new(note_id, tags)
                if tag_info['success']:
                    logger.info(f"✅ Applied {len(tags)} tag(s) to note (new: {len(tag_info['new_tags'])}, existing: {len(tag_info['existing_tags'])})")
                else:
                    logger.warning(f"⚠️ Some tags failed to apply")

            return {
                'note_id': note_id,
                'tag_info': tag_info
            }

        except Exception as e:
            logger.error(f"💥 Error creating note in Joplin: {e}")
            logger.debug(f"Note data: {note_data}", exc_info=True)
            return None

    def _format_tag_display(self, tag_info: Dict[str, Any]) -> str:
        """Format tags for display in success message

        Format: "tag1, tag2 (new), tag3"
        Only marks tags with (new) if they were newly created
        """
        if not tag_info.get('all_tags'):
            return ""

        # Create a set of new tags for quick lookup
        new_tag_set = set(tag_info.get('new_tags', []))

        # Format each tag
        formatted_tags = []
        for tag in tag_info.get('all_tags', []):
            if tag in new_tag_set:
                formatted_tags.append(f"{tag} (new)")
            else:
                formatted_tags.append(tag)

        return ", ".join(formatted_tags)

    def _log_tag_creation(self, user_id: int, note_id: str, tag_info: Dict[str, Any]) -> None:
        """Log tag creation to database for audit trail

        Args:
            user_id: Telegram user ID
            note_id: Joplin note ID
            tag_info: Dict with new_tags, existing_tags, all_tags
        """
        try:
            for tag_name in tag_info.get('new_tags', []):
                self.logging_service.log_tag_creation(
                    user_id=user_id,
                    note_id=note_id,
                    tag_name=tag_name,
                    is_new=True
                )

            for tag_name in tag_info.get('existing_tags', []):
                self.logging_service.log_tag_creation(
                    user_id=user_id,
                    note_id=note_id,
                    tag_name=tag_name,
                    is_new=False
                )
        except Exception as e:
            logger.warning(f"Failed to log tag creation: {e}")

def main():
    """Main function to run the bot"""
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Optionally reduce httpx logging verbosity (uncomment if logs are too noisy)
    # logging.getLogger("httpx").setLevel(logging.WARNING)

    # Check token
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Create orchestrator
    orchestrator = TelegramOrchestrator()

    # Add handlers
    application.add_handler(CommandHandler("start", orchestrator.handle_start))
    application.add_handler(CommandHandler("status", orchestrator.handle_status))
    application.add_handler(CommandHandler("helpme", orchestrator.handle_helpme))
    application.add_handler(CommandHandler("authorize_google_tasks", orchestrator.handle_authorize_google_tasks))
    application.add_handler(CommandHandler("verify_google", orchestrator.handle_verify_google))
    application.add_handler(CommandHandler("google_tasks_config", orchestrator.handle_google_tasks_config))
    application.add_handler(CommandHandler("set_task_list", orchestrator.handle_set_task_list))
    application.add_handler(CommandHandler("toggle_auto_tasks", orchestrator.handle_toggle_auto_tasks))
    application.add_handler(CommandHandler("toggle_privacy", orchestrator.handle_toggle_privacy))
    application.add_handler(CommandHandler("google_tasks_status", orchestrator.handle_google_tasks_status))
    application.add_handler(CommandHandler("list_inbox_tasks", orchestrator.handle_list_inbox_tasks))
    application.add_handler(CommandHandler("daily_report", orchestrator.handle_daily_report))
    application.add_handler(CommandHandler("configure_report_time", orchestrator.handle_configure_report_time))
    application.add_handler(CommandHandler("configure_report_timezone", orchestrator.handle_configure_report_timezone))
    application.add_handler(CommandHandler("toggle_daily_report", orchestrator.handle_toggle_daily_report))
    application.add_handler(CommandHandler("show_report_config", orchestrator.handle_show_report_config))
    application.add_handler(CommandHandler("configure_report_content", orchestrator.handle_configure_report_content))
    application.add_handler(CommandHandler("report_help", orchestrator.handle_report_help))
    application.add_handler(CommandHandler("braindump", orchestrator.handle_braindump))
    application.add_handler(CommandHandler("capture", orchestrator.handle_braindump))  # Alias
    application.add_handler(CommandHandler("braindump_stop", orchestrator.handle_braindump_stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, orchestrator.handle_message))

    # Register startup and shutdown callbacks for scheduler
    async def startup_callback(context):
        """Called when bot starts - initialize scheduler"""
        try:
            await orchestrator.scheduler.start()
            logger.info("Scheduler started on bot startup")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

    async def shutdown_callback(context):
        """Called when bot shuts down - stop scheduler"""
        try:
            await orchestrator.scheduler.stop()
            logger.info("Scheduler stopped on bot shutdown")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

    application.post_init = startup_callback
    application.post_shutdown = shutdown_callback

    # Start the bot with configurable polling
    logger.info("Starting Telegram bot...")

    # Configure polling parameters
    # poll_interval: seconds between polling requests (default: ~10s)
    # timeout: how long to wait for updates (default: 10s)
    # drop_pending_updates: ignore pending updates on startup
    application.run_polling(
        poll_interval=3,  # Check for messages every 3 seconds
        timeout=10,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()