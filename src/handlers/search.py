"""
Search handlers: /find and /search for quick note lookup.
"""

from __future__ import annotations

import html
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


def _search_html_to_plain(html_text: str) -> str:
    """Strip HTML tags for plain-text fallback (BF-022)."""
    out = re.sub(r"</?b>", "", html_text)
    out = re.sub(r"</?i>", "", out)
    return out.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


async def _send_search_results_safe(message: Any, msg_html: str) -> None:
    """Send search results with HTML; fall back to plain text on parse/send error (BF-022)."""
    plain = _search_html_to_plain(msg_html)
    try:
        await message.reply_text(msg_html, parse_mode="HTML")
    except Exception as exc:
        exc_str = str(exc).lower()
        exc_type = type(exc).__name__
        is_parse_error = (
            "parse" in exc_str
            or "entities" in exc_str
            or "badrequest" in exc_type.lower()
        )
        logger.warning(
            "Search results send failed (%s), falling back to plain text: %s",
            "parse" if is_parse_error else "other",
            exc,
        )
        try:
            await message.reply_text(plain)
        except Exception as fallback_exc:
            logger.error("Search results plain fallback also failed: %s", fallback_exc)
            raise exc from fallback_exc


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
            await update.message.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        query = " ".join(context.args) if context.args else ""

        if not query:
            await update.message.reply_text(
                "🔍 <b>搜索笔记</b>\n\n"
                "用法：/find &lt;查询&gt; 或 /search &lt;查询&gt;\n"
                "示例：/find 会议笔记",
                parse_mode="HTML",
            )
            return

        try:
            results = await orch.joplin_client.search_notes(query, limit=MAX_RESULTS)
        except Exception as exc:
            logger.error("Search failed for user %d: %s", user.id, exc)
            await update.message.reply_text("❌ 搜索失败。请重试。")
            return

        if not results:
            await update.message.reply_text(
                f"没有找到包含 '{query}' 的笔记。请尝试不同的关键词或检查拼写。"
            )
            return

        # BF-022: get_folders can fail (timeout, Joplin down); use empty map on error
        try:
            folders = await orch.joplin_client.get_folders()
            folder_by_id = {f.get("id"): f.get("title") or "未知" for f in folders}
        except Exception as exc:
            logger.warning("get_folders failed for search, using Unknown for folders: %s", exc)
            folder_by_id = {}

        # BF-022: Use HTML + escape to avoid Markdown parse errors from user content
        q_esc = html.escape(query)
        lines = [f"🔍 <b>'{q_esc}' 的搜索结果</b>（找到 {len(results)} 个）\n"]

        for i, note in enumerate(results, 1):
            title = note.get("title") or "(无标题)"
            parent_id = note.get("parent_id") or ""
            folder_name = folder_by_id.get(parent_id, "未知")
            body = note.get("body") or ""
            snippet = _extract_snippet(body, query)
            if snippet:
                snippet = re.sub(r"\s+", " ", snippet).strip()
            title_esc = html.escape(title)
            folder_esc = html.escape(folder_name)
            lines.append(f"{i}️⃣ <b>{title_esc}</b>")
            lines.append(f"   📁 {folder_esc}")
            if snippet:
                snippet_esc = html.escape(snippet)
                lines.append(f"   <i>{snippet_esc}</i>")
            lines.append("")

        lines.append("回复数字查看完整笔记，或再次搜索。")
        msg_html = "\n".join(lines)
        await _send_search_results_safe(update.message, msg_html)

        orch.state_manager.update_state(
            user.id,
            {
                "active_persona": "SEARCH",
                "search_results": [
                    {"id": n.get("id"), "title": n.get("title") or "(无标题)"}
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
    """处理带有数字（1–5）的回复以查看选定的搜索结果。完成后清除状态。"""
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "SEARCH":
        return
    results = state.get("search_results") or []
    if not results:
        orch.state_manager.clear_state(user_id)
        return

    stripped = text.strip()
    if not stripped.isdigit():
        await message.reply_text("回复数字（1–5）查看该笔记，或再次运行 /find。")
        return

    idx = int(stripped)
    if idx < 1 or idx > len(results):
        await message.reply_text(
            f"请回复 1 到 {len(results)} 之间的数字。"
        )
        return

    note_ref = results[idx - 1]
    note_id = note_ref.get("id")
    if not note_id:
        orch.state_manager.clear_state(user_id)
        await message.reply_text("无效选择。")
        return

    try:
        note = await orch.joplin_client.get_note(note_id)
    except Exception as exc:
        logger.error("Failed to fetch note %s for user %d: %s", note_id, user_id, exc)
        orch.state_manager.clear_state(user_id)
        await message.reply_text("❌ 无法加载该笔记。")
        return

    orch.state_manager.clear_state(user_id)

    title = note.get("title") or "(无标题)"
    body = (note.get("body") or "").strip()
    preview = body[:2000] + "..." if len(body) > 2000 else body
    if preview:
        await message.reply_text(f"📄 {title}\n\n{preview}")
    else:
        await message.reply_text(f"📄 {title}\n\n(空)")
