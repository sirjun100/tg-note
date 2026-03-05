"""
Stoic Journal handlers: /stoic, /stoic morning, /stoic evening, /stoic_done.
Guided reflection with questions from template; create or append to today's note.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import Message, Update
from telegram.ext import CommandHandler, ContextTypes

from src.security_utils import check_whitelist
from src.timezone_utils import get_current_date_str, get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

STOIC_JOURNAL_PATH = ["Areas", "📓 Journaling", "Stoic Journal"]
STOIC_TAGS = ["stoic", "journal", "daily"]


def _load_stoic_template() -> tuple[list[str], list[str], str]:
    """Load prompts/stoic_journal_template.md; return (morning_questions, evening_questions, body_template)."""
    path = Path(__file__).parent.parent / "prompts" / "stoic_journal_template.md"
    if not path.exists():
        return (
            ["What is your intention for today?", "What will you focus on?"],
            ["What went well?", "What did you control?", "What are you grateful for?"],
            "# {{DATE}} - Daily Stoic Reflection\n\n## Morning Reflection\n\n{{MORNING_CONTENT}}\n\n## Evening Reflection\n\n{{EVENING_CONTENT}}",
        )
    raw = path.read_text(encoding="utf-8")
    # Single "---" separates questions block from body template
    parts = raw.split("---", 1)
    if len(parts) < 2:
        return (
            ["What is your intention for today?"],
            ["What went well today?"],
            "# {{DATE}} - Daily Stoic Reflection\n\n{{MORNING_CONTENT}}\n\n{{EVENING_CONTENT}}",
        )
    block, body_template = parts[0].strip(), parts[1].strip()
    morning_questions: list[str] = []
    evening_questions: list[str] = []
    current: list[str] | None = None
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper() == "MORNING_QUESTIONS:":
            current = morning_questions
            continue
        if line.upper() == "EVENING_QUESTIONS:":
            current = evening_questions
            continue
        if current is not None:
            current.append(line)
    if not morning_questions:
        morning_questions = ["What is your intention for today?"]
    if not evening_questions:
        evening_questions = ["What went well today?"]
    return morning_questions, evening_questions, body_template


def _get_answer(answers: list[dict[str, str]], index: int) -> str:
    """Get answer text at index, or empty string."""
    if index < 0 or index >= len(answers):
        return ""
    return (answers[index].get("a") or "").strip()


def _format_morning_content(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    """Fill morning template: professional objective, personal objective, obstacle, greater goals, top 3 priorities."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")
    professional = _get_answer(answers, 0)
    personal = _get_answer(answers, 1)
    obstacle = _get_answer(answers, 2)
    greater_goals = _get_answer(answers, 3)
    p1 = _get_answer(answers, 4)
    p2 = _get_answer(answers, 5)
    p3 = _get_answer(answers, 6)

    lines = [
        f"### 🌞 Morning ({ts})",
        "",
        "- **Professional Objective:**",
        f"  {professional}" if professional else "  -",
        "",
        "- **Personal Objective:**",
        f"  {personal}" if personal else "  -",
        "",
        "- **Obstacle & Response:**",
        f"  {obstacle}" if obstacle else "  -",
        "",
        "- **Greater Goals:**",
        f"  {greater_goals}" if greater_goals else "  -",
        "",
        "- **Top 3 Priorities:**",
        f"  1. {p1}" if p1 else "  1. -",
        f"  2. {p2}" if p2 else "  2. -",
        f"  3. {p3}" if p3 else "  3. -",
    ]
    return "\n".join(lines)


