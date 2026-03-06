"""
Flashcard practice handlers: /flashcard, /flashcard_done, callback for ratings.

Sprint 14 - FR-033.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.flashcard_service import (
    add_cards_from_note,
    create_session,
    get_card_by_id,
    get_due_cards,
    get_stats,
    record_review,
    update_session,
)
from src.security_utils import check_whitelist, format_error_message

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

FLASHCARD_PERSONA = "FLASHCARD"


def _build_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Show answer", callback_data="fc_show")],
    ])


def _build_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Again", callback_data="fc_again"),
            InlineKeyboardButton("😓 Hard", callback_data="fc_hard"),
            InlineKeyboardButton("👍 Good", callback_data="fc_good"),
            InlineKeyboardButton("😊 Easy", callback_data="fc_easy"),
        ],
    ])


async def _get_flashcard_note_ids(orch: TelegramOrchestrator) -> list[str]:
    """Get note IDs from notes tagged #flashcard or #practice."""
    note_ids: list[str] = []
    for tag_name in ("flashcard", "practice"):
        tag_id = await orch.joplin_client.get_tag_id_by_name(tag_name)
        if tag_id:
            notes = await orch.joplin_client.get_notes_with_tag(tag_id)
            for n in notes:
                nid = n.get("id")
                if nid and nid not in note_ids:
                    note_ids.append(nid)
    return note_ids


