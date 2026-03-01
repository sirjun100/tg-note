"""
Core handlers: /start, /status, /helpme, and message routing.
"""

from __future__ import annotations

import asyncio
import difflib
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Dict, Optional

from telegram import Message, Update
from telegram.constants import ChatAction
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
from src.url_enrichment import extract_urls, fetch_url_context

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)
_sync_task: Optional[asyncio.Task] = None
PROJECT_STATUS_TAGS = {
    "status/planning",
    "status/building",
    "status/blocked",
    "status/done",
}


def register_core_handlers(application: Any, orch: "TelegramOrchestrator") -> None:
    application.add_handler(CommandHandler("start", _start(orch)))
    application.add_handler(CommandHandler("status", _status(orch)))
    application.add_handler(CommandHandler("project_status", _project_status(orch)))
    application.add_handler(CommandHandler("sync", _sync(orch)))
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
            "/sync - Force Joplin sync with Dropbox\n"
            "/project_status - Show project status tag summary\n"
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
        dropbox_sync_ok, dropbox_sync_msg = await _get_joplin_dropbox_sync_status()
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
            f"Joplin Sync (Dropbox): {'✅ Configured' if dropbox_sync_ok else '❌ Not configured'}"
            f"{f' ({dropbox_sync_msg})' if dropbox_sync_msg else ''}\n"
            f"Pending clarification: {'✅ Yes' if has_pending else '❌ No'}\n"
            f"Google Tasks: {'✅ Configured' if google_ok else '❌ Not configured'}\n"
        )
        if not joplin_ok:
            msg += "\n⚠️ Make sure Joplin is running with Web Clipper enabled."
        await update.message.reply_text(msg)

    return handler


def _sync(orch: "TelegramOrchestrator"):
    """Force a Joplin sync with the configured target (e.g. Dropbox)."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        await update.message.reply_chat_action(ChatAction.TYPING)
        dropbox_ok, sync_target_msg = await _get_joplin_dropbox_sync_status()
        target_label = "Dropbox" if dropbox_ok else sync_target_msg

        await update.message.reply_text(
            f"🔄 Syncing Joplin with {target_label}… This may take up to a minute."
        )

        profile = os.environ.get("JOPLIN_PROFILE")
        if not profile and os.path.isdir("/app/data/joplin"):
            profile = "/app/data/joplin"
        cmd = ["joplin"] + (["--profile", profile] if profile else []) + ["sync"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        except FileNotFoundError:
            await update.message.reply_text(
                format_error_message("Joplin CLI not found; sync unavailable.")
            )
            return
        except asyncio.TimeoutError:
            await update.message.reply_text(
                format_error_message("Sync timed out after 90 seconds.")
            )
            return
        except Exception as exc:
            logger.exception("Sync command failed")
            await update.message.reply_text(format_error_message(f"Sync failed: {exc}"))
            return

        if proc.returncode == 0:
            await update.message.reply_text(
                f"✅ Sync with {target_label} completed successfully."
            )
        else:
            err = (stderr or stdout).decode("utf-8", errors="ignore").strip()
            await update.message.reply_text(
                format_error_message(f"Sync failed (exit {proc.returncode}): {err or 'unknown error'}")
            )
        logger.info("User %d ran /sync", user.id)

    return handler


async def _get_joplin_dropbox_sync_status() -> tuple[bool, str]:
    """Return whether Joplin sync target is configured to Dropbox (target=7)."""
    profile = os.environ.get("JOPLIN_PROFILE")
    if not profile and os.path.isdir("/app/data/joplin"):
        profile = "/app/data/joplin"

    cmd = ["joplin", "config", "sync.target"]
    if profile:
        cmd = ["joplin", "--profile", profile, "config", "sync.target"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return False, "Joplin CLI unavailable"

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=6)
    except asyncio.TimeoutError:
        proc.kill()
        return False, "status check timeout"

    output = f"{stdout.decode('utf-8', errors='ignore')}\n{stderr.decode('utf-8', errors='ignore')}"
    match = re.search(r"sync\.target\s*=\s*(\d+)", output)
    if not match:
        return False, "unknown target"

    target = int(match.group(1))
    if target == 7:
        return True, "target=Dropbox"
    if target == 0:
        return False, "target=None"
    return False, f"target={target}"


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
            "/sync - Force Joplin sync with Dropbox (or configured sync target)\n"
            "/project_status - Show counts by project status tags\n"
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


def _project_status(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            folders = await orch.joplin_client.get_folders()
            by_id = {f.get("id"): f for f in folders if f.get("id")}

            project_root_id = None
            for f in folders:
                if (f.get("title") or "").strip().lower() == "01 - projects":
                    project_root_id = f.get("id")
                    break

            if not project_root_id:
                await update.message.reply_text("❌ I couldn't find folder `01 - Projects`.")
                return

            def in_projects(folder_id: str) -> bool:
                cur = folder_id
                seen: set[str] = set()
                while cur and cur not in seen:
                    if cur == project_root_id:
                        return True
                    seen.add(cur)
                    node = by_id.get(cur)
                    if not node:
                        break
                    cur = node.get("parent_id", "")
                return False

            tags = await orch.joplin_client.fetch_tags()
            tag_id_by_name = {
                (t.get("title") or "").strip().lower(): t.get("id")
                for t in tags
                if t.get("id")
            }

            status_order = [
                "status/planning",
                "status/building",
                "status/blocked",
                "status/done",
            ]
            status_counts = {name: 0 for name in status_order}
            tagged_project_note_ids: set[str] = set()

            for status_name in status_order:
                tag_id = tag_id_by_name.get(status_name)
                if not tag_id:
                    continue
                notes = await orch.joplin_client.get_notes_with_tag(tag_id)
                for note in notes:
                    note_id = note.get("id")
                    parent_id = note.get("parent_id", "")
                    if note_id and parent_id and in_projects(parent_id):
                        status_counts[status_name] += 1
                        tagged_project_note_ids.add(note_id)

            all_notes = await orch.joplin_client.get_all_notes(fields="id,parent_id")
            all_project_note_ids = {
                n.get("id")
                for n in all_notes
                if n.get("id") and n.get("parent_id") and in_projects(n.get("parent_id", ""))
            }
            untagged_count = max(len(all_project_note_ids) - len(tagged_project_note_ids), 0)

            msg = (
                "📊 Project Status Tags\n\n"
                f"🟡 Planning: {status_counts['status/planning']}\n"
                f"🔵 Building: {status_counts['status/building']}\n"
                f"🟠 Blocked: {status_counts['status/blocked']}\n"
                f"✅ Done: {status_counts['status/done']}\n"
                f"⚪ Untagged: {untagged_count}\n"
            )
            await update.message.reply_text(msg)
        except Exception as exc:
            logger.error("Failed to compute project status: %s", exc, exc_info=True)
            await update.message.reply_text("❌ Failed to compute project status right now.")

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
                    await _handle_clarification_reply(orch, user_id, validated, message, context)
            else:
                await _handle_new_request(orch, user_id, validated, message, telegram_message_id, context)

        except Exception as exc:
            logger.error("Error handling message from user %d: %s", user_id, exc)
            await message.reply_text(format_error_message(handle_api_error(exc, "message handling")))

    return handler


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _send_typing(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send typing indicator; ignore errors so they don't break the flow."""
    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    except Exception:
        pass


