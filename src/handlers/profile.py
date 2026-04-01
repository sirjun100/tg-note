"""
Profile and AI Identity handlers. FR-038.

- /profile — show or set user profile (data/user_profile.md)
- /identity — show or set AI identity (data/ai_identity.md)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.security_utils import check_whitelist, format_error_message

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USER_PROFILE_PATH = DATA_DIR / "user_profile.md"
AI_IDENTITY_PATH = DATA_DIR / "ai_identity.md"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_user_profile() -> str:
    """Read user profile from data/user_profile.md."""
    if USER_PROFILE_PATH.exists():
        try:
            return USER_PROFILE_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("Failed to read user_profile.md: %s", e)
    return ""


def _write_user_profile(content: str) -> bool:
    """Write user profile to data/user_profile.md."""
    try:
        _ensure_data_dir()
        USER_PROFILE_PATH.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning("Failed to write user_profile.md: %s", e)
        return False


def _read_ai_identity_from_disk() -> str:
    """Read AI identity from data/ai_identity.md (user override)."""
    if AI_IDENTITY_PATH.exists():
        try:
            return AI_IDENTITY_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("Failed to read ai_identity.md: %s", e)
    return ""


def _write_ai_identity(content: str) -> bool:
    """Write AI identity to data/ai_identity.md."""
    try:
        _ensure_data_dir()
        AI_IDENTITY_PATH.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning("Failed to write ai_identity.md: %s", e)
        return False


def get_user_profile_context() -> str:
    """Return user profile content for LLM context injection. FR-038."""
    return _read_user_profile()


def register_profile_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register /profile and /identity command handlers."""

    async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        args = (context.args or []) if context else []
        if args and args[0].lower() == "set" and len(args) >= 2:
            content = " ".join(args[1:]).strip()
            if _write_user_profile(content):
                await msg.reply_text("✅ 个人资料已更新。AI 将在未来的消息中使用此上下文。")
            else:
                await msg.reply_text(format_error_message("保存个人资料失败。"))
            return

        profile = _read_user_profile()
        if not profile:
            await msg.reply_text(
                "📋 **用户个人资料**（空）\n\n"
                "设置您的个人资料，让 AI 了解您：\n"
                "• `/profile set <您的自我介绍>`\n\n"
                "包括：工作背景、偏好、目标、时区等。",
                parse_mode="Markdown",
            )
        else:
            preview = profile[:500] + "…" if len(profile) > 500 else profile
            await msg.reply_text(
                f"📋 **用户个人资料**\n\n{preview}\n\n"
                "使用 `/profile set <文本>` 更新。",
                parse_mode="Markdown",
            )

    async def identity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = update.message
        if not user or not msg:
            return
        if not check_whitelist(user.id):
            await msg.reply_text("❌ 抱歉，您没有使用此机器人的权限。")
            return

        args = (context.args or []) if context else []
        if args and args[0].lower() == "set" and len(args) >= 2:
            content = " ".join(args[1:]).strip()
            if _write_ai_identity(content):
                orch.llm_orchestrator.reload_ai_identity()
                await msg.reply_text("✅ AI 身份已更新。")
            else:
                await msg.reply_text(format_error_message("保存身份失败。"))
            return

        identity = _read_ai_identity_from_disk() or orch.llm_orchestrator._load_ai_identity()
        if not identity:
            await msg.reply_text(
                "🤖 **AI 身份**（使用默认）\n\n"
                "未设置自定义身份。使用 `/identity set <markdown>` 覆盖。",
                parse_mode="Markdown",
            )
        else:
            preview = identity[:500] + "…" if len(identity) > 500 else identity
            await msg.reply_text(
                f"🤖 **AI 身份**\n\n{preview}\n\n"
                "使用 `/identity set <markdown>` 更新。",
                parse_mode="Markdown",
            )

    application.add_handler(CommandHandler("profile", profile_cmd))
    application.add_handler(CommandHandler("about_me", profile_cmd))
    application.add_handler(CommandHandler("identity", identity_cmd))
    logger.info("Profile and identity handlers registered")
