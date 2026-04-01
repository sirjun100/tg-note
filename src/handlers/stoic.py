"""
Stoic Journal handlers: /stoic, /stoic morning, /stoic evening, /stoic_done,
/stoic_quick, /stoic_review.
Sprint 18: mood check-in, quote priming, question rotation, self-compassion,
streak tracking, /stoic quick mode, /stoic review weekly synthesis, US-042
"What I Learned Today".
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes

from src.exceptions import GoogleAuthError
from src.security_utils import check_whitelist, format_error_message
from src.timezone_utils import get_current_date_str, get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

STOIC_JOURNAL_PATH = ["01 - Areas", "📓 Journaling", "Stoic Journal"]
STOIC_TAGS = ["stoic", "journal", "daily"]

_STOIC_IMAGE_MARKER = "<!-- stoic-image -->"
_pending_stoic_image_tasks: dict[int, asyncio.Task] = {}

# Preference keys
_PREF_STREAK = "stoic_streak"
_PREF_LAST_ENTRY = "stoic_last_entry_date"

# Quick mode question counts per phase
_QUICK_MORNING_COUNT = 2  # intention + priorities #1
_QUICK_EVENING_COUNT = 2  # one win + gratitude


# ---------------------------------------------------------------------------
# Quote loading (T-004)
# ---------------------------------------------------------------------------

def _load_stoic_quotes() -> dict[str, list[str]]:
    """Load quotes from stoic_quotes.md; return {morning: [...], evening: [...]}."""
    path = Path(__file__).parent.parent / "prompts" / "stoic_quotes.md"
    result: dict[str, list[str]] = {"morning": [], "evening": []}
    if not path.exists():
        result["morning"] = ["Marcus Aurelius: \"Confine yourself to the present.\""]
        result["evening"] = ["Seneca: \"Let us go to our sleep with joy and gladness; let us say 'I have lived today.'\""]
        return result
    current: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "## MORNING":
            current = result["morning"]
        elif stripped == "## EVENING":
            current = result["evening"]
        elif stripped.startswith("*") or not stripped:
            continue
        elif current is not None and stripped:
            current.append(stripped)
    return result


def _daily_quote(mode: str) -> str:
    """Pick a quote for today's session, rotating daily."""
    quotes = _load_stoic_quotes()
    pool = quotes.get(mode, quotes["morning"])
    if not pool:
        return ""
    # Use UTC ordinal for consistent daily rotation across timezones
    idx = datetime.now(UTC).toordinal() % len(pool)
    return pool[idx]


# ---------------------------------------------------------------------------
# Template loading with variant rotation (T-003)
# ---------------------------------------------------------------------------

def _parse_variant_block(lines: list[str]) -> list[str]:
    """
    Given lines that may have VARIANT_0/1/2 prefixes, pick one variant per
    question slot using today's date as seed (so same day = same questions).
    A new slot begins when VARIANT_0 is seen after variants have already been
    collected, or after a blank line.  Lines without VARIANT_ prefix are
    returned as-is.
    """
    slot_seed = datetime.now(UTC).toordinal()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("VARIANT_"):
            # Collect variants for this slot; VARIANT_0 after non-empty
            # variants starts the next slot.
            variants: list[str] = []
            while i < len(lines):
                text = lines[i].strip()
                if not text.startswith("VARIANT_"):
                    break
                # VARIANT_0 after we already have variants → new slot
                if text.startswith("VARIANT_0:") and variants:
                    break
                colon = text.index(":")
                variants.append(text[colon + 2:])
                i += 1
            if variants:
                chosen = variants[slot_seed % len(variants)]
                result.append(chosen)
        else:
            result.append(line)
            i += 1
    return result


def _load_stoic_template() -> tuple[list[str], list[str], str]:
    """Load prompts/stoic_journal_template.md; return (morning_questions, evening_questions, body_template).
    Applies date-seeded question rotation for VARIANT_ lines."""
    path = Path(__file__).parent.parent / "prompts" / "stoic_journal_template.md"
    if not path.exists():
        return (
            ["What is your intention for today?", "What will you focus on?"],
            ["What went well?", "What did you control?", "What are you grateful for?"],
            "# {{DATE}} - Daily Stoic Reflection\n\n## Morning Reflection\n\n{{MORNING_CONTENT}}\n\n## Evening Reflection\n\n{{EVENING_CONTENT}}",
        )
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 1)
    if len(parts) < 2:
        return (
            ["What is your intention for today?"],
            ["What went well today?"],
            "# {{DATE}} - Daily Stoic Reflection\n\n{{MORNING_CONTENT}}\n\n{{EVENING_CONTENT}}",
        )
    block, body_template = parts[0].strip(), parts[1].strip()
    morning_raw: list[str] = []
    evening_raw: list[str] = []
    current: list[str] | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.upper() == "MORNING_QUESTIONS:":
            current = morning_raw
            continue
        if stripped.upper() == "EVENING_QUESTIONS:":
            current = evening_raw
            continue
        if current is not None:
            current.append(line)

    morning_questions = _parse_variant_block(morning_raw)
    evening_questions = _parse_variant_block(evening_raw)

    if not morning_questions:
        morning_questions = ["What is your intention for today?"]
    if not evening_questions:
        evening_questions = ["What went well today?"]
    return morning_questions, evening_questions, body_template


# ---------------------------------------------------------------------------
# Answer helpers
# ---------------------------------------------------------------------------

def _get_answer(answers: list[dict[str, str]], index: int) -> str:
    if index < 0 or index >= len(answers):
        return ""
    return (answers[index].get("a") or "").strip()


# ---------------------------------------------------------------------------
# Mood check-in (T-001)
# ---------------------------------------------------------------------------