async def _handle_new_request(
    orch: "TelegramOrchestrator",
    user_id: int,
    text: str,
    message: Message,
    telegram_message_id: Optional[int],
    context: ContextTypes.DEFAULT_TYPE,
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
    await _send_typing(message, context)
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

    # Status: fetching link when message contains a URL
    urls = extract_urls(text)
    if urls:
        await _send_typing(message, context)
        await message.reply_text("🔗 Fetching link...")
    url_context = await _build_url_context(validated_text=text)

    await _send_typing(message, context)
    await message.reply_text("🤖 Analyzing...")
    folders = await orch.joplin_client.get_folders()
    ctx = {"existing_tags": existing_tags, "folders": folders, "url_context": url_context}
    llm_response = await orch.llm_orchestrator.process_message(text, ctx)

    await _process_llm_response(
        orch, user_id, llm_response, message, telegram_message_id,
        url_context=url_context, context=context,
    )


async def _handle_clarification_reply(
    orch: "TelegramOrchestrator",
    user_id: int,
    text: str,
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
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
    urls = extract_urls(combined)
    if urls:
        await _send_typing(message, context)
        await message.reply_text("🔗 Fetching link...")
    url_context = await _build_url_context(validated_text=combined)
    await _send_typing(message, context)
    await message.reply_text("🤖 Analyzing...")
    folders = await orch.joplin_client.get_folders()
    ctx = {"existing_tags": existing_tags, "folders": folders, "url_context": url_context}
    llm_response = await orch.llm_orchestrator.process_message(combined, ctx)
    await _process_llm_response(
        orch, user_id, llm_response, message,
        clear_state=True, url_context=url_context, context=context,
    )


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
    url_context: Optional[Dict[str, Any]] = None,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
) -> None:
    if llm_response.status == "SUCCESS" and llm_response.note:
        if context:
            await _send_typing(message, context)
        await message.reply_text("📝 Saving to Joplin...")
        note_result = await create_note_in_joplin(
            orch, llm_response.note, url_context=url_context, message=message,
        )
        if note_result:
            if note_result.get("error") == "folder_not_found":
                requested = note_result.get("requested_folder") or "(empty)"
                suggestions = note_result.get("suggestions", [])
                msg = f"❌ I couldn't find folder `{requested}`.\n\n"
                if suggestions:
                    msg += "Try one of these folders:\n"
                    for name in suggestions:
                        msg += f"• {name}\n"
                    msg += "\nReply with one folder name and I'll save the note there."
                else:
                    msg += "Please provide a valid folder name."
                await message.reply_text(msg)
                return

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

            _schedule_joplin_sync()

            folder_id = note_result.get("folder_id") or llm_response.note.get("parent_id")
            folder_name = "Unknown"
            if folder_id:
                try:
                    folder = await orch.joplin_client.get_folder(folder_id)
                    folder_name = folder.get("title", "Unknown") if folder else "Unknown"
                except Exception as exc:
                    logger.warning("Failed to resolve folder '%s' after note creation: %s", folder_id, exc)

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
        await message.reply_text(
            "🧠 Second Brain folders: 00 - Inbox, 01 - Projects, 02 - Areas, 03 - Resources, 04 - Archives.\n\n"
            f"🤔 {llm_response.question}"
        )
    else:
        logger.error("Unexpected LLM response: %s", llm_response)
        await message.reply_text(format_error_message("I had trouble understanding. Please try rephrasing."))


async def create_note_in_joplin(
    orch: "TelegramOrchestrator",
    note_data: Dict[str, Any],
    url_context: Optional[Dict[str, Any]] = None,
    message: Optional[Message] = None,
) -> Optional[Dict[str, Any]]:
    try:
        requested_folder = (note_data.get("parent_id") or "").strip()
        resolved_folder_id, suggestions = await _resolve_folder_id_or_suggestions(
            orch,
            requested_folder,
            note_title=note_data.get("title", ""),
            note_body=note_data.get("body", ""),
        )
        # For recipe notes, fall back to default recipe folder when resolution fails
        if not resolved_folder_id and url_context and url_context.get("content_type") == "recipe":
            for fallback_name in ("03 - Resources", "Recipes"):
                resolved_folder_id, _ = await _resolve_folder_id_or_suggestions(
                    orch,
                    fallback_name,
                    note_title=note_data.get("title", ""),
                    note_body=note_data.get("body", ""),
                )
                if resolved_folder_id:
                    break
        if not resolved_folder_id:
            return {
                "error": "folder_not_found",
                "requested_folder": requested_folder,
                "suggestions": suggestions,
            }

        # Validate after folder resolution so missing/invalid parent_id
        # can be recovered via inference/suggestions.
        normalized_note = dict(note_data)
        normalized_note["parent_id"] = resolved_folder_id
        normalized_note["tags"] = await _ensure_project_status_tag(
            orch,
            resolved_folder_id,
            normalized_note.get("tags", []),
            normalized_note.get("title", ""),
            normalized_note.get("body", ""),
        )
        errors = validate_note_data(normalized_note)
        if errors:
            logger.error("Note validation failed: %s", errors)
            return None

        image_data_url: Optional[str] = None
        needs_image = (
            (url_context and url_context.get("content_type") == "recipe")
            or (
                url_context
                and url_context.get("url")
                and not url_context.get("skip_screenshot")
            )
        )
        if needs_image and message:
            await message.reply_text("🖼️ Adding image...")
        if url_context and url_context.get("url") and url_context.get("skip_screenshot") and message:
            await message.reply_text("⚠️ Screenshot skipped (site uses security verification).")
        if url_context and url_context.get("content_type") == "recipe":
            from src.recipe_image import generate_recipe_image
            image_data_url = await generate_recipe_image(normalized_note["title"])
        if (
            image_data_url is None
            and url_context
            and url_context.get("url")
            and not url_context.get("skip_screenshot")
        ):
            from src.url_screenshot import capture_url_screenshot
            image_data_url = await capture_url_screenshot(url_context["url"])
            if image_data_url is None and message:
                await message.reply_text("⚠️ Couldn't capture screenshot for this link.")

        note_id = await orch.joplin_client.create_note(
            folder_id=resolved_folder_id,
            title=normalized_note["title"],
            body=normalized_note["body"],
            image_data_url=image_data_url,
        )

        tags = normalized_note.get("tags", [])
        tag_info: Dict[str, Any] = {"new_tags": [], "existing_tags": [], "all_tags": []}
        if tags:
            tag_info = await orch.joplin_client.apply_tags_and_track_new(note_id, tags)

        return {"note_id": note_id, "tag_info": tag_info, "folder_id": resolved_folder_id}
    except Exception as exc:
        logger.error("Error creating note: %s", exc, exc_info=True)
        return None


async def _resolve_folder_id_or_suggestions(
    orch: "TelegramOrchestrator",
    requested_folder: str,
    note_title: str = "",
    note_body: str = "",
) -> tuple[Optional[str], list[str]]:
    folders = await orch.joplin_client.get_folders()
    if not folders:
        # Self-heal first-run/empty setups by creating a default Inbox folder.
        try:
            created = await orch.joplin_client.create_folder("00 - Inbox")
            created_id = created.get("id")
            if created_id:
                logger.info("Created default folder '00 - Inbox' (%s)", created_id)
                return created_id, []
        except Exception as exc:
            logger.warning("Failed to auto-create default inbox folder: %s", exc)
        return None, []

    def _fallback_inbox_id() -> Optional[str]:
        # Preferred explicit folder name
        for f in folders:
            title = (f.get("title") or "").strip().lower()
            if title == "00 - inbox":
                return f.get("id")

        # Common variants
        for f in folders:
            title = (f.get("title") or "").strip().lower()
            if title in {"inbox", "00-inbox", "00 inbox"}:
                return f.get("id")
            if "inbox" in title and title.startswith("00"):
                return f.get("id")
            if "inbox" in title:
                return f.get("id")
        return None

    by_id = {f.get("id"): f for f in folders if f.get("id")}
    if requested_folder in by_id:
        return requested_folder, []

    requested_lower = requested_folder.lower()
    by_title_lower = {
        (f.get("title") or "").strip().lower(): f
        for f in folders
        if f.get("title")
    }

    # Exact title match (case-insensitive)
    exact = by_title_lower.get(requested_lower)
    if exact:
        return exact.get("id"), []

    # Empty folder hint -> default inbox immediately.
    if not requested_lower:
        inbox_id = _fallback_inbox_id()
        if inbox_id:
            logger.info("Resolved empty folder hint to inbox folder id '%s'", inbox_id)
            return inbox_id, []

    # Ask LLM to pick the best existing folder when user gives vague input
    # like "I trust you" or a non-existent folder.
    try:
        folder_text = ""
        for f in folders:
            fid = f.get("id")
            title = f.get("title")
            if fid and title:
                folder_text += f"- {fid}: {title}\n"

        note_with_hint = f"Preferred folder from user: {requested_folder}\n\n{note_body or ''}"
        classification = await orch.llm_orchestrator.classify_note(
            note_title or "Untitled",
            note_with_hint,
            folder_text,
        )

        suggested_folder_id = classification.get("suggested_folder_id")
        try:
            confidence = float(classification.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0

        if suggested_folder_id in by_id and confidence >= 0.55:
            logger.info(
                "Resolved folder via LLM: requested='%s' -> folder_id='%s' (confidence=%.2f)",
                requested_folder,
                suggested_folder_id,
                confidence,
            )
            return suggested_folder_id, []
    except Exception as exc:
        logger.warning("LLM folder resolution failed for '%s': %s", requested_folder, exc)

    titles = [f.get("title", "") for f in folders if f.get("title")]
    title_map = {t.lower(): t for t in titles}

    candidates: list[str] = []

    # Prefer substring matches
    for t in titles:
        tl = t.lower()
        if requested_lower and (requested_lower in tl or tl in requested_lower):
            candidates.append(t)

    # Add fuzzy matches
    fuzzy = difflib.get_close_matches(
        requested_lower, list(title_map.keys()), n=5, cutoff=0.3
    )
    for f in fuzzy:
        candidates.append(title_map[f])

    # Deduplicate while preserving order
    deduped: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    # Ensure 3-5 suggestions when possible
    if len(deduped) < 3:
        for t in sorted(titles):
            if t not in seen:
                deduped.append(t)
                seen.add(t)
            if len(deduped) >= 5:
                break

    # Final fallback: if we still can't resolve, use/create inbox folder.
    inbox_id = _fallback_inbox_id()
    if inbox_id:
        logger.info(
            "Falling back to inbox folder for unresolved hint '%s' (id '%s')",
            requested_folder,
            inbox_id,
        )
        return inbox_id, []

    # No inbox exists yet; create one and continue.
    try:
        created = await orch.joplin_client.create_folder("00 - Inbox")
        created_id = created.get("id")
        if created_id:
            logger.info(
                "Created missing default inbox folder for unresolved hint '%s' (id '%s')",
                requested_folder,
                created_id,
            )
            return created_id, []
    except Exception as exc:
        logger.warning("Failed to create fallback inbox folder: %s", exc)

    return None, deduped[:5]


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


async def _build_url_context(validated_text: str) -> Dict[str, Any]:
    """
    Build enrichment context for the first URL in text.

    Keeps LLM payload bounded while still improving note quality.
    """
    urls = extract_urls(validated_text)
    if not urls:
        return {}

    first_url = urls[0]
    context = await fetch_url_context(first_url)
    if context.get("error"):
        logger.info("URL enrichment fallback for %s: %s", first_url, context["error"])
    else:
        logger.info(
            "URL enrichment ready (%s, template=%s)",
            context.get("domain", "unknown"),
            context.get("template_name", "unknown"),
        )
    return context


def _schedule_joplin_sync() -> None:
    """
    Schedule a best-effort Joplin sync.

    Debounces concurrent note creations by allowing only one sync task at a time.
    """
    global _sync_task
    if _sync_task and not _sync_task.done():
        return
    _sync_task = asyncio.create_task(_run_joplin_sync())


async def _run_joplin_sync() -> None:
    profile = os.environ.get("JOPLIN_PROFILE")
    if not profile and os.path.isdir("/app/data/joplin"):
        profile = "/app/data/joplin"

    cmd = ["joplin"]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.append("sync")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    except FileNotFoundError:
        logger.warning("Joplin CLI not found; skipping post-note sync")
        return
    except asyncio.TimeoutError:
        logger.warning("Joplin sync timed out after note creation")
        return
    except Exception as exc:
        logger.warning("Failed to run post-note Joplin sync: %s", exc)
        return

    if proc.returncode == 0:
        logger.info("Post-note Joplin sync completed")
    else:
        err = stderr.decode("utf-8", errors="ignore").strip()
        out = stdout.decode("utf-8", errors="ignore").strip()
        logger.warning(
            "Post-note Joplin sync failed (code=%s): %s",
            proc.returncode,
            err or out or "unknown error",
        )


async def _ensure_project_status_tag(
    orch: "TelegramOrchestrator",
    folder_id: str,
    tags: Any,
    title: str,
    body: str,
) -> list[str]:
    """
    Ensure project notes have exactly one status/* tag.

    Applies only when note goes into 01 - Projects subtree.
    """
    tag_list = [str(t).strip() for t in (tags or []) if str(t).strip()]
    lowered = [t.lower() for t in tag_list]

    # Keep non-status tags and preserve first valid status tag if present.
    existing_status = [t for t in lowered if t in PROJECT_STATUS_TAGS]
    kept_non_status = [t for t in tag_list if t.lower() not in PROJECT_STATUS_TAGS]

    try:
        folders = await orch.joplin_client.get_folders()
    except Exception as exc:
        logger.warning("Could not fetch folders for status-tag policy: %s", exc)
        return tag_list

    by_id = {f.get("id"): f for f in folders if f.get("id")}
    project_root_id = None
    for f in folders:
        if (f.get("title") or "").strip().lower() == "01 - projects":
            project_root_id = f.get("id")
            break
    if not project_root_id:
        return tag_list

    # Walk up parents: if folder is not inside 01 - Projects, leave tags untouched.
    cur = folder_id
    in_projects = False
    visited: set[str] = set()
    while cur and cur not in visited:
        visited.add(cur)
        if cur == project_root_id:
            in_projects = True
            break
        node = by_id.get(cur)
        if not node:
            break
        cur = node.get("parent_id", "")
    if not in_projects:
        return tag_list

    status_tag = existing_status[0] if existing_status else _infer_status_tag(title, body)
    final_tags = kept_non_status + [status_tag]

    # Deduplicate while preserving order.
    out: list[str] = []
    seen: set[str] = set()
    for tag in final_tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out


def _infer_status_tag(title: str, body: str) -> str:
    text = f"{title}\n{body}".lower()
    if any(k in text for k in ["blocked", "on hold", "back burner", "waiting on", "stuck"]):
        return "status/blocked"
    if any(k in text for k in ["done", "completed", "finished", "released", "shipped"]):
        return "status/done"
    if any(k in text for k in ["plan", "planning", "discovery", "research", "backlog", "idea", "todo"]):
        return "status/planning"
    return "status/building"
