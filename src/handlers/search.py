"""
Search handlers: /find and /search for quick note lookup.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

CONTEXT_CHARS = 80
MAX_RESULTS = 5


def _extract_snippet(body: str, query: str, context_chars: int = CONTEXT_CHARS) -> str:
    """Extract a snippet around the first match of query in body."""
    if not body:
        return ""
    body_lower = body.lower()
    query_lower = query.lower()
    pos = body_lower.find(query_lower)
    if pos == -1:
        return (body[: context_chars * 2] + "...") if len(body) > context_chars * 2 else body
    start = max(0, pos - context_chars)
    end = min(len(body), pos + len(query) + context_chars)
    snippet = body[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(body):
        snippet = snippet + "..."
    return snippet


def register_search_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    application.add_handler(CommandHandler("find", _find(orch)))
    application.add_handler(CommandHandler("search", _find(orch)))


def _find(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not update.message:
            return
        from src.security_utils import check_whitelist

        if not check_whitelist(user.id):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        query = " ".join(context.args) if context.args else ""

        if not query:
            await update.message.reply_text(
                "🔍 **Search Notes**\n\n"
                "Usage: `/find <query>` or `/search <query>`\n"
                "Example: `/find meeting notes`",
                parse_mode="Markdown",
            )
            return

        try:
            results = await orch.joplin_client.search_notes(query, limit=MAX_RESULTS)
        except Exception as exc:
            logger.error("Search failed for user %d: %s", user.id, exc)
            await update.message.reply_text("❌ Search failed. Please try again.")
            return

        if not results:
            await update.message.reply_text(
                f'No notes found for "{query}".\nTry different keywords or check spelling.'
            )
            return

        folders = await orch.joplin_client.get_folders()
        folder_by_id = {f.get("id"): f.get("title") or "Unknown" for f in folders}

        lines = [f'🔍 **Search results for "{query}"** ({len(results)} found)\n"]

        for i, note in enumerate(results, 1):
            title = note.get("title") or "(Untitled)"
            parent_id = note.get("parent_id") or ""
            folder_name = folder_by_id.get(parent_id, "Unknown")
            body = note.get("body") or ""
            snippet = _extract_snippet(body, query)
            if snippet:
                snippet = re.sub(r"\s+", " ", snippet).strip()
            lines.append(f"{i}️⃣ **{title}**")
            lines.append(f"   📁 {folder_name}")
            if snippet:
                lines.append(f"   _{snippet}_")
            lines.append("")

        lines.append("Reply with the number to view full note, or search again.")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        orch.state_manager.update_state(
            user.id,
            {
                "active_persona": "SEARCH",
                "search_results": [
                    {"id": n.get("id"), "title": n.get("title") or "(Untitled)"}
                    for n in results
                ],
            },
        )
        logger.info("Search '%s' returned %d results for user %d", query[:30], len(results), user.id)

    return handler


async def handle_search_selection(
    orch: TelegramOrchestrator,
    user_id: int,
    text: str,
    message: Any,
) -> None:
    """Handle reply with number (1–5) to view selected search result. Clears state when done."""
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "SEARCH":
        return
    results = state.get("search_results") or []
    if not results:
        orch.state_manager.clear_state(user_id)
        return

    stripped = text.strip()
    if not stripped.isdigit():
        await message.reply_text("Reply with a number (1–5) to view that note, or run /find again.")
        return

    idx = int(stripped)
    if idx < 1 or idx > len(results):
        await message.reply_text(
            f"Please reply with a number between 1 and {len(results)}."
        )
        return

    note_ref = results[idx - 1]
    note_id = note_ref.get("id")
    if not note_id:
        orch.state_manager.clear_state(user_id)
        await message.reply_text("Invalid selection.")
        return

    try:
        note = await orch.joplin_client.get_note(note_id)
    except Exception as exc:
        logger.error("Failed to fetch note %s for user %d: %s", note_id, user_id, exc)
        orch.state_manager.clear_state(user_id)
        await message.reply_text("❌ Could not load that note.")
        return

    orch.state_manager.clear_state(user_id)

    title = note.get("title") or "(Untitled)"
    body = (note.get("body") or "").strip()
    preview = body[:2000] + "..." if len(body) > 2000 else body
    if preview:
        await message.reply_text(f"📄 {title}\n\n{preview}")
    else:
        await message.reply_text(f"📄 {title}\n\n(empty)")
