"""
Read Later queue handlers: /readlater, /rl, /reading.

Sprint 11 Story 2 - FR-028.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.reading_service import (
    add_to_queue,
    delete_from_queue,
    get_queue,
    get_random_unread,
    get_stats,
    mark_as_read,
)
from src.security_utils import check_whitelist, format_error_message, format_success_message
from src.url_enrichment import URL_PATTERN

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

READING_STATE_KEY = "reading_queue_items"


def _format_relative_time(saved_at: datetime | None) -> str:
    """Format saved_at as relative time (e.g. '2 days ago')."""
    if not saved_at:
        return "Unknown"
    now = datetime.now(datetime.UTC)
    dt = saved_at.replace(tzinfo=datetime.UTC) if saved_at.tzinfo is None else saved_at
    delta = now - dt
    days = delta.days
    if days == 0:
        return "Today"
    if days == 1:
        return "1 day ago"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "1 week ago"
    if days < 30:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def register_reading_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register read-later and reading queue handlers."""
    application.add_handler(CommandHandler("readlater", _readlater_cmd(orch)))
    application.add_handler(CommandHandler("rl", _readlater_cmd(orch)))
    application.add_handler(CommandHandler("reading", _reading_cmd(orch)))
    logger.info("Reading handlers registered")


def _readlater_cmd(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        text = " ".join(context.args) if context.args else ""
        urls = URL_PATTERN.findall(text)
        if not urls:
            await msg.reply_text(
                "📚 **Read Later**\n\n"
                "Usage: `/readlater <url>` or `/rl <url>`\n"
                "Example: `/rl https://example.com/article`",
                parse_mode="Markdown",
            )
            return

        url = urls[0]
        await msg.reply_text("📚 Fetching article...")
        try:
            result = await add_to_queue(orch.joplin_client, url, datetime.utcnow())
            if result.get("duplicate"):
                await msg.reply_text(
                    format_success_message(f"Already in queue: {result.get('title', 'Untitled')}")
                )
            else:
                await msg.reply_text(
                    format_success_message(f"Added: {result.get('title', 'Untitled')}")
                )
        except Exception as exc:
            logger.error("Read later failed for %s: %s", url, exc)
            await msg.reply_text(format_error_message("Failed to add to reading queue. Please try again."))

    return handler


def _reading_cmd(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        args = (context.args or [])
        sub = (args[0] or "").lower() if args else ""
        page = 1
        if len(args) >= 2 and args[-1].isdigit():
            page = max(1, int(args[-1]))

        if sub == "done" and len(args) >= 2:
            idx_str = args[1]
            if idx_str.isdigit():
                idx = int(idx_str)
                items, _ = await get_queue(orch.joplin_client, unread_only=True, page=1)
                state_items = (orch.state_manager.get_state(user.id) or {}).get(READING_STATE_KEY) or []
                resolved = state_items if state_items else items
                if 1 <= idx <= len(resolved):
                    note_id = resolved[idx - 1].get("id")
                    if note_id:
                        ok = await mark_as_read(orch.joplin_client, note_id)
                        if ok:
                            await msg.reply_text(format_success_message("Marked as read ✓"))
                        else:
                            await msg.reply_text(format_error_message("Could not mark as read."))
                    else:
                        await msg.reply_text(format_error_message("Invalid item."))
                else:
                    await msg.reply_text(format_error_message("Invalid number. Use /reading to see the queue."))
            else:
                await msg.reply_text("Usage: `/reading done <number>`", parse_mode="Markdown")
            return

        if sub == "delete" and len(args) >= 2:
            idx_str = args[1]
            if idx_str.isdigit():
                idx = int(idx_str)
                items, _ = await get_queue(orch.joplin_client, unread_only=False, page=1)
                state_items = (orch.state_manager.get_state(user.id) or {}).get(READING_STATE_KEY) or []
                resolved = state_items if state_items else items
                if 1 <= idx <= len(resolved):
                    note_id = resolved[idx - 1].get("id")
                    if note_id:
                        ok = await delete_from_queue(orch.joplin_client, note_id)
                        if ok:
                            await msg.reply_text(format_success_message("Removed from queue."))
                        else:
                            await msg.reply_text(format_error_message("Could not delete."))
                    else:
                        await msg.reply_text(format_error_message("Invalid item."))
                else:
                    await msg.reply_text(format_error_message("Invalid number."))
            else:
                await msg.reply_text("Usage: `/reading delete <number>`", parse_mode="Markdown")
            return

        if sub == "random":
            item = await get_random_unread(orch.joplin_client)
            if not item:
                await msg.reply_text("📚 Your reading queue is empty. Add articles with /readlater <url>")
                return
            title = item.get("title") or "Untitled"
            domain = item.get("domain") or ""
            await msg.reply_text(
                f"📚 **Random pick**\n\n"
                f"**{title}**\n"
                f"_{domain}_\n\n"
                f"Use /reading to see the full queue.",
                parse_mode="Markdown",
            )
            return

        if sub == "stats":
            stats = await get_stats(orch.joplin_client)
            await msg.reply_text(
                f"📚 **Reading Queue Stats**\n\n"
                f"• Unread: {stats['unread']}\n"
                f"• Read: {stats['read']}\n"
                f"• Total: {stats['total']}",
                parse_mode="Markdown",
            )
            return

        unread_only = sub != "all"
        items, total = await get_queue(orch.joplin_client, unread_only=unread_only, page=page)

        current = orch.state_manager.get_state(user.id) or {}
        current[READING_STATE_KEY] = items
        orch.state_manager.update_state(user.id, current)

        if not items:
            await msg.reply_text(
                "📚 Your reading queue is empty. Add articles with /readlater <url>"
            )
            return

        label = "unread" if unread_only else "total"
        lines = [f"📚 **Reading Queue** ({total} {label})\n"]
        for i, it in enumerate(items, 1):
            title = it.get("title") or "Untitled"
            domain = it.get("domain") or ""
            summary = (it.get("summary") or "")[:100]
            if len(it.get("summary") or "") > 100:
                summary += "..."
            saved = _format_relative_time(it.get("saved_at"))
            lines.append(f"{i}️⃣ **{title}**")
            lines.append(f"   _{domain} • Saved {saved}_")
            if summary:
                lines.append(f"   {summary}")
            lines.append("")
        lines.append("Reply with number to open, or `/reading done <number>` to mark as read.")
        if total > 5:
            lines.append(f"Page {page}. Use `/reading {'all' if unread_only else ''} {page + 1}` for more.")
        await msg.reply_text("\n".join(lines), parse_mode="Markdown")

    return handler
