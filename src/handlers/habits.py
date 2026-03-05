"""
Habit tracking handlers: /habits, add, remove, list, stats, callback for buttons.

Sprint 11 Story 4 - FR-032.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.habit_service import (
    add_habit,
    delete_today_entry,
    get_habit_by_id,
    get_habit_by_name,
    get_habits,
    get_stats,
    get_today_entries,
    log_entry,
    remove_habit,
)
from src.security_utils import check_whitelist, format_error_message, format_success_message
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _get_today_for_user(user_id: int, orch: TelegramOrchestrator) -> date:
    """Get today's date in user's timezone."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    return now.date()


def _build_habit_keyboard(
    habits: list[dict[str, Any]],
    today_entries: dict[str, dict[str, Any]],
    stats: list[dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Build inline keyboard for habit check-in."""
    keyboard = []
    stats_by_id = {s["habit_id"]: s for s in stats}
    for habit in habits:
        hid = habit["id"]
        name = habit["name"]
        entry = today_entries.get(hid)
        st = stats_by_id.get(hid, {})

        if entry is not None:
            status = "✅" if entry.get("completed") else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {name} (logged)",
                    callback_data=f"habit_undo_{hid}",
                )
            ])
        else:
            streak = st.get("current_streak", 0)
            streak_label = f" 🔥{streak}" if streak > 0 else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {name}{streak_label}",
                    callback_data=f"habit_yes_{hid}",
                ),
                InlineKeyboardButton("❌", callback_data=f"habit_no_{hid}"),
            ])
    keyboard.append([InlineKeyboardButton("📊 View Stats", callback_data="habit_stats")])
    return InlineKeyboardMarkup(keyboard)


def _format_checkin_message(
    habits: list[dict[str, Any]],
    today_entries: dict[str, dict[str, Any]],
    stats: list[dict[str, Any]],
    today: date,
) -> str:
    """Format the daily check-in message."""
    completed = sum(1 for e in today_entries.values() if e.get("completed"))
    total = len(habits)
    date_str = today.strftime("%B %d")
    lines = [f"🌟 **Daily Habits - {date_str}**", ""]
    stats_by_id = {s["habit_id"]: s for s in stats}
    for habit in habits:
        hid = habit["id"]
        name = habit["name"]
        entry = today_entries.get(hid)
        st = stats_by_id.get(hid, {})
        streak = st.get("current_streak", 0)
        if entry is not None:
            status = "✅" if entry.get("completed") else "❌"
            lines.append(f"{status} **{name}**")
        else:
            if streak > 0:
                lines.append(f"**{name}** — 🔥 {streak} day streak")
            else:
                lines.append(f"**{name}** — ⚡ Start streak!")
        lines.append("")
    lines.append(f"✅ {completed}/{total} completed today")
    return "\n".join(lines)


def _format_stats(stats: list[dict[str, Any]]) -> str:
    """Format stats for display."""
    if not stats:
        return "No habits yet. Use `/habits add <name>` to add one."
    lines = ["📊 **Habit Stats - Last 30 Days**", ""]
    total_completed = 0
    total_possible = 0
    for s in stats:
        name = s["name"]
        cs = s["current_streak"]
        ls = s["longest_streak"]
        c7, t7 = s["last_7_days"], s["total_7"]
        c30, t30 = s["last_30_days"], s["total_30"]
        r7 = s["completion_rate_7"]
        r30 = s["completion_rate_30"]
        total_completed += c30
        total_possible += t30
        lines.append(f"**{name}**")
        lines.append(f"├ Current streak: {cs} days {'🔥' if cs > 0 else ''}")
        lines.append(f"├ Longest streak: {ls} days")
        lines.append(f"├ Last 7 days: {c7}/{t7} ({r7:.0f}%)")
        lines.append(f"└ Last 30 days: {c30}/{t30} ({r30:.0f}%)")
        lines.append("")
    if total_possible > 0:
        overall = total_completed / total_possible * 100
        lines.append(f"**Overall completion rate: {overall:.0f}%**")
    return "\n".join(lines)


def register_habit_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register habit command and callback handlers."""

    async def habits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return

        args = (context.args or [])
        today = _get_today_for_user(user.id, orch)

        if not args:
            habits = get_habits(user.id)
            if not habits:
                await msg.reply_text(
                    "🌟 No habits yet. Use `/habits add <name>` to add one.\n"
                    "Example: `/habits add Exercise`",
                    parse_mode="Markdown",
                )
                return
            today_entries = get_today_entries(user.id, today)
            stats = get_stats(user.id, today)
            text = _format_checkin_message(habits, today_entries, stats, today)
            keyboard = _build_habit_keyboard(habits, today_entries, stats)
            await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
            return

        sub = (args[0] or "").lower()
        if sub == "add" and len(args) >= 2:
            name = " ".join(args[1:]).strip()
            habit = add_habit(user.id, name)
            if habit:
                await msg.reply_text(format_success_message(f"Added habit: {habit['name']}"))
            else:
                await msg.reply_text(
                    format_error_message(f"Habit '{name}' already exists.")
                )
            return

        if sub == "remove" and len(args) >= 2:
            name = " ".join(args[1:]).strip()
            ok = remove_habit(user.id, name)
            if ok:
                await msg.reply_text(format_success_message(f"Removed habit: {name}"))
            else:
                await msg.reply_text(format_error_message(f"Habit '{name}' not found."))
            return

        if sub == "list":
            habits = get_habits(user.id)
            if not habits:
                await msg.reply_text("No habits yet. Use `/habits add <name>` to add one.")
                return
            stats = get_stats(user.id, today)
            stats_by_id = {s["habit_id"]: s for s in stats}
            lines = ["🌟 **Your Habits**", ""]
            for h in habits:
                st = stats_by_id.get(h["id"], {})
                cs = st.get("current_streak", 0)
                lines.append(f"• **{h['name']}** — 🔥 {cs} day streak")
            await msg.reply_text("\n".join(lines), parse_mode="Markdown")
            return

        if sub == "stats":
            habits = get_habits(user.id)
            if not habits:
                await msg.reply_text("No habits yet. Use `/habits add <name>` to add one.")
                return
            stats = get_stats(user.id, today)
            if len(args) >= 2:
                name = " ".join(args[1:]).strip()
                habit = get_habit_by_name(user.id, name)
                if habit:
                    stats = [s for s in stats if s["habit_id"] == habit["id"]]
            await msg.reply_text(_format_stats(stats), parse_mode="Markdown")
            return

        await msg.reply_text(
            "🌟 **Habits**\n\n"
            "• `/habits` — Daily check-in with buttons\n"
            "• `/habits add <name>` — Add a habit\n"
            "• `/habits remove <name>` — Remove a habit\n"
            "• `/habits list` — List habits with streaks\n"
            "• `/habits stats` — Detailed statistics",
            parse_mode="Markdown",
        )

    async def habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await query.answer("Unauthorized.")
            return

        await query.answer()
        data = query.data
        today = _get_today_for_user(user.id, orch)

        if data == "habit_stats":
            habits = get_habits(user.id)
            if habits:
                stats = get_stats(user.id, today)
                await query.message.reply_text(_format_stats(stats), parse_mode="Markdown")  # type: ignore[attr-defined]
            else:
                await query.message.reply_text("No habits yet.")  # type: ignore[attr-defined]
            return

        if data.startswith("habit_yes_"):
            habit_id = data.replace("habit_yes_", "")
            habit = get_habit_by_id(user.id, habit_id)
            if habit:
                log_entry(user.id, habit_id, today, completed=True)

        elif data.startswith("habit_no_"):
            habit_id = data.replace("habit_no_", "")
            habit = get_habit_by_id(user.id, habit_id)
            if habit:
                log_entry(user.id, habit_id, today, completed=False)

        elif data.startswith("habit_undo_"):
            habit_id = data.replace("habit_undo_", "")
            delete_today_entry(user.id, habit_id, today)

        habits = get_habits(user.id)
        if not habits:
            await query.edit_message_text("No habits. Use /habits add <name> to add one.")
            return
        today_entries = get_today_entries(user.id, today)
        stats = get_stats(user.id, today)
        text = _format_checkin_message(habits, today_entries, stats, today)
        keyboard = _build_habit_keyboard(habits, today_entries, stats)
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as exc:
            logger.warning("Failed to edit habit message: %s", exc)

    application.add_handler(CommandHandler("habits", habits_cmd))
    application.add_handler(CallbackQueryHandler(habit_callback, pattern="^habit_"))
    logger.info("Habit handlers registered")