def register_flashcard_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register flashcard command and callback handlers."""

    async def flashcard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        args = context.args or []
        limit = 10
        if args and args[0].isdigit():
            limit = min(int(args[0]), 20)
            args = args[1:]

        # /flashcard from <note title>
        if args and args[0].lower() == "from" and len(args) >= 2:
            title_query = " ".join(args[1:]).strip()
            try:
                notes = await orch.joplin_client.search_notes(title_query, limit=5)
                if not notes:
                    await msg.reply_text(
                        format_error_message(f"No notes found matching '{title_query}'.")
                    )
                    return
                note = notes[0]
                note_id = note.get("id")
                note_title = note.get("title", "Untitled")
                body = note.get("body", "")
                if not body:
                    await msg.reply_text(
                        format_error_message(f"Note '{note_title}' has no content to extract from.")
                    )
                    return
                pairs = await orch.llm_orchestrator.extract_flashcards_from_note(note_title, body)
                if not pairs:
                    await msg.reply_text(
                        f"No flashcard-worthy content found in '{note_title}'. "
                        "Try a note with definitions, facts, or concepts."
                    )
                    return
                cards = add_cards_from_note(user.id, note_id, note_title, pairs)
                await msg.reply_text(
                    f"🧠 Extracted {len(cards)} card(s) from '{note_title}'. "
                    f"Use /flashcard to practice!"
                )
            except Exception as exc:
                logger.exception("Flashcard from-note failed: %s", exc)
                await msg.reply_text(format_error_message("Failed to extract flashcards."))
            return

        # /flashcard stats
        if args and args[0].lower() == "stats":
            stats = get_stats(user.id)
            await msg.reply_text(
                f"📊 **Flashcard Stats**\n\n"
                f"• Total cards: {stats['total']}\n"
                f"• Due today: {stats['due']}\n\n"
                f"Use /flashcard to practice!",
                parse_mode="Markdown",
            )
            return

        # /flashcard help
        if args and args[0].lower() == "help":
            await msg.reply_text(
                "🧠 **Flashcard Practice**\n\n"
                "• `/flashcard` — Start session (up to 10 cards)\n"
                "• `/flashcard N` — Session with up to N cards\n"
                "• `/flashcard from <title>` — Extract cards from a note\n"
                "• `/flashcard stats` — Due count, total cards\n"
                "• `/flashcard help` — This message\n"
                "• `/flashcard_done` — End session early\n\n"
                "Tag notes with #flashcard or #practice to include them.",
                parse_mode="Markdown",
            )
            return

        # Start session
        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == FLASHCARD_PERSONA:
            await msg.reply_text("You already have an active session. Use /flashcard_done to end it.")
            return

        try:
            note_ids = await _get_flashcard_note_ids(orch)
            cards = get_due_cards(user.id, note_ids=note_ids if note_ids else None, limit=limit)
        except Exception as exc:
            logger.exception("get_due_cards failed: %s", exc)
            await msg.reply_text(format_error_message("Failed to load flashcards."))
            return

        if not cards:
            stats = get_stats(user.id)
            if stats["total"] == 0:
                await msg.reply_text(
                    "🧠 No flashcards yet. Tag notes with #flashcard or #practice, "
                    "or use /flashcard from <note title> to extract cards."
                )
            else:
                await msg.reply_text(
                    f"🎯 All caught up! No cards due today. "
                    f"Total cards: {stats['total']}."
                )
            return

        session_id = create_session(user.id)
        queue = [c["id"] for c in cards]
        state = {
            "active_persona": FLASHCARD_PERSONA,
            "phase": "question",
            "session_id": session_id,
            "queue": queue,
            "current_index": 0,
            "cards_shown": 0,
            "cards_correct": 0,
        }
        orch.state_manager.update_state(user.id, state)

        card = get_card_by_id(queue[0], user.id)
        if not card:
            orch.state_manager.clear_state(user.id)
            await msg.reply_text(format_error_message("Card not found."))
            return

        text = f"🧠 Flashcard time! You have {len(queue)} card(s) due.\n\n📌 Card 1/{len(queue)}\n\nQ: {card['question']}"
        await msg.reply_text(text, reply_markup=_build_question_keyboard())

    async def flashcard_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != FLASHCARD_PERSONA:
            await msg.reply_text("No active flashcard session. Use /flashcard to start one.")
            return

        session_id = state.get("session_id")
        cards_shown = state.get("cards_shown", 0)
        cards_correct = state.get("cards_correct", 0)
        if session_id:
            update_session(session_id, cards_shown, cards_correct)
        orch.state_manager.clear_state(user.id)

        await msg.reply_text(
            f"✅ Session ended. 🎯 {cards_correct}/{cards_shown} correct. Nice work!"
        )

    async def flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await query.answer("Unauthorized.")
            return

        await query.answer()
        data = query.data
        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != FLASHCARD_PERSONA:
            await query.edit_message_text("Session ended. Use /flashcard to start a new one.")
            return

        queue = state.get("queue", [])
        idx = state.get("current_index", 0)
        cards_shown = state.get("cards_shown", 0)
        cards_correct = state.get("cards_correct", 0)

        if idx >= len(queue):
            orch.state_manager.clear_state(user.id)
            session_id = state.get("session_id")
            if session_id:
                update_session(session_id, cards_shown, cards_correct)
            await query.edit_message_text(
                f"🎯 Session complete! {cards_correct}/{cards_shown} correct. Well done!"
            )
            return

        card_id = queue[idx]
        card = get_card_by_id(card_id, user.id)
        if not card:
            await query.edit_message_text(format_error_message("Card not found."))
            return

        if data == "fc_show":
            # Show answer, show rating buttons
            text = (
                f"📌 Card {idx + 1}/{len(queue)}\n\n"
                f"Q: {card['question']}\n\n"
                f"A: {card['answer']}"
            )
            state["phase"] = "answer"
            orch.state_manager.update_state(user.id, state)
            await query.edit_message_text(text, reply_markup=_build_rating_keyboard())
            return

        if data in ("fc_again", "fc_hard", "fc_good", "fc_easy"):
            rating = data.replace("fc_", "")
            record_review(user.id, card_id, rating)
            cards_shown += 1
            if rating in ("good", "easy"):
                cards_correct += 1
            state["cards_shown"] = cards_shown
            state["cards_correct"] = cards_correct
            state["current_index"] = idx + 1
            state["phase"] = "question"
            orch.state_manager.update_state(user.id, state)

            if idx + 1 >= len(queue):
                orch.state_manager.clear_state(user.id)
                session_id = state.get("session_id")
                if session_id:
                    update_session(session_id, cards_shown, cards_correct)
                await query.edit_message_text(
                    f"🎯 Session complete! {cards_correct}/{cards_shown} correct. Well done!"
                )
                return

            next_card_id = queue[idx + 1]
            next_card = get_card_by_id(next_card_id, user.id)
            if not next_card:
                orch.state_manager.clear_state(user.id)
                await query.edit_message_text(format_error_message("Card not found."))
                return

            text = f"📌 Card {idx + 2}/{len(queue)}\n\nQ: {next_card['question']}"
            await query.edit_message_text(text, reply_markup=_build_question_keyboard())
            return

    application.add_handler(CommandHandler("flashcard", flashcard_cmd))
    application.add_handler(CommandHandler("flashcard_done", flashcard_done_cmd))
    application.add_handler(CallbackQueryHandler(flashcard_callback, pattern="^fc_"))
    logger.info("Flashcard handlers registered")
