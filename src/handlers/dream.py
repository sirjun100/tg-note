"""
Jungian Dream Analysis handlers: /dream, /dream_done, /dream_cancel.

Guided dream analysis with symbolic image generation and life associations.
Sprint 11 Story 3 - FR-025.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.handlers.core import _schedule_joplin_sync
from src.security_utils import check_whitelist, format_error_message, split_message_for_telegram
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

# Pending image generation tasks (user_id -> Task). Not persisted in state.
_pending_dream_image_tasks: dict[int, asyncio.Task] = {}

DREAM_JOURNAL_PATH = ["01 - Areas", "📓 Journaling", "Dream Journal"]
DREAM_TAGS = ["dream-journal", "jungian"]
DREAM_DISCLAIMER = (
    "\n\n🌙 *Note: This analysis is for self-reflection and personal growth. "
    "It is not a substitute for professional psychological support. "
    "If your dreams are causing distress, please consult a qualified therapist.*"
)


def _strip_dream_title_from_analysis(analysis_text: str) -> str:
    """Remove the Dream Title line from analysis so it's not duplicated in the note body."""
    return re.sub(
        r"\n*\*\*Dream Title:\*\*[^\n]*(?:\n|$)",
        "\n",
        analysis_text,
        flags=re.IGNORECASE,
    ).strip()


