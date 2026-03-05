"""
Security and validation utilities.

Uses the new settings module and domain exceptions.
"""

from __future__ import annotations

import logging
import re

from src.constants import MESSAGE_MAX_LENGTH, NOTE_BODY_MAX_LENGTH, NOTE_TITLE_MAX_LENGTH, SANITIZE_MAX_LENGTH
from src.exceptions import AppError
from src.settings import get_settings

logger = logging.getLogger(__name__)


def check_whitelist(user_id: int) -> bool:
    allowed = get_settings().telegram.allowed_ids
    if not allowed:
        logger.warning("No allowed user IDs configured — allowing all users")
        return True

    ok = user_id in allowed
    if ok:
        logger.info("User %d is whitelisted", user_id)
    else:
        logger.warning("User %d denied — not whitelisted", user_id)
    return ok


def validate_message_text(text: str) -> str | None:
    if not text or not text.strip():
        return None
    text = text.strip()
    if len(text) > MESSAGE_MAX_LENGTH:
        logger.warning("Message too long: %d chars", len(text))
        return None
    return text


async def ping_joplin_api(base_url: str | None = None) -> bool:
    """Async health check for Joplin API."""
    import httpx

    from src.constants import JOPLIN_PING_TIMEOUT

    if base_url is None:
        base_url = get_settings().joplin.url

    try:
        async with httpx.AsyncClient(timeout=JOPLIN_PING_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/ping")
            ok = resp.status_code == 200
            if ok:
                logger.debug("Joplin API is accessible")
            else:
                logger.warning("Joplin API returned %d", resp.status_code)
            return ok
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Joplin API connection failed: %s", exc)
        return False


def sanitize_input(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    if len(text) > SANITIZE_MAX_LENGTH:
        text = text[:SANITIZE_MAX_LENGTH] + "..."
    return text.strip()


def log_user_action(user_id: int, action: str, details: dict | None = None) -> None:
    extra = f" - {details}" if details else ""
    logger.info("User %d: %s%s", user_id, action, extra)


def handle_api_error(error: Exception, context: str = "") -> str:
    """Return a user-friendly message for an API error."""
    if isinstance(error, AppError):
        return error.user_message

    name = type(error).__name__
    if "OpenAI" in name:
        return "The AI service isn't responding. Please try again in a moment."
    if "Timeout" in str(error):
        return "The request took too long. Please try again."
    if "Joplin" in context:
        return "I can't reach Joplin right now. Please check it's running."

    logger.error("Unhandled error in %s: %s", context, error)
    return "Something went wrong. Please try again."


def validate_note_data(note_data: dict) -> list[str]:
    errors: list[str] = []
    if not note_data.get("title"):
        errors.append("Note title is required")
    if not note_data.get("body"):
        errors.append("Note body is required")
    if not note_data.get("parent_id"):
        errors.append("Parent folder ID is required")
    if len(note_data.get("title", "")) > NOTE_TITLE_MAX_LENGTH:
        errors.append(f"Title too long (max {NOTE_TITLE_MAX_LENGTH})")
    if len(note_data.get("body", "")) > NOTE_BODY_MAX_LENGTH:
        errors.append(f"Body too long (max {NOTE_BODY_MAX_LENGTH:,})")
    return errors


def format_error_message(error: str) -> str:
    return f"❌ {error}"


def format_success_message(message: str) -> str:
    """Prepend check mark. Skips if message already starts with ✅ (BF-013)."""
    if message.strip().startswith("✅"):
        return message
    return f"✅ {message}"
