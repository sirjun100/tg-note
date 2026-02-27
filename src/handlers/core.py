"""
Core handlers: /start, /status, /helpme, and message routing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from telegram import Message, Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from src.constants import is_action_item
from src.logging_service import Decision, TelegramMessage
from src.security_utils import (
    check_whitelist,
    format_error_message,
    format_success_message,
    handle_api_error,
    ping_joplin_api,
    validate_message_text,
    validate_note_data,
)

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def register_core_handlers(application: Any, orch: "TelegramOrchestrator") -> None:
    application.add_handler(CommandHandler("start", _start(orch)))
    application.add_handler(CommandHandler("status", _status(orch)))
    application.add_handler(CommandHandler("helpme", _helpme(orch)))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _message(orch))
    )


# ---------------------------------------------------------------------------
# Handler factories — each returns an async callback bound to the orchestrator
# ---------------------------------------------------------------------------


def _start(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user:
            return
        if not check_whitelist(user.id):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        orch.state_manager.clear_state(user.id)

        welcome = (
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
        await update.message.reply_text(welcome)
        logger.info("Started conversation with user %d", user.id)

    return handler


def _status(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        joplin_ok = await ping_joplin_api()
        has_pending = orch.state_manager.has_pending_state(user.id)

        google_ok = False
        if orch.task_service:
            try:
                token = orch.logging_service.load_google_token(str(user.id))
                google_ok = token is not None
            except Exception:
                pass

        msg = (
            "🤖 Bot Status:\n\n"
            f"Joplin API: {'✅ Connected' if joplin_ok else '❌ Not accessible'}\n"
            f"Pending clarification: {'✅ Yes' if has_pending else '❌ No'}\n"
            f"Google Tasks: {'✅ Configured' if google_ok else '❌ Not configured'}\n"
        )
        if not joplin_ok:
            msg += "\n⚠️ Make sure Joplin is running with Web Clipper enabled."
        await update.message.reply_text(msg)

    return handler


def _helpme(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "/configure_report_time HH:MM - Set delivery time\n"
            "/toggle_daily_report on|off - Enable/disable scheduled reports\n"
            "/report_help - Show all report commands\n\n"
            "🧠 **GTD Brain Dump**\n"
            "/braindump - Start an interactive mind sweep session\n"
            "/braindump_stop - End the session early\n\n"
            "🏗️ **Joplin Database Organization**\n"
            "/reorg_status - Check notes, folders, and organization health\n"
            "/reorg_init status|roles - Initialize PARA structure\n"
            "/reorg_preview - See migration plan without changes\n"
            "/reorg_execute - Apply reorganization\n"
            "/enrich_notes [limit] - Add metadata to notes\n"
            "/reorg_help - Show all reorganization commands\n\n"
            "❓ **Questions?**\n"
            "Just send /status to check connectivity."
        )
        await update.message.reply_text(help_message)
        logger.info("Showed help to user %d", user.id)

    return handler


# ---------------------------------------------------------------------------
# Message handler (the main routing logic)
# ---------------------------------------------------------------------------


def _message(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not user or not message or not message.text:
            return

        user_id = user.id
        text = message.text.strip()

        if not check_whitelist(user_id):
            await message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        validated = validate_message_text(text)
        if not validated:
            await message.reply_text("❌ Please send a valid message.")
            return

        try:
            logger.info("Processing message from user %d: '%s'", user_id, validated[:50])

            telegram_msg = TelegramMessage(user_id=user_id, message_text=validated)
            telegram_message_id = orch.logging_service.log_telegram_message(telegram_msg)

            pending = orch.state_manager.get_state(user_id)

            if pending:
                if pending.get("active_persona") == "GTD_EXPERT":
                    await _handle_braindump_message(orch, user_id, validated, message)
                else:
                    await _handle_clarification_reply(orch, user_id, validated, message)
            else:
                await _handle_new_request(orch, user_id, validated, message, telegram_message_id)

        except Exception as exc:
            logger.error("Error handling message from user %d: %s", user_id, exc)
            await message.reply_text(format_error_message(handle_api_error(exc, "message handling")))

    return handler


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _handle_new_request(
    orch: "TelegramOrchestrator",
    user_id: int,
    text: str,
    message: Message,
    telegram_message_id: Optional[int],
) -> None:
    if is_action_item(text):
        logger.info("Detected action item from user %d", user_id)
        if not orch.task_service:
            await message.reply_text(
                "⚠️ Google Tasks integration is not available. "
                "Please authorize first with /authorize_google_tasks"
            )
            return
        try:
            decision = Decision(
                user_id=user_id,
                telegram_message_id=telegram_message_id,
                status="SUCCESS",
                note_title=text,
                note_body="",
                tags=[],
            )
            created = orch.task_service.create_tasks_from_decision(decision, str(user_id))
            count = len(created) if created else 0
            if count > 0:
                orch.logging_service.log_decision(decision)
                await message.reply_text(format_success_message(f"✅ Created {count} Google Task(s): '{text}'"))
            else:
                await message.reply_text(format_error_message("Failed to create Google Task. Check /google_tasks_status"))
        except Exception as exc:
            logger.error("Error creating Google Task: %s", exc, exc_info=True)
            await message.reply_text(format_error_message(f"Failed to create task: {exc}"))
        return

    logger.info("Processing as Joplin note for user %d", user_id)
    if not await ping_joplin_api():
        await message.reply_text(
            "❌ I'm ready, but Joplin isn't accessible. "
            "Please make sure Joplin is running with Web Clipper enabled."
        )
        return

    existing_tags = []
    try:
        tags = await orch.joplin_client.fetch_tags()
        existing_tags = [t.get("title", "") for t in tags if t.get("title")]
    except Exception as exc:
        logger.warning("Failed to fetch tags: %s", exc)

    folders = await orch.joplin_client.get_folders()
    ctx = {"existing_tags": existing_tags, "folders": folders}
    llm_response = orch.llm_orchestrator.process_message(text, ctx)
    await _process_llm_response(orch, user_id, llm_response, message, telegram_message_id)


async def _handle_clarification_reply(
    orch: "TelegramOrchestrator", user_id: int, text: str, message: Message
) -> None:
    state = orch.state_manager.get_state(user_id)
    if not state:
        await message.reply_text("❌ No pending clarification found. Please start a new request.")
        return

    original = state.get("original_message", "")
    combined = f"{original}\n\nClarification: {text}"

    if is_action_item(combined) and orch.task_service:
        try:
            decision = Decision(user_id=user_id, status="SUCCESS", note_title=combined, note_body="", tags=[])
            created = orch.task_service.create_tasks_from_decision(decision, str(user_id))
            count = len(created) if created else 0
            if count > 0:
                orch.logging_service.log_decision(decision)
                orch.state_manager.clear_state(user_id)
                await message.reply_text(format_success_message(f"✅ Created {count} Google Task(s): '{combined}'"))
            else:
                await message.reply_text(format_error_message("Failed to create Google Task."))
        except Exception as exc:
            await message.reply_text(format_error_message(f"Failed to create task: {exc}"))
        return

    existing_tags = state.get("existing_tags", [])
    folders = await orch.joplin_client.get_folders()
    ctx = {"existing_tags": existing_tags, "folders": folders}
    llm_response = orch.llm_orchestrator.process_message(combined, ctx)
    await _process_llm_response(orch, user_id, llm_response, message, clear_state=True)


async def _handle_braindump_message(
    orch: "TelegramOrchestrator", user_id: int, text: str, message: Message
) -> None:
    from src.handlers.braindump import handle_braindump_message
    await handle_braindump_message(orch, user_id, text, message)


async def _process_llm_response(
    orch: "TelegramOrchestrator",
    user_id: int,
    llm_response: Any,
    message: Message,
    telegram_message_id: Optional[int] = None,
    clear_state: bool = False,
) -> None:
    if llm_response.status == "SUCCESS" and llm_response.note:
        note_result = await create_note_in_joplin(orch, llm_response.note)
        if note_result:
            note_id = note_result["note_id"]
            tag_info = note_result.get("tag_info", {})

            try:
                await orch.joplin_client.append_log(llm_response.log_entry)
            except Exception as exc:
                logger.warning("Failed to append log: %s", exc)

            decision = Decision(
                user_id=user_id,
                telegram_message_id=telegram_message_id,
                status=llm_response.status,
                folder_chosen=llm_response.note.get("parent_id"),
                note_title=llm_response.note.get("title"),
                note_body=llm_response.note.get("body"),
                tags=llm_response.note.get("tags", []),
                joplin_note_id=note_id,
            )
            orch.logging_service.log_decision(decision)
            _log_tag_creation(orch, user_id, note_id, tag_info)

            if clear_state:
                orch.state_manager.clear_state(user_id)

            folder_id = llm_response.note.get("parent_id")
            folder = await orch.joplin_client.get_folder(folder_id) if folder_id else None
            folder_name = folder.get("title", "Unknown") if folder else "Unknown"

            success_msg = f"✅ Note created: '{llm_response.note['title']}' in folder '{folder_name}'"
            if tag_info.get("all_tags"):
                success_msg += f"\nTags: {_format_tag_display(tag_info)}"
            await message.reply_text(format_success_message(success_msg))
        else:
            await message.reply_text(format_error_message("Failed to create note in Joplin. Please try again."))

    elif llm_response.status == "NEED_INFO" and llm_response.question:
        state = {
            "original_message": message.text,
            "existing_tags": llm_response.note.get("existing_tags", []) if llm_response.note else [],
            "llm_response": llm_response.dict(),
        }
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(f"🤔 {llm_response.question}")
    else:
        logger.error("Unexpected LLM response: %s", llm_response)
        await message.reply_text(format_error_message("I had trouble understanding. Please try rephrasing."))


async def create_note_in_joplin(
    orch: "TelegramOrchestrator", note_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    try:
        errors = validate_note_data(note_data)
        if errors:
            logger.error("Note validation failed: %s", errors)
            return None

        note_id = await orch.joplin_client.create_note(
            folder_id=note_data["parent_id"],
            title=note_data["title"],
            body=note_data["body"],
        )

        tags = note_data.get("tags", [])
        tag_info: Dict[str, Any] = {"new_tags": [], "existing_tags": [], "all_tags": []}
        if tags:
            tag_info = await orch.joplin_client.apply_tags_and_track_new(note_id, tags)

        return {"note_id": note_id, "tag_info": tag_info}
    except Exception as exc:
        logger.error("Error creating note: %s", exc, exc_info=True)
        return None


def _format_tag_display(tag_info: Dict[str, Any]) -> str:
    if not tag_info.get("all_tags"):
        return ""
    new_set = set(tag_info.get("new_tags", []))
    parts = [f"{t} (new)" if t in new_set else t for t in tag_info.get("all_tags", [])]
    return ", ".join(parts)


def _log_tag_creation(
    orch: "TelegramOrchestrator", user_id: int, note_id: str, tag_info: Dict[str, Any]
) -> None:
    try:
        for name in tag_info.get("new_tags", []):
            orch.logging_service.log_tag_creation(user_id=user_id, note_id=note_id, tag_name=name, is_new=True)
        for name in tag_info.get("existing_tags", []):
            orch.logging_service.log_tag_creation(user_id=user_id, note_id=note_id, tag_name=name, is_new=False)
    except Exception as exc:
        logger.warning("Failed to log tag creation: %s", exc)