def _format_evening_content(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    """Fill evening template: morning priorities completed, prof/personal wins, went wrong, control, progress, gratitude, tomorrow."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")
    priorities_completed = _get_answer(answers, 0)
    prof_wins = _get_answer(answers, 1)
    personal_wins = _get_answer(answers, 2)
    went_wrong = _get_answer(answers, 3)
    control = _get_answer(answers, 4)
    progress = _get_answer(answers, 5)
    gratitude = _get_answer(answers, 6)
    tomorrow = _get_answer(answers, 7)

    lines = [
        f"### 🌙 Evening ({ts})",
        "",
        "- **Morning Priorities Completed?**",
        f"  {priorities_completed}" if priorities_completed else "  -",
        "",
        "- **What Went Well (Professional):**",
        f"  {prof_wins}" if prof_wins else "  -",
        "",
        "- **What Went Well (Personal):**",
        f"  {personal_wins}" if personal_wins else "  -",
        "",
        "- **What Went Wrong / Will Correct:**",
        f"  {went_wrong}" if went_wrong else "  -",
        "",
        "- **Within My Control / Not:**",
        f"  {control}" if control else "  -",
        "",
        "- **Progress Toward Greater Goals:**",
        f"  {progress}" if progress else "  -",
        "",
        "- **Grateful For:**",
        f"  {gratitude}" if gratitude else "  -",
        "",
        "- **Tomorrow:**",
        f"  {tomorrow}" if tomorrow else "  -",
    ]
    return "\n".join(lines)


def _format_section(mode: str, answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    """Format answers into template structure (morning or evening) with timestamp."""
    if mode == "morning":
        return _format_morning_content(answers, user_id, orch)
    return _format_evening_content(answers, user_id, orch)


def _empty_morning_placeholder() -> str:
    """Placeholder when no morning content yet."""
    return "### 🌞 Morning\n\n- **Professional Objective:**\n  -\n\n- **Personal Objective:**\n  -\n\n- **Obstacle & Response:**\n  -\n\n- **Greater Goals:**\n  -\n\n- **Top 3 Priorities:**\n  1. -\n  2. -\n  3. -"


def _empty_evening_placeholder() -> str:
    """Placeholder when no evening content yet."""
    return "### 🌙 Evening\n\n- **Morning Priorities Completed?**\n  -\n\n- **What Went Well (Professional):**\n  -\n\n- **What Went Well (Personal):**\n  -\n\n- **What Went Wrong / Will Correct:**\n  -\n\n- **Within My Control / Not:**\n  -\n\n- **Progress Toward Greater Goals:**\n  -\n\n- **Grateful For:**\n  -\n\n- **Tomorrow:**\n  -"


def _build_full_body(
    body_template: str,
    date_str: str,
    morning_content: str,
    evening_content: str,
) -> str:
    return (
        body_template.replace("{{DATE}}", date_str)
        .replace("{{MORNING_CONTENT}}", morning_content or _empty_morning_placeholder())
        .replace("{{EVENING_CONTENT}}", evening_content or _empty_evening_placeholder())
    )


def _replace_section(body: str, new_section: str, mode: str) -> str:
    """Replace the morning/evening section in note body with new content."""
    import re

    pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
    flags = re.DOTALL

    if mode == "morning":
        # For morning, replace until we hit evening section or end
        replacement = re.sub(pattern, new_section.rstrip(), body, flags=flags)
    else:
        # For evening, replace until end of document
        replacement = re.sub(pattern, new_section.rstrip(), body, flags=flags)

    return replacement


async def _apply_replace_action(orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]) -> bool:
    """Apply the replace action for duplicate sections."""
    if state.get("pending_action") != "duplicate_detected":
        await message.reply_text("❌ No pending duplicate action. Use /stoic_done to save your reflection.")
        return False

    note_id = state.get("existing_note_id")
    existing_body = state.get("existing_body", "")
    new_section = state.get("new_section_content", "")
    mode = state.get("mode", "morning")

    if not note_id or not new_section:
        await message.reply_text("❌ Missing required information. Please try again.")
        return False

    try:
        new_body = _replace_section(existing_body, new_section, mode)
        await orch.joplin_client.update_note(note_id, {"body": new_body})
        logger.info("Stoic save: replaced %s section in note %s", mode, note_id)

        # Clear the pending action state
        state.pop("pending_action", None)
        state.pop("existing_note_id", None)
        state.pop("existing_body", None)
        state.pop("new_section_content", None)
        orch.state_manager.update_state(user_id, state)

        await message.reply_text(f"✅ Replaced {mode} reflection.")
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
        except Exception as exc:
            logger.debug("Could not schedule Joplin sync: %s", exc)
        return True
    except Exception as exc:
        logger.error("Failed to replace stoic section: %s", exc)
        await message.reply_text("❌ Failed to replace reflection.")
        return False


async def _apply_append_action(orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]) -> bool:
    """Apply the append action for duplicate sections."""
    if state.get("pending_action") != "duplicate_detected":
        await message.reply_text("❌ No pending duplicate action. Use /stoic_done to save your reflection.")
        return False

    note_id = state.get("existing_note_id")
    existing_body = state.get("existing_body", "")
    new_section = state.get("new_section_content", "")

    if not note_id or not new_section:
        await message.reply_text("❌ Missing required information. Please try again.")
        return False

    try:
        new_body = f"{existing_body}\n\n{new_section}"
        await orch.joplin_client.update_note(note_id, {"body": new_body})
        logger.info("Stoic save: appended section to note %s", note_id)

        # Clear the pending action state
        state.pop("pending_action", None)
        state.pop("existing_note_id", None)
        state.pop("existing_body", None)
        state.pop("new_section_content", None)
        orch.state_manager.update_state(user_id, state)

        await message.reply_text("✅ Appended reflection to today's note.")
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
        except Exception as exc:
            logger.debug("Could not schedule Joplin sync: %s", exc)
        return True
    except Exception as exc:
        logger.error("Failed to append stoic section: %s", exc)
        await message.reply_text("❌ Failed to append reflection.")
        return False


def _stoic_cancel(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)

        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text(
                "No active Stoic journal session to cancel. Use /stoic to start one."
            )
            return

        mode = state.get("mode", "morning")
        answer_count = len(state.get("answers", []))
        orch.state_manager.clear_state(user_id)
        logger.info("User %s cancelled Stoic journal session (%s mode, %d answers)", user_id, mode, answer_count)

        await update.message.reply_text(
            "❌ Stoic journal session cancelled. No changes were saved.\n\n"
            "Start a new session with /stoic, /stoic morning, or /stoic evening."
        )

    return handler


def _stoic_replace(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text(
                "❌ No active Stoic journal session with pending duplicate. "
                "Use /stoic_done first to see the duplicate options."
            )
            return

        logger.info("User %s executing /stoic_replace", user_id)
        saved = await _apply_replace_action(orch, user_id, update.message, state)
        if saved:
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                "✅ Stoic reflection saved.\n\n"
                "It's in *Areas → 📓 Journaling → Stoic Journal*. "
                "If you don't see it on your Mac, run /sync then sync in Joplin.\n\nMemento mori.",
                parse_mode="Markdown",
            )

    return handler


def _stoic_append(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text(
                "❌ No active Stoic journal session with pending duplicate. "
                "Use /stoic_done first to see the duplicate options."
            )
            return

        logger.info("User %s executing /stoic_append", user_id)
        saved = await _apply_append_action(orch, user_id, update.message, state)
        if saved:
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                "✅ Stoic reflection saved.\n\n"
                "It's in *Areas → 📓 Journaling → Stoic Journal*. "
                "If you don't see it on your Mac, run /sync then sync in Joplin.\n\nMemento mori.",
                parse_mode="Markdown",
            )

    return handler


def register_stoic_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    application.add_handler(CommandHandler("stoic", _stoic(orch)))
    application.add_handler(CommandHandler("stoic_done", _stoic_done(orch)))
    application.add_handler(CommandHandler("stoic_cancel", _stoic_cancel(orch)))
    application.add_handler(CommandHandler("stoic_replace", _stoic_replace(orch)))
    application.add_handler(CommandHandler("stoic_append", _stoic_append(orch)))


def _stoic(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        mode = "morning"
        if context.args:
            arg = (context.args[0] or "").strip().lower()
            if arg in ("morning", "evening"):
                mode = arg

        state = orch.state_manager.get_state(user_id)
        if state and state.get("active_persona") == "STOIC_JOURNAL":
            await update.message.reply_text(
                "📓 You already have a Stoic journal session.\n\n"
                "Options:\n"
                "  Keep replying with more answers\n"
                "  /stoic_done - Save your reflection\n"
                "  /stoic_cancel - Cancel and start over"
            )
            return

        morning_q, evening_q, body_tpl = _load_stoic_template()
        questions = morning_q if mode == "morning" else evening_q
        if not questions:
            await update.message.reply_text("No questions configured for this mode.")
            return

        session_start = get_user_timezone_aware_now(user_id, orch.logging_service)
        new_state: dict[str, Any] = {
            "active_persona": "STOIC_JOURNAL",
            "session_start": session_start.isoformat(),
            "mode": mode,
            "questions": questions,
            "answers": [],
            "body_template": body_tpl,
            "morning_questions": morning_q,
            "evening_questions": evening_q,
        }
        orch.state_manager.update_state(user_id, new_state)
        logger.info("User %s started Stoic journal (%s), %d questions", user_id, mode, len(questions))
        await update.message.reply_text(
            f"📓 *Stoic Journal — {mode.capitalize()}*\n\n{questions[0]}",
            parse_mode="Markdown",
        )

    return handler


def _stoic_done(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            logger.info("User %s called /stoic_done but no active session", user_id)
            await update.message.reply_text(
                "No active Stoic journal session. Use /stoic or /stoic morning or /stoic evening to start."
            )
            return

        logger.info("User %s finishing Stoic session (%s answers)", user_id, len(state.get("answers", [])))
        await update.message.reply_text("📓 Saving to Stoic Journal...")
        saved = await _finish_stoic_session(orch, user_id, update.message, state)
        if saved:
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                "✅ Stoic reflection saved.\n\n"
                "It’s in *Areas → 📓 Journaling → Stoic Journal*. "
                "If you don’t see it on your Mac, run /sync then sync in Joplin.\n\nMemento mori.",
                parse_mode="Markdown",
            )

    return handler


def _check_section_exists(note_body: str, mode: str) -> bool:
    """Check if morning/evening section already exists with REAL content (not just placeholder)."""
    import re

    # Find the section
    pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
    match = re.search(pattern, note_body, re.DOTALL)

    if not match:
        return False

    section = match.group(0)

    # Check if section has actual content (not just empty placeholders)
    # Empty placeholder: "- **Wins:**\n  -" or "- **Wins:**\n  - " (with just dash)
    # Real content: "- **Wins:**\n  - Completed task"
    lines = section.split("\n")

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip section header (e.g., "### 🌙 Evening")
        if stripped.startswith("###"):
            continue

        # Skip section labels (e.g., "- **Wins:**", "- **Challenges:**")
        if stripped.startswith("- **") and stripped.endswith(":**"):
            continue

        # Skip empty bullet points (just "-" or nothing after dash)
        if stripped == "-":
            continue

        # Any other line is real content
        return True

    # Only found header and labels, no real content
    return False


async def _finish_stoic_session(
    orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]
) -> bool:
    mode = state.get("mode", "morning")
    answers = state.get("answers", [])
    body_template = state.get("body_template") or ""
    if not body_template.strip():
        _, __, body_template = _load_stoic_template()

    date_str = get_current_date_str(user_id, orch.logging_service)
    title = f"{date_str} - Daily Stoic Reflection"

    if not answers:
        await message.reply_text(
            "No answers to save. Use /stoic_cancel to exit, or start a new session with /stoic."
        )
        return False

    await message.reply_text("📝 Formatting reflection...")
    section_content = None
    try:
        section_content = await orch.llm_orchestrator.format_stoic_reflection(mode, answers)
    except Exception as exc:
        logger.debug("Stoic LLM format failed, using rule-based: %s", exc)
    if not section_content:
        section_content = _format_section(mode, answers, user_id, orch)
    logger.info("Stoic save: formatted %s reflection, %d answers", mode, len(answers))

    await message.reply_text("📂 Finding Stoic Journal folder...")
    try:
        folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
    except Exception as exc:
        logger.error("Stoic Journal folder resolution failed: %s", exc)
        await message.reply_text("❌ Could not find or create Stoic Journal folder.")
        return False

    notes_in_folder = await orch.joplin_client.get_notes_in_folder(folder_id)
    existing = next((n for n in notes_in_folder if n.get("title") == title), None)

    tags = STOIC_TAGS + [mode]

    if existing:
        await message.reply_text("📎 Updating today's note...")
        note_id = existing["id"]
        try:
            full_note = await orch.joplin_client.get_note(note_id)
            existing_body = (full_note.get("body") or "").strip()
        except Exception as exc:
            logger.error("Failed to fetch existing note body for update: %s", exc)
            await message.reply_text(
                "❌ Could not fetch your existing note for updating. "
                "This is a safety measure to prevent data loss. "
                "Please try again or contact support if the problem persists."
            )
            return False

        # Debug logging for data loss investigation
        logger.info("BF-008 DEBUG: mode=%s, existing_body length=%d", mode, len(existing_body))
        logger.info("BF-008 DEBUG: existing has Morning: %s", "### 🌞 Morning" in existing_body)
        logger.info("BF-008 DEBUG: existing has Evening: %s", "### 🌙 Evening" in existing_body)

        # Check for duplicate sections with REAL content
        if _check_section_exists(existing_body, mode):
            await message.reply_text(
                f"⚠️ You already have a {mode.capitalize()} reflection for today.\n\n"
                f"What would you like to do?\n"
                f"  /stoic_replace - Replace the existing reflection\n"
                f"  /stoic_append - Add another reflection to the note"
            )
            # Store state for pending action
            state["pending_action"] = "duplicate_detected"
            state["existing_note_id"] = note_id
            state["existing_body"] = existing_body
            state["new_section_content"] = section_content
            orch.state_manager.update_state(user_id, state)
            return False

        # No real content found - either replace empty placeholder or append
        # Check if section exists at all (even if empty)
        import re
        pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
        section_exists_empty = bool(re.search(pattern, existing_body, re.DOTALL))

        if section_exists_empty:
            # Section exists but is empty - replace the placeholder
            new_body = _replace_section(existing_body, section_content, mode)
            logger.info("BF-008 DEBUG: Replaced empty %s placeholder", mode)
        else:
            # Section doesn't exist at all - append
            new_body = f"{existing_body}\n\n{section_content}" if existing_body else section_content
            logger.info("BF-008 DEBUG: Appended %s section", mode)

        # Debug logging for data loss investigation
        logger.info("BF-008 DEBUG: new_body length=%d", len(new_body))
        logger.info("BF-008 DEBUG: new has Morning: %s", "### 🌞 Morning" in new_body)
        logger.info("BF-008 DEBUG: new has Evening: %s", "### 🌙 Evening" in new_body)

        try:
            await orch.joplin_client.update_note(note_id, {"body": new_body})
        except Exception as exc:
            logger.error("Failed to update Stoic note %s: %s", note_id, exc)
            await message.reply_text("❌ Failed to update today's note.")
            return False
        await orch.joplin_client.apply_tags(note_id, tags)
        logger.info("Stoic save: updated note %s (%s)", note_id, title)
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
            await message.reply_text("🔄 Syncing so it appears on your devices...")
        except Exception as exc:
            logger.debug("Could not schedule Joplin sync after Stoic save: %s", exc)
        return True
    else:
        await message.reply_text("📄 Creating new note...")
        morning_content = section_content if mode == "morning" else ""
        evening_content = section_content if mode == "evening" else ""
        full_body = _build_full_body(body_template, date_str, morning_content, evening_content)
        try:
            note_id = await orch.joplin_client.create_note(
                folder_id=folder_id,
                title=title,
                body=full_body,
            )
            await orch.joplin_client.apply_tags(note_id, tags)
        except Exception as exc:
            logger.error("Failed to create Stoic note: %s", exc)
            await message.reply_text("❌ Failed to create note in Stoic Journal.")
            return False
        logger.info("Stoic save: created note %s in folder %s (%s)", note_id, folder_id, title)
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
            await message.reply_text("🔄 Syncing so it appears on your devices...")
        except Exception as exc:
            logger.debug("Could not schedule Joplin sync after Stoic save: %s", exc)
        return True


async def handle_stoic_message(
    orch: TelegramOrchestrator, user_id: int, text: str, message: Message
) -> None:
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "STOIC_JOURNAL":
        return

    text_stripped = (text or "").strip().lower()
    if text_stripped in ("done", "save", "finish"):
        await message.reply_text("Use /stoic_done to save your reflection.")
        return

    mode = state.get("mode", "morning")
    # Always get questions from template so we never rely on persisted list
    morning_q, evening_q, body_tpl = _load_stoic_template()
    questions = morning_q if mode == "morning" else evening_q
    state["questions"] = questions
    state["body_template"] = body_tpl

    answers = list(state.get("answers", []))
    current_index = len(answers)
    question_text = questions[current_index] if current_index < len(questions) else "Additional thought"
    answers.append({"q": question_text, "a": text})
    state["answers"] = answers
    orch.state_manager.update_state(user_id, state)

    next_index = len(answers)
    if next_index < len(questions):
        await message.reply_text(questions[next_index])
    else:
        await message.reply_text(
            "Anything else? Reply with more, or /stoic_done to save to your Stoic Journal."
        )
