"""
Daily and weekly report handlers: generate, schedule, configure.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.handlers.core import build_project_portfolio_html
from src.monthly_report_generator import MonthlyReportGenerator
from src.report_generator import PriorityLevel
from src.security_utils import check_whitelist
from src.timezone_utils import get_user_timezone_aware_now
from src.weekly_report_generator import WeeklyReportGenerator

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _cleanup_completed_tasks_before_report(orch: TelegramOrchestrator, user_id: int) -> None:
    """Delete completed tasks older than 30 days before generating report (fresh data)."""
    if orch.task_service:
        try:
            orch.task_service.delete_completed_tasks_older_than(str(user_id), days=30)
        except Exception as exc:
            logger.debug("Cleanup before report failed (non-fatal): %s", exc)


_DEFAULT_CONFIG = {
    "enabled": True,
    "delivery_time": "08:00",
    "timezone": "UTC",
    "include_critical": True,
    "include_high": True,
    "include_medium": False,
    "include_google_tasks": True,
    "include_clarification_pending": True,
    "include_project_portfolio": False,
    "detail_level": "detailed",
}


def register_report_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    # New names (report_* prefix); old names kept as aliases
    application.add_handler(CommandHandler("report_daily", _daily_report(orch)))
    application.add_handler(CommandHandler("daily_report", _daily_report(orch)))
    application.add_handler(CommandHandler("report_weekly", _weekly_report(orch)))
    application.add_handler(CommandHandler("weekly_report", _weekly_report(orch)))
    application.add_handler(CommandHandler("report_monthly", _monthly_report(orch)))
    application.add_handler(CommandHandler("monthly_report", _monthly_report(orch)))
    application.add_handler(CommandHandler("report_set_time", _configure_time(orch)))
    application.add_handler(CommandHandler("configure_report_time", _configure_time(orch)))
    application.add_handler(CommandHandler("report_set_timezone", _configure_tz(orch)))
    application.add_handler(CommandHandler("configure_report_timezone", _configure_tz(orch)))
    application.add_handler(CommandHandler("report_toggle_schedule", _toggle(orch)))
    application.add_handler(CommandHandler("toggle_daily_report", _toggle(orch)))
    application.add_handler(CommandHandler("report_config", _show_config(orch)))
    application.add_handler(CommandHandler("show_report_config", _show_config(orch)))
    application.add_handler(CommandHandler("report_set_content", _configure_content(orch)))
    application.add_handler(CommandHandler("configure_report_content", _configure_content(orch)))
    application.add_handler(CommandHandler("report_toggle_portfolio", _toggle_portfolio(orch)))
    application.add_handler(CommandHandler("report_help", _help(orch)))


def _daily_report(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此命令的权限。")
            return

        try:
            _cleanup_completed_tasks_before_report(orch, user.id)
            logger.info("Generating on-demand daily report for user %d", user.id)
            progress_msg = await update.message.reply_text("📊 正在获取笔记和任务…")

            state = orch.state_manager.get_state(user.id)
            pending = state.get("pending_clarifications", []) if state else []

            report = await orch.report_generator.generate_report_async(
                user_id=user.id,
                pending_clarifications=pending,
                completed_items=[],
                min_priority=PriorityLevel.LOW,
            )

            include = report.total_items > 0 or bool(pending)
            message = orch.report_generator.format_report_message(report, include_details=include)
            await progress_msg.delete()
            await update.message.reply_text(message, parse_mode="HTML")

            orch.logging_service.log_system_event(
                level="INFO",
                module="daily_report",
                message=f"Generated on-demand daily report for user {user.id}",
                extra_data={
                    "total_items": report.total_items,
                    "joplin_count": report.joplin_count,
                    "google_tasks_count": report.google_tasks_count,
                    "generated_by": "manual",
                },
            )
            logger.info("Daily report sent to user %d: %d items", user.id, report.total_items)
        except Exception as exc:
            await update.message.reply_text("❌ 生成每日报告时出错，请稍后重试。")
            logger.error("Error in handle_daily_report: %s", exc, exc_info=True)

    return handler


async def send_scheduled_report(orch: TelegramOrchestrator, user_id: int) -> None:
    """Callback invoked by the scheduler at the configured time."""
    try:
        logger.info("Sending scheduled report to user %d", user_id)
        _cleanup_completed_tasks_before_report(orch, user_id)

        cfg = orch.logging_service.get_report_configuration(user_id)
        if not cfg or not cfg.get("enabled", True):
            logger.debug("Scheduled reports disabled for user %d", user_id)
            return

        state = orch.state_manager.get_state(user_id)
        pending = state.get("pending_clarifications", []) if state else []

        report = await orch.report_generator.generate_report_async(
            user_id=user_id,
            pending_clarifications=pending,
            completed_items=[],
            min_priority=PriorityLevel.LOW,
        )

        if not cfg.get("include_critical") and not cfg.get("include_high"):
            logger.debug("User %d has all content filters disabled", user_id)
            return

        detail_level = cfg.get("detail_level", "detailed")
        message = orch.report_generator.format_report_message(
            report, include_details=(detail_level == "detailed")
        )

        from telegram import Bot

        from config import TELEGRAM_BOT_TOKEN

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        sent = await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")

        orch.logging_service.log_daily_report(
            user_id=user_id,
            report_data={
                "joplin_count": report.joplin_count,
                "google_tasks_count": report.google_tasks_count,
                "clarification_count": report.clarification_count,
                "critical_items": len(report.critical_items),
                "high_items": len(report.high_items),
                "medium_items": len(report.medium_items),
                "low_items": len(report.low_items),
                "completed_count": report.completed_count,
                "generated_by": "scheduled",
            },
        )
        logger.info(
            "Scheduled report sent to user %d: %d items, message_id=%d",
            user_id, report.total_items, sent.message_id,
        )
    except Exception as exc:
        logger.error("Failed to send scheduled report to user %d: %s", user_id, exc, exc_info=True)


def _weekly_report(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此命令的权限。")
            return

        try:
            _cleanup_completed_tasks_before_report(orch, user.id)
            logger.info("Generating on-demand weekly report for user %d", user.id)
            progress_msg = await update.message.reply_text("📊 正在生成周报…")

            ref_date: datetime | None = None
            if context.args:
                arg = context.args[0].lower()
                if arg == "last":
                    ref_date = get_user_timezone_aware_now(user.id, orch.logging_service) - timedelta(days=7)

            generator = WeeklyReportGenerator(
                joplin_client=orch.joplin_client,
                task_service=orch.task_service,
                logging_service=orch.logging_service,
            )
            report = await generator.generate_weekly_report(user.id, ref_date)
            message = generator.format_weekly_report(report)
            cfg = orch.logging_service.get_report_configuration(user.id) or _DEFAULT_CONFIG
            if cfg.get("include_project_portfolio") and orch.reorg_orchestrator:
                portfolio = await build_project_portfolio_html(orch, user.id)
                if portfolio:
                    message += "\n\n" + portfolio
            await progress_msg.delete()
            await update.message.reply_text(message, parse_mode="HTML")

            orch.logging_service.log_system_event(
                level="INFO",
                module="weekly_report",
                message=f"Generated on-demand weekly report for user {user.id}",
                extra_data={
                    "velocity": report.current.velocity,
                    "completion_rate": report.current.completion_rate,
                    "generated_by": "manual",
                },
            )
            logger.info("Weekly report sent to user %d", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 生成周报时出错，请稍后重试。")
            logger.error("Error in weekly_report handler: %s", exc, exc_info=True)

    return handler


def _monthly_report(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此命令的权限。")
            return

        try:
            _cleanup_completed_tasks_before_report(orch, user.id)

            now = get_user_timezone_aware_now(user.id, orch.logging_service)
            year, month = now.year, now.month

            if context.args:
                arg = context.args[0].strip().lower()
                if arg == "last":
                    if month == 1:
                        year, month = year - 1, 12
                    else:
                        month -= 1
                else:
                    # Parse YYYY-MM
                    parts = arg.split("-")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        year, month = int(parts[0]), int(parts[1])
                        if not (1 <= month <= 12):
                            await update.message.reply_text(
                                "用法：`/report_monthly` 或 `/report_monthly 2026-02` 或 `/report_monthly last`",
                                parse_mode="Markdown",
                            )
                            return
                    else:
                        await update.message.reply_text(
                            "用法：`/monthly_report` 或 `/monthly_report 2026-02` 或 `/monthly_report last`",
                            parse_mode="Markdown",
                        )
                        return

            logger.info("Generating monthly report for user %d: %d-%02d", user.id, year, month)
            progress_msg = await update.message.reply_text(
                f"📊 正在生成 {year}-{month:02d} 的月报…"
            )

            generator = MonthlyReportGenerator(
                joplin_client=orch.joplin_client,
                task_service=orch.task_service,
                logging_service=orch.logging_service,
                llm_orchestrator=orch.llm_orchestrator,
            )
            report = await generator.generate(user.id, year, month)
            message = generator.format_report(report)
            await progress_msg.delete()
            await update.message.reply_text(message, parse_mode="HTML")

            orch.logging_service.log_system_event(
                level="INFO",
                module="monthly_report",
                message=f"Generated monthly report for user {user.id}: {year}-{month:02d}",
                extra_data={
                    "year": year,
                    "month": month,
                    "notes_created": report.metrics.notes_created,
                    "tasks_completed": report.metrics.tasks_completed,
                },
            )
            logger.info("Monthly report sent to user %d: %d-%02d", user.id, year, month)
        except Exception as exc:
            await update.message.reply_text("❌ 生成月报时出错，请稍后重试。")
            logger.error("Error in monthly_report handler: %s", exc, exc_info=True)

    return handler


async def send_scheduled_weekly_report(orch: TelegramOrchestrator, user_id: int) -> None:
    """Callback invoked by the scheduler for weekly reports."""
    try:
        logger.info("Sending scheduled weekly report to user %d", user_id)
        _cleanup_completed_tasks_before_report(orch, user_id)

        generator = WeeklyReportGenerator(
            joplin_client=orch.joplin_client,
            task_service=orch.task_service,
            logging_service=orch.logging_service,
        )
        report = await generator.generate_weekly_report(user_id)
        message = generator.format_weekly_report(report)
        cfg = orch.logging_service.get_report_configuration(user_id) or _DEFAULT_CONFIG
        if cfg.get("include_project_portfolio") and orch.reorg_orchestrator:
            portfolio = await build_project_portfolio_html(orch, user_id)
            if portfolio:
                message += "\n\n" + portfolio

        from telegram import Bot

        from config import TELEGRAM_BOT_TOKEN

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        sent = await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")

        orch.logging_service.log_system_event(
            level="INFO",
            module="weekly_report",
            message=f"Scheduled weekly report sent to user {user_id}",
            extra_data={
                "velocity": report.current.velocity,
                "message_id": sent.message_id,
                "generated_by": "scheduled",
            },
        )
        logger.info("Scheduled weekly report sent to user %d, message_id=%d", user_id, sent.message_id)
    except Exception as exc:
        logger.error("Failed to send scheduled weekly report to user %d: %s", user_id, exc, exc_info=True)


def _configure_time(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ 用法：/report_set_time HH:MM\n示例：/report_set_time 08:00"
                )
                return

            time_str = context.args[0]
            try:
                hour, minute = map(int, time_str.split(":"))
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError()
            except Exception:
                await update.message.reply_text(
                    f"❌ 无效的时间格式：{time_str}\n使用24小时格式：HH:MM（例如：08:00, 14:30）"
                )
                return

            cfg = orch.logging_service.get_report_configuration(user.id) or {**_DEFAULT_CONFIG}
            cfg["delivery_time"] = time_str
            orch.logging_service.save_report_configuration(user.id, cfg)

            if cfg.get("enabled", True):
                tz = cfg.get("timezone", "UTC")
                scheduled = await orch.scheduler.schedule_daily_report(
                    user_id=user.id,
                    delivery_time=time_str,
                    timezone_str=tz,
                    report_callback=lambda uid: send_scheduled_report(orch, uid),
                )
                sched_line = "✓ 已安排" if scheduled else "⚠️ 安排任务失败"
                await update.message.reply_text(f"✅ 报告发送时间已设置为 {time_str}\n时区：{tz}\n{sched_line}")
            else:
                await update.message.reply_text(
                    f"✅ 报告发送时间已设置为 {time_str}\n时区：{cfg.get('timezone', 'UTC')}\n（报告当前已禁用）"
                )
            logger.info("User %d set report time to %s", user.id, time_str)
        except Exception as exc:
            await update.message.reply_text("❌ 设置报告时间出错。")
            logger.error("Error in configure_report_time: %s", exc)

    return handler


def _configure_tz(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ 用法：/report_set_timezone 时区\n"
                    "示例：US/Eastern, Europe/London, Asia/Tokyo, UTC"
                )
                return

            tz_str = context.args[0]
            try:
                import pytz
                pytz.timezone(tz_str)
            except Exception:
                await update.message.reply_text(
                    f"❌ 未知时区：{tz_str}\n示例：US/Eastern, Europe/London, Asia/Tokyo, UTC"
                )
                return

            cfg = orch.logging_service.get_report_configuration(user.id) or {**_DEFAULT_CONFIG}
            cfg["timezone"] = tz_str
            orch.logging_service.save_report_configuration(user.id, cfg)

            if cfg.get("enabled", True):
                delivery = cfg.get("delivery_time", "08:00")
                scheduled = await orch.scheduler.schedule_daily_report(
                    user_id=user.id,
                    delivery_time=delivery,
                    timezone_str=tz_str,
                    report_callback=lambda uid: send_scheduled_report(orch, uid),
                )
                sched_line = "✓ 已安排" if scheduled else "⚠️ 安排任务失败"
                await update.message.reply_text(f"✅ 时区已设置为 {tz_str}\n报告时间：{delivery}\n{sched_line}")
            else:
                await update.message.reply_text(
                    f"✅ 时区已设置为 {tz_str}\n报告时间：{cfg.get('delivery_time', '08:00')}\n（报告当前已禁用）"
                )
            logger.info("User %d set timezone to %s", user.id, tz_str)
        except Exception as exc:
            await update.message.reply_text("❌ 设置时区出错。")
            logger.error("Error in configure_report_timezone: %s", exc)

    return handler


def _toggle(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text("❌ 用法：/report_toggle_schedule on|off")
                return

            action = context.args[0].lower()
            if action not in ("on", "off", "yes", "no", "true", "false", "1", "0"):
                await update.message.reply_text("❌ 无效选项。使用：on, off, yes, no, true 或 false")
                return

            enabled = action in ("on", "yes", "true", "1")
            cfg = orch.logging_service.get_report_configuration(user.id) or {**_DEFAULT_CONFIG}
            cfg["enabled"] = enabled
            orch.logging_service.save_report_configuration(user.id, cfg)

            if enabled:
                delivery = cfg.get("delivery_time", "08:00")
                tz = cfg.get("timezone", "UTC")
                scheduled = await orch.scheduler.schedule_daily_report(
                    user_id=user.id,
                    delivery_time=delivery,
                    timezone_str=tz,
                    report_callback=lambda uid: send_scheduled_report(orch, uid),
                )
                sched_line = "✓ 任务已安排" if scheduled else "安排失败"
                await update.message.reply_text(
                    f"✅ 每日报告已启用\n安排时间：{delivery} {tz}\n{sched_line}"
                )
            else:
                cancelled = await orch.scheduler.cancel_daily_report(user.id)
                cancel_line = "✓ 任务已取消" if cancelled else "(未找到已安排的任务)"
                await update.message.reply_text(f"❌ 每日报告已禁用\n{cancel_line}")

            logger.info("User %d %s daily reports", user.id, "enabled" if enabled else "disabled")
        except Exception as exc:
            await update.message.reply_text("❌ 切换每日报告时出错。")
            logger.error("Error in toggle_daily_report: %s", exc)

    return handler


def _show_config(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            cfg = orch.logging_service.get_report_configuration(user.id)
            if not cfg:
                msg = (
                    "⚙️ 您的报告配置（默认）\n\n"
                    "状态：✅ 已启用\n"
                    "发送时间：08:00\n"
                    "时区：UTC\n\n"
                    "包含内容：\n"
                    "  • 紧急：是\n"
                    "  • 高优先级：是\n"
                    "  • 中优先级：否\n"
                    "  • Google Tasks：是\n"
                    "  • 待澄清：是\n"
                    "  • 周报中的项目组合：否\n\n"
                    "详细级别：详细\n\n"
                    "尚未设置自定义配置。\n使用命令进行自定义。"
                )
            else:
                msg = orch.report_generator.format_configuration_display(cfg)
            await update.message.reply_text(msg)
            logger.info("User %d viewed report configuration", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 获取配置时出错。")
            logger.error("Error in show_report_config: %s", exc)

    return handler


def _configure_content(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ 用法：/report_set_content 级别\n"
                    "选项：critical, high, medium, all\n"
                    "  • critical：仅紧急项目\n"
                    "  • high：紧急和高优先级\n"
                    "  • medium：紧急、高和中优先级\n"
                    "  • all：所有优先级"
                )
                return

            level = context.args[0].lower()
            if level not in ("critical", "high", "medium", "all"):
                await update.message.reply_text("❌ 无效级别。使用：critical, high, medium 或 all")
                return

            cfg = orch.logging_service.get_report_configuration(user.id) or {**_DEFAULT_CONFIG}
            cfg["include_critical"] = True
            cfg["include_high"] = level in ("high", "medium", "all")
            cfg["include_medium"] = level in ("medium", "all")
            cfg["include_low"] = level == "all"
            orch.logging_service.save_report_configuration(user.id, cfg)

            await update.message.reply_text(
                f"✅ 报告内容已设置为：{level.upper()}\n"
                "包含：\n"
                f"  • 紧急：是\n"
                f"  • 高优先级：{'是' if cfg['include_high'] else '否'}\n"
                f"  • 中优先级：{'是' if cfg['include_medium'] else '否'}\n"
                f"  • 低优先级：{'是' if cfg.get('include_low') else '否'}"
            )
            logger.info("User %d set report content level to %s", user.id, level)
        except Exception as exc:
            await update.message.reply_text("❌ 设置报告内容时出错。")
            logger.error("Error in configure_report_content: %s", exc)

    return handler


def _toggle_portfolio(orch: TelegramOrchestrator):
    """Toggle project portfolio section in weekly report (T-007)."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args or context.args[0].lower() not in ("on", "off"):
                await update.message.reply_text(
                    "❌ 用法：/report_toggle_portfolio on|off\n"
                    "  on  – 在周报中包含项目组合\n"
                    "  off – 不包含项目组合（默认）"
                )
                return

            enabled = context.args[0].lower() == "on"
            cfg = orch.logging_service.get_report_configuration(user.id) or {**_DEFAULT_CONFIG}
            cfg["include_project_portfolio"] = enabled
            orch.logging_service.save_report_configuration(user.id, cfg)

            status = "是" if enabled else "否"
            await update.message.reply_text(
                f"✅ 周报中的项目组合：{status}\n"
                "使用 /report_config 查看所有设置。"
            )
            logger.info("User %d set report include_project_portfolio to %s", user.id, enabled)
        except Exception as exc:
            await update.message.reply_text("❌ 更新设置时出错。")
            logger.error("Error in report_toggle_portfolio: %s", exc)

    return handler


