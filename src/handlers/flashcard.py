"""
Flashcard practice handlers: /flashcard, /flashcard_done, callback for ratings.

Sprint 14 - FR-033.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.flashcard_service import (
    add_cards_from_note,
    create_session,
    get_card_by_id,
    get_due_cards,
    get_stats,
    record_review,
    update_session,
)
from src.security_utils import check_whitelist, format_error_message

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

FLASHCARD_PERSONA = "FLASHCARD"


def _build_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 显示答案", callback_data="fc_show")],
    ])


def _build_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 再一次", callback_data="fc_again"),
            InlineKeyboardButton("😓 困难", callback_data="fc_hard"),
            InlineKeyboardButton("👍 良好", callback_data="fc_good"),
            InlineKeyboardButton("😊 简单", callback_data="fc_easy"),
        ],
    ])


async def _get_flashcard_note_ids(orch: TelegramOrchestrator) -> list[str]:
    """Get note IDs from notes tagged #flashcard or #practice."""
    note_ids: list[str] = []
    for tag_name in ("flashcard", "practice"):
        tag_id = await orch.joplin_client.get_tag_id_by_name(tag_name)
        if tag_id:
            notes = await orch.joplin_client.get_notes_with_tag(tag_id)
            for n in notes:
                nid = n.get("id")
                if nid and nid not in note_ids:
                    note_ids.append(nid)
    return note_ids