def _extract_dream_title(analysis_text: str, dream_text: str) -> str:
    """Extract short clever title from analysis, or derive from dream text."""
    # Look for **Dream Title:** or Dream Title: followed by the title
    match = re.search(
        r"\*\*Dream Title:\*\*\s*(.+?)(?:\n|$)",
        analysis_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        match = re.search(r"Dream Title:\s*(.+?)(?:\n|$)", analysis_text, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Remove markdown, limit length
        title = re.sub(r"\*+", "", title).strip()
        if len(title) <= 60:
            return title
    # Fallback: first ~40 chars of dream, cleaned
    first_line = dream_text.split("\n")[0].strip()[:50]
    return first_line + "…" if len(first_line) >= 50 else first_line or "Dream"


def _extract_symbols_from_analysis(analysis_text: str) -> list[str]:
    """Extract symbol names from Key Symbols section (• Symbol - Interpretation)."""
    symbols: list[str] = []
    in_section = False
    for line in analysis_text.splitlines():
        line = line.strip()
        if "**Key Symbols:**" in line or "Key Symbols:" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("**") and ":" in line:
                break
            if line.startswith("•") or line.startswith("-"):
                part = line.lstrip("•- ").split(" - ", 1)[0].strip()
                if part and len(part) < 80:
                    symbols.append(part)
    return symbols[:5]


def _build_dream_note_body(
    dream_text: str,
    analysis: str,
    associations: str,
    resource_id: str | None,
    user_id: int,
    orch: TelegramOrchestrator,
) -> str:
    """Build dream journal note body. Image goes right after title (at top)."""
    lines: list[str] = []
    # Image first, right after the note title
    if resource_id:
        lines.extend([
            "![Dream symbolic image](:/" + resource_id + ")",
            "",
        ])
    lines.extend(["## The Dream", "", dream_text, "", "## Jungian Analysis", "", analysis, ""])
    if associations:
        lines.extend(["## Life Associations", "", associations, ""])
    lines.extend(["---", "*Analysis generated with Jungian AI Assistant*"])
    return "\n".join(lines)


async def handle_dream_message(
    orch: TelegramOrchestrator,
    user_id: int,
    text: str,
    message: Any,
) -> None:
    """Handle incoming message when user is in DREAM_ANALYST session."""
    logger.debug("Dream message: user=%d phase=checking", user_id)
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "DREAM_ANALYST":
        return

    phase = state.get("phase", "dream_description")
    logger.debug("Dream message: user=%d phase=%s len=%d", user_id, phase, len(text or ""))
    text_lower = text.strip().lower()

    if phase == "dream_description":
        if len(text.strip()) < 20:
            await message.reply_text(
                "Please share more detail about your dream. "
                "The richer your description, the more meaningful the analysis. "
                "What happened? Who was there? What did you see, hear, feel?"
            )
            return

        state["dream_text"] = text.strip()
        state["phase"] = "analyzing"
        orch.state_manager.update_state(user_id, state)
        logger.info("Dream: user=%d starting analysis (dream len=%d)", user_id, len(text.strip()))

        status_msg = await message.reply_text(
            "🔮 Analyzing your dream... This may take 30–60 seconds. "
            "I'm identifying symbols, archetypes, and themes."
        )
        from src.dream_image import generate_dream_image

        async def _send_progress_updates() -> None:
            """Send typing indicator and status edits while LLM runs."""
            updates = [
                (15, "📖 Identifying symbols and themes..."),
                (30, "🔍 Exploring archetypes and meanings..."),
                (45, "🎨 Almost done, preparing your analysis..."),
            ]
            for delay, text in updates:
                await asyncio.sleep(delay)
                try:
                    await message.chat.send_action("typing")
                    await status_msg.edit_text(text)
                except Exception:
                    pass

        analysis_prompt = (
            f"Analyze this dream from a Jungian perspective. "
            f"Provide: Key Symbols, Archetypes Present, Shadow Elements, Overall Theme.\n\n"
            f"Dream:\n{text.strip()}\n\n"
            f"At the very end of your response, add exactly one line:\n"
            f"**Dream Title:** [a short, clever 3-7 word phrase that captures the dream's essence]"
        )
        analysis_response = None
        progress_task = asyncio.create_task(_send_progress_updates())
        try:
            analysis_response = await orch.llm_orchestrator.process_message(
                analysis_prompt,
                persona="jungian_analyst",
            )
        except Exception as exc:
            progress_task.cancel()
            logger.error("Dream analysis LLM failed: %s", exc)
            state["phase"] = "dream_description"
            orch.state_manager.update_state(user_id, state)
            await message.reply_text(format_error_message("Analysis failed. Please try again."))
            return
        finally:
            progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress_task

        with contextlib.suppress(Exception):
            await status_msg.edit_text("📖 Preparing your analysis...")

        analysis = ""
        if analysis_response and analysis_response.question:
            analysis = analysis_response.question
        elif analysis_response and analysis_response.note and analysis_response.note.get("body"):
            analysis = analysis_response.note["body"]
        if not analysis:
            analysis = "Analysis could not be generated. Please try again with more detail."

        state["interpretation"] = analysis
        symbols = _extract_symbols_from_analysis(analysis)
        symbols = symbols or ["dream", "symbol", "unconscious"]

        # Run image generation in background so user gets analysis immediately
        state["dream_image_url"] = None
        state["phase"] = "association_prompt"
        orch.state_manager.update_state(user_id, state)

        async def _generate_and_send_image() -> None:
            try:
                image_url = await generate_dream_image(text.strip(), symbols)
                state["dream_image_url"] = image_url
                orch.state_manager.update_state(user_id, state)
                if image_url:
                    try:
                        data = image_url.split(",", 1)[1] if "," in image_url else ""
                        if data:
                            image_bytes = base64.b64decode(data)
                            await message.reply_photo(photo=BytesIO(image_bytes))
                    except Exception as exc:
                        logger.warning("Failed to send dream image: %s", exc)
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning("Dream image generation failed: %s", exc)
            finally:
                _pending_dream_image_tasks.pop(user_id, None)

        _pending_dream_image_tasks[user_id] = asyncio.create_task(_generate_and_send_image())

        # Send analysis immediately without waiting for image
        # BF-014/BF-016: LLM analysis contains Markdown chars (*, _, etc.) that break
        # Telegram's parser. Always send as plain text (no parse_mode) to avoid parse errors.
        # BF-019: Split long messages — Telegram limit is 4096 chars.
        msg = f"📖 Jungian Analysis\n\n{analysis}\n\n---\n\n"
        msg += "Would you like to explore how this dream connects to your current life? (yes/no)"
        msg += DREAM_DISCLAIMER
        for chunk in split_message_for_telegram(msg):
            await message.reply_text(chunk)
        await message.reply_text("🎨 Creating your symbolic image... (will arrive shortly)")
        logger.info("Dream: user=%d analysis sent, image generating in background", user_id)
        return

    if phase == "association_prompt":
        if text_lower in ("yes", "y"):
            state["phase"] = "association"
            orch.state_manager.update_state(user_id, state)
            await message.reply_text(
                "Let's connect this dream to your waking life.\n\n"
                "🔮 Reflection Questions:\n\n"
                "1. What current situation in your life feels similar to something in the dream?\n"
                "2. Which symbol or archetype resonates most with you right now?\n"
                "3. Is there something you're avoiding or seeking that the dream might point to?\n\n"
                "Take your time. Share what resonates. When you're done, type /dream_done to save."
            )
        elif text_lower in ("no", "n"):
            state["phase"] = "ready_to_save"
            state["associations"] = ""
            orch.state_manager.update_state(user_id, state)
            await message.reply_text(
                "No problem. Type /dream_done when you're ready to save this analysis."
            )
        else:
            await message.reply_text("Please reply with yes or no.")

        return

    if phase == "association":
        state["associations"] = state.get("associations", "") + "\n\n" + text.strip()
        state["phase"] = "ready_to_save"
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            "Thank you for sharing. Type /dream_done to save this analysis to your Dream Journal."
        )


async def _save_dream_to_joplin(orch: TelegramOrchestrator, user_id: int, state: dict) -> bool:
    """Save dream analysis to Joplin. Returns True on success."""
    # If image is still generating, wait up to 15s for it
    task = _pending_dream_image_tasks.get(user_id)
    if task and not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=15.0)
            state = orch.state_manager.get_state(user_id) or state
        except TimeoutError:
            logger.debug("Dream image still generating at save time; saving without image")
    _pending_dream_image_tasks.pop(user_id, None)

    dream_text = state.get("dream_text", "")
    interpretation = state.get("interpretation", "")
    associations = state.get("associations", "").strip()
    image_url = state.get("dream_image_url")

    if not dream_text or not interpretation:
        return False

    resource_id: str | None = None
    if image_url and "," in image_url:
        try:
            header, b64_data = image_url.split(",", 1)
            mime = "image/png"
            if "image/" in header:
                mime = header.split(":", 1)[1].split(";", 1)[0].strip()
            image_bytes = base64.b64decode(b64_data)
            resource = await orch.joplin_client.create_resource(
                image_bytes,
                filename="dream_symbolic.png",
                mime_type=mime,
            )
            resource_id = resource.get("id")
        except Exception as exc:
            logger.warning("Failed to create dream image resource: %s", exc)

    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    date_str = now.strftime("%Y-%m-%d")
    dream_title = _extract_dream_title(interpretation, dream_text)
    interpretation_clean = _strip_dream_title_from_analysis(interpretation)
    title = f"{date_str} - {dream_title}"

    body = _build_dream_note_body(
        dream_text, interpretation_clean, associations, resource_id, user_id, orch
    )

    folder_id = await orch.joplin_client.get_or_create_folder_by_path(DREAM_JOURNAL_PATH)
    note_id = await orch.joplin_client.create_note(
        folder_id, title, body, image_data_url=None
    )
    await orch.joplin_client.apply_tags(note_id, DREAM_TAGS)
    _schedule_joplin_sync()
    return True


