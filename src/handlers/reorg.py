"""
Joplin Database Reorganization handlers (FR-016):
reorg_status, reorg_init, reorg_preview, reorg_execute, enrich_notes,
reorg_history, reorg_audit_tags, reorg_detect_conflicts, reorg_help.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.security_utils import check_whitelist

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def register_reorg_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    application.add_handler(CommandHandler("project_new", _project_new(orch)))
    application.add_handler(CommandHandler("pn", _project_new(orch)))
    application.add_handler(CommandHandler("reorg_status", _status(orch)))
    application.add_handler(CommandHandler("reorg_init", _init(orch)))
    application.add_handler(CommandHandler("reorg_preview", _preview(orch)))
    application.add_handler(CommandHandler("reorg_conflicts", _detect_conflicts(orch)))
    application.add_handler(CommandHandler("reorg_detect_conflicts", _detect_conflicts(orch)))
    application.add_handler(CommandHandler("reorg_execute", _execute(orch)))
    application.add_handler(CommandHandler("reorg_history", _history(orch)))
    application.add_handler(CommandHandler("reorg_enrich", _enrich(orch)))
    application.add_handler(CommandHandler("enrich_notes", _enrich(orch)))
    application.add_handler(CommandHandler("reorg_audit_tags", _audit_tags(orch)))
    application.add_handler(CommandHandler("reorg_help", _help(orch)))


def _project_new(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        name = " ".join(context.args).strip() if context.args else ""
        if not name:
            await update.message.reply_text(
                "📁 <b>创建项目</b>\n\n"
                "用法：/project_new &lt;名称&gt; 或 /pn &lt;名称&gt;\n"
                "示例：/project_new 网站重新设计",
                parse_mode="HTML",
            )
            return

        try:
            result = await orch.reorg_orchestrator.create_project(name)
            subs = ", ".join(result["subfolders"])
            await update.message.reply_text(
                f"✅ 已创建项目 '{name}'，包含文件夹：{subs}",
                parse_mode="HTML",
            )
        except Exception as e:
            err = str(e)
            if "already exists" in err.lower():
                await update.message.reply_text(
                    f"ℹ️ {err}\n\n使用 /find 搜索其中的笔记。"
                )
            else:
                await update.message.reply_text(f"❌ 错误：{err}")
                logger.error("project_new failed: %s", e, exc_info=True)

    return handler


def _status(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            all_notes = await orch.joplin_client.get_all_notes()
            folders = await orch.joplin_client.get_folders()
            tags = await orch.joplin_client.fetch_tags()

            notes_by_folder: dict[str, int] = {}
            for note in all_notes:
                fid = note.get("parent_id", "Unknown")
                notes_by_folder[fid] = notes_by_folder.get(fid, 0) + 1

            msg = "📊 Joplin 组织状态\n\n"
            msg += f"📝 笔记：{len(all_notes)}\n"
            msg += f"📁 文件夹：{len(folders)}\n"
            msg += f"🏷️ 标签：{len(tags)}\n\n"

            if all_notes:
                msg += "📈 按文件夹的笔记：\n"
                for fid, count in sorted(notes_by_folder.items(), key=lambda x: x[1], reverse=True)[:5]:
                    name = next((f["title"] for f in folders if f["id"] == fid), "未知")
                    msg += f"  • {name}: {count} 条笔记\n"

                summary = await orch.enrichment_service.get_enrichment_summary(all_notes)
                msg += (
                    f"\n丰富进度：\n"
                    f"  • 已丰富：{summary['enriched_notes']}/{summary['total_notes']}\n"
                    f"  • 进度：{summary['enrichment_percentage']:.1f}%\n"
                )
            else:
                msg += "在 Joplin 数据库中未找到笔记\n先使用 /start 创建一些笔记\n"

            msg += "\n下一步：/reorg_init status\n或 /reorg_init roles"
            await update.message.reply_text(msg)
            logger.info("User %d viewed organization status", user.id)
        except Exception as exc:
            await update.message.reply_text(f"❌ 检查状态时出错：{exc}")
            logger.error("Error in handle_reorg_status: %s", exc, exc_info=True)

    return handler


def _init(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text(
                    "🏗️ *初始化 PARA 结构*\n\n"
                    "用法：/reorg_init <模板>\n\n"
                    "可用模板：\n"
                    "  status - 项目模板（概览、待办、执行、决策、资源、参考）\n"
                    "  roles  - 按角色组织（职业、个人、志愿）\n\n"
                    "示例：\n"
                    "  /reorg_init status\n"
                    "  /reorg_init roles\n"
                )
                return

            template = " ".join(context.args)
            available = orch.reorg_orchestrator.get_available_templates()
            if template not in available:
                await update.message.reply_text(
                    f"❌ 未知模板：{template}\n可用：{', '.join(available)}"
                )
                return

            await update.message.reply_text(f"🏗️ 正在使用模板初始化 PARA 结构：{template}")
            success = await orch.reorg_orchestrator.initialize_structure(template)

            if success:
                await update.message.reply_text(
                    f"✅ PARA 结构初始化成功！\n"
                    f"模板：{template}\n\n"
                    "项目包含 *项目模板*（概览、待办、执行、决策、资源、参考）。"
                    "添加新项目时复制该文件夹。\n"
                    "领域包含 *📓 日记*（梦境日记、斯多葛日记、其他）用于日记。\n\n"
                    "下一步：\n"
                    "1. 使用 `/reorg_preview` 查看迁移计划\n"
                    "2. 使用 `/reorg_execute` 重组您的笔记"
                )
                logger.info("User %d initialized PARA with template: %s", user.id, template)
            else:
                await update.message.reply_text("❌ 初始化 PARA 结构失败。请检查机器人日志。")
                logger.error("Failed to initialize PARA for user %d", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 初始化 PARA 结构时出错。")
            logger.error("Error in reorg_init: %s", exc)

    return handler


def _preview(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("📋 正在生成迁移计划…这可能需要一分钟…")

            plan = await orch.reorg_orchestrator.generate_migration_plan()
            summary = plan.get("summary", {})
            moves = plan.get("moves", [])

            sampled = summary.get("analysis_sample_size", len(moves))
            resp = (
                "📋 *迁移计划预览*\n\n"
                f"📊 摘要：\n"
                f"  • 总笔记数：{summary.get('total_notes', 0)}\n"
                f"  • 需要移动的笔记：{summary.get('notes_to_move', 0)}\n"
                f"  • 分析抽样：{sampled}\n\n"
            )

            if moves:
                resp += "📌 前 5 条建议移动：\n\n"
                for move in moves[:5]:
                    resp += (
                        f"• **{move.get('note_title', '无标题')}**\n"
                        f"  → {move.get('reasoning', 'AI 建议')}\n"
                    )
            else:
                resp += "✅ 未建议移动 - 您的笔记组织得很好！"

            resp += "\n\n准备好重组了吗？\n使用 `/reorg_execute` 应用所有更改"
            await update.message.reply_text(resp)
            logger.info("User %d viewed migration preview", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 生成迁移计划时出错。")
            logger.error("Error in reorg_preview: %s", exc)

    return handler


def _execute(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            dry_run = bool(context.args and context.args[0].lower() == "dry-run")

            if dry_run:
                await update.message.reply_text("🔍 试运行模式：模拟重组而不进行更改…")
            else:
                await update.message.reply_text(
                    "警告：这将重组您的笔记\n\n"
                    "此操作将把笔记移动到建议的文件夹。\n"
                    "您随时可以手动移回。\n\n"
                    "先使用 /reorg_execute dry-run 预览！"
                )

            plan = await orch.reorg_orchestrator.generate_migration_plan()
            moves = plan.get("moves", [])

            if not moves:
                await update.message.reply_text("ℹ️ 无需重组笔记。\n运行 /reorg_status 检查您的笔记。")
                return

            label = "模拟" if dry_run else "执行"
            await update.message.reply_text(f"🔄 正在{label} {len(moves)} 条笔记的重组…")

            results = await orch.reorg_orchestrator.execute_migration_plan(moves, dry_run=dry_run)

            if dry_run:
                await update.message.reply_text(
                    f"🔍 试运行结果：\n\n"
                    f"  将移动：{results.get('success', 0)} 条笔记\n\n"
                    "要实际应用更改，请运行：\n/reorg_execute\n\n"
                    "或获取更多详情：\n/reorg_preview"
                )
            else:
                tags_line = f"  添加的标签：{results.get('tags_added', 0)}\n" if results.get('tags_added', 0) > 0 else ""
                await update.message.reply_text(
                    f"✅ 重组完成！\n\n"
                    f"  ✓ 成功：{results.get('success', 0)} 条笔记\n"
                    f"  ✗ 失败：{results.get('failed', 0)} 条笔记\n"
                    f"{tags_line}\n下一步：使用 /enrich_notes 添加 AI 元数据"
                )
            logger.info("User %d executed reorganization: %s (dry_run=%s)", user.id, results, dry_run)
        except Exception as exc:
            await update.message.reply_text("❌ 执行重组时出错。")
            logger.error("Error in reorg_execute: %s", exc)

    return handler


def _enrich(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        try:
            limit = 10
            filter_unenriched = False
            if context.args:
                for arg in context.args:
                    if arg == "--unenriched-only":
                        filter_unenriched = True
                    elif arg.isdigit():
                        limit = int(arg)

            summary = await orch.enrichment_service.get_enrichment_summary()
            await update.message.reply_text(
                f"丰富状态\n"
                f"总笔记数：{summary['total_notes']}\n"
                f"已丰富：{summary['enriched_notes']}\n"
                f"待丰富：{summary['unenriched_notes']}\n"
                f"丰富进度：{summary['enrichment_percentage']:.1f}%\n"
            )

            notes = await orch.joplin_client.get_all_notes()
            if not notes:
                await update.message.reply_text("ℹ️ 未找到可丰富的笔记。")
                return

            filter_func = None
            to_process = notes
            if filter_unenriched:
                filter_func = orch.enrichment_service.get_unenriched_notes_filter()
                to_process = [n for n in notes if filter_func(n)]
                count = len(to_process)
                await update.message.reply_text(
                    f"🔍 找到 {count} 条待丰富的笔记。\n开始丰富过程…"
                )
            else:
                await update.message.reply_text(
                    f"⏳ 开始丰富（最多 {min(limit, len(notes))} 条笔记）…"
                )

            progress_interval = 5  # send a chat update every N notes
            last_sent_at = [0]  # use list so closure can mutate

            async def progress_callback(stats: Any) -> None:
                processed = stats.enriched + stats.skipped + stats.failed
                if stats.total == 0:
                    return
                # Send progress at 1st note, then every progress_interval, then at end
                should_send = (
                    processed == 1
                    or processed % progress_interval == 0
                    or processed == stats.total
                )
                if should_send and processed != last_sent_at[0]:
                    last_sent_at[0] = processed
                    msg = (
                        f"📊 Progress: {processed}/{stats.total}\n"
                        f"  ✓ Enriched: {stats.enriched}  ⊘ Skipped: {stats.skipped}  ✗ Failed: {stats.failed}"
                    )
                    try:
                        await update.message.reply_text(msg)
                    except Exception as e:
                        logger.warning("Progress callback send failed: %s", e)
                logger.debug("Enrichment progress: %d/%d", processed, stats.total)

            stats = await orch.enrichment_service.enrich_notes_batch(
                notes=notes, limit=limit, filter_func=filter_func,
                progress_callback=progress_callback,  # type: ignore[arg-type]
            )

            await update.message.reply_text(
                f"丰富完成！\n\n"
                f"结果：\n"
                f"  ✓ 已丰富：{stats.enriched} 条笔记\n"
                f"  ⊘ 跳过：{stats.skipped}（已丰富）\n"
                f"  ✗ 失败：{stats.failed} 条笔记\n"
                f"  成功率：{stats.success_rate}\n\n"
                "添加的元数据：\n"
                "  • 状态（活跃/等待/将来/完成）\n"
                "  • 优先级（紧急/高/中/低）\n"
                "  • 摘要\n"
                "  • 关键要点\n"
                "  • 建议标签"
            )
            logger.info("User %d completed batch enrichment: %d/%d", user.id, stats.enriched, stats.total)
        except Exception as exc:
            if update.message:
                await update.message.reply_text("❌ 丰富笔记时出错。")
            logger.error("Error in enrich_notes: %s", exc)

    return handler


def _history(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            entries = orch.reorg_orchestrator.get_migration_history(limit=5)
            if not entries:
                await update.message.reply_text("📋 暂无迁移历史。\n运行 /reorg_execute 重组您的笔记。")
                return

            resp = "📋 迁移历史（最近 5 条）\n\n"
            for i, entry in enumerate(entries, 1):
                ts = entry["timestamp"].split("T")[1].split(".")[0]
                icon = "✅" if entry["status"] == "success" else "⚠️"
                resp += (
                    f"{i}. {icon} {entry['operation']}\n"
                    f"   时间：{ts}\n"
                    f"   结果：{entry['details']}\n"
                    f"   项目：{entry['affected_items']}\n\n"
                )
            await update.message.reply_text(resp)
            logger.info("User %d viewed migration history", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 获取历史时出错。")
            logger.error("Error in reorg_history: %s", exc)

    return handler


def _audit_tags(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("🔍 正在审核您的标签…")
            audit = await orch.reorg_orchestrator.audit_tags()

            resp = f"📊 *标签审核报告*\n\n总标签数：{audit.get('total_tags', 0)}\n"
            dups = audit.get("duplicate_names", [])
            if dups:
                resp += "\n⚠️ 潜在重复（不区分大小写）：\n"
                for d in dups[:5]:
                    resp += f"  • {d['original']} ↔ {d['duplicate']}\n"
            else:
                resp += "\n✅ 未找到重复标签\n"
            resp += "\n💡 下一步：\n• 手动审核重复项\n• 使用 `/enrich_notes` 为笔记添加一致的标签"
            await update.message.reply_text(resp)
            logger.info("User %d viewed tag audit report", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ 审核标签时出错。")
            logger.error("Error in reorg_audit_tags: %s", exc)

    return handler


def _detect_conflicts(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("🔍 正在扫描潜在冲突…")
            plan = await orch.reorg_orchestrator.generate_migration_plan()
            moves = plan.get("moves", [])
            conflicts = await orch.reorg_orchestrator.detect_conflicts(moves)

            resp = "📋 *冲突检测报告*\n\n"
            if conflicts["total_conflicts"] == 0:
                resp += "✅ 未检测到冲突！可以安全地进行重组。"
            else:
                resp += f"⚠️ 发现 {conflicts['total_conflicts']} 个潜在冲突：\n\n"
                if conflicts["duplicate_titles_in_folder"]:
                    resp += "**重复标题：**\n"
                    for d in conflicts["duplicate_titles_in_folder"][:3]:
                        resp += f"  • '{d['title']}' 出现 {d['count']} 次\n"
                if conflicts["target_folder_issues"]:
                    resp += "\n**文件夹问题：**\n"
                    for issue in conflicts["target_folder_issues"][:3]:
                        resp += f"  • {issue['issue']}\n"
                if conflicts["tag_conflicts"]:
                    resp += "\n**标签重复：**\n"
                    for tc in conflicts["tag_conflicts"][:3]:
                        resp += f"  • '{tc['original']}' ↔ '{tc['duplicate']}'\n"
                resp += "\n下一步：\n• 手动审核冲突\n• 使用 /reorg_execute 继续\n• 或 /reorg_help 查看更多选项"

            await update.message.reply_text(resp)
            logger.info("User %d viewed conflict report: %d conflicts", user.id, conflicts["total_conflicts"])
        except Exception as exc:
            await update.message.reply_text("❌ 检测冲突时出错。")
            logger.error("Error in reorg_detect_conflicts: %s", exc)

    return handler


def _help(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        await update.message.reply_text(
            "Joplin 数据库重组命令 (FR-016)\n\n"
            "状态和诊断：\n"
            "  /reorg_status - 查看笔记数、文件夹、标签、丰富状态\n\n"
            "设置和规划：\n"
            "  /reorg_init status|roles - 初始化 PARA 文件夹结构\n"
            "  /reorg_preview - 查看迁移计划而不更改\n"
            "  /reorg_detect_conflicts - 检查潜在问题\n\n"
            "重组：\n"
            "  /reorg_execute dry-run - 预览更改而不应用\n"
            "  /reorg_execute - 应用所有重组更改\n"
            "  /reorg_history - 查看最近 5 次迁移（审计跟踪）\n\n"
            "丰富：\n"
            "  /enrich_notes [限制] [--unenriched-only] - 为笔记添加元数据\n"
            "    添加：状态、优先级、摘要、关键要点、标签\n"
            "    示例：/enrich_notes 20 --unenriched-only\n\n"
            "标签管理：\n"
            "  /reorg_audit_tags - 检查标签一致性\n\n"
            "什么是 PARA？\n"
            "• 项目：有截止日期的目标导向任务\n"
            "• 领域：长期维护的标准\n"
            "• 资源：参考材料\n"
            "• 归档：已完成的项目"
        )
        logger.info("User %d viewed reorganization help", user.id)

    return handler
