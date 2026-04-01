"""
Weekly Planning Session handlers: /plan, /plan_done, /plan_cancel.

Guided weekly planning with priorities and obstacle identification.
Sprint 12 Story 2 - FR-027.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.exceptions import GoogleAuthError
from src.security_utils import check_whitelist, format_error_message, format_success_message
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

PLANNING_PATH = ["01 - Areas", "📓 Journaling", "Weekly Planning"]
PLANNING_TAGS = ["planning", "weekly", "gtd"]
PHASES = ["review", "priorities", "obstacles", "commit"]


def _get_week_start(now: datetime) -> datetime:
    """Get Monday of current week (ISO week)."""
    weekday = now.weekday()
    return (now - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)


def _get_friday_rfc3339(now: datetime) -> str:
    """Get Friday of current week as RFC3339 for Google Tasks."""
    weekday = now.weekday()
    days_until_friday = (4 - weekday) % 7
    if days_until_friday == 0 and now.hour > 18:
        days_until_friday = 7
    friday = now + timedelta(days=days_until_friday)
    friday = friday.replace(hour=17, minute=0, second=0, microsecond=0)
    return friday.strftime("%Y-%m-%dT%H:%M:%S")


def _gather_review_context(orch: TelegramOrchestrator, user_id: int) -> str:
    """收集待处理任务以供审查。返回格式化字符串。"""
    if not orch.task_service:
        return ""
    try:
        task_lists = orch.task_service.get_available_task_lists(str(user_id))
        if not task_lists:
            return ""
        lines = ["**待处理任务：**"]
        count = 0
        for tl in task_lists:
            tasks = orch.task_service.get_user_tasks(str(user_id), tl.get("id")) or []
            for t in tasks:
                if t.get("status") == "completed":
                    continue
                title = t.get("title", "(无标题)")
                lines.append(f"• {title}")
                count += 1
                if count >= 10:
                    break
            if count >= 10:
                break
        if count == 0:
            return "没有待处理任务。"
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to gather tasks for planning: %s", exc)
        return ""


def _build_planning_note(
    state: dict[str, Any],
    user_id: int,
    orch: TelegramOrchestrator,
) -> str:
    """构建每周计划笔记正文。"""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    week_start = _get_week_start(now)
    date_str = week_start.strftime("%B %d, %Y")

    reflection = state.get("last_week_reflection", "").strip()
    priorities = state.get("priorities", [])
    obstacles = state.get("obstacles", [])
    top_priority = state.get("top_priority", "").strip()

    lines = [
        f"# 每周计划 - {date_str} 这周",
        "",
        "## 上周反思",
        reflection or "-",
        "",
        "## 这周的优先事项",
        "",
    ]
    if top_priority:
        lines.append("### 🎯 第一优先事项")
        lines.append(top_priority)
        lines.append("")
    if priorities:
        lines.append("### 其他优先事项")
        for i, p in enumerate(priorities[:5], 1):
            if p != top_priority:
                lines.append(f"{i}. {p}")
        lines.append("")

    if obstacles:
        lines.append("## 潜在障碍")
        lines.append("")
        for o in obstacles:
            if isinstance(o, dict):
                obs = o.get("obstacle", "")
                mit = o.get("mitigation", "")
                lines.append(f"- **{obs}** → {mit}")
            else:
                lines.append(f"- {o}")
        lines.append("")

    lines.append("---")
    lines.append(f"*通过 /plan 在 {now.strftime('%Y-%m-%d %H:%M')} 生成*")
    return "\n".join(lines)


async def _save_planning_note(orch: TelegramOrchestrator, user_id: int, state: dict) -> bool:
    """将计划笔记保存到 Joplin。"""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    week_start = _get_week_start(now)
    title = f"每周计划 - {week_start.strftime('%Y-%m-%d')}"
    body = _build_planning_note(state, user_id, orch)
    folder_id = await orch.joplin_client.get_or_create_folder_by_path(PLANNING_PATH)
    note_id = await orch.joplin_client.create_note(folder_id, title, body)
    await orch.joplin_client.apply_tags(note_id, PLANNING_TAGS)
    return True


def _create_priority_tasks(orch: TelegramOrchestrator, user_id: int, state: dict) -> int:
    """为优先事项创建 Google Tasks。返回创建的数量。"""
    if not orch.task_service:
        return 0
    priorities = state.get("priorities", [])
    top_priority = state.get("top_priority", "").strip()
    if not priorities and top_priority:
        priorities = [top_priority]
    if not priorities:
        return 0
    due = _get_friday_rfc3339(get_user_timezone_aware_now(user_id, orch.logging_service))
    created = 0
    for p in priorities[:5]:
        p = str(p).strip()
        if not p:
            continue
        is_top = p == top_priority
        title = f"⭐ {p}" if is_top else p
        try:
            result = orch.task_service.create_task_with_metadata(
                title=title,
                user_id=str(user_id),
                notes="来自 /plan 会话的每周优先事项",
                due_date=due,
            )
        except GoogleAuthError:
            raise
        except Exception as exc:
            logger.warning("Failed to create planning task '%s': %s", title[:50], exc)
            continue
        if result:
            created += 1
    return created


async def handle_planning_message(
    orch: TelegramOrchestrator,
    user_id: int,
    text: str,
    message: Any,
) -> None:
    """当用户处于 PLANNING_COACH 会话时处理传入消息。"""
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "PLANNING_COACH":
        return

    phase = state.get("phase", "review")

    if phase == "review":
        state["last_week_reflection"] = text.strip()
        state["phase"] = "priorities"
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            "🎯 **优先事项**\n\n"
            "这周要完成的 3-5 件最重要的事是什么？"
            "列出来（每行一个或用逗号分隔）。"
        )
        return

    if phase == "priorities":
        raw = text.strip()
        priorities = []
        for line in raw.replace(",", "\n").split("\n"):
            p = line.strip()
            if p:
                priorities.append(p)
        state["priorities"] = priorities[:5]
        state["phase"] = "obstacles"
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            "⚠️ **障碍**\n\n"
            "可能会遇到什么阻碍？对于每个障碍，您将如何处理？"
            "（例如：'会议 → 在日历中屏蔽专注时间'）"
        )
        return

    if phase == "obstacles":
        raw = text.strip()
        obstacles = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "→" in line or "->" in line:
                parts = line.replace("->", "→").split("→", 1)
                obstacles.append({"obstacle": parts[0].strip(), "mitigation": parts[1].strip() if len(parts) > 1 else ""})
            else:
                obstacles.append({"obstacle": line, "mitigation": ""})
        state["obstacles"] = obstacles
        state["phase"] = "commit"
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            "🎯 **承诺**\n\n"
            "看看您的优先事项，这周您的第一重点是什么？"
        )
        return

    if phase == "commit":
        state["top_priority"] = text.strip()
        state["phase"] = "complete"
        orch.state_manager.update_state(user_id, state)
        await _finish_planning(orch, user_id, state, message)
        return


async def _finish_planning(orch: TelegramOrchestrator, user_id: int, state: dict, message: Any) -> None:
    """保存笔记、创建任务、清除状态。"""
    try:
        await _save_planning_note(orch, user_id, state)
        task_count = _create_priority_tasks(orch, user_id, state)
        orch.state_manager.clear_state(user_id)
        msg = format_success_message("每周计划已保存到 Joplin。")
        if task_count > 0:
            msg += f"\n✅ {task_count} 个优先任务已添加到 Google Tasks。"
        await message.reply_text(msg)
    except GoogleAuthError:
        orch.state_manager.clear_state(user_id)
        await message.reply_text(format_error_message(
            "🔑 Google 令牌已过期或被撤销。使用 /tasks_connect 重新认证。"
        ))
    except Exception as exc:
        logger.error("Planning save failed: %s", exc)
        await message.reply_text(format_error_message("无法保存计划。请重试。"))


def register_planning_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """注册计划会话处理程序。"""

    async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == "PLANNING_COACH":
            await msg.reply_text(
                "📅 您已经有一个活动的计划会话。"
                "继续回答，或使用 /plan_done 完成。"
            )
            return

        now = get_user_timezone_aware_now(user.id, orch.logging_service)
        week_start = _get_week_start(now)
        new_state = {
            "active_persona": "PLANNING_COACH",
            "phase": "review",
            "started_at": now.isoformat(),
            "last_week_reflection": "",
            "priorities": [],
            "obstacles": [],
            "top_priority": "",
            "conversation_history": [],
        }
        orch.state_manager.update_state(user.id, new_state)
        review_ctx = _gather_review_context(orch, user.id)
        intro = (
            f"📅 **每周计划会话**\n\n"
            f"{week_start.strftime('%B %d')} 这周\n\n"
        )
        if review_ctx:
            intro += f"📋 {review_ctx}\n\n"
        intro += (
            "上周怎么样？哪些做得好，哪些不好？\n\n"
            "输入 /plan_done 提前完成，/plan_cancel 退出不保存。"
        )
        await msg.reply_text(intro, parse_mode="Markdown")
        logger.info("Planning session started for user %d", user.id)

    async def plan_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != "PLANNING_COACH":
            await msg.reply_text("没有活动的计划会话。使用 /plan 开始一个。")
            return

        phase = state.get("phase", "")
        if phase == "review":
            orch.state_manager.clear_state(user.id)
            await msg.reply_text("计划会话已取消。")
            return

        await _finish_planning(orch, user.id, state, msg)

    async def plan_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == "PLANNING_COACH":
            orch.state_manager.clear_state(user.id)
            await msg.reply_text("计划会话已取消。没有保存任何内容。")
        else:
            await msg.reply_text("没有活动的计划会话可以取消。")

    application.add_handler(CommandHandler("plan", plan_cmd))
    application.add_handler(CommandHandler("plan_done", plan_done_cmd))
    application.add_handler(CommandHandler("plan_cancel", plan_cancel_cmd))
    logger.info("Planning handlers registered")
