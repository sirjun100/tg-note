"""
Semantic Q&A handlers: /ask, /reindex, /search_status (FR-026).
BF-023: HTML escape + safe send + split long messages.
"""

from __future__ import annotations

import html
import logging
import re
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.qa_service import ask_question
from src.security_utils import check_whitelist, format_error_message, split_message_for_telegram

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _ask_html_to_plain(html_text: str) -> str:
    """Strip HTML for plain-text fallback (BF-023)."""
    out = re.sub(r"</?b>", "", html_text)
    out = re.sub(r"</?i>", "", out)
    return out.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


async def _send_ask_response_safe(message: Any, msg_html: str) -> None:
    """Send /ask response with HTML; fallback to plain; split if > 4096 chars (BF-023)."""
    plain = _ask_html_to_plain(msg_html)
    if len(msg_html) > 4096:
        for chunk in split_message_for_telegram(plain):
            await message.reply_text(chunk)
        return
    try:
        await message.reply_text(msg_html, parse_mode="HTML")
    except Exception as exc:
        exc_str = str(exc).lower()
        is_parse = (
            "parse" in exc_str
            or "entities" in exc_str
            or "badrequest" in type(exc).__name__.lower()
        )
        if is_parse:
            for chunk in split_message_for_telegram(plain):
                await message.reply_text(chunk)
            return
        raise


def register_ask_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register /ask, /reindex, /search_status handlers."""
    application.add_handler(CommandHandler("ask", _ask(orch)))
    application.add_handler(CommandHandler("search_reindex", _reindex(orch)))
    application.add_handler(CommandHandler("reindex", _reindex(orch)))
    application.add_handler(CommandHandler("search_status", _search_status(orch)))


def _ask(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        question = " ".join(context.args) if context.args else ""
        if not question:
            await msg.reply_text(
                "🔍 **询问有关您笔记的问题**\n\n"
                "用法：`/ask <问题>`\n"
                "示例：`/ask 我是如何解决缓存问题的？`\n\n"
                "使用语义搜索查找相关笔记并用 AI 回答。",
                parse_mode="Markdown",
            )
            return

        try:
            await msg.chat.send_action("typing")
            result = await ask_question(
                question,
                note_index=orch.note_index,
                joplin_client=orch.joplin_client,
                llm_orchestrator=orch.llm_orchestrator,
            )
            answer = result["answer"]
            sources = result["sources"]

            # BF-023: HTML + escape to avoid Markdown parse errors from LLM/Joplin content
            q_esc = html.escape(question)
            lines = [f"🔍 <b>{q_esc}</b>\n", html.escape(answer)]
            if sources:
                lines.append("\n📚 <b>来源：</b>")
                for s in sources[:5]:
                    lines.append(f"• \"{html.escape(s['title'])}\"")
            response = "\n".join(lines)
            await _send_ask_response_safe(msg, response)
            logger.info("Ask '%s' answered for user %d", question[:50], user.id)
        except RuntimeError as exc:
            await msg.reply_text(format_error_message(str(exc)))
        except Exception as exc:
            logger.error("Ask failed for user %d: %s", user.id, exc, exc_info=True)
            await msg.reply_text(format_error_message("无法回答。请重试或运行 /reindex。"))

    return handler


def _reindex(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        try:
            status = await msg.reply_text("🔄 正在重建搜索索引...这可能需要一分钟。")
            await msg.chat.send_action("typing")

            orch.note_index.clear()
            notes = await orch.joplin_client.get_all_notes(fields="id,title,body")
            indexed = 0
            for note in notes:
                note_id = note.get("id")
                title = note.get("title") or "(无标题)"
                body = note.get("body") or ""
                if note_id:
                    chunks = await orch.note_index.index_note_async(note_id, title, body)
                    indexed += chunks

            stats = orch.note_index.get_stats()
            await status.edit_text(
                f"✅ 索引已重建。\n"
                f"• 已索引 {stats['notes']} 个笔记\n"
                f"• 共 {stats['chunks']} 个块\n\n"
                f"使用 /ask 询问问题。"
            )
            logger.info("Reindex complete for user %d: %d notes, %d chunks", user.id, stats["notes"], stats["chunks"])
        except RuntimeError as exc:
            await msg.reply_text(format_error_message(str(exc)))
        except Exception as exc:
            logger.error("Reindex failed for user %d: %s", user.id, exc, exc_info=True)
            await msg.reply_text(format_error_message("重建索引失败。请重试。"))

    return handler


def _search_status(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        try:
            stats = orch.note_index.get_stats()
            if stats["chunks"] == 0:
                await msg.reply_text(
                    "📊 **搜索索引为空。**\n\n"
                    "运行 /reindex 从您的 Joplin 笔记构建索引。",
                    parse_mode="Markdown",
                )
            else:
                await msg.reply_text(
                    f"📊 **搜索索引**\n"
                    f"• 笔记：{stats['notes']}\n"
                    f"• 块：{stats['chunks']}\n"
                    f"• 最后更新：{stats['last_updated'] or '无'}\n\n"
                    f"使用 /ask 查询您的笔记。",
                    parse_mode="Markdown",
                )
        except Exception as exc:
            logger.error("Search status failed for user %d: %s", user.id, exc)
            await msg.reply_text(format_error_message("无法获取状态。"))

    return handler
