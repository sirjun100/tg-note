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


def register_reorg_handlers(application: Any, orch: "TelegramOrchestrator") -> None:
    application.add_handler(CommandHandler("reorg_status", _status(orch)))
    application.add_handler(CommandHandler("reorg_init", _init(orch)))
    application.add_handler(CommandHandler("reorg_preview", _preview(orch)))
    application.add_handler(CommandHandler("reorg_detect_conflicts", _detect_conflicts(orch)))
    application.add_handler(CommandHandler("reorg_execute", _execute(orch)))
    application.add_handler(CommandHandler("reorg_history", _history(orch)))
    application.add_handler(CommandHandler("enrich_notes", _enrich(orch)))
    application.add_handler(CommandHandler("reorg_audit_tags", _audit_tags(orch)))
    application.add_handler(CommandHandler("reorg_help", _help(orch)))


def _status(orch: "TelegramOrchestrator"):
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

            msg = "📊 Joplin Organization Status\n\n"
            msg += f"📝 Notes: {len(all_notes)}\n"
            msg += f"📁 Folders: {len(folders)}\n"
            msg += f"🏷️ Tags: {len(tags)}\n\n"

            if all_notes:
                msg += "📈 Notes by Folder:\n"
                for fid, count in sorted(notes_by_folder.items(), key=lambda x: x[1], reverse=True)[:5]:
                    name = next((f["title"] for f in folders if f["id"] == fid), "Unknown")
                    msg += f"  • {name}: {count} notes\n"

                summary = await orch.enrichment_service.get_enrichment_summary(all_notes)
                msg += (
                    f"\nEnrichment Progress:\n"
                    f"  • Enriched: {summary['enriched_notes']}/{summary['total_notes']}\n"
                    f"  • Progress: {summary['enrichment_percentage']:.1f}%\n"
                )
            else:
                msg += "No notes found in Joplin database\nCreate some notes first with /start\n"

            msg += "\nNext: /reorg_init status\nor /reorg_init roles"
            await update.message.reply_text(msg)
            logger.info("User %d viewed organization status", user.id)
        except Exception as exc:
            await update.message.reply_text(f"❌ Error checking status: {exc}")
            logger.error("Error in handle_reorg_status: %s", exc, exc_info=True)

    return handler