_MOOD_QUESTION = (
    "你现在感觉如何？"
    "（例如：精力充沛、焦虑、充满希望、沮丧、平静、分散、清晰）"
)
_ENERGY_QUESTION = "能量水平：1（疲惫）→ 5（巅峰）。只需输入数字。"

_CHECKIN_STEP_MOOD = 0
_CHECKIN_STEP_ENERGY = 1
_CHECKIN_DONE = 2


def _quick_replies_for_question(question: str) -> ReplyKeyboardMarkup | None:
    """
    Return a ReplyKeyboardMarkup with context-appropriate suggestions for a question,
    or None if no suggestions are relevant.  (US-053)
    """
    q = question.lower()

    # Energy rating
    if "energy" in q and ("1" in q or "rate" in q or "scale" in q or "level" in q):
        rows = [[KeyboardButton(str(i)) for i in range(1, 6)]]
        return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

    # Mood / how are you feeling
    if "mood" in q or "feeling" in q or "emotion" in q or "how are you" in q:
        rows = [
            [KeyboardButton("很好 😊"), KeyboardButton("一般 😐"), KeyboardButton("低落 😔")],
            [KeyboardButton("精力充沛 ⚡"), KeyboardButton("有压力 😤"), KeyboardButton("感恩 🙏")],
        ]
        return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

    # Yes / No / Skip questions
    if any(kw in q for kw in ("did you", "were you", "have you", "did your", "skip")):
        rows = [[KeyboardButton("是"), KeyboardButton("否"), KeyboardButton("跳过")]]
        return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

    # All other questions get a Skip button only
    rows = [[KeyboardButton("跳过")]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def _format_checkin_section(mood: str, energy: str) -> str:
    """Format check-in as a note section."""
    lines = ["## 🔎 签到", ""]
    if mood:
        lines.append(f"- **心情**：{mood}")
    if energy:
        lines.append(f"- **能量**：{energy}/5")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Note formatting (updated for new question order with self-compassion + learnings)
# ---------------------------------------------------------------------------

def _format_morning_content(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    """Fill morning template with answers."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")
    professional = _get_answer(answers, 0)
    personal = _get_answer(answers, 1)
    obstacle = _get_answer(answers, 2)
    greater_goals = _get_answer(answers, 3)
    p1 = _get_answer(answers, 4)
    p2 = _get_answer(answers, 5)
    p3 = _get_answer(answers, 6)

    lines = [
        f"### 🌞 早晨 ({ts})",
        "",
        "- **职业目标：**",
        f"  {professional}" if professional else "  -",
        "",
        "- **个人目标：**",
        f"  {personal}" if personal else "  -",
        "",
        "- **障碍与应对：**",
        f"  {obstacle}" if obstacle else "  -",
        "",
        "- **更宏大的目标：**",
        f"  {greater_goals}" if greater_goals else "  -",
        "",
        "- **三大优先事项：**",
        f"  1. {p1}" if p1 else "  1. -",
        f"  2. {p2}" if p2 else "  2. -",
        f"  3. {p3}" if p3 else "  3. -",
    ]
    return "\n".join(lines)


def _format_evening_content(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    """Fill evening template.
    New question order (Sprint 18):
      0: priorities completed
      1: professional wins
      2: personal wins
      3: what went wrong
      4: self-compassion (NEW)
      5: within control
      6: progress toward goals
      7: gratitude
      8: what I learned today (US-042)
      9: tomorrow
    """
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")

    priorities_completed = _get_answer(answers, 0)
    prof_wins = _get_answer(answers, 1)
    personal_wins = _get_answer(answers, 2)
    went_wrong = _get_answer(answers, 3)
    self_compassion = _get_answer(answers, 4)
    control = _get_answer(answers, 5)
    progress = _get_answer(answers, 6)
    gratitude = _get_answer(answers, 7)
    learned = _get_answer(answers, 8)
    tomorrow = _get_answer(answers, 9)

    lines = [
        f"### 🌙 晚上 ({ts})",
        "",
        "- **早晨的优先事项完成了吗？**",
        f"  {priorities_completed}" if priorities_completed else "  -",
        "",
        "- **进展顺利的事（职业）：**",
        f"  {prof_wins}" if prof_wins else "  -",
        "",
        "- **进展顺利的事（个人）：**",
        f"  {personal_wins}" if personal_wins else "  -",
        "",
        "- **出错的事/将纠正：**",
        f"  {went_wrong}" if went_wrong else "  -",
        "",
        "- **自我关怀：**",
        f"  {self_compassion}" if self_compassion else "  -",
        "",
        "- **在我控制之内/之外：**",
        f"  {control}" if control else "  -",
        "",
        "- **朝更宏大目标的进展：**",
        f"  {progress}" if progress else "  -",
        "",
        "- **感恩的事：**",
        f"  {gratitude}" if gratitude else "  -",
    ]

    if learned and learned.lower() not in ("-", "skip", ""):
        lines += [
            "",
            "### 📚 我今天学到了什么",
            "",
            f"  {learned}",
        ]

    lines += [
        "",
        "- **明天：**",
        f"  {tomorrow}" if tomorrow else "  -",
    ]
    return "\n".join(lines)


def _format_section(mode: str, answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    if mode == "morning":
        return _format_morning_content(answers, user_id, orch)
    return _format_evening_content(answers, user_id, orch)


# ---------------------------------------------------------------------------
# Quick-mode formatting (T-007)
# ---------------------------------------------------------------------------

def _format_quick_morning(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")
    intention = _get_answer(answers, 0)
    priority = _get_answer(answers, 1)
    lines = [
        f"### 🌞 早晨 — 快速 ({ts})",
        "",
        "- **意图：**",
        f"  {intention}" if intention else "  -",
        "",
        "- **#1 优先事项：**",
        f"  {priority}" if priority else "  -",
    ]
    return "\n".join(lines)


def _format_quick_evening(answers: list[dict[str, str]], user_id: int, orch: TelegramOrchestrator) -> str:
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    ts = now.strftime("%H:%M")
    win = _get_answer(answers, 0)
    gratitude = _get_answer(answers, 1)
    lines = [
        f"### 🌙 晚上 — 快速 ({ts})",
        "",
        "- **一件胜利：**",
        f"  {win}" if win else "  -",
        "",
        "- **感恩的事：**",
        f"  {gratitude}" if gratitude else "  -",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Morning priorities extraction
# ---------------------------------------------------------------------------

def _extract_morning_priorities(note_body: str) -> list[str]:
    import re
    match = re.search(r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)", note_body, re.DOTALL)
    if not match:
        return []
    section = match.group(0)
    priorities: list[str | None] = [None, None, None]
    for m in re.finditer(r"^\s*([123])\.\s+(.+)$", section, re.MULTILINE):
        num = int(m.group(1))
        text = (m.group(2) or "").strip()
        if text and text != "-":
            priorities[num - 1] = text
    return [p for p in priorities if p is not None]


def _empty_morning_placeholder() -> str:
    return (
        "### 🌞 早晨\n\n"
        "- **职业目标：**\n  -\n\n"
        "- **个人目标：**\n  -\n\n"
        "- **障碍与应对：**\n  -\n\n"
        "- **更宏大的目标：**\n  -\n\n"
        "- **三大优先事项：**\n  1. -\n  2. -\n  3. -"
    )


def _empty_evening_placeholder() -> str:
    return (
        "### 🌙 晚上\n\n"
        "- **早晨的优先事项完成了吗？**\n  -\n\n"
        "- **进展顺利的事（职业）：**\n  -\n\n"
        "- **进展顺利的事（个人）：**\n  -\n\n"
        "- **出错的事/将纠正：**\n  -\n\n"
        "- **自我关怀：**\n  -\n\n"
        "- **在我控制之内/之外：**\n  -\n\n"
        "- **朝更宏大目标的进展：**\n  -\n\n"
        "- **感恩的事：**\n  -\n\n"
        "- **明天：**\n  -"
    )


# ---------------------------------------------------------------------------
# Streak tracking (T-006)
# ---------------------------------------------------------------------------

def _update_streak(orch: TelegramOrchestrator, user_id: int) -> int:
    """Increment streak if first entry today, reset if gap > 1 day. Returns new streak."""
    # DEF-030: use user's local date, not UTC
    now_local = get_user_timezone_aware_now(user_id, orch.logging_service)
    today = now_local.date().isoformat()
    last = orch.state_manager.get_user_pref(user_id, _PREF_LAST_ENTRY)
    streak_str = orch.state_manager.get_user_pref(user_id, _PREF_STREAK) or "0"
    streak = int(streak_str) if streak_str.isdigit() else 0

    if last == today:
        # Already journaled today — streak unchanged
        return streak

    if last:
        try:
            last_date = datetime.fromisoformat(last).date()
            today_date = now_local.date()
            gap = (today_date - last_date).days
            streak = streak + 1 if gap == 1 else 1
        except ValueError:
            streak = 1
    else:
        streak = 1

    orch.state_manager.set_user_pref(user_id, _PREF_STREAK, str(streak))
    orch.state_manager.set_user_pref(user_id, _PREF_LAST_ENTRY, today)
    return streak


def _streak_message(streak: int, mode: str, is_quick: bool = False) -> str:
    prefix = "⚡ 快速记录" if is_quick else "📓 斯多葛反思"
    if streak == 1:
        return f"{prefix}已保存。第 1 天 — 每段旅程都从这里开始。"
    elif streak < 7:
        return f"{prefix}已保存。🔥 连续 {streak} 天！您正在建立习惯。"
    elif streak < 30:
        return f"{prefix}已保存。🔥 连续 {streak} 天！坚持是成长的基础。"
    else:
        return f"{prefix}已保存。🔥 连续 {streak} 天！您是真正坚持的 1%。"


# ---------------------------------------------------------------------------
# Tomorrow task creation
# ---------------------------------------------------------------------------

def _get_tomorrow_rfc3339(user_id: int, orch: TelegramOrchestrator) -> str:
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow.isoformat()


def _get_tomorrow_answer(answers: list[dict[str, str]]) -> str | None:
    """Extract tomorrow answer — index 9 in full evening (10 questions)."""
    if len(answers) > 9:
        text = (answers[9].get("a") or "").strip()
        if text and text not in ("-", "skip"):
            return text
    return None


async def _create_tomorrow_task_from_stoic(
    orch: TelegramOrchestrator, user_id: int, mode: str, answers: list[dict[str, str]], message: Message
) -> bool:
    if mode != "evening":
        return False
    tomorrow_text = _get_tomorrow_answer(answers)
    if not tomorrow_text or not orch.task_service:
        return False
    try:
        due = _get_tomorrow_rfc3339(user_id, orch)
        created = orch.task_service.create_task_with_metadata(
            title=tomorrow_text,
            user_id=str(user_id),
            notes="来自斯多葛日记晚上反思",
            due_date=due,
        )
        if created:
            await message.reply_text("📋 已在 Google Tasks 中为明天创建任务。")
            return True
    except GoogleAuthError:
        await message.reply_text(format_error_message(
            "🔑 Google 令牌已过期或已撤销。使用 /tasks_connect 重新验证。"
        ))
        return False
    except Exception as exc:
        logger.debug("Could not create Stoic tomorrow task: %s", exc)
    return False


# ---------------------------------------------------------------------------
# Note body helpers
# ---------------------------------------------------------------------------

def _build_full_body(body_template: str, date_str: str, morning_content: str, evening_content: str) -> str:
    return (
        body_template.replace("{{DATE}}", date_str)
        .replace("{{MORNING_CONTENT}}", morning_content or _empty_morning_placeholder())
        .replace("{{EVENING_CONTENT}}", evening_content or _empty_evening_placeholder())
    )


def _replace_section(body: str, new_section: str, mode: str) -> str:
    import re
    pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
    flags = re.DOTALL
    return re.sub(pattern, new_section.rstrip(), body, flags=flags)


def _check_section_exists(note_body: str, mode: str) -> bool:
    import re
    pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
    match = re.search(pattern, note_body, re.DOTALL)
    if not match:
        return False
    section = match.group(0)
    for line in section.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("###") or (stripped.startswith("- **") and stripped.endswith(":**")) or stripped == "-":
            continue
        return True
    return False


def _embed_stoic_image_in_body(note_body: str, resource_id: str) -> str:
    """Insert Stoic image below the top title, idempotently via marker."""
    if not note_body:
        return note_body
    if _STOIC_IMAGE_MARKER in note_body:
        return note_body
    image_block = f"{_STOIC_IMAGE_MARKER}\n\n![Stoic reflection](:/{resource_id})"
    lines = note_body.split("\n", 2)
    if not lines:
        return note_body
    if lines[0].lstrip().startswith("#"):
        head = lines[0]
        rest = "\n".join(lines[1:]) if len(lines) > 1 else ""
        rest = rest.lstrip("\n")
        return f"{head}\n\n{image_block}\n\n{rest}".rstrip() + "\n"
    return f"{image_block}\n\n{note_body}".rstrip() + "\n"


async def _add_stoic_image_async(
    orch: TelegramOrchestrator,
    user_id: int,
    note_id: str,
    mode: str,
    reflection_markdown: str,
    message: Message,
) -> None:
    """Background task: generate image, upload resource, embed into note body."""
    try:
        from src.stoic_image import generate_stoic_image

        img_msg = await message.reply_text("🖼️ 正在生成斯多葛图像…")
        data_url, reason = await generate_stoic_image(mode, reflection_markdown)
        if not data_url or "," not in data_url:
            await img_msg.edit_text("⚠️ 无法为此反思生成图像。")
            if reason:
                logger.info("Stoic image skipped (%s)", reason)
            return

        header, b64_data = data_url.split(",", 1)
        mime = "image/png"
        if "image/" in header:
            mime = header.split(":", 1)[1].split(";", 1)[0].strip()
        image_bytes = base64.b64decode(b64_data)
        resource = await orch.joplin_client.create_resource(
            image_bytes,
            filename=f"stoic_{mode}.png",
            mime_type=mime,
        )
        resource_id = resource.get("id")
        if not resource_id:
            await img_msg.edit_text("⚠️ 无法将图像附加到 Joplin。")
            return

        full_note = await orch.joplin_client.get_note(note_id)
        body = (full_note.get("body") or "").strip()
        new_body = _embed_stoic_image_in_body(body, resource_id)
        await orch.joplin_client.update_note(note_id, {"body": new_body})

        try:
            from src.handlers.core import _schedule_joplin_sync

            _schedule_joplin_sync()
        except Exception as exc:
            logger.debug("Could not schedule sync after stoic image: %s", exc)

        await img_msg.edit_text("✅ 已将图像添加到您的斯多葛笔记中。")
    except Exception as exc:
        logger.warning("Stoic image generation failed: %s", exc)
        with contextlib.suppress(Exception):
            await message.reply_text("⚠️ 无法为此反思生成图像。")
    finally:
        task = _pending_stoic_image_tasks.get(user_id)
        if task and task.done():
            _pending_stoic_image_tasks.pop(user_id, None)


# ---------------------------------------------------------------------------
# Apply replace / append actions (duplicate detection)
# ---------------------------------------------------------------------------

async def _apply_replace_action(orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]) -> bool:
    if state.get("pending_action") != "duplicate_detected":
        await message.reply_text("❌ 没有待处理的重复操作。使用 /stoic_done 保存您的反思。")
        return False
    note_id = state.get("existing_note_id")
    existing_body = state.get("existing_body", "")
    new_section = state.get("new_section_content", "")
    mode = state.get("mode", "morning")
    if not note_id or not new_section:
        await message.reply_text("❌ 缺少必要信息。请重试。")
        return False
    try:
        new_body = _replace_section(existing_body, new_section, mode)
        await orch.joplin_client.update_note(note_id, {"body": new_body})
        state.pop("pending_action", None)
        state.pop("existing_note_id", None)
        state.pop("existing_body", None)
        state.pop("new_section_content", None)
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(f"✅ 已替换 {mode} 反思。")
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
        except Exception as exc:
            logger.debug("Could not schedule sync: %s", exc)
        answers = state.get("answers", [])
        # US-061: add image after reflection is finalized
        _pending_stoic_image_tasks[user_id] = asyncio.create_task(
            _add_stoic_image_async(
                orch, user_id, note_id, mode, new_section, message
            )
        )
        await _create_tomorrow_task_from_stoic(orch, user_id, mode, answers, message)
        return True
    except Exception as exc:
        logger.error("Failed to replace stoic section: %s", exc)
        await message.reply_text("❌ 替换反思失败。")
        return False


async def _apply_append_action(orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]) -> bool:
    if state.get("pending_action") != "duplicate_detected":
        await message.reply_text("❌ 没有待处理的重复操作。使用 /stoic_done 保存您的反思。")
        return False
    note_id = state.get("existing_note_id")
    existing_body = state.get("existing_body", "")
    new_section = state.get("new_section_content", "")
    if not note_id or not new_section:
        await message.reply_text("❌ 缺少必要信息。请重试。")
        return False
    try:
        new_body = f"{existing_body}\n\n{new_section}"
        await orch.joplin_client.update_note(note_id, {"body": new_body})
        state.pop("pending_action", None)
        state.pop("existing_note_id", None)
        state.pop("existing_body", None)
        state.pop("new_section_content", None)
        orch.state_manager.update_state(user_id, state)
        await message.reply_text("✅ 已将反思附加到今天的笔记中。")
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
        except Exception as exc:
            logger.debug("Could not schedule sync: %s", exc)
        mode = state.get("mode", "morning")
        answers = state.get("answers", [])
        # US-061: add image after reflection is finalized
        _pending_stoic_image_tasks[user_id] = asyncio.create_task(
            _add_stoic_image_async(
                orch, user_id, note_id, mode, new_section, message
            )
        )
        await _create_tomorrow_task_from_stoic(orch, user_id, mode, answers, message)
        return True
    except Exception as exc:
        logger.error("Failed to append stoic section: %s", exc)
        await message.reply_text("❌ 附加反思失败。")
        return False


# ---------------------------------------------------------------------------
# Finish session (save to Joplin)
# ---------------------------------------------------------------------------

async def _finish_stoic_session(
    orch: TelegramOrchestrator, user_id: int, message: Message, state: dict[str, Any]
) -> bool:
    mode = state.get("mode", "morning")
    is_quick = state.get("is_quick", False)
    answers = state.get("answers", [])
    body_template = state.get("body_template") or ""
    if not body_template.strip():
        _, __, body_template = _load_stoic_template()

    date_str = get_current_date_str(user_id, orch.logging_service)
    title = f"{date_str} - 每日斯多葛反思"

    if not answers:
        await message.reply_text("没有要保存的答案。使用 /stoic_cancel 退出。")
        return False

    await message.reply_text("📝 正在格式化反思…")
    ts = get_user_timezone_aware_now(user_id, orch.logging_service).strftime("%H:%M")
    section_content: str | None = None
    try:
        section_content = await orch.llm_orchestrator.format_stoic_reflection(mode, answers, is_quick=is_quick, ts=ts)
    except Exception as exc:
        logger.debug("Stoic LLM format failed, using rule-based: %s", exc)
    if not section_content:
        if is_quick:
            section_content = _format_quick_morning(answers, user_id, orch) if mode == "morning" else _format_quick_evening(answers, user_id, orch)
        else:
            section_content = _format_section(mode, answers, user_id, orch)

    # Prepend check-in section if present
    mood = state.get("mood_checkin", "")
    energy = state.get("energy_level", "")
    checkin_block = ""
    if mood or energy:
        checkin_block = _format_checkin_section(mood, energy)

    await message.reply_text("📂 正在查找斯多葛日记文件夹…")
    try:
        folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
    except Exception as exc:
        logger.error("Stoic Journal folder resolution failed: %s", exc)
        await message.reply_text("❌ 无法找到或创建斯多葛日记文件夹。")
        return False

    notes_in_folder = await orch.joplin_client.get_notes_in_folder(folder_id)
    existing = next((n for n in notes_in_folder if n.get("title") == title), None)

    tags = STOIC_TAGS + [mode]
    # Apply learnings tags if "What I learned" was answered (evening only)
    if mode == "evening" and not is_quick:
        learned = _get_answer(answers, 8)
        if learned and learned.lower() not in ("-", "skip", ""):
            tags = tags + ["learnings", "content-ideas"]

    if existing:
        await message.reply_text("📎 正在更新今天的笔记…")
        note_id = existing["id"]
        try:
            full_note = await orch.joplin_client.get_note(note_id)
            existing_body = (full_note.get("body") or "").strip()
        except Exception as exc:
            logger.error("Failed to fetch existing note: %s", exc)
            await message.reply_text("❌ 无法获取现有笔记。请重试。")
            return False

        if _check_section_exists(existing_body, mode):
            await message.reply_text(
                f"⚠️ 您今天已经有一个 {mode.capitalize()} 反思。\n\n"
                f"  /stoic_replace — 替换现有反思\n"
                f"  /stoic_append — 向笔记添加另一个反思"
            )
            state["pending_action"] = "duplicate_detected"
            state["existing_note_id"] = note_id
            state["existing_body"] = existing_body
            state["new_section_content"] = section_content
            orch.state_manager.update_state(user_id, state)
            return False

        import re
        pattern = r"### 🌞 Morning.*?(?=\n### 🌙 Evening|$)" if mode == "morning" else r"### 🌙 Evening.*$"
        section_exists_empty = bool(re.search(pattern, existing_body, re.DOTALL))

        if section_exists_empty:
            new_body = _replace_section(existing_body, section_content, mode)
        else:
            new_body = f"{existing_body}\n\n{section_content}" if existing_body else section_content

        # Prepend check-in block if not already present
        if checkin_block and "## 🔎 签到" not in new_body:
            # Insert after the title line
            lines = new_body.split("\n", 2)
            if len(lines) >= 1:
                new_body = lines[0] + "\n\n" + checkin_block + "\n\n" + "\n".join(lines[1:])

        try:
            await orch.joplin_client.update_note(note_id, {"body": new_body})
        except Exception as exc:
            logger.error("Failed to update stoic note: %s", exc)
            await message.reply_text("❌ 更新今天的笔记失败。")
            return False
        await orch.joplin_client.apply_tags(note_id, tags)
        logger.info("Stoic save: updated note %s (%s mode)", note_id, mode)
        # US-061: generate image after finalizing note content
        _pending_stoic_image_tasks[user_id] = asyncio.create_task(
            _add_stoic_image_async(
                orch, user_id, note_id, mode, section_content, message
            )
        )
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
            await message.reply_text("🔄 正在同步，以便在您的设备上显示…")
        except Exception as exc:
            logger.debug("Could not schedule sync: %s", exc)
        await _create_tomorrow_task_from_stoic(orch, user_id, mode, answers, message)
        return True
    else:
        await message.reply_text("📄 正在创建新笔记…")
        morning_content = section_content if mode == "morning" else ""
        evening_content = section_content if mode == "evening" else ""
        full_body = _build_full_body(body_template, date_str, morning_content, evening_content)
        if checkin_block and "## 🔎 签到" not in full_body:
            lines = full_body.split("\n", 2)
            if len(lines) >= 1:
                full_body = lines[0] + "\n\n" + checkin_block + "\n\n" + "\n".join(lines[1:])
        try:
            note_id = await orch.joplin_client.create_note(folder_id=folder_id, title=title, body=full_body)
            await orch.joplin_client.apply_tags(note_id, tags)
        except Exception as exc:
            logger.error("Failed to create stoic note: %s", exc)
            await message.reply_text("❌ 在斯多葛日记中创建笔记失败。")
            return False
        logger.info("Stoic save: created note %s (%s mode)", note_id, mode)
        # US-061: generate image after finalizing note content
        _pending_stoic_image_tasks[user_id] = asyncio.create_task(
            _add_stoic_image_async(
                orch, user_id, note_id, mode, section_content, message
            )
        )
        try:
            from src.handlers.core import _schedule_joplin_sync
            _schedule_joplin_sync()
            await message.reply_text("🔄 正在同步，以便在您的设备上显示…")
        except Exception as exc:
            logger.debug("Could not schedule sync: %s", exc)
        await _create_tomorrow_task_from_stoic(orch, user_id, mode, answers, message)
        return True


# ---------------------------------------------------------------------------
# /stoic main handler (T-001, T-004, T-006 start)
# ---------------------------------------------------------------------------

def _stoic(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        mode = "morning"
        if context.args:
            arg = (context.args[0] or "").strip().lower()
            if arg in ("morning", "evening"):
                mode = arg

        state = orch.state_manager.get_state(user_id)
        if state and state.get("active_persona") == "STOIC_JOURNAL":
            await update.message.reply_text(
                "📓 您已经有一个斯多葛日记会话。\n\n"
                "选项：\n"
                "  继续回复更多答案\n"
                "  /stoic_done — 保存您的反思\n"
                "  /stoic_cancel — 取消并重新开始"
            )
            return

        morning_q, evening_q, body_tpl = _load_stoic_template()
        questions = morning_q if mode == "morning" else evening_q

        # For evening: prepend morning priorities to first question
        first_question = questions[0]
        if mode == "evening":
            try:
                date_str = get_current_date_str(user_id, orch.logging_service)
                title = f"{date_str} - 每日斯多葛反思"
                folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
                notes_in_folder = await orch.joplin_client.get_notes_in_folder(folder_id)
                existing = next((n for n in notes_in_folder if n.get("title") == title), None)
                if existing:
                    full_note = await orch.joplin_client.get_note(existing["id"])
                    body = full_note.get("body") or ""
                    priorities = _extract_morning_priorities(body)
                    if priorities:
                        priorities_text = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(priorities))
                        first_question = (
                            f"您今天的 3 个早晨优先事项是：\n{priorities_text}\n\n{first_question}"
                        )
            except Exception as exc:
                logger.debug("Could not fetch morning priorities for evening: %s", exc)

        session_start = get_user_timezone_aware_now(user_id, orch.logging_service)
        new_state: dict[str, Any] = {
            "active_persona": "STOIC_JOURNAL",
            "session_start": session_start.isoformat(),
            "mode": mode,
            "questions": questions,
            "answers": [],
            "body_template": body_tpl,
            "morning_questions": morning_q,
            "evening_questions": evening_q,
            "checkin_step": _CHECKIN_STEP_MOOD,
            "mood_checkin": "",
            "energy_level": "",
            "is_quick": False,
        }
        orch.state_manager.update_state(user_id, new_state)
        logger.info("User %s started Stoic journal (%s), %d questions", user_id, mode, len(questions))

        # Show quote + mood check-in
        quote = _daily_quote(mode)
        quote_block = f"_{quote}_\n\n" if quote else ""
        await update.message.reply_text(
            f"📓 *斯多葛日记 — {mode.capitalize()}*\n\n{quote_block}{_MOOD_QUESTION}",
            parse_mode="Markdown",
        )

    return handler


# ---------------------------------------------------------------------------
# /stoic quick handler (T-007)
# ---------------------------------------------------------------------------

def _stoic_quick(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if state and state.get("active_persona") == "STOIC_JOURNAL":
            await update.message.reply_text(
                "📓 您已经有一个斯多葛会话在运行。\n"
                "  /stoic_done — 保存它\n"
                "  /stoic_cancel — 放弃它"
            )
            return

        # Detect mode from args or time of day
        mode = "morning"
        if context.args:
            arg = (context.args[0] or "").strip().lower()
            if arg in ("morning", "evening"):
                mode = arg
        else:
            hour = get_user_timezone_aware_now(user_id, orch.logging_service).hour
            mode = "evening" if hour >= 17 else "morning"

        _, __, body_tpl = _load_stoic_template()
        quick_morning_q = ["您今天的意图是什么？", "您的 #1 优先事项是什么？"]
        quick_evening_q = ["今天的一件胜利是什么？", "您今天感恩什么？"]
        questions = quick_morning_q if mode == "morning" else quick_evening_q

        session_start = get_user_timezone_aware_now(user_id, orch.logging_service)
        new_state: dict[str, Any] = {
            "active_persona": "STOIC_JOURNAL",
            "session_start": session_start.isoformat(),
            "mode": mode,
            "questions": questions,
            "answers": [],
            "body_template": body_tpl,
            "is_quick": True,
            "checkin_step": _CHECKIN_DONE,  # No check-in for quick mode
            "mood_checkin": "",
            "energy_level": "",
        }
        orch.state_manager.update_state(user_id, new_state)
        logger.info("User %s started Stoic quick (%s)", user_id, mode)

        quote = _daily_quote(mode)
        quote_block = f"_{quote}_\n\n" if quote else ""
        await update.message.reply_text(
            f"⚡ *斯多葛快速 — {mode.capitalize()}* (2 个问题)\n\n{quote_block}{questions[0]}",
            parse_mode="Markdown",
        )

    return handler


# ---------------------------------------------------------------------------
# /stoic review — weekly synthesis (T-005)
# ---------------------------------------------------------------------------

def _stoic_review(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return

        await update.message.reply_text("📖 正在获取过去 7 天的斯多葛日记条目…")
        try:
            folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
            notes_in_folder = await orch.joplin_client.get_notes_in_folder(folder_id)
        except Exception as exc:
            logger.error("Could not fetch Stoic Journal folder: %s", exc)
            await update.message.reply_text("❌ 无法访问 Joplin 中的斯多葛日记。")
            return

        # Filter to past 7 days (exclude existing review notes)
        now_local = get_user_timezone_aware_now(user.id, orch.logging_service)
        cutoff = (now_local - timedelta(days=7)).date()
        daily_notes = [
            n for n in notes_in_folder
            if "斯多葛周报" not in n.get("title", "")
            and "每日斯多葛反思" in n.get("title", "")
        ]

        # Fetch bodies for recent notes
        recent: list[str] = []
        for note_meta in daily_notes[-10:]:  # fetch up to 10, filter by date
            try:
                full = await orch.joplin_client.get_note(note_meta["id"])
                title = full.get("title", "")
                # Parse date from title "YYYY-MM-DD - 每日斯多葛反思"
                date_part = title.split(" - ")[0].strip()
                try:
                    note_date = datetime.fromisoformat(date_part).date()
                    if note_date >= cutoff:
                        recent.append(f"## {title}\n\n{full.get('body', '')}")
                except ValueError:
                    pass
            except Exception:
                pass

        if len(recent) < 3:
            await update.message.reply_text(
                f"您本周有 {len(recent)} 条日记条目。"
                f"回顾需要至少 3 条以上。继续写日记，然后重试！"
            )
            return

        await update.message.reply_text(f"🧠 正在用 AI 综合 {len(recent)} 条条目…")
        combined = "\n\n---\n\n".join(recent)
        try:
            synthesis = await orch.llm_orchestrator.generate_stoic_weekly_review(combined)
        except Exception as exc:
            logger.error("Stoic weekly review LLM failed: %s", exc)
            await update.message.reply_text("❌ AI 综合失败。稍后重试。")
            return

        if not synthesis:
            await update.message.reply_text("❌ 无法生成综合。稍后重试。")
            return

        # Save review note
        week_label = now_local.strftime("%Y-W%W")
        review_title = f"{week_label} - 斯多葛周报"
        review_body = f"# {review_title}\n\n{synthesis}\n\n---\n*从 {len(recent)} 条日记条目生成。*"
        try:
            folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
            note_id = await orch.joplin_client.create_note(
                folder_id=folder_id, title=review_title, body=review_body
            )
            await orch.joplin_client.apply_tags(note_id, ["stoic", "journal", "weekly-review"])
        except Exception as exc:
            logger.warning("Could not save stoic review note: %s", exc)

        # Send to Telegram (truncate if needed)
        reply = f"📖 *斯多葛周报*\n\n{synthesis}"
        if len(reply) > 4000:
            reply = reply[:3990] + "…"
        await update.message.reply_text(reply, parse_mode="Markdown")

    return handler


# ---------------------------------------------------------------------------
# /stoic_cancel, /stoic_replace, /stoic_append
# ---------------------------------------------------------------------------

def _stoic_cancel(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return
        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text("没有活动的斯多葛日记会话。使用 /stoic 开始一个。")
            return
        orch.state_manager.clear_state(user_id)
        await update.message.reply_text(
            "❌ 斯多葛日记会话已取消。\n\n"
            "重新开始：/stoic、/stoic morning、/stoic evening 或 /stoic_quick"
        )
    return handler


def _stoic_replace(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return
        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text("❌ 没有带待处理重复项的活动斯多葛会话。")
            return
        saved = await _apply_replace_action(orch, user_id, update.message, state)
        if saved:
            streak = _update_streak(orch, user_id)
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                f"{_streak_message(streak, state.get('mode', 'morning'))}\n\n"
                f"它在 *领域 → 📓 日记 → 斯多葛日记* 中。\n\n记住你终将死亡。",
                parse_mode="Markdown",
            )
    return handler


def _stoic_append(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return
        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text("❌ 没有带待处理重复项的活动斯多葛会话。")
            return
        saved = await _apply_append_action(orch, user_id, update.message, state)
        if saved:
            streak = _update_streak(orch, user_id)
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                f"{_streak_message(streak, state.get('mode', 'morning'))}\n\n"
                f"它在 *领域 → 📓 日记 → 斯多葛日记* 中。\n\n记住你终将死亡。",
                parse_mode="Markdown",
            )
    return handler


# ---------------------------------------------------------------------------
# /stoic_done
# ---------------------------------------------------------------------------

def _stoic_done(orch: TelegramOrchestrator):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user or not check_whitelist(user.id):
            return
        if not update.message:
            return
        user_id = user.id
        state = orch.state_manager.get_state(user_id)
        if not state or state.get("active_persona") != "STOIC_JOURNAL":
            await update.message.reply_text("没有活动的斯多葛会话。使用 /stoic 或 /stoic_quick 开始。")
            return

        await update.message.reply_text("📓 正在保存到斯多葛日记…")
        saved = await _finish_stoic_session(orch, user_id, update.message, state)
        if saved:
            streak = _update_streak(orch, user_id)
            is_quick = state.get("is_quick", False)
            mode = state.get("mode", "morning")
            orch.state_manager.clear_state(user_id)
            await update.message.reply_text(
                f"{_streak_message(streak, mode, is_quick=is_quick)}\n\n"
                f"它在 *领域 → 📓 日记 → 斯多葛日记* 中。"
                f"如果您在 Mac 上看不到它，请运行 /sync。\n\n记住你终将死亡。",
                parse_mode="Markdown",
            )

    return handler


# ---------------------------------------------------------------------------
# handle_stoic_message — message routing during session (T-001 check-in phase)
# ---------------------------------------------------------------------------

async def handle_stoic_message(
    orch: TelegramOrchestrator, user_id: int, text: str, message: Message
) -> None:
    state = orch.state_manager.get_state(user_id)
    if not state or state.get("active_persona") != "STOIC_JOURNAL":
        return

    text_stripped = (text or "").strip()
    if text_stripped.lower() in ("done", "save", "finish", "完成", "保存"):
        await message.reply_text("使用 /stoic_done 保存您的反思。")
        return

    is_quick = state.get("is_quick", False)
    checkin_step = state.get("checkin_step", _CHECKIN_DONE)

    # --- Check-in phase (mood then energy) ---
    if checkin_step == _CHECKIN_STEP_MOOD:
        state["mood_checkin"] = text_stripped
        state["checkin_step"] = _CHECKIN_STEP_ENERGY
        orch.state_manager.update_state(user_id, state)
        await message.reply_text(
            _ENERGY_QUESTION,
            reply_markup=_quick_replies_for_question(_ENERGY_QUESTION),
        )
        return

    if checkin_step == _CHECKIN_STEP_ENERGY:
        state["energy_level"] = text_stripped[:10]  # cap length
        state["checkin_step"] = _CHECKIN_DONE
        orch.state_manager.update_state(user_id, state)
        # Transition to first real question
        mode = state.get("mode", "morning")
        morning_q, evening_q, body_tpl = _load_stoic_template()
        questions = morning_q if mode == "morning" else evening_q
        state["questions"] = questions
        state["body_template"] = body_tpl
        orch.state_manager.update_state(user_id, state)

        first_q = questions[0]
        if mode == "evening":
            # Try to prepend morning priorities
            try:
                date_str = get_current_date_str(user_id, orch.logging_service)
                title = f"{date_str} - 每日斯多葛反思"
                folder_id = await orch.joplin_client.get_or_create_folder_by_path(STOIC_JOURNAL_PATH)
                notes_in_folder = await orch.joplin_client.get_notes_in_folder(folder_id)
                existing = next((n for n in notes_in_folder if n.get("title") == title), None)
                if existing:
                    full_note = await orch.joplin_client.get_note(existing["id"])
                    body = full_note.get("body") or ""
                    priorities = _extract_morning_priorities(body)
                    if priorities:
                        priorities_text = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(priorities))
                        first_q = f"您今天的 3 个早晨优先事项是：\n{priorities_text}\n\n{first_q}"
            except Exception as exc:
                logger.debug("Could not fetch morning priorities: %s", exc)
        await message.reply_text(
            first_q,
            reply_markup=_quick_replies_for_question(first_q),
        )
        return

    # --- Main Q&A phase ---
    mode = state.get("mode", "morning")
    morning_q, evening_q, body_tpl = _load_stoic_template()
    questions = morning_q if mode == "morning" else evening_q
    if is_quick:
        questions = (
            ["您今天的意图是什么？", "您的 #1 优先事项是什么？"]
            if mode == "morning"
            else ["今天的一件胜利是什么？", "您今天感恩什么？"]
        )
    state["questions"] = questions
    state["body_template"] = body_tpl

    answers = list(state.get("answers", []))
    current_index = len(answers)
    question_text = questions[current_index] if current_index < len(questions) else "额外想法"
    answers.append({"q": question_text, "a": text_stripped})
    state["answers"] = answers
    orch.state_manager.update_state(user_id, state)

    next_index = len(answers)
    if next_index < len(questions):
        next_q = questions[next_index]
        await message.reply_text(
            next_q,
            reply_markup=_quick_replies_for_question(next_q),
        )
    else:
        await message.reply_text(
            "还有其他吗？回复更多，或使用 /stoic_done 保存到您的斯多葛日记。",
            reply_markup=_remove_keyboard(),
        )


# ---------------------------------------------------------------------------
# Register all handlers
# ---------------------------------------------------------------------------

def register_stoic_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    application.add_handler(CommandHandler("stoic", _stoic(orch)))
    application.add_handler(CommandHandler("stoic_done", _stoic_done(orch)))
    application.add_handler(CommandHandler("stoic_cancel", _stoic_cancel(orch)))
    application.add_handler(CommandHandler("stoic_replace", _stoic_replace(orch)))
    application.add_handler(CommandHandler("stoic_append", _stoic_append(orch)))
    application.add_handler(CommandHandler("stoic_quick", _stoic_quick(orch)))
    application.add_handler(CommandHandler("stoic_review", _stoic_review(orch)))
