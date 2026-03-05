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

from src.security_utils import check_whitelist, format_error_message, format_success_message
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

PLANNING_PATH = ["Areas", "📓 Journaling", "Weekly Planning"]
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
    """Gather pending tasks for review. Returns formatted string."""
    if not orch.task_service:
        return ""
    try:
        task_lists = orch.task_service.get_available_task_lists(str(user_id))
        if not task_lists:
            return ""
        lines = ["**Pending tasks:**"]
        count = 0
        for tl in task_lists:
            tasks = orch.task_service.get_user_tasks(str(user_id), tl.get("id")) or []
            for t in tasks:
                if t.get("status") == "completed":
                    continue
                title = t.get("title", "(Untitled)")
                lines.append(f"• {title}")
                count += 1
                if count >= 10:
                    break
            if count >= 10:
                break
        if count == 0:
            return "No pending tasks."
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to gather tasks for planning: %s", exc)
        return ""


def _build_planning_note(
    state: dict[str, Any],
    user_id: int,
    orch: TelegramOrchestrator,
) -> str:
    """Build the weekly planning note body."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    week_start = _get_week_start(now)
    date_str = week_start.strftime("%B %d, %Y")

    reflection = state.get("last_week_reflection", "").strip()
    priorities = state.get("priorities", [])
    obstacles = state.get("obstacles", [])
    top_priority = state.get("top_priority", "").strip()

    lines = [
        f"# Weekly Plan - Week of {date_str}",
        "",
        "## Last Week Reflection",
        reflection or "-",
        "",
        "## This Week's Priorities",
        "",
    ]
    if top_priority:
        lines.append("### 🎯 #1 Priority")
        lines.append(top_priority)
        lines.append("")
    if priorities:
        lines.append("### Other Priorities")
        for i, p in enumerate(priorities[:5], 1):
            if p != top_priority:
                lines.append(f"{i}. {p}")
        lines.append("")

    if obstacles:
        lines.append("## Potential Obstacles")
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
    lines.append(f"*Generated via /plan on {now.strftime('%Y-%m-%d %H:%M')}*")
    return "\n".join(lines)


async def _save_planning_note(orch: TelegramOrchestrator, user_id: int, state: dict) -> bool:
    """Save planning note to Joplin."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    week_start = _get_week_start(now)
    title = f"Weekly Plan - {week_start.strftime('%Y-%m-%d')}"
    body = _build_planning_note(state, user_id, orch)
    folder_id = await orch.joplin_client.get_or_create_folder_by_path(PLANNING_PATH)
    note_id = await orch.joplin_client.create_note(folder_id, title, body)
    await orch.joplin_client.apply_tags(note_id, PLANNING_TAGS)
    return True


def _create_priority_tasks(orch: TelegramOrchestrator, user_id: int, state: dict) -> int:
    """Create Google Tasks for priorities. Returns count created."""
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
        result = orch.task_service.create_task_with_metadata(
            title=title,
            user_id=str(user_id),
            notes="Weekly priority from /plan session",
            due_date=due,
        )
        if result:
            created += 1
    return created


async def handle_planning_message(
    orch: TelegramOrchestrator,
    user_id: int,
    text: str,
    message: Any,
) -> None:
    """Handle incoming message when user is in PLANNING_COACH session."""
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "PLANNING_COACH":
        return

    phase = state.get("phase", "review")

    if phase == "review":
        state["last_week_reflection"] = text.strip()
        state["phase"] = "priorities"
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            "🎯 **Priorities**\n\n"
            "What are the 3-5 most important things to accomplish this week? "
            "List them (one per line or comma-separated)."
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
            "⚠️ **Obstacles**\n\n"
            "What might get in the way? For each, how will you handle it? "
            "(e.g. 'Meetings → Block focus time in calendar')"
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
            "🎯 **Commit**\n\n"
            "Looking at your priorities, what's your #1 focus for this week?"
        )
        return

    if phase == "commit":
        state["top_priority"] = text.strip()
        state["phase"] = "complete"
        orch.state_manager.update_state(user_id, state)
        await _finish_planning(orch, user_id, state, message)
        return


async def _finish_planning(orch: TelegramOrchestrator, user_id: int, state: dict, message: Any) -> None:
    """Save note, create tasks, clear state."""
    try:
        await _save_planning_note(orch, user_id, state)
        task_count = _create_priority_tasks(orch, user_id, state)
        orch.state_manager.clear_state(user_id)
        msg = format_success_message("Weekly plan saved to Joplin.")
        if task_count > 0:
            msg += f"\n✅ {task_count} priority task(s) added to Google Tasks."
        await message.reply_text(msg)
    except Exception as exc:
        logger.error("Planning save failed: %s", exc)
        await message.reply_text(format_error_message("Failed to save plan. Please try again."))


def register_planning_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register planning session handlers."""

    async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == "PLANNING_COACH":
            await msg.reply_text(
                "📅 You already have an active planning session. "
                "Keep answering, or use /plan_done to finish."
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
            f"📅 **Weekly Planning Session**\n\n"
            f"Week of {week_start.strftime('%B %d')}\n\n"
        )
        if review_ctx:
            intro += f"📋 {review_ctx}\n\n"
        intro += (
            "How did last week go? What worked, what didn't?\n\n"
            "Type /plan_done to finish early, /plan_cancel to exit without saving."
        )
        await msg.reply_text(intro, parse_mode="Markdown")
        logger.info("Planning session started for user %d", user.id)

    async def plan_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != "PLANNING_COACH":
            await msg.reply_text("No active planning session. Use /plan to start one.")
            return

        phase = state.get("phase", "")
        if phase == "review":
            orch.state_manager.clear_state(user.id)
            await msg.reply_text("Planning session cancelled.")
            return

        await _finish_planning(orch, user.id, state, msg)

    async def plan_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == "PLANNING_COACH":
            orch.state_manager.clear_state(user.id)
            await msg.reply_text("Planning session cancelled. Nothing was saved.")
        else:
            await msg.reply_text("No active planning session to cancel.")

    application.add_handler(CommandHandler("plan", plan_cmd))
    application.add_handler(CommandHandler("plan_done", plan_done_cmd))
    application.add_handler(CommandHandler("plan_cancel", plan_cancel_cmd))
    logger.info("Planning handlers registered")
