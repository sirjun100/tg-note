"""
GTD Brain Dump handlers: /braindump, /braindump_stop, in-session messages.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import Message, Update
from telegram.ext import CommandHandler, ContextTypes

from src.logging_service import Decision
from src.security_utils import check_whitelist

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

GOOGLE_TASKS_AVAILABLE = False
try:
    import src.google_tasks_client  # noqa: F401
    import src.task_service  # noqa: F401
    GOOGLE_TASKS_AVAILABLE = True
except ImportError:
    pass


def register_braindump_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    application.add_handler(CommandHandler("braindump", _braindump(orch)))
    application.add_handler(CommandHandler("capture", _braindump(orch)))
    application.add_handler(CommandHandler("braindump_stop", _braindump_stop(orch)))


def _braindump(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        user_id = user.id
        logger.info("User %d starting /braindump session", user_id)

        state = orch.state_manager.get_state(user_id)
        if state and state.get("active_persona") == "GTD_EXPERT":
            await update.message.reply_text(
                "💡 You already have an active brain dump session! "
                "Just keep typing, or use /braindump_stop to finish."
            )
            return

        new_state: dict[str, Any] = {
            "active_persona": "GTD_EXPERT",
            "session_start": datetime.now().isoformat(),
            "captured_items": [],
            "conversation_history": [],
        }

        first_question = (
            "Ready to dump your brain? Let's do 15 minutes. "
            "First—what is the thing that has been poking at you the most lately? "
            "The one that keeps coming back."
        )

        prompt_path = Path(__file__).parent.parent / "prompts" / "gtd_expert.txt"
        if prompt_path.exists():
            try:
                lines = prompt_path.read_text().strip().split("\n")
                if lines:
                    first_question = lines[-1]
            except Exception as exc:
                logger.warning("Failed to read GTD prompt: %s", exc)

        orch.state_manager.update_state(user_id, new_state)
        await update.message.reply_text(
            f"🧠 *GTD MIND SWEEP SESSION STARTED*\n\n{first_question}",
            parse_mode="Markdown",
        )

    return handler


def _braindump_stop(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "GTD_EXPERT":
            await update.message.reply_text(
                "❌ You don't have an active brain dump session. Use /braindump to start one."
            )
            return

        logger.info("User %d stopping /braindump session via command", user_id)
        await _finish_session(orch, user_id, update.message)

    return handler


# ---------------------------------------------------------------------------
# Public helper called by core message router
# ---------------------------------------------------------------------------


async def handle_braindump_message(
    orch: TelegramOrchestrator, user_id: int, text: str, message: Message
) -> None:
    state = orch.state_manager.get_state(user_id)
    if not state:
        return

    history = state.get("conversation_history", [])
    ctx = {
        "session_start": state.get("session_start"),
        "item_count": len(state.get("captured_items", [])),
    }

    try:
        llm_response = await orch.llm_orchestrator.process_message(
            user_message=text, context=ctx, persona="gtd_expert", history=history
        )

        history.append({"role": "user", "content": text})

        if llm_response.status == "SUCCESS":
            logger.info("GTD session for user %d completed by LLM", user_id)
            state["final_note"] = llm_response.note
            state["conversation_history"] = history
            orch.state_manager.update_state(user_id, state)
            await _finish_session(orch, user_id, message, llm_response.note)
        else:
            next_q = llm_response.question or "Any other thoughts?"
            history.append({"role": "assistant", "content": next_q})
            state["conversation_history"] = history[-15:]
            orch.state_manager.update_state(user_id, state)
            await message.reply_text(next_q)
    except Exception as exc:
        logger.error("Error in GTD brain dump for user %d: %s", user_id, exc)
        await message.reply_text(
            "❌ Sorry, I had some trouble processing that. "
            "You can continue or use /braindump_stop to finish."
        )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


async def _finish_session(
    orch: TelegramOrchestrator,
    user_id: int,
    message: Message,
    note_data: dict[str, Any] | None = None,
) -> None:
    state = orch.state_manager.get_state(user_id)
    if not state:
        return

    await message.reply_text("🏁 *FINISHING BRAIN DUMP SESSION...*", parse_mode="Markdown")

    try:
        final_note = note_data or state.get("final_note")

        if not final_note:
            history = state.get("conversation_history", [])
            if history:
                await message.reply_text("📊 Generating summary of your session...")
                llm_response = await orch.llm_orchestrator.process_message(
                    user_message="Please summarize everything we've talked about so far into an organized list.",
                    persona="gtd_expert",
                    history=history,
                )
                if llm_response.status == "SUCCESS":
                    final_note = llm_response.note
                else:
                    await message.reply_text(
                        "⚠️ Couldn't generate a structured summary. I'll save our conversation as-is."
                    )
                    final_note = {
                        "title": f"Brain Dump Session - {datetime.now().strftime('%Y-%m-%d')}",
                        "body": "\n".join(f"{h['role']}: {h['content']}" for h in history),
                        "parent_id": "Inbox",
                        "tags": ["brain-dump", "mindsweep"],
                    }

        if final_note:
            if not final_note.get("parent_id") or final_note.get("parent_id") == "Inbox":
                folders = await orch.joplin_client.get_folders()
                inbox_id = None
                for f in folders:
                    if f["title"].lower() in ("inbox", "brain dump", "capture"):
                        inbox_id = f["id"]
                        break
                if inbox_id:
                    final_note["parent_id"] = inbox_id
                elif folders:
                    final_note["parent_id"] = folders[0]["id"]

            from src.handlers.core import create_note_in_joplin

            note_result = await create_note_in_joplin(orch, final_note)

            if note_result:
                await message.reply_text(
                    f"✅ *BRAIN DUMP SAVED TO JOPLIN*\n\nNote: {final_note['title']}",
                    parse_mode="Markdown",
                )
                decision = Decision(
                    user_id=user_id,
                    status="SUCCESS",
                    folder_chosen=final_note.get("parent_id"),
                    note_title=final_note.get("title"),
                    note_body=final_note.get("body"),
                    tags=final_note.get("tags", []),
                    joplin_note_id=note_result["note_id"],
                )
                orch.logging_service.log_decision(decision)

                if GOOGLE_TASKS_AVAILABLE and orch.task_service:
                    await message.reply_text("🚀 Extracting action items to Google Tasks...")
                    created = orch.task_service.create_tasks_from_decision(decision, str(user_id))
                    if created:
                        try:
                            status = orch.task_service.get_task_sync_status(user_id)
                            s, f = status.get("success_count", 0), status.get("failed_count", 0)
                            status_line = f"\n\n📊 Sync: ✅ {s} successful, ❌ {f} failed — /google_tasks_status"
                        except Exception:
                            status_line = ""
                        await message.reply_text(f"✅ Created {len(created)} task(s) in Google Tasks.{status_line}")
                    else:
                        has_token = orch.logging_service.load_google_token(str(user_id)) is not None
                        if has_token:
                            await message.reply_text("❌ Could not create Google Tasks. Check /google_tasks_status for details.")
                        else:
                            await message.reply_text(
                                "❌ Could not create Google Tasks. Use /authorize_google_tasks to connect your Google account first."
                            )
            else:
                await message.reply_text("❌ Failed to save note to Joplin.")

        orch.state_manager.clear_state(user_id)
        await message.reply_text("✨ Brain dump session closed. Your head should feel lighter now!")
    except Exception as exc:
        logger.error("Error finishing brain dump for user %d: %s", user_id, exc, exc_info=True)
        await message.reply_text(
            "❌ An error occurred while finishing your session. I've cleared the session state."
        )
        orch.state_manager.clear_state(user_id)