def _help(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        await update.message.reply_text(
            "📊 报告命令\n\n"
            "生成报告：\n"
            "  /report_daily - 生成每日优先级报告\n"
            "  /report_weekly - 生成周报回顾\n"
            "  /report_weekly last - 回顾上周\n"
            "  /report_monthly - 生成月报回顾\n"
            "  /report_monthly 2026-02 - 特定月份\n"
            "  /report_monthly last - 上月\n\n"
            "配置发送：\n"
            "  /report_set_time <HH:MM> - 设置每日发送时间\n"
            "    示例：/report_set_time 08:00\n\n"
            "  /report_set_timezone <时区> - 设置您的时区\n"
            "    示例：/report_set_timezone US/Eastern\n"
            "    常用：US/Eastern, US/Central, US/Pacific, Europe/London, Asia/Tokyo\n\n"
            "  /report_toggle_schedule on|off - 启用/禁用自动报告\n"
            "    示例：/report_toggle_schedule on\n\n"
            "自定义内容：\n"
            "  /report_set_content <级别> - 设置最低优先级级别\n"
            "    选项：critical, high, medium, all\n"
            "    示例：/report_set_content high\n\n"
            "  /report_toggle_portfolio on|off - 在周报中包含项目组合\n"
            "    示例：/report_toggle_portfolio on\n\n"
            "查看设置：\n"
            "  /report_config - 查看您当前的配置\n\n"
            "帮助：\n"
            "  /report_help - 显示此帮助消息\n\n"
            "每日报告包含：\n"
            "• 高优先级 Joplin 笔记（标记：#urgent, #critical, #important）\n"
            "• 未完成的 Google Tasks\n"
            "• 待澄清的笔记\n"
            "• 跨所有来源的智能优先级排序\n\n"
            "周报包含：\n"
            "• 本周创建和修改的笔记\n"
            "• 已完成、待处理和逾期的 Google Tasks\n"
            "• 生产力指标和速度趋势\n"
            "• 按文件夹和星期几的细分\n"
            "• 可操作的建议"
        )
        logger.info("User %d viewed report help", user.id)

    return handler
