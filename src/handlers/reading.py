"""
Read Later queue handlers: /readlater, /rl, /reading.

Sprint 11 Story 2 - FR-028.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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
from src.timezone_utils import get_now_in_default_tz
from src.url_enrichment import URL_PATTERN

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

READING_STATE_KEY = "reading_queue_items"


def _format_relative_time(saved_at: datetime | None) -> str:
    """Format saved_at as relative time (e.g. '2 days ago')."""
    if not saved_at:
        return "未知"
    now = datetime.now(timezone.utc)  # noqa: UP017
    dt = saved_at.replace(tzinfo=timezone.utc) if saved_at.tzinfo is None else saved_at  # noqa: UP017
    delta = now - dt
    days = delta.days
    if days == 0:
        return "今天"
    if days == 1:
        return "1天前"
    if days < 7:
        return f"{days}天前"
    if days < 14:
        return "1周前"
    if days < 30:
        return f"{days // 7}周前"
    return f"{days // 30}个月前"


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
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        text = " ".join(context.args) if context.args else ""
        urls = URL_PATTERN.findall(text)
        if not urls:
            await msg.reply_text(
                "📚 **稍后阅读**\n\n"
                "用法：`/readlater <链接>` 或 `/rl <链接>`\n"
                "示例：`/rl https://example.com/article`",
                parse_mode="Markdown",
            )
            return

        url = urls[0]
        await msg.reply_text("📚 正在获取文章…")
        try:
            result = await add_to_queue(orch.joplin_client, url, get_now_in_default_tz())
            if result.get("duplicate"):
                await msg.reply_text(
                    format_success_message(f"已在队列中：{result.get('title', '无标题')}")
                )
            else:
                await msg.reply_text(
                    format_success_message(f"已添加：{result.get('title', '无标题')}")
                )
        except Exception as exc:
            logger.error("Read later failed for %s: %s", url, exc)
            await msg.reply_text(format_error_message("添加到阅读队列失败，请重试。"))

    return handler


def _reading_cmd(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
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
                            await msg.reply_text(format_success_message("标记为已读 ✓"))
                        else:
                            await msg.reply_text(format_error_message("无法标记为已读。"))
                    else:
                        await msg.reply_text(format_error_message("无效的项目。"))
                else:
                    await msg.reply_text(format_error_message("无效的编号。使用 /reading 查看队列。"))
            else:
                await msg.reply_text("用法：`/reading done <编号>`", parse_mode="Markdown")
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
                            await msg.reply_text(format_success_message("已从队列中移除。"))
                        else:
                            await msg.reply_text(format_error_message("无法删除。"))
                    else:
                        await msg.reply_text(format_error_message("无效的项目。"))
                else:
                    await msg.reply_text(format_error_message("无效的编号。"))
            else:
                await msg.reply_text("用法：`/reading delete <编号>`", parse_mode="Markdown")
            return

        if sub == "random":
            item = await get_random_unread(orch.joplin_client)
            if not item:
                await msg.reply_text("📚 您的阅读队列为空。使用 /readlater <链接> 添加文章")
                return
            title = item.get("title") or "无标题"
            domain = item.get("domain") or ""
            await msg.reply_text(
                f"📚 **随机推荐**\n\n"
                f"**{title}**\n"
                f"_{domain}_\n\n"
                f"使用 /reading 查看完整队列。",
                parse_mode="Markdown",
            )
            return

        if sub == "stats":
            stats = await get_stats(orch.joplin_client)
            await msg.reply_text(
                f"📚 **阅读队列统计**\n\n"
                f"• 未读：{stats['unread']}\n"
                f"• 已读：{stats['read']}\n"
                f"• 总计：{stats['total']}",
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
                "📚 您的阅读队列为空。使用 /readlater <链接> 添加文章"
            )
            return

        label = "未读" if unread_only else "全部"
        lines = [f"📚 **阅读队列** ({total} {label})\n"]
        for i, it in enumerate(items, 1):
            title = it.get("title") or "无标题"
            domain = it.get("domain") or ""
            summary = (it.get("summary") or "")[:100]
            if len(it.get("summary") or "") > 100:
                summary += "..."
            saved = _format_relative_time(it.get("saved_at"))
            lines.append(f"{i}️⃣ **{title}**")
            lines.append(f"   _{domain} • 保存于 {saved}_")
            if summary:
                lines.append(f"   {summary}")
            lines.append("")
        lines.append("回复编号打开，或 `/reading done <编号>` 标记为已读。")
        if total > 5:
            lines.append(f"第 {page} 页。使用 `/reading {'all' if unread_only else ''} {page + 1}` 查看更多。")
        await msg.reply_text("\n".join(lines), parse_mode="Markdown")

    return handler