def register_flashcard_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register flashcard command and callback handlers."""

    async def flashcard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        args = context.args or []
        limit = 10
        if args and args[0].isdigit():
            limit = min(int(args[0]), 20)
            args = args[1:]

        # /flashcard from <note title>
        if args and args[0].lower() == "from" and len(args) >= 2:
            title_query = " ".join(args[1:]).strip()
            try:
                notes = await orch.joplin_client.search_notes(title_query, limit=5)
                if not notes:
                    await msg.reply_text(
                        format_error_message(f"没有找到匹配 '{title_query}' 的笔记。")
                    )
                    return
                note = notes[0]
                note_id = note.get("id")
                note_title = note.get("title", "无标题")
                body = note.get("body", "")
                if not body:
                    await msg.reply_text(
                        format_error_message(f"笔记 '{note_title}' 没有内容可提取。")
                    )
                    return
                pairs = await orch.llm_orchestrator.extract_flashcards_from_note(note_title, body)
                if not pairs:
                    await msg.reply_text(
                        f"在 '{note_title}' 中没有找到适合制作闪卡的内容。"
                        "尝试使用包含定义、事实或概念的笔记。"
                    )
                    return
                cards = add_cards_from_note(user.id, note_id, note_title, pairs)
                await msg.reply_text(
                    f"🧠 从 '{note_title}' 中提取了 {len(cards)} 张卡片。"
                    f"使用 /flashcard 进行练习！"
                )
            except Exception as exc:
                logger.exception("Flashcard from-note failed: %s", exc)
                await msg.reply_text(format_error_message("提取闪卡失败。"))
            return

        # /flashcard stats
        if args and args[0].lower() == "stats":
            stats = get_stats(user.id)
            await msg.reply_text(
                f"📊 **闪卡统计**\n\n"
                f"• 总卡片数：{stats['total']}\n"
                f"• 今日到期：{stats['due']}\n\n"
                f"使用 /flashcard 进行练习！",
                parse_mode="Markdown",
            )
            return

        # /flashcard help
        if args and args[0].lower() == "help":
            await msg.reply_text(
                "🧠 **闪卡练习**\n\n"
                "• `/flashcard` — 开始会话（最多 10 张卡片）\n"
                "• `/flashcard N` — 最多 N 张卡片的会话\n"
                "• `/flashcard from <标题>` — 从笔记中提取卡片\n"
                "• `/flashcard tag <标签>` — 仅练习带有该标签笔记中的卡片\n"
                "• `/flashcard folder <路径>` — 仅练习该文件夹中笔记的卡片\n"
                "• `/flashcard stats` — 到期数、总卡片数\n"
                "• `/flashcard help` — 此消息\n"
                "• `/flashcard_done` — 提前结束会话\n\n"
                "使用 #flashcard 或 #practice 标签笔记以包含它们。",
                parse_mode="Markdown",
            )
            return

        # Resolve note_ids for tag or folder filter
        note_ids: list[str] | None = None
        filter_hint: str | None = None  # for empty-result messages
        if args and args[0].lower() == "tag" and len(args) >= 2:
            tag_name = " ".join(args[1:]).strip()
            tag_id = await orch.joplin_client.get_tag_id_by_name(tag_name)
            if not tag_id:
                await msg.reply_text(
                    format_error_message(f"标签 '{tag_name}' 未找到。")
                )
                return
            notes = await orch.joplin_client.get_notes_with_tag(tag_id)
            note_ids = [n["id"] for n in notes if n.get("id")]
            filter_hint = f"标签 '{tag_name}'"
            args = []  # consumed
        elif args and args[0].lower() == "folder" and len(args) >= 2:
            path_str = " ".join(args[1:]).strip()
            path_parts = [p.strip() for p in path_str.split("/") if p.strip()]
            if not path_parts:
                await msg.reply_text(
                    format_error_message("文件夹路径不能为空。")
                )
                return
            folder_id = await orch.joplin_client.get_folder_id_by_path(path_parts)
            if not folder_id:
                await msg.reply_text(
                    format_error_message(f"文件夹 '{path_str}' 未找到。")
                )
                return
            notes = await orch.joplin_client.get_notes_in_folder(folder_id)
            note_ids = [n["id"] for n in notes if n.get("id")]
            filter_hint = f"文件夹 '{path_str}'"
            args = []  # consumed

        # Start session
        state = orch.state_manager.get_state(user.id)
        if state and state.get("active_persona") == FLASHCARD_PERSONA:
            await msg.reply_text("您已经有一个进行中的会话。使用 /flashcard_done 结束它。")
            return

        try:
            if note_ids is None:
                note_ids = await _get_flashcard_note_ids(orch)
            cards = get_due_cards(user.id, note_ids=note_ids if note_ids else None, limit=limit)
        except Exception as exc:
            logger.exception("get_due_cards failed: %s", exc)
            await msg.reply_text(format_error_message("加载闪卡失败。"))
            return

        if not cards:
            stats = get_stats(user.id)
            if filter_hint and (not note_ids or len(note_ids) == 0):
                await msg.reply_text(
                    f"没有找到带有 {filter_hint} 的笔记。"
                    "添加带有该标签/文件夹的笔记，并使用 /flashcard from <笔记> 提取卡片。"
                )
            elif stats["total"] == 0:
                await msg.reply_text(
                    "🧠 还没有闪卡。使用 #flashcard 或 #practice 标签笔记，"
                    "或使用 /flashcard from <笔记标题> 提取卡片。"
                )
            else:
                await msg.reply_text(
                    f"🎯 全都赶上了！今天没有到期的卡片。"
                    f"总卡片数：{stats['total']}。"
                )
            return

        session_id = create_session(user.id)
        queue = [c["id"] for c in cards]
        state = {
            "active_persona": FLASHCARD_PERSONA,
            "phase": "question",
            "session_id": session_id,
            "queue": queue,
            "current_index": 0,
            "cards_shown": 0,
            "cards_correct": 0,
        }
        orch.state_manager.update_state(user.id, state)

        card = get_card_by_id(queue[0], user.id)
        if not card:
            orch.state_manager.clear_state(user.id)
            await msg.reply_text(format_error_message("卡片未找到。"))
            return

        text = f"🧠 闪卡时间！您有 {len(queue)} 张卡片到期。\n\n📌 卡片 1/{len(queue)}\n\n问：{card['question']}"
        await msg.reply_text(text, reply_markup=_build_question_keyboard())

    async def flashcard_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != FLASHCARD_PERSONA:
            await msg.reply_text("没有进行中的闪卡会话。使用 /flashcard 开始一个。")
            return

        session_id = state.get("session_id")
        cards_shown = state.get("cards_shown", 0)
        cards_correct = state.get("cards_correct", 0)
        if session_id:
            update_session(session_id, cards_shown, cards_correct)
        orch.state_manager.clear_state(user.id)

        await msg.reply_text(
            f"✅ 会话结束。🎯 {cards_correct}/{cards_shown} 正确。干得好！"
        )

    async def flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            await query.answer("未授权。")
            return

        await query.answer()
        data = query.data
        state = orch.state_manager.get_state(user.id)
        if not state or state.get("active_persona") != FLASHCARD_PERSONA:
            await query.edit_message_text("会话已结束。使用 /flashcard 开始新的会话。")
            return

        queue = state.get("queue", [])
        idx = state.get("current_index", 0)
        cards_shown = state.get("cards_shown", 0)
        cards_correct = state.get("cards_correct", 0)

        if idx >= len(queue):
            orch.state_manager.clear_state(user.id)
            session_id = state.get("session_id")
            if session_id:
                update_session(session_id, cards_shown, cards_correct)
            await query.edit_message_text(
                f"🎯 会话完成！{cards_correct}/{cards_shown} 正确。做得好！"
            )
            return

        card_id = queue[idx]
        card = get_card_by_id(card_id, user.id)
        if not card:
            await query.edit_message_text(format_error_message("卡片未找到。"))
            return

        if data == "fc_show":
            # Show answer, show rating buttons
            text = (
                f"📌 卡片 {idx + 1}/{len(queue)}\n\n"
                f"问：{card['question']}\n\n"
                f"答：{card['answer']}"
            )
            state["phase"] = "answer"
            orch.state_manager.update_state(user.id, state)
            await query.edit_message_text(text, reply_markup=_build_rating_keyboard())
            return

        if data in ("fc_again", "fc_hard", "fc_good", "fc_easy"):
            rating = data.replace("fc_", "")
            record_review(user.id, card_id, rating)
            cards_shown += 1
            if rating in ("good", "easy"):
                cards_correct += 1
            state["cards_shown"] = cards_shown
            state["cards_correct"] = cards_correct
            state["current_index"] = idx + 1
            state["phase"] = "question"
            orch.state_manager.update_state(user.id, state)

            if idx + 1 >= len(queue):
                orch.state_manager.clear_state(user.id)
                session_id = state.get("session_id")
                if session_id:
                    update_session(session_id, cards_shown, cards_correct)
                await query.edit_message_text(
                    f"🎯 会话完成！{cards_correct}/{cards_shown} 正确。做得好！"
                )
                return

            next_card_id = queue[idx + 1]
            next_card = get_card_by_id(next_card_id, user.id)
            if not next_card:
                orch.state_manager.clear_state(user.id)
                await query.edit_message_text(format_error_message("卡片未找到。"))
                return

            text = f"📌 卡片 {idx + 2}/{len(queue)}\n\n问：{next_card['question']}"
            await query.edit_message_text(text, reply_markup=_build_question_keyboard())
            return

    application.add_handler(CommandHandler("flashcard", flashcard_cmd))
    application.add_handler(CommandHandler("flashcard_done", flashcard_done_cmd))
    application.add_handler(CallbackQueryHandler(flashcard_callback, pattern="^fc_"))
    logger.info("Flashcard handlers registered")