def _init(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            if not context.args:
                await update.message.reply_text(
                    "🏗️ *Initialize PARA Structure*\n\n"
                    "Usage: /reorg_init <template>\n\n"
                    "Available templates:\n"
                    "  status - Project template (Overview, Backlog, Execution, Decisions, Assets, References)\n"
                    "  roles  - Organize by roles (Professional, Personal, Volunteer)\n\n"
                    "Examples:\n"
                    "  /reorg_init status\n"
                    "  /reorg_init roles\n"
                )
                return

            template = " ".join(context.args)
            available = orch.reorg_orchestrator.get_available_templates()
            if template not in available:
                await update.message.reply_text(
                    f"❌ Unknown template: {template}\nAvailable: {', '.join(available)}"
                )
                return

            await update.message.reply_text(f"🏗️ Initializing PARA structure with template: {template}")
            success = await orch.reorg_orchestrator.initialize_structure(template)

            if success:
                await update.message.reply_text(
                    f"✅ PARA structure initialized successfully!\n"
                    f"Template: {template}\n\n"
                    "Projects include *Project Template* (Overview, Backlog, Execution, Decisions, Assets, References). "
                    "Duplicate that folder when you add a new project.\n"
                    "Areas include *📓 Journaling* (Dream Journal, Stoic Journal, Other) for journals.\n\n"
                    "Next steps:\n"
                    "1. Use `/reorg_preview` to see migration plan\n"
                    "2. Use `/reorg_execute` to reorganize your notes"
                )
                logger.info("User %d initialized PARA with template: %s", user.id, template)
            else:
                await update.message.reply_text("❌ Failed to initialize PARA structure. Check bot logs.")
                logger.error("Failed to initialize PARA for user %d", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ Error initializing PARA structure.")
            logger.error("Error in reorg_init: %s", exc)

    return handler


def _preview(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("📋 Generating migration plan... This may take a minute...")

            plan = await orch.reorg_orchestrator.generate_migration_plan()
            summary = plan.get("summary", {})
            moves = plan.get("moves", [])

            sampled = summary.get("analysis_sample_size", len(moves))
            resp = (
                "📋 *Migration Plan Preview*\n\n"
                f"📊 Summary:\n"
                f"  • Total notes: {summary.get('total_notes', 0)}\n"
                f"  • Notes to move: {summary.get('notes_to_move', 0)}\n"
                f"  • Sampled for analysis: {sampled}\n\n"
            )

            if moves:
                resp += "📌 First 5 suggested moves:\n\n"
                for move in moves[:5]:
                    resp += (
                        f"• **{move.get('note_title', 'Untitled')}**\n"
                        f"  → {move.get('reasoning', 'AI suggested')}\n"
                    )
            else:
                resp += "✅ No moves suggested - your notes are well-organized!"

            resp += "\n\nReady to reorganize?\nUse `/reorg_execute` to apply all changes"
            await update.message.reply_text(resp)
            logger.info("User %d viewed migration preview", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ Error generating migration plan.")
            logger.error("Error in reorg_preview: %s", exc)

    return handler


def _execute(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            dry_run = bool(context.args and context.args[0].lower() == "dry-run")

            if dry_run:
                await update.message.reply_text("🔍 DRY-RUN MODE: Simulating reorganization without making changes...")
            else:
                await update.message.reply_text(
                    "WARNING: This will reorganize your notes\n\n"
                    "This action will move notes to their suggested folders.\n"
                    "You can always move them back manually.\n\n"
                    "Use /reorg_execute dry-run to preview first!"
                )

            plan = await orch.reorg_orchestrator.generate_migration_plan()
            moves = plan.get("moves", [])

            if not moves:
                await update.message.reply_text("ℹ️ No notes need reorganization.\nRun /reorg_status to check your notes.")
                return

            label = "simulating" if dry_run else "executing"
            await update.message.reply_text(f"🔄 {label.capitalize()} reorganization of {len(moves)} notes...")

            results = await orch.reorg_orchestrator.execute_migration_plan(moves, dry_run=dry_run)

            if dry_run:
                await update.message.reply_text(
                    f"🔍 DRY-RUN RESULTS:\n\n"
                    f"  Would move: {results.get('success', 0)} notes\n\n"
                    "To actually apply changes, run:\n/reorg_execute\n\n"
                    "Or get more details:\n/reorg_preview"
                )
            else:
                tags_line = f"  Tags added: {results.get('tags_added', 0)}\n" if results.get("tags_added", 0) > 0 else ""
                await update.message.reply_text(
                    f"✅ Reorganization Complete!\n\n"
                    f"  ✓ Success: {results.get('success', 0)} notes\n"
                    f"  ✗ Failed: {results.get('failed', 0)} notes\n"
                    f"{tags_line}\nNext: Use /enrich_notes to add AI metadata"
                )
            logger.info("User %d executed reorganization: %s (dry_run=%s)", user.id, results, dry_run)
        except Exception as exc:
            await update.message.reply_text("❌ Error executing reorganization.")
            logger.error("Error in reorg_execute: %s", exc)

    return handler


def _enrich(orch: "TelegramOrchestrator"):
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
                f"Enrichment Status\n"
                f"Total notes: {summary['total_notes']}\n"
                f"Already enriched: {summary['enriched_notes']}\n"
                f"Awaiting enrichment: {summary['unenriched_notes']}\n"
                f"Enrichment: {summary['enrichment_percentage']:.1f}%\n"
            )

            notes = await orch.joplin_client.get_all_notes()
            if not notes:
                await update.message.reply_text("ℹ️ No notes found to enrich.")
                return

            filter_func = None
            to_process = notes
            if filter_unenriched:
                filter_func = orch.enrichment_service.get_unenriched_notes_filter()
                to_process = [n for n in notes if filter_func(n)]
                count = len(to_process)
                await update.message.reply_text(
                    f"🔍 Found {count} notes awaiting enrichment.\nStarting enrichment process..."
                )
            else:
                await update.message.reply_text(
                    f"⏳ Starting enrichment (up to {min(limit, len(notes))} notes)..."
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
                notes=notes, limit=limit, filter_func=filter_func, progress_callback=progress_callback
            )

            await update.message.reply_text(
                f"Enrichment Complete!\n\n"
                f"Results:\n"
                f"  ✓ Enriched: {stats.enriched} notes\n"
                f"  ⊘ Skipped: {stats.skipped} (already enriched)\n"
                f"  ✗ Failed: {stats.failed} notes\n"
                f"  Success Rate: {stats.success_rate}\n\n"
                "Metadata Added:\n"
                "  • Status (Active/Waiting/Someday/Done)\n"
                "  • Priority (Critical/High/Medium/Low)\n"
                "  • Summary\n"
                "  • Key Takeaways\n"
                "  • Suggested Tags"
            )
            logger.info("User %d completed batch enrichment: %d/%d", user.id, stats.enriched, stats.total)
        except Exception as exc:
            if update.message:
                await update.message.reply_text("❌ Error enriching notes.")
            logger.error("Error in enrich_notes: %s", exc)

    return handler


def _history(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            entries = orch.reorg_orchestrator.get_migration_history(limit=5)
            if not entries:
                await update.message.reply_text("📋 No migration history yet.\nRun /reorg_execute to reorganize your notes.")
                return

            resp = "📋 Migration History (Last 5)\n\n"
            for i, entry in enumerate(entries, 1):
                ts = entry["timestamp"].split("T")[1].split(".")[0]
                icon = "✅" if entry["status"] == "success" else "⚠️"
                resp += (
                    f"{i}. {icon} {entry['operation']}\n"
                    f"   Time: {ts}\n"
                    f"   Result: {entry['details']}\n"
                    f"   Items: {entry['affected_items']}\n\n"
                )
            await update.message.reply_text(resp)
            logger.info("User %d viewed migration history", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ Error retrieving history.")
            logger.error("Error in reorg_history: %s", exc)

    return handler


def _audit_tags(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("🔍 Auditing your tags...")
            audit = await orch.reorg_orchestrator.audit_tags()

            resp = f"📊 *Tag Audit Report*\n\nTotal tags: {audit.get('total_tags', 0)}\n"
            dups = audit.get("duplicate_names", [])
            if dups:
                resp += "\n⚠️ Potential duplicates (case-insensitive):\n"
                for d in dups[:5]:
                    resp += f"  • {d['original']} ↔ {d['duplicate']}\n"
            else:
                resp += "\n✅ No duplicate tags found\n"
            resp += "\n💡 Next steps:\n• Review duplicates manually\n• Use `/enrich_notes` to add consistent tags to notes"
            await update.message.reply_text(resp)
            logger.info("User %d viewed tag audit report", user.id)
        except Exception as exc:
            await update.message.reply_text("❌ Error auditing tags.")
            logger.error("Error in reorg_audit_tags: %s", exc)

    return handler


def _detect_conflicts(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        try:
            await update.message.reply_text("🔍 Scanning for potential conflicts...")
            plan = await orch.reorg_orchestrator.generate_migration_plan()
            moves = plan.get("moves", [])
            conflicts = await orch.reorg_orchestrator.detect_conflicts(moves)

            resp = "📋 *Conflict Detection Report*\n\n"
            if conflicts["total_conflicts"] == 0:
                resp += "✅ No conflicts detected! Safe to proceed with reorganization."
            else:
                resp += f"⚠️ Found {conflicts['total_conflicts']} potential conflicts:\n\n"
                if conflicts["duplicate_titles_in_folder"]:
                    resp += "**Duplicate Titles:**\n"
                    for d in conflicts["duplicate_titles_in_folder"][:3]:
                        resp += f"  • '{d['title']}' appears {d['count']}x\n"
                if conflicts["target_folder_issues"]:
                    resp += "\n**Folder Issues:**\n"
                    for issue in conflicts["target_folder_issues"][:3]:
                        resp += f"  • {issue['issue']}\n"
                if conflicts["tag_conflicts"]:
                    resp += "\n**Tag Duplicates:**\n"
                    for tc in conflicts["tag_conflicts"][:3]:
                        resp += f"  • '{tc['original']}' ↔ '{tc['duplicate']}'\n"
                resp += "\nNext Steps:\n• Review conflicts manually\n• Use /reorg_execute to proceed anyway\n• Or /reorg_help for more options"

            await update.message.reply_text(resp)
            logger.info("User %d viewed conflict report: %d conflicts", user.id, conflicts["total_conflicts"])
        except Exception as exc:
            await update.message.reply_text("❌ Error detecting conflicts.")
            logger.error("Error in reorg_detect_conflicts: %s", exc)

    return handler


def _help(orch: "TelegramOrchestrator"):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return

        await update.message.reply_text(
            "Joplin Database Reorganization Commands (FR-016)\n\n"
            "Status & Diagnostics:\n"
            "  /reorg_status - View notes count, folders, tags, enrichment status\n\n"
            "Setup & Planning:\n"
            "  /reorg_init status|roles - Initialize PARA folder structure\n"
            "  /reorg_preview - See migration plan without changes\n"
            "  /reorg_detect_conflicts - Check for potential issues\n\n"
            "Reorganization:\n"
            "  /reorg_execute dry-run - Preview changes without applying\n"
            "  /reorg_execute - Apply all reorganization changes\n"
            "  /reorg_history - View last 5 migrations (audit trail)\n\n"
            "Enrichment:\n"
            "  /enrich_notes [limit] [--unenriched-only] - Add metadata to notes\n"
            "    Adds: Status, Priority, Summary, Key Takeaways, Tags\n"
            "    Example: /enrich_notes 20 --unenriched-only\n\n"
            "Tag Management:\n"
            "  /reorg_audit_tags - Review tag consistency\n\n"
            "What's PARA?\n"
            "• Projects: Goal-oriented tasks with deadlines\n"
            "• Areas: Standards maintained over time\n"
            "• Resources: Reference materials\n"
            "• Archive: Completed items"
        )
        logger.info("User %d viewed reorganization help", user.id)

    return handler