def register_dream_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register dream analysis handlers."""

    async def dream_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Dream command received")
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            logger.warning("Dream command: missing user or message")
            return
        if not check_whitelist(user.id):
            logger.info("Dream command: user %d not whitelisted", user.id)
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = {
            "active_persona": "DREAM_ANALYST",
            "phase": "dream_description",
            "dream_text": "",
            "dream_image_url": "",
            "interpretation": "",
            "associations": "",
        }
        try:
            orch.state_manager.update_state(user.id, state)
            logger.info("Dream command: state updated for user %d", user.id)
        except Exception as exc:
            logger.error("Dream command: state update failed for user %d: %s", user.id, exc, exc_info=True)
            await msg.reply_text(format_error_message("Could not start dream session. Please try again."))
            return

        # BF-017: Use plain text for welcome — Markdown parse_mode can cause BadRequest
        # (similar to BF-010, BF-014). Plain text avoids parse errors entirely.
        welcome = (
            "🌙 Welcome to Dream Analysis\n\n"
            "Take a moment to recall your dream...\n\n"
            "When you're ready, describe everything you remember:\n"
            "• What happened?\n"
            "• Who was there?\n"
            "• What did you see, hear, feel?\n"
            "• Any symbols, colors, or unusual elements?\n\n"
            "Take your time. The more detail, the richer the analysis.\n\n"
            "Type /dream_cancel to cancel anytime."
        )
        await msg.reply_text(welcome)
        logger.info("Dream session started for user %d", user.id)

    async def dream_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Dream done command received")
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            logger.warning("Dream done: missing user or message")
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        logger.debug("Dream done: user=%d state=%s", user.id, "present" if state else "none")
        if not state or state.get("active_persona") != "DREAM_ANALYST":
            await msg.reply_text("You don't have an active dream session. Use /dream to start one.")
            return

        if state.get("phase") == "dream_description":
            await msg.reply_text("Please describe your dream first before saving.")
            return

        try:
            logger.info("Dream done: user=%d saving to Joplin", user.id)
            await msg.reply_text("📝 Saving to your Dream Journal...")
            ok = await _save_dream_to_joplin(orch, user.id, state)
            orch.state_manager.clear_state(user.id)
            if ok:
                await msg.reply_text(
                    "✅ Dream analysis saved to your Dream Journal. "
                    "Syncing to your other devices…"
                )
                logger.info("Dream done: user=%d saved successfully", user.id)
            else:
                await msg.reply_text(format_error_message("Failed to save. Please try again."))
                logger.warning("Dream done: user=%d save returned False", user.id)
        except Exception as exc:
            logger.error("Dream save failed for user %d: %s", user.id, exc, exc_info=True)
            await msg.reply_text(format_error_message("Failed to save. Please try again."))

    async def dream_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Dream cancel command received")
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == "DREAM_ANALYST":
            task = _pending_dream_image_tasks.pop(user.id, None)
            if task and not task.done():
                task.cancel()
            orch.state_manager.clear_state(user.id)
            await msg.reply_text("Dream session cancelled. Nothing was saved.")
        else:
            await msg.reply_text("No active dream session to cancel.")

    application.add_handler(CommandHandler("dream", dream_cmd))
    application.add_handler(CommandHandler("dream_done", dream_done_cmd))
    application.add_handler(CommandHandler("dream_cancel", dream_cancel_cmd))
    logger.info("Dream handlers registered")
