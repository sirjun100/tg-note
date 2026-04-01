"""
Google Tasks handlers: authorization, configuration, listing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytz
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.security_utils import check_whitelist
from src.timezone_utils import get_user_timezone

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _utc_str_to_local(utc_str: str, user_id: int, logging_service: Any) -> str:
    """Convert a UTC datetime string (ISO or RFC3339) to user's local date+time string."""
    try:
        tz = pytz.timezone(get_user_timezone(user_id, logging_service))
        # Normalise: replace trailing Z, handle space vs T separator
        s = utc_str.replace("Z", "+00:00").replace(" ", "T")
        dt_utc = datetime.fromisoformat(s)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.utc.localize(dt_utc)
        return dt_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_str[:16]  # fallback: trim to YYYY-MM-DD HH:MM


def _due_to_local_date(due_str: str, user_id: int, logging_service: Any) -> str:
    """Convert a Google Tasks RFC3339 due date to the user's local date string."""
    try:
        tz = pytz.timezone(get_user_timezone(user_id, logging_service))
        s = due_str.replace("Z", "+00:00")
        dt_utc = datetime.fromisoformat(s)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.utc.localize(dt_utc)
        return dt_utc.astimezone(tz).strftime("%Y-%m-%d")
    except Exception:
        return due_str[:10]


def register_google_tasks_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    # New names (tasks_* prefix); old names kept as aliases for backward compatibility
    application.add_handler(CommandHandler("tasks_connect", _authorize(orch)))
    application.add_handler(CommandHandler("authorize_google_tasks", _authorize(orch)))
    application.add_handler(CommandHandler("tasks_verify", _verify(orch)))
    application.add_handler(CommandHandler("verify_google", _verify(orch)))
    application.add_handler(CommandHandler("tasks_config", _config(orch)))
    application.add_handler(CommandHandler("google_tasks_config", _config(orch)))
    application.add_handler(CommandHandler("tasks_status", _tasks_status(orch)))
    application.add_handler(CommandHandler("google_tasks_status", _tasks_status(orch)))
    application.add_handler(CommandHandler("tasks_set_list", _set_task_list(orch)))
    application.add_handler(CommandHandler("set_task_list", _set_task_list(orch)))
    application.add_handler(CommandHandler("tasks", _list_inbox_tasks(orch)))
    application.add_handler(CommandHandler("tasks_list", _list_inbox_tasks(orch)))
    application.add_handler(CommandHandler("list_inbox_tasks", _list_inbox_tasks(orch)))
    application.add_handler(CommandHandler("tasks_toggle_auto", _toggle_auto_tasks(orch)))
    application.add_handler(CommandHandler("toggle_auto_tasks", _toggle_auto_tasks(orch)))
    application.add_handler(CommandHandler("tasks_toggle_privacy", _toggle_privacy(orch)))
    application.add_handler(CommandHandler("toggle_privacy", _toggle_privacy(orch)))
    application.add_handler(CommandHandler("tasks_toggle_project_sync", _toggle_project_sync(orch)))
    application.add_handler(CommandHandler("toggle_project_sync", _toggle_project_sync(orch)))
    application.add_handler(CommandHandler("tasks_sync_projects", _sync_projects(orch)))
    application.add_handler(CommandHandler("sync_projects", _sync_projects(orch)))
    application.add_handler(CommandHandler("tasks_reset_project_sync", _reset_project_sync(orch)))
    application.add_handler(CommandHandler("reset_project_sync", _reset_project_sync(orch)))
    application.add_handler(CommandHandler("tasks_set_projects_folder", _set_projects_folder(orch)))
    application.add_handler(CommandHandler("set_projects_folder", _set_projects_folder(orch)))
    application.add_handler(CommandHandler("tasks_cleanup", _cleanup_completed_tasks(orch)))
    application.add_handler(CommandHandler("cleanup_completed_tasks", _cleanup_completed_tasks(orch)))
    application.add_handler(CommandHandler("tasks_sync_detail", _tasks_sync_detail(orch)))


