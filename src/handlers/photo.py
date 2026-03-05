"""
Photo message handler: OCR capture via Gemini, save to Joplin with image attachment.

Sprint 11 Story 1 - FR-030.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from src.security_utils import (
    check_whitelist,
    format_error_message,
    format_success_message,
    handle_api_error,
)
from src.timezone_utils import get_user_timezone_aware_now

if TYPE_CHECKING:
    from src.telegram_orchestrator import TelegramOrchestrator

logger = logging.getLogger(__name__)


def _image_bytes_to_data_url(data: bytes, mime_type: str = "image/jpeg") -> str:
    """Convert image bytes to data URL for Joplin."""
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _build_photo_note_body(ocr_result: dict, user_id: int, orch: TelegramOrchestrator) -> str:
    """Build note body from OCR result."""
    now = get_user_timezone_aware_now(user_id, orch.logging_service)
    date_str = now.strftime("%Y-%m-%d")
    text = (ocr_result.get("text") or "").strip()
    summary = (ocr_result.get("summary") or "").strip()
    img_type = (ocr_result.get("type") or "other").replace("_", " ").title()
    structured = ocr_result.get("structured_data")

    lines = [
        "📷 *Captured from photo*",
        "",
        f"**Type:** {img_type}",
        "",
    ]
    if summary:
        lines.extend(["**Summary:**", summary, ""])
    if text:
        lines.extend(["## Extracted Text", "", text, ""])
    if structured and isinstance(structured, dict):
        lines.append("## Structured Data")
        for k, v in structured.items():
            if v is not None and str(v).strip():
                lines.append(f"- **{k}:** {v}")
        lines.append("")
    lines.append("---")
    lines.append(f"*Captured via photo on {date_str}*")
    return "\n".join(lines)


async def _handle_photo(orch: TelegramOrchestrator, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process photo: OCR, classify, create note with image."""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.photo:
        return

    user_id = user.id
    if not check_whitelist(user_id):
        await message.reply_text("❌ Sorry, you're not authorized to use this bot.")
        return

    caption = (message.caption or "").strip()
    photo = message.photo[-1]
    photo_file = await photo.get_file()
    image_bytes = await photo_file.download_as_bytearray()
    image_data = bytes(image_bytes)

    status_msg = await message.reply_text("🔍 Processing image...")
    try:
        await status_msg.edit_text("🔍 Extracting text...")
        from src.ocr_service import extract_text_from_image

        ocr_result = await extract_text_from_image(image_data)
        if not ocr_result:
            await status_msg.edit_text(
                "❌ OCR unavailable. Set GEMINI_API_KEY in your environment to enable photo capture."
            )
            return

        await status_msg.edit_text("🧠 Classifying content...")
        synthetic_message = (
            f"[Photo capture - {ocr_result.get('type', 'image')}]\n\n"
            f"Summary: {ocr_result.get('summary', '')}\n\n"
            f"Extracted text:\n{ocr_result.get('text', '')}"
        )
        if caption:
            synthetic_message = f"User caption: {caption}\n\n{synthetic_message}"

        llm_response = await orch.llm_orchestrator.process_message(synthetic_message)
        if not llm_response or llm_response.status == "ERROR":
            await status_msg.edit_text(
                format_error_message("Could not classify the image content. Please try again.")
            )
            return
        if llm_response.status == "NEED_INFO" and llm_response.question:
            await status_msg.edit_text(llm_response.question)
            return

        note_data = llm_response.note
        if not note_data:
            await status_msg.edit_text(format_error_message("No note data from classifier."))
            return

        title = (note_data.get("title") or ocr_result.get("suggested_title") or "Photo capture").strip()
        body = _build_photo_note_body(ocr_result, user_id, orch)
        note_data = dict(note_data)
        note_data["title"] = title
        note_data["body"] = body

        await status_msg.edit_text("📝 Creating note...")
        from src.handlers.core import create_note_in_joplin

        image_data_url = _image_bytes_to_data_url(image_data)
        result = await create_note_in_joplin(
            orch,
            note_data,
            url_context=None,
            message=status_msg,
            image_data_url=image_data_url,
        )

        if result and "error" not in result:
            folder_id = result.get("folder_id", "")
            folder_name = ""
            if folder_id:
                try:
                    folder = await orch.joplin_client.get_folder(folder_id)
                    folder_name = folder.get("title", "")
                except Exception:
                    pass
            img_type = (ocr_result.get("type") or "image").replace("_", " ").title()
            await status_msg.edit_text(
                format_success_message(
                    f"Saved: {title}\n📁 {folder_name or 'Joplin'}\n📷 {img_type} captured"
                )
            )
        elif result and result.get("error") == "folder_not_found":
            await status_msg.edit_text(
                format_error_message(
                    "Could not find folder. Try specifying a folder name in the caption."
                )
            )
        else:
            await status_msg.edit_text(format_error_message("Failed to create note in Joplin."))
    except Exception as exc:
        logger.error("Photo capture failed: %s", exc, exc_info=True)
        await status_msg.edit_text(format_error_message(handle_api_error(exc, "photo capture")))


def register_photo_handlers(application: Any, orch: TelegramOrchestrator) -> None:
    """Register photo message handler."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _handle_photo(orch, update, context)

    application.add_handler(MessageHandler(filters.PHOTO, handler))
    logger.info("Photo handlers registered")