def _authorize(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此机器人的权限。")
            return

        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()
            auth_url, state = tasks_client.get_authorization_url()

            orch.state_manager.update_state(user.id, {"google_auth_state": state})

            msg = (
                "🔐 Google Tasks 授权\n\n"
                "点击下面的链接授权机器人访问您的 Google Tasks：\n\n"
                f"{auth_url}\n\n"
                "点击链接并授权后：\n"
                "1. 您将看到一个授权码\n"
                "2. 复制授权码\n"
                "3. 使用：/tasks_verify [授权码] 发送给我\n\n"
                "示例：`/tasks_verify 4/0AY0e-g7X...`"
            )
            await update.message.reply_text(msg)
            logger.info("Google Tasks authorization initiated for user %d", user.id)
        except ValueError as exc:
            await update.message.reply_text(
                f"❌ Google Tasks 配置不正确：{exc}\n"
                "请检查您的 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET。"
            )
        except Exception as exc:
            logger.error("Error in Google Tasks authorization: %s", exc)
            await update.message.reply_text(f"❌ 授权失败：{exc}")

    return handler


def _verify(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此机器人的权限。")
            return

        if not context.args:
            await update.message.reply_text(
                "用法：`/tasks_verify [授权码]`\n\n"
                "示例：`/tasks_verify 4/0AY0e-g7X...`"
            )
            return

        auth_code = context.args[0]
        try:
            from src.google_tasks_client import GoogleTasksClient
            tasks_client = GoogleTasksClient()
            token = tasks_client.exchange_code_for_token(auth_code)

            orch.logging_service.save_google_token(str(user.id), token)

            config = {
                "enabled": True,
                "auto_create_tasks": True,
                "include_only_tagged": False,
                "task_creation_tags": [],
                "privacy_mode": False,
                "project_sync_enabled": False,
            }
            orch.logging_service.save_google_tasks_config(user.id, config)

            state = orch.state_manager.get_state(user.id)
            if state and "google_auth_state" in state:
                del state["google_auth_state"]
                if state:
                    orch.state_manager.update_state(user.id, state)
                else:
                    orch.state_manager.clear_state(user.id)

            await update.message.reply_text(
                "✅ Google Tasks 授权成功！\n\n"
                "您的机器人现在可以：\n"
                "• 从笔记自动创建任务\n"
                "• 读取您的 Google Tasks\n"
                "• 在每日/每周报告中包含任务\n\n"
                "使用以下命令配置：\n"
                "/tasks_config - 管理设置\n"
                "/tasks_status - 查看同步状态\n\n"
                "使用 /status 验证连接。"
            )
            logger.info("Google Tasks authorized for user %d", user.id)
        except ValueError as exc:
            await update.message.reply_text(f"❌ 无效的授权码或配置错误：{exc}")
            logger.error("Google Tasks verification failed: %s", exc)
        except Exception as exc:
            await update.message.reply_text(
                f"❌ 授权失败：{exc}\n\n请重试：`/tasks_connect`"
            )
            logger.error("Error in Google Tasks verification: %s", exc)

    return handler


def _config(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks 集成不可用")
            return

        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text(
                    "❌ Google Tasks 尚未授权。\n首先使用 /tasks_connect。"
                )
                return

            task_lists = orch.task_service.get_available_task_lists(str(user.id))

            msg = "⚙️ Google Tasks 配置\n\n"
            msg += f"状态：{'✅ 已启用' if cfg.get('enabled') else '❌ 已禁用'}\n"
            msg += f"自动任务创建：{'✅ 开启' if cfg.get('auto_create_tasks') else '❌ 关闭'}\n"
            msg += f"隐私模式：{'🔒 开启' if cfg.get('privacy_mode') else '🔓 关闭'}\n"
            msg += f"项目同步 (FR-034)：{'✅ 开启' if cfg.get('project_sync_enabled') else '❌ 关闭'}\n"
            msg += f"当前任务列表：{cfg.get('task_list_name', '未设置')}\n\n"

            if task_lists:
                msg += "可用的任务列表：\n"
                for idx, tl in enumerate(task_lists, 1):
                    msg += f"{idx}. {tl.get('title')} (ID: {tl.get('id')[:10]}...)\n"
                msg += "\n回复：/tasks_set_list [数字]\n"
            else:
                msg += "未找到任务列表\n"

            msg += "\n其他命令：\n"
            msg += "/tasks_toggle_auto - 开启/关闭自动任务创建\n"
            msg += "/tasks_toggle_privacy - 开启/关闭隐私模式\n"
            msg += "/tasks_toggle_project_sync - Joplin 项目作为父任务 (FR-034)\n"
            msg += "/tasks_sync_projects - 为所有项目文件夹创建父任务\n"
            msg += "/tasks_reset_project_sync - 清除映射（在重新同步到不同列表前使用）\n"
            msg += "/tasks_set_projects_folder - 选择哪个文件夹 = 项目根目录\n"
            msg += "/tasks_status - 查看同步状态\n"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ 加载配置出错：{exc}")
            logger.error("Error in google_tasks_config: %s", exc)

    return handler


def _set_task_list(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not context.args:
            await update.message.reply_text("用法：/tasks_set_list [数字]")
            return
        try:
            list_num = int(context.args[0]) - 1
            task_lists = orch.task_service.get_available_task_lists(str(user.id))
            if list_num < 0 or list_num >= len(task_lists):
                await update.message.reply_text("❌ 无效的任务列表编号")
                return
            selected = task_lists[list_num]
            orch.task_service.set_preferred_task_list(user.id, selected.get("id"), selected.get("title"))
            await update.message.reply_text(f"✅ 任务列表已更改为：{selected.get('title')}")
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in set_task_list: %s", exc)

    return handler


def _toggle_auto_tasks(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks 未授权")
                return
            enabled = not cfg.get("auto_create_tasks", True)
            orch.task_service.toggle_auto_task_creation(user.id, enabled)
            await update.message.reply_text(f"自动任务创建：{'✅ 已启用' if enabled else '❌ 已禁用'}")
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")

    return handler


def _toggle_project_sync(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks 未授权")
                return
            enabled = not cfg.get("project_sync_enabled", False)
            if orch.task_service.toggle_project_sync(user.id, enabled):
                await update.message.reply_text(
                    f"项目同步 (FR-034)：{'✅ 已启用' if enabled else '❌ 已禁用'}\n\n"
                    "开启时，来自 Projects/ 文件夹中笔记的任务将成为该项目下的子任务。"
                )
            else:
                await update.message.reply_text("❌ 更新设置失败")
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")

    return handler


def _set_projects_folder(orch: TelegramOrchestrator):
    """FR-034 选项 D：设置哪个 Joplin 文件夹是项目根目录（覆盖默认值）。"""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not orch.joplin_client:
            await update.message.reply_text("❌ Joplin 不可用")
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text(
                    "❌ Google Tasks 未配置\n\n首先使用 /tasks_connect"
                )
                return
            if not context.args:
                # Show current + list root folders to pick
                current = cfg.get("projects_folder_id")
                folders = await orch.joplin_client.get_folders()
                root_folders = [f for f in folders if not (f.get("parent_id") or "")]
                if not root_folders:
                    await update.message.reply_text("在 Joplin 中未找到根文件夹。")
                    return
                lines = [
                    "选择哪个文件夹是您的项目根目录：",
                    "",
                    "当前：" + (current or "默认（Projects / 01 - projects / project）"),
                    "",
                    "回复数字进行设置，或使用 'default' 清除覆盖：",
                ]
                for i, f in enumerate(root_folders[:15], 1):
                    fid = f.get("id", "")
                    title = f.get("title", "未知")
                    mark = " ← 当前" if fid == current else ""
                    lines.append(f"  {i}. {title}{mark}")
                lines.append("  0. 使用默认（清除覆盖）")
                await update.message.reply_text("\n".join(lines))
                orch.state_manager.update_state(user.id, {
                    "awaiting_projects_folder": True,
                    "root_folders": [(f.get("id"), f.get("title", "未知")) for f in root_folders[:15]],
                })
                return
            # Direct arg: folder ID
            folder_id = context.args[0].strip()
            if folder_id.lower() == "default":
                cfg["projects_folder_id"] = None
                orch.logging_service.save_google_tasks_config(user.id, cfg)
                await update.message.reply_text("✅ 使用默认的 Projects 文件夹（Projects / 01 - projects / project）")
                return
            folders = await orch.joplin_client.get_folders()
            if any(f.get("id") == folder_id for f in folders):
                cfg["projects_folder_id"] = folder_id
                orch.logging_service.save_google_tasks_config(user.id, cfg)
                await update.message.reply_text(f"✅ 项目根目录已设置为文件夹 ID：{folder_id[:12]}...")
            else:
                await update.message.reply_text("❌ 未知的文件夹 ID。使用不带参数的 /tasks_set_projects_folder 从列表中选择。")
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in set_projects_folder: %s", exc)

    return handler


def _sync_projects(orch: TelegramOrchestrator):
    """FR-034：为所有 Joplin 项目文件夹在 Google Tasks 中创建父任务。"""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks 集成不可用")
            return
        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks 未授权\n\n首先使用 /tasks_connect"
                )
                return
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg or not cfg.get("project_sync_enabled"):
                await update.message.reply_text(
                    "❌ 项目同步已禁用\n\n首先使用 /tasks_toggle_project_sync 启用"
                )
                return
            if not orch.reorg_orchestrator:
                await update.message.reply_text("❌ 无法访问 Joplin 文件夹")
                return
            await update.message.chat.send_action("typing")
            proj_folder_id = cfg.get("projects_folder_id")
            projects = await orch.reorg_orchestrator.get_project_folders(
                projects_folder_id=proj_folder_id
            )
            if not projects:
                await update.message.reply_text(
                    "未找到项目文件夹。\n\n"
                    "在 Joplin 中创建 Projects（或 01 - projects）下的文件夹。"
                )
                return
            # FR-034 选项 C：清理孤立映射（Joplin 中已删除的文件夹）
            folders = await orch.joplin_client.get_folders()
            folder_ids = {f.get("id", "") for f in folders}
            removed = orch.task_service.cleanup_orphaned_project_mappings(
                str(user.id), folder_ids
            )
            created, existing = orch.task_service.sync_project_parent_tasks(
                str(user.id), projects
            )
            msg = (
                f"✅ 已同步项目\n\n"
                f"已创建：{created} 个父任务\n"
                f"已存在：{existing}"
            )
            if removed > 0:
                msg += f"\n已删除：{removed} 个孤立映射"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in sync_projects: %s", exc)

    return handler


def _reset_project_sync(orch: TelegramOrchestrator):
    """清除所有项目同步映射，以便下次 /sync_projects 创建新的父任务。"""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks 集成不可用")
            return
        try:
            count = orch.task_service.reset_project_sync(user.id)
            msg = (
                f"✅ 已清除 {count} 个项目同步映射。\n\n"
                "下一步：\n"
                "1. 从 Google Tasks 中的错误列表中删除旧的项目父任务（如果有）\n"
                "2. 运行 /tasks_set_list [数字] 选择正确的列表（例如 Projects）\n"
                "3. 运行 /tasks_sync_projects 在正确的列表中创建新的父任务"
            )
            await update.message.reply_text(msg)
            logger.info("Reset project sync for user %d: cleared %d mappings", user.id, count)
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in reset_project_sync: %s", exc)

    return handler


def _toggle_privacy(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg:
                await update.message.reply_text("❌ Google Tasks 未授权")
                return
            enabled = not cfg.get("privacy_mode", False)
            orch.task_service.toggle_privacy_mode(user.id, enabled)
            await update.message.reply_text(f"隐私模式：{'🔒 已启用' if enabled else '🔓 已禁用'}")
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")

    return handler


def _tasks_status(orch: TelegramOrchestrator):
    """US-059：GTD 个人生产力座舱 — 替代同步诊断。"""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "📋 Google Tasks 尚未连接。\n使用 /tasks_connect 链接您的账户。"
                )
                return

            if not orch.task_service:
                await update.message.reply_text("❌ Google Tasks 集成不可用")
                return

            data = orch.task_service.get_dashboard_data(str(user.id))
            if data is None:
                await update.message.reply_text(
                    "📋 Google Tasks 尚未连接。\n使用 /tasks_connect 链接您的账户。"
                )
                return

            overdue = data["overdue"]
            due_today = data["due_today"]
            due_week = data["due_week"]
            inbox_count = data["inbox_count"]
            last_sync = data.get("last_sync", "")
            next_task = data.get("next_task")

            # 激励性空状态
            if not overdue and not due_today and inbox_count == 0:
                msg = "✅ <b>您一切都井井有条。</b>\n"
                msg += "无过期 · 今日无到期 · 收件箱清空\n"
                if next_task:
                    next_title = next_task.get("title", "无标题")
                    next_due = next_task.get("due", "")[:10]
                    msg += f"\n📆 下一个：{next_title}"
                    if next_due:
                        msg += f" ({next_due})"
                sync_line = "\n\n✅ Google Tasks 已连接"
                if last_sync:
                    sync_line += f" · 上次同步：{last_sync}"
                msg += sync_line
                await update.message.reply_text(msg, parse_mode="HTML")
                return

            lines: list[str] = []

            # 第 1 部分 — 需要操作（过期）
            if overdue:
                days_overdue_fn = _days_overdue_label
                lines.append(f"⚠️ <b>{len(overdue)} 个已过期</b> — 现在需要操作")
                for task in overdue[:3]:
                    title = task.get("title", "无标题")
                    due_str = task.get("due", "")
                    label = days_overdue_fn(due_str) if due_str else ""
                    lines.append(f"  • {title}{label}")
                if len(overdue) > 3:
                    lines.append(f"  +{len(overdue) - 3} 个更多过期")
            else:
                lines.append("✅ 全部正常 — 无过期")

            lines.append("")

            # 第 2 部分 — 今日
            if due_today:
                lines.append(f"📅 <b>{len(due_today)} 个今日到期</b>")
                for task in due_today[:5]:
                    title = task.get("title", "无标题")
                    lines.append(f"  • {title}")
                if len(due_today) > 5:
                    lines.append(f"  +{len(due_today) - 5} 个更多今日")
            else:
                lines.append("📅 今日无安排 — 使用 /task 添加一个")

            lines.append("")

            # 第 3 部分 — 本周
            if due_week:
                lines.append(f"📆 <b>{len(due_week)} 个本周到期</b>")
                for task in due_week[:5]:
                    title = task.get("title", "无标题")
                    due_date = task.get("due", "")[:10]
                    lines.append(f"  • {title} ({due_date})")
                if len(due_week) > 5:
                    lines.append(f"  +{len(due_week) - 5} 个更多本周")
            else:
                lines.append("📆 本周无其他到期")

            lines.append("")

            # 第 4 部分 — 收件箱
            if inbox_count > 0:
                if inbox_count > 5:
                    lines.append(f"📥 <b>收件箱：{inbox_count} 个未分类任务</b> — 是时候快速查看了")
                else:
                    lines.append(f"📥 收件箱：{inbox_count} 个未分类任务")
            # 其他情况：全部正常（已在上面处理）

            # 第 5 部分 — 系统健康（单行，始终在最后）
            failed_syncs = orch.logging_service.get_failed_syncs(user.id)
            if failed_syncs:
                health = f"⚠️ {len(failed_syncs)} 个同步错误 — 使用 /tasks_sync_detail 查看更多"
            else:
                health = "✅ Google Tasks 已连接"
                if last_sync:
                    health += f" · 上次同步：{last_sync}"
            lines.append("")
            lines.append(health)

            await update.message.reply_text("\n".join(lines), parse_mode="HTML")

        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in tasks_status cockpit: %s", exc)

    return handler


def _days_overdue_label(due_str: str) -> str:
    """为到期日期字符串返回 ' · 已过期 N 天' 字符串。"""
    try:
        from datetime import date

        from src.timezone_utils import get_now_in_default_tz
        due_date = date.fromisoformat(due_str[:10])
        delta = (get_now_in_default_tz().date() - due_date).days
        if delta == 1:
            return " · 已过期 1 天"
        elif delta > 1:
            return f" · 已过期 {delta} 天"
    except Exception:
        pass
    return ""


def _tasks_sync_detail(orch: TelegramOrchestrator):
    """旧的 /tasks_status 诊断输出，现在在 /tasks_sync_detail。"""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks 未授权\n\n使用 /tasks_connect 设置访问"
                )
                return

            valid, err = orch.task_service.validate_google_token(user.id)
            if not valid:
                await update.message.reply_text(
                    f"❌ {err}\n\n使用 /tasks_connect 重新连接。"
                )
                return

            status = orch.task_service.get_task_sync_status(user.id)
            msg = "📊 Google Tasks 同步详情\n\n"
            msg += f"总同步：{status.get('total_synced', 0)}\n"
            msg += f"✅ 成功：{status.get('success_count', 0)}\n"
            msg += f"❌ 失败：{status.get('failed_count', 0)}\n\n"
            if status.get("recent_syncs"):
                msg += "最近的同步：\n"
                for sync in status["recent_syncs"][:3]:
                    action = sync.get("action", "未知")
                    icon = "✅" if sync.get("sync_result") == "success" else "❌"
                    raw_ts = sync.get("created_at", "")
                    ts = _utc_str_to_local(raw_ts, user.id, orch.logging_service) if raw_ts else "N/A"
                    msg += f"{icon} {action} - {ts}\n"
            if status.get("failed_syncs"):
                msg += f"\n⚠️ 失败的同步：{len(status['failed_syncs'])}\n"
                for sync in status["failed_syncs"][:2]:
                    msg += f"• {sync.get('error_message', '未知错误')}\n"
            await update.message.reply_text(msg)
        except Exception as exc:
            await update.message.reply_text(f"❌ 错误：{exc}")
            logger.error("Error in tasks_sync_detail: %s", exc)

    return handler


def _list_inbox_tasks(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks 集成不可用")
            return

        try:
            token = orch.logging_service.load_google_token(str(user.id))
            if not token:
                await update.message.reply_text(
                    "❌ Google Tasks 未授权\n\n使用 /tasks_connect 设置访问"
                )
                return

            cfg = orch.logging_service.get_google_tasks_config(user.id)
            if not cfg or not cfg.get("enabled"):
                await update.message.reply_text("❌ Google Tasks 已禁用")
                return

            task_list_id = cfg.get("task_list_id")
            tasks_client = orch.task_service.tasks_client
            tasks_client.set_token(
                token,
                token_updater=lambda t: orch.logging_service.save_google_token(str(user.id), t),
            )

            if not task_list_id:
                try:
                    task_lists = tasks_client.get_task_lists()
                    if tasks_client.token and tasks_client.token != token:
                        orch.logging_service.save_google_token(str(user.id), tasks_client.token)
                    if not task_lists:
                        await update.message.reply_text(
                            "❌ 未找到 Google Tasks 列表\n\n"
                            "请在 Google Tasks 中创建一个任务列表（https://calendar.google.com）"
                        )
                        return
                    task_list_id = task_lists[0]["id"]
                except Exception as exc:
                    await update.message.reply_text(f"❌ 获取任务列表出错：{exc}")
                    return

            tasks = tasks_client.get_tasks(task_list_id, show_completed=False)
            if tasks_client.token and tasks_client.token != token:
                orch.logging_service.save_google_token(str(user.id), tasks_client.token)

            if not tasks:
                await update.message.reply_text("📭 Google Tasks 中没有待处理任务")
                return

            task_list_name = cfg.get("task_list_name", "我的任务")
            msg = f"📋 Google Tasks - {task_list_name}（{len(tasks)} 个待处理）\n\n"
            for i, task in enumerate(tasks, 1):
                title = task.get("title", "无标题")
                due = task.get("due", "")
                due_str = f"（到期：{_due_to_local_date(due, user.id, orch.logging_service)}）" if due else ""
                icon = "✅" if task.get("status") == "completed" else "⭕"
                msg += f"{i}. {icon} {title}{due_str}\n"

            await update.message.reply_text(msg)
            logger.info("Listed %d Google Tasks for user %d", len(tasks), user.id)
        except Exception as exc:
            await update.message.reply_text(f"❌ 列出任务出错：{exc}")
            logger.error("Error in list_inbox_tasks: %s", exc)

    return handler


def _cleanup_completed_tasks(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await update.message.reply_text("❌ 您没有使用此机器人的权限。")
            return

        if not orch.task_service:
            await update.message.reply_text("❌ Google Tasks 未配置。")
            return

        token = orch.logging_service.load_google_token(str(user.id))
        if not token:
            await update.message.reply_text(
                "❌ Google Tasks 未授权\n\n使用 /authorize_google_tasks 设置访问"
            )
            return

        days = 30
        if context.args:
            try:
                days = int(context.args[0])
                if days < 1 or days > 365:
                    raise ValueError("天数必须在 1–365 之间")
            except ValueError:
                await update.message.reply_text(
                    "用法：/tasks_cleanup [天数]\n"
                    "删除超过 N 天的已完成任务（默认：30）。\n"
                    "示例：/tasks_cleanup 30"
                )
                return

        await update.message.chat.send_action("typing")
        deleted, errors = orch.task_service.delete_completed_tasks_older_than(
            str(user.id), days=days
        )
        if errors > 0:
            msg = f"🧹 已清理 {deleted} 个超过 {days} 天的已完成任务。\n⚠️ {errors} 个删除失败。"
        else:
            msg = f"🧹 已清理 {deleted} 个超过 {days} 天的已完成任务。"
        await update.message.reply_text(msg)
        logger.info("User %d cleaned up %d completed tasks (errors: %d)", user.id, deleted, errors)

    return handler
